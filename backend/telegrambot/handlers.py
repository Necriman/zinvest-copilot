"""
What the bot does with an update.

The shape of a conversation:
  photo / voice  → the bear reads it, shows a draft entry, waits for a tap
  "-50000 flour" → straight into the books, no model call, no waiting
  /quiz          → a question from the bank as a native quiz poll
  /predict       → a real market moment: up or down from here?
  anything else  → the advisor answers

Nothing is written without a tap on "Save", and nothing happens at all in a
chat that is not linked to an account.
"""
import logging
import re
import secrets
import uuid
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from html import escape

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from accounts import security
from config import languages
from learning import practice, predict
from learning import services as learning_services
from learning.models import DailyQuestion, MarketEpisode, PracticeAttempt, PredictionAttempt
from startup.models import CashFlowEntry, StartupProfile

from . import api, brain, cards, charts, money, premium, reactions, texts
from .models import TelegramDraft, TelegramLink, TelegramLinkCode, TelegramQuiz, TelegramUpdate

log = logging.getLogger("telegrambot")

MAX_MESSAGES_PER_MINUTE = 20
MAX_AI_PER_HOUR = 30  # photos, voice notes and questions together


# --------------------------------------------------------------------------- #
# Entry point
def handle_update(update):
    """One Telegram update. Safe to call twice with the same one."""
    update_id = update.get("update_id")
    if update_id is not None:
        try:
            with transaction.atomic():
                TelegramUpdate.objects.create(update_id=update_id)
        except IntegrityError:
            return  # Telegram retried something we already did
    # Lesson titles and other course words follow the chat's language, which
    # each handler switches to once it knows the chat; this puts it back after.
    token = languages.activate(languages.BASE)
    try:
        if "callback_query" in update:
            _on_callback(update["callback_query"])
        elif "message" in update:
            _on_message(update["message"])
        elif "poll_answer" in update:
            _on_poll_answer(update["poll_answer"])
    except Exception:  # noqa: BLE001 — one bad update must not stop the queue
        log.exception("telegram update failed: %s", update_id)
    finally:
        languages.deactivate(token)


def _chat_of(message):
    return (message.get("chat") or {}).get("id")


def _link_for(chat_id):
    # A switched-off or banned account is treated as no link at all.
    return TelegramLink.objects.filter(chat_id=chat_id, user__is_active=True).select_related("user").first()


def _lang_of(message, link=None):
    if link:
        return link.lang
    code = ((message.get("from") or {}).get("language_code") or "ru")[:2]
    return code if code in texts.LANGS else "ru"


def _say(chat_id, table, lang, keyboard=None, **kw):
    text = texts.pick(table, lang)
    sent = api.send_message(chat_id, text.format(**kw) if kw else text, keyboard=keyboard)
    if sent and table in (texts.NO_AI, texts.NO_AMOUNT, texts.BAD_CODE, texts.AI_ERROR):
        reactions.send(chat_id, "error")
    return sent


# --------------------------------------------------------------------------- #
# Messages
def _on_message(message):
    chat_id = _chat_of(message)
    if chat_id is None or (message.get("chat") or {}).get("type") != "private":
        return  # the bot is a one-to-one assistant, not a group member
    link = _link_for(chat_id)
    lang = _lang_of(message, link)
    languages.activate(lang)

    if not security.hit("tg-msg", chat_id, MAX_MESSAGES_PER_MINUTE, 60):
        _say(chat_id, texts.TOO_FAST, lang)
        return

    text = (message.get("text") or "").strip()
    if text.startswith("/"):
        _on_command(chat_id, text, link, lang, message)
        return
    if link is None:
        _say(chat_id, texts.NEED_LINK, lang)
        return

    link.last_seen_at = timezone.now()
    link.save(update_fields=["last_seen_at"])

    if message.get("photo"):
        _on_photo(link, message)
    elif message.get("voice") or message.get("audio"):
        _on_voice(link, message)
    elif text:
        tapped = texts.menu_command(text)
        if tapped:
            _on_command(chat_id, f"/{tapped}", link, link.lang, message)
            return
        entry = _quick_entry(text)
        if entry is None:
            _on_question(link, text)
        elif entry["kind"] is None:
            _ask_direction(link, entry)
        else:
            _save_entry(link, entry, announce=True)


def _on_command(chat_id, text, link, lang, message):
    command, _, argument = text.partition(" ")
    command = command.split("@")[0].lower()
    argument = argument.strip()

    if command == "/start":
        if link:
            _welcome_back(link)
            return
        if argument:
            _try_link(chat_id, argument, lang, message)
        else:
            cards.send(chat_id, "skills", caption=texts.pick(texts.HELLO, lang) + "\n\n" + texts.pick(texts.NEED_LINK, lang))
        return

    if link is None:
        _say(chat_id, texts.NEED_LINK, lang)
        return

    if command == "/emoji":
        # Hidden helper for whoever dresses the bot: send premium emoji with
        # /emoji and get their ids back, ready for premium_emoji.json.
        found = premium.ids_in(message)
        if not found:
            api.send_message(chat_id, "Пришлите премиум-эмодзи в одном сообщении с /emoji — отвечу их id.")
        else:
            lines = "\n".join(f"{emoji} <code>{emoji_id}</code>" for emoji, emoji_id in found)
            api.send_message(chat_id, f"<b>id этих эмодзи</b>\n{lines}")
        return

    if command == "/help":
        cards.send(chat_id, "commands", caption=texts.pick(texts.HELP, link.lang),
                   keyboard=_feature_keyboard(link.lang))
    elif command == "/today":
        _send_today(link)
    elif command in ("/money", "/cashflow"):
        _send_money(link)
    elif command in ("/quiz", "/practice"):
        _send_quiz(link, intro=True)
    elif command in ("/predict", "/game"):
        _send_predict(link)
    elif command == "/league":
        _send_league(link)
    elif command == "/settings":
        _send_settings(link)
    elif command == "/stop":
        cards.send(
            chat_id, "stop",
            caption=texts.pick(texts.STOP_CONFIRM, link.lang),
            keyboard=[
                [{"text": "🔗 " + texts.pick(texts.EXTRA["yes_unlink"], link.lang), "callback_data": "stop:yes"}],
                [{"text": texts.pick(texts.EXTRA["cancel"], link.lang), "callback_data": "stop:no"}],
            ],
        )
    else:
        cards.send(chat_id, "commands", caption=texts.pick(texts.HELP, link.lang),
                   keyboard=_feature_keyboard(link.lang))


def _feature_keyboard(lang):
    """The four things the bot can do, each behind its own illustrated card."""
    return [
        [
            {"text": "📷 " + texts.pick(texts.EXTRA["receipt"], lang), "callback_data": "show:receipt"},
            {"text": "🎙 " + texts.pick(texts.EXTRA["voice"], lang), "callback_data": "show:voice"},
        ],
        [
            {"text": "✍️ " + texts.pick(texts.EXTRA["quick"], lang), "callback_data": "show:quick"},
            {"text": "💬 " + texts.pick(texts.EXTRA["question"], lang), "callback_data": "show:question"},
        ],
        [{"text": texts.pick(texts.MENU["quiz"], lang), "callback_data": "go:quiz"},
         {"text": texts.pick(texts.MENU["predict"], lang), "callback_data": "go:predict"}],
        [{"text": "💵 " + texts.pick(texts.MENU["money"], lang).split(" ", 1)[-1], "callback_data": "go:money"},
         {"text": "📚 " + texts.pick(texts.MENU["today"], lang).split(" ", 1)[-1], "callback_data": "go:today"}],
    ]


def _welcome_back(link):
    """/start in a chat that is already linked: the menu, not the pitch again."""
    cards.send(link.chat_id, "commands", caption=texts.pick(texts.WELCOME_BACK, link.lang), markup=texts.menu_keyboard(link.lang))


def _try_link(chat_id, code, lang, message):
    """/start <code> — swallow a one-time code from the app."""
    if not security.hit("tg-link", chat_id, 5, 600):
        _say(chat_id, texts.TOO_FAST, lang)
        return
    with transaction.atomic():
        row = (
            TelegramLinkCode.objects.select_for_update()
            .filter(code=code[:16]).select_related("user").first()
        )
        if row is None or not row.is_usable or not row.user.is_active:
            _say(chat_id, texts.BAD_CODE, lang)
            return
        row.used_at = timezone.now()
        row.save(update_fields=["used_at"])
        sender = message.get("from") or {}
        # One account per chat, and one chat per account: re-linking replaces.
        TelegramLink.objects.filter(chat_id=chat_id).delete()
        TelegramLink.objects.filter(user=row.user).delete()
        link = TelegramLink.objects.create(
            user=row.user,
            chat_id=chat_id,
            username=(sender.get("username") or "")[:64],
            first_name=(sender.get("first_name") or "")[:64],
            lang=lang,
        )
    cards.send(chat_id, "skills", caption=texts.pick(texts.LINKED, link.lang).format(name=escape(link.first_name or "")),
               markup=texts.menu_keyboard(link.lang), scene="linked")


# --------------------------------------------------------------------------- #
# Money in
def _on_photo(link, message):
    if not _ai_allowed(link):
        return
    sizes = message.get("photo") or []
    largest = max(sizes, key=lambda s: s.get("file_size") or 0)
    api.send_chat_action(link.chat_id)
    data = _download(largest.get("file_id"))
    if data is None:
        _say(link.chat_id, texts.NO_AMOUNT, link.lang)
        return
    draft = brain.read_receipt(link.user, data, "image/jpeg", link.lang)
    _offer(link, draft, fallback=texts.NO_AI)


def _on_voice(link, message):
    if not _ai_allowed(link):
        return
    note = message.get("voice") or message.get("audio") or {}
    api.send_chat_action(link.chat_id)
    data = _download(note.get("file_id"))
    if data is None:
        _say(link.chat_id, texts.NO_AMOUNT, link.lang)
        return
    heard = brain.read_voice(link.user, data, note.get("mime_type") or "audio/ogg", link.lang)
    if heard is None:
        _say(link.chat_id, texts.NO_AI, link.lang)
        return
    if heard["kind"] == "question" or heard["amount"] <= 0:
        _on_question(link, heard.get("transcript") or heard.get("note") or "")
        return
    _offer(link, heard, fallback=texts.NO_AMOUNT)


def _download(file_id):
    if not file_id:
        return None
    info = api.get_file(file_id)
    if not info or not info.get("file_path"):
        return None
    return api.download(info["file_path"], settings.TELEGRAM_MAX_FILE_MB * 1024 * 1024)


def _ai_allowed(link):
    """A brake of its own for the calls that cost money, plus the app's own AI switch and allowance."""
    from adminpanel.models import PlatformSettings
    from ai_engine.models import UserAIQuota

    if not PlatformSettings.current().ai_enabled or not UserAIQuota.get_or_create_for(link.user).has_allowance():
        _say(link.chat_id, texts.NO_AI, link.lang)
        return False
    if security.hit("tg-ai", link.chat_id, MAX_AI_PER_HOUR, 3600):
        return True
    _say(link.chat_id, texts.TOO_FAST, link.lang)
    return False


def _known_category(label):
    """
    "аренду" → "Аренда", so the month view groups the entry with the rest.

    Only a strong match counts; anything else keeps the learner's own word,
    which is usually more useful than "Прочее".
    """
    stem = label.lower()[:5]
    if len(stem) < 4:
        return label
    for name in brain.CATEGORIES:
        if name.lower().startswith(stem) or stem.startswith(name.lower()[:5]):
            return name
    return label


def _quick_entry(text):
    """
    A typed entry → a draft, with no model call. See telegrambot.money for
    what counts as one. ``kind`` is None when the message does not say which
    way the money went; then the chat asks instead of guessing.
    """
    read = money.read(text)
    if read is None:
        return None
    return {
        "kind": read["kind"],
        "amount": read["amount"],
        "currency": "",
        "category": _known_category(read["category"]) or brain.CATEGORIES[-1],
        "description": "",
        "date": timezone.localdate().isoformat(),
        "confidence": 1.0,
        "note": "",
    }


def _money(value):
    return f"{int(round(float(value))):,}".replace(",", " ")


def _offer(link, draft, fallback):
    """Show what the bear read and wait for a tap."""
    if draft is None:
        _say(link.chat_id, fallback, link.lang)
        return
    if draft["amount"] <= 0:
        _say(link.chat_id, texts.NO_AMOUNT, link.lang)
        return

    key = secrets.token_urlsafe(6)[:12]
    TelegramDraft.objects.create(link=link, key=key, payload=draft)
    sent = api.send_message(link.chat_id, _draft_text(draft, link.lang), keyboard=_draft_keyboard(key, link.lang))
    if sent:
        reactions.send(link.chat_id, "draft")


def _draft_text(draft, lang):
    note = ""
    if draft.get("confidence", 1) < 0.6:
        note += texts.pick(texts.LOW_CONFIDENCE, lang)
    return texts.pick(texts.DRAFT, lang).format(
        icon="🧾" if draft["kind"] == "spending" else "💵",
        title=texts.pick(texts.DRAFT_TITLE[draft["kind"]], lang),
        amount=_money(draft["amount"]),
        currency=f" {escape(draft['currency'])}" if draft.get("currency") else "",
        category=f"🏷 {escape(draft['category'])}",
        description=f"\n{escape(draft['description'])}" if draft.get("description") else "",
        date=escape(_date_label(draft["date"], lang)),
        note=note,
    )


def _date_label(iso, lang):
    """Today and yesterday read better as words than as a date."""
    try:
        when = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso
    today = timezone.localdate()
    if when == today:
        return {"ru": "сегодня", "en": "today", "uz": "bugun"}.get(lang, "today")
    if when == today - timedelta(days=1):
        return {"ru": "вчера", "en": "yesterday", "uz": "kecha"}.get(lang, "yesterday")
    return when.strftime("%d.%m.%Y")


def _ask_direction(link, draft):
    """A number with nothing saying where it went: ask, never guess."""
    key = secrets.token_urlsafe(6)[:12]
    TelegramDraft.objects.create(link=link, key=key, payload=draft)
    api.send_message(
        link.chat_id,
        texts.pick(texts.WHICH_WAY, link.lang).format(
            amount=_money(draft["amount"]),
            category=escape(draft["category"]),
        ),
        keyboard=_direction_keyboard(key, link.lang),
    )


def _direction_keyboard(key, lang):
    return [
        [
            {"text": "↘️ " + texts.pick(texts.BTN["spending"], lang), "callback_data": f"kind:{key}:spending"},
            {"text": "↗️ " + texts.pick(texts.BTN["revenue"], lang), "callback_data": f"kind:{key}:revenue"},
        ],
        [{"text": "✕ " + texts.pick(texts.BTN["drop"], lang), "callback_data": f"drop:{key}"}],
    ]


def _draft_keyboard(key, lang):
    return [
        [{"text": "✅ " + texts.pick(texts.BTN["save"], lang), "callback_data": f"save:{key}"}],
        [
            {"text": "🏷 " + texts.pick(texts.BTN["category"], lang), "callback_data": f"cat:{key}"},
            {"text": "✕ " + texts.pick(texts.BTN["drop"], lang), "callback_data": f"drop:{key}"},
        ],
    ]


def _category_keyboard(key, lang):
    """Two columns — eleven categories in one column is a scroll, not a choice."""
    rows = [
        [
            {"text": name, "callback_data": f"set:{key}:{index + offset}"}
            for offset, name in enumerate(brain.CATEGORIES[index : index + 2])
        ]
        for index in range(0, len(brain.CATEGORIES), 2)
    ]
    rows.append([{"text": "← " + texts.pick(texts.BTN["back"], lang), "callback_data": f"back:{key}"}])
    return rows


def _save_entry(link, draft, announce=False, draft_row=None):
    """Write the entry the learner confirmed into the same table the app uses."""
    entry = _write_entry(link, draft, draft_row)
    if announce:
        sent = api.send_message(
            link.chat_id,
            texts.pick(texts.SAVED, link.lang).format(**_saved_context(link, draft)),
            keyboard=_saved_keyboard(link, entry),
        )
        if sent:
            reactions.send(link.chat_id, "saved")
    return entry


def _saved_keyboard(link, entry):
    """A written entry keeps an undo for as long as the message is on screen."""
    return [[
        {"text": "↩️ " + texts.pick(texts.EXTRA["undo"], link.lang), "callback_data": f"undo:{entry.pk}"},
        {"text": "💵 " + texts.pick(texts.EXTRA["month"], link.lang), "callback_data": "go:money"},
    ]]


@transaction.atomic
def _write_entry(link, draft, draft_row=None):
    entry = CashFlowEntry.objects.create(
        user=link.user,
        entry_type=CashFlowEntry.Type.REVENUE if draft["kind"] == "revenue" else CashFlowEntry.Type.SPENDING,
        category=(draft.get("category") or "Прочее")[:80],
        amount=Decimal(str(draft["amount"])),
        description=(draft.get("description") or "")[:200],
        occurred_on=date.fromisoformat(draft["date"]),
    )
    if draft_row is not None:
        draft_row.used_at = timezone.now()
        draft_row.save(update_fields=["used_at"])
    return entry


def _minutes_of(step):
    """How long the next node takes, for the "5 minutes" promise in a nudge."""
    if step.get("kind") == "lesson" and step.get("id"):
        from learning.models import Lesson

        lesson = Lesson.objects.filter(pk=step["id"]).only("estimated_minutes").first()
        if lesson:
            return lesson.estimated_minutes
    return 10 if step.get("kind") == "test" else 5


def _month_totals(user, today=None):
    today = today or timezone.localdate()
    first = today.replace(day=1)
    totals = CashFlowEntry.objects.filter(user=user, occurred_on__gte=first, occurred_on__lte=today).aggregate(
        income=Sum("amount", filter=Q(entry_type=CashFlowEntry.Type.REVENUE), default=Decimal("0")),
        spending=Sum("amount", filter=Q(entry_type=CashFlowEntry.Type.SPENDING), default=Decimal("0")),
        count=Count("pk"),
    )
    return {**totals, "total": totals["income"] - totals["spending"], "first": first}


def _saved_context(link, draft):
    totals = _month_totals(link.user)
    return {
        "kind": texts.pick(texts.KIND[draft["kind"]], link.lang),
        "amount": _money(draft["amount"]),
        "currency": f" {escape(draft['currency'])}" if draft.get("currency") else "",
        "category": f"🏷 {escape(draft.get('category') or '')}",
        "month": _month_label(totals["first"], link.lang),
        "income": _money(totals["income"]),
        "spending": _money(totals["spending"]),
        "total": _money(totals["total"]),
    }


MONTHS = {
    "ru": ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"],
    "uz": ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"],
}


def _month_label(day, lang):
    """Django's %B follows the server locale, which is rarely the reader's."""
    names = MONTHS.get(lang)
    return f"{names[day.month - 1]} {day.year}" if names else day.strftime("%B %Y")


def _top_spending(user, first, today, lang, limit=3):
    """The few categories that ate the most this month, as a short list."""
    rows = (
        CashFlowEntry.objects.filter(
            user=user, entry_type=CashFlowEntry.Type.SPENDING, occurred_on__gte=first, occurred_on__lte=today
        )
        .values("category").annotate(total=Sum("amount")).order_by("-total")[:limit]
    )
    if not rows:
        return ""
    lines = "\n".join(f"· {escape(row['category'])} — {_money(row['total'])}" for row in rows)
    return texts.pick(texts.MONEY_TOP, lang).format(rows=lines)


def _send_money(link):
    totals = _month_totals(link.user)
    month = _month_label(totals["first"], link.lang)
    keyboard = [
        [{"text": "📊 " + texts.pick(texts.BTN["open"], link.lang), "url": f"{settings.APP_ORIGIN}/app/cashflow"}],
        [
            {"text": "📚 " + texts.pick(texts.MENU["today"], link.lang).split(" ", 1)[-1], "callback_data": "go:today"},
            {"text": "🏆 " + texts.pick(texts.MENU["league"], link.lang).split(" ", 1)[-1], "callback_data": "go:league"},
        ],
    ]
    if not totals["count"]:
        cards.show(link, "money", texts.pick(texts.MONEY_EMPTY, link.lang).format(month=month),
                   keyboard=[[{"text": "📷 " + texts.pick(texts.EXTRA["receipt"], link.lang), "callback_data": "show:receipt"}]])
        return
    text = texts.pick(texts.MONEY, link.lang).format(
        month=month,
        income=_money(totals["income"]),
        spending=_money(totals["spending"]),
        total=_money(totals["total"]),
        top=_top_spending(link.user, totals["first"], timezone.localdate(), link.lang),
        count=totals["count"],
    )
    cards.show(link, "money", text, keyboard=keyboard)


# --------------------------------------------------------------------------- #
# Questions
def _on_question(link, question):
    if not question:
        return
    _ask_ai(link, question[:1000], _business_context)


def _business_context(link):
    profile = StartupProfile.objects.filter(user=link.user).first()
    totals = _month_totals(link.user)
    return (
        f"Business: {profile.name if profile else 'not set up yet'}"
        f"{', ' + profile.industry if profile and profile.industry else ''}. "
        f"This month: income {totals['income']}, spending {totals['spending']}."
    )


def _ask_ai(link, question, context, title=texts.ANSWER_TITLE, keyboard=None):
    """
    One question to the advisor, behind the brake for paid calls. `context`
    is a function of the link, so a refused call does not even read the books.
    """
    if not _ai_allowed(link):
        return
    api.send_chat_action(link.chat_id)
    try:
        result = brain.answer(link.user, question, context(link), link.lang)
    except Exception as exc:
        log.warning("bot question failed: %s", type(exc).__name__)
        _say(link.chat_id, texts.AI_ERROR, link.lang)
        return
    text = result.text.strip()
    if result.is_stub or not text:
        _say(link.chat_id, texts.NO_AI, link.lang)
        return
    # Model output is plain text, never trusted Telegram HTML. Split before
    # escaping so neither an entity nor a markup tag is cut in half.
    sent = api.send_message(
        link.chat_id, "💬 <b>" + texts.pick(title, link.lang) + "</b>\n\n" + escape(text[:3500]), keyboard=keyboard
    )
    if sent:
        reactions.send(link.chat_id, "answer")


# --------------------------------------------------------------------------- #
# Learning
def _send_today(link):
    step = learning_services.next_step_payload(link.user)
    stats = learning_services.get_or_create_stats(link.user)
    if not step or step.get("kind") == "done":
        cards.show(link, "today", texts.pick(texts.TODAY_DONE, link.lang).format(streak=stats.day_streak), scene="today_done")
        return
    text = texts.pick(texts.TODAY, link.lang).format(
        title=escape(step.get("title") or ""), minutes=_minutes_of(step), streak=stats.day_streak
    )
    cards.show(link, "today", text, keyboard=[
        [{"text": "▶️ " + texts.pick(texts.BTN["lesson"], link.lang), "url": _lesson_url(step)}],
        [
            {"text": "🏆 " + texts.pick(texts.MENU["league"], link.lang).split(" ", 1)[-1], "callback_data": "go:league"},
            {"text": "💵 " + texts.pick(texts.MENU["money"], link.lang).split(" ", 1)[-1], "callback_data": "go:money"},
        ],
    ])


def _lesson_url(step):
    if step and step.get("kind") == "test" and step.get("id"):
        return f"{settings.APP_ORIGIN}/learn/test/{step['id']}"
    if step and step.get("id"):
        return f"{settings.APP_ORIGIN}/learn/{step['id']}"
    return f"{settings.APP_ORIGIN}/app"


def _send_league(link):
    from learning import league as league_service

    seat, rows = league_service.standings(link.user)
    mine = next((r for r in rows if r["seat"].user_id == link.user.pk), None)
    rank = mine["rank"] if mine else len(rows)
    points = mine["points"] if mine else 0
    if rank <= league_service.PROMOTE:
        hint = texts.pick(texts.LEAGUE_HINT_UP, link.lang)
    elif len(rows) > league_service.PROMOTE and rank > len(rows) - league_service.DEMOTE:
        hint = texts.pick(texts.LEAGUE_HINT_DOWN, link.lang)
    else:
        gap = max(0, rows[league_service.PROMOTE - 1]["points"] - points + 1) if len(rows) >= league_service.PROMOTE else 0
        hint = texts.pick(texts.LEAGUE_HINT_MID, link.lang).format(gap=gap)
    text = texts.pick(texts.LEAGUE, link.lang).format(
        division=_division_label(seat.division, link.lang), rank=rank, total=len(rows), points=points,
        board=_mini_board(rows, link.user.pk), hint=hint,
    )
    cards.show(link, "league", text, keyboard=[
        [{"text": "🏆 " + texts.pick(texts.BTN["league"], link.lang), "url": f"{settings.APP_ORIGIN}/app/leaderboard"}],
        [
            {"text": "ℹ️ " + texts.pick(texts.EXTRA["rules"], link.lang), "callback_data": "go:rules"},
            {"text": "📚 " + texts.pick(texts.MENU["today"], link.lang).split(" ", 1)[-1], "callback_data": "go:today"},
        ],
    ])


DIVISION_NAMES = {
    "ru": {"bronze": "Бронза", "silver": "Серебро", "gold": "Золото", "platinum": "Платина", "diamond": "Алмаз"},
    "uz": {"bronze": "Bronza", "silver": "Kumush", "gold": "Oltin", "platinum": "Platina", "diamond": "Olmos"},
}


def _division_label(division, lang):
    return DIVISION_NAMES.get(lang, {}).get(division, division.title())


def _mini_board(rows, me_id, around=1):
    """The podium plus the neighbours — the whole group would be a wall of text."""
    from learning.league import display_name

    mine = next((r for r in rows if r["seat"].user_id == me_id), None)
    wanted = {r["rank"] for r in rows[:3]}
    if mine:
        wanted |= {mine["rank"] + step for step in range(-around, around + 1)}
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines, gap_shown = [], False
    for row in rows:
        if row["rank"] not in wanted:
            if not gap_shown and lines:
                lines.append("⋯")
                gap_shown = True
            continue
        gap_shown = False
        name = escape(display_name(row["seat"].user))
        label = medals.get(row["rank"], f"{row['rank']}.")
        line = f"{label} {name} — {row['points']}"
        lines.append(f"<b>{line}</b>" if row["seat"].user_id == me_id else line)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Practice (/quiz) and "Up or down?" (/predict)
#
# Both are the site's games, played in the chat: the same question bank and
# market episodes, graded by the same code, so a question answered here is
# one the site will not ask again and a round played here is gone there too.
GAME_CONTEXT = (
    "They are learning with Zinvest's practice questions and its 'Up or down?' game, "
    "which replays real moments of market history. Explain like a patient teacher."
)


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _option(options, index):
    return options[index] if isinstance(index, int) and 0 <= index < len(options) else ""


def _quiz_today(user, lang):
    """"Today: 3 of 4 right", once there is a today to speak of."""
    stats = practice.stats(user)
    if not stats["today"]:
        return ""
    return texts.pick(texts.QUIZ_TODAY, lang).format(correct=stats["today_correct"], total=stats["today"])


def _send_quiz(link, after=None, intro=False):
    """The next question from the bank, as a native quiz poll."""
    question = practice.next_question(link.user, link.lang, exclude=after)
    if question is None:
        _say(link.chat_id, texts.QUIZ_EMPTY, link.lang)
        return
    if intro:
        cards.show(link, "quiz", texts.pick(texts.QUIZ_INTRO, link.lang).format(
            count=DailyQuestion.objects.filter(active=True).count(), today=_quiz_today(link.user, link.lang),
        ))
    row = DailyQuestion.objects.get(pk=question["id"])
    sent = api.send_quiz(
        link.chat_id, question["question"], question["options"], row.answer, row.text(link.lang).get("explain", "")
    )
    poll_id = ((sent or {}).get("poll") or {}).get("id")
    if poll_id:
        TelegramQuiz.objects.create(poll_id=str(poll_id), link=link, question=row)


def _on_poll_answer(answer):
    """
    A tap on one of our quiz polls. Telegram has already shown right or wrong;
    this records it as the site would and offers the next step.
    """
    quiz = (
        TelegramQuiz.objects.select_related("link__user")
        .filter(poll_id=str(answer.get("poll_id") or "")).first()
    )
    if quiz is None:
        return
    link, chosen = quiz.link, answer.get("option_ids") or []
    languages.activate(link.lang)
    # A forwarded poll collects votes from anyone; only its own learner's count.
    if (answer.get("user") or {}).get("id") != link.chat_id or not chosen:
        return
    if not TelegramQuiz.objects.filter(pk=quiz.pk, answered=False).update(answered=True):
        return  # graded already
    result = practice.answer(link.user, quiz.question_id, chosen[0], link.lang, source=PracticeAttempt.Source.BOT)
    if result is None:
        return
    today = texts.pick(texts.QUIZ_TODAY, link.lang).format(
        correct=result["stats"]["today_correct"], total=result["stats"]["today"]
    )
    table = texts.QUIZ_RIGHT if result["correct"] else texts.QUIZ_WRONG
    api.send_message(
        link.chat_id,
        texts.pick(table, link.lang).format(
            answer=escape(_option(result["options"], result["answer"])), explain=escape(result["explain"]), today=today,
        ),
        keyboard=[[
            {"text": "🤖 " + texts.pick(texts.GAME_BTN["ask_ai"], link.lang), "callback_data": f"quizai:{result['id']}"},
            {"text": "➡️ " + texts.pick(texts.GAME_BTN["next_question"], link.lang), "callback_data": f"quiz:{result['id']}"},
        ]],
    )


def _change_suffix(episode):
    """" (+44%)" — or nothing when the price crossed zero and a percentage means nothing."""
    change = charts.change(episode.before[-1], episode.after[-1])
    return f" ({change})" if change else ""


def _round_caption(episode, lang, round_no):
    text = episode.text(lang)
    return texts.pick(texts.PREDICT_ROUND, lang).format(
        round=round_no, per_day=predict.ROUNDS_PER_DAY, asset=escape(episode.asset),
        when=escape(text.get("when", "")), headline=escape(text.get("headline", "")),
        question=escape(text.get("question", "")), coins=predict.COINS_RIGHT,
    )


def _send_picture(link, content, filename, caption, keyboard):
    """A drawn chart with its text; the text follows on its own when it is too long for a caption."""
    if len(caption) <= cards.CAPTION_LIMIT:
        sent = api.send_photo_bytes(link.chat_id, content, filename, caption=caption, keyboard=keyboard)
    else:
        sent = api.send_photo_bytes(link.chat_id, content, filename) and api.send_message(
            link.chat_id, caption, keyboard=keyboard
        )
    # Without the picture the round still has to be playable.
    return sent or api.send_message(link.chat_id, caption, keyboard=keyboard)


def _send_predict(link):
    """The next round: the chart up to the moment of the call, and two buttons."""
    state = predict.state(link.user, link.lang)
    if state["round"] is None:
        table = texts.PREDICT_LIMIT if state["remaining"] else texts.PREDICT_ALL_DONE
        cards.show(link, "predict", texts.pick(table, link.lang).format(per_day=state["rounds_per_day"], **state["stats"]),
                   keyboard=[[{"text": texts.pick(texts.MENU["quiz"], link.lang), "callback_data": "quiz:new"}]])
        return
    if not state["stats"]["played"]:
        cards.show(link, "predict", texts.pick(texts.PREDICT_INTRO, link.lang).format(
            per_day=state["rounds_per_day"], coins=predict.COINS_RIGHT,
        ))
    episode = MarketEpisode.objects.get(pk=state["round"]["id"])
    _send_picture(
        link, charts.question(episode.asset, episode.before, episode.unit), "round.png",
        _round_caption(episode, link.lang, state["rounds_per_day"] - state["left_today"] + 1),
        [[
            {"text": "📈 " + texts.pick(texts.GAME_BTN["up"], link.lang), "callback_data": f"pred:{episode.id}:up"},
            {"text": "📉 " + texts.pick(texts.GAME_BTN["down"], link.lang), "callback_data": f"pred:{episode.id}:down"},
        ]],
    )


def _on_predict_button(link, query, argument, message_id):
    episode_id, _, choice = argument.partition(":")
    if episode_id == "next":
        api.answer_callback(query.get("id"))
        _send_predict(link)
        return
    result, error = predict.answer(link.user, episode_id, choice, link.lang, source=PracticeAttempt.Source.BOT)
    if error:
        refused = texts.PREDICT_REFUSED.get(error)
        api.answer_callback(query.get("id"), texts.pick(refused, link.lang) if refused else "")
        return
    api.answer_callback(query.get("id"))
    episode = MarketEpisode.objects.get(pk=result["id"])
    lang = link.lang

    # The question stays in the chat with the call written under it; its buttons go.
    edit = api.edit_caption if (query.get("message") or {}).get("photo") else api.edit_message
    edit(link.chat_id, message_id, _round_caption(episode, lang, predict.ROUNDS_PER_DAY - result["left_today"])
         + "\n\n" + texts.pick(texts.PREDICT_CALL, lang).format(choice=texts.pick(texts.GAME_BTN[choice], lang)))

    stats = result["stats"]
    left = texts.pick(texts.PREDICT_LEFT, lang).format(left=result["left_today"]) if result["left_today"] else ""
    caption = texts.pick(texts.PREDICT_RIGHT if result["correct"] else texts.PREDICT_WRONG, lang).format(
        coins=result["coins"],
        direction=texts.pick(texts.DIRECTION[episode.direction], lang),
        asset=escape(episode.asset),
        start=escape(charts.price(episode.before[-1], episode.unit)),
        end=escape(charts.price(episode.after[-1], episode.unit)),
        change=_change_suffix(episode),
        explain=escape(result["explain"]),
        lesson=escape(result["lesson"]),
        stats=texts.pick(texts.PREDICT_STATS, lang).format(
            streak=stats["streak"], correct=stats["correct"], played=stats["played"], left=left
        ),
    )
    onward = (
        {"text": "➡️ " + texts.pick(texts.GAME_BTN["next_round"], lang), "callback_data": "pred:next"}
        if result["left_today"]
        else {"text": texts.pick(texts.MENU["quiz"], lang), "callback_data": "quiz:new"}
    )
    image = charts.reveal(episode.asset, episode.before, episode.after, episode.unit, episode.direction == "up")
    sent = _send_picture(link, image, "reveal.png", caption, [[
        {"text": "🤖 " + texts.pick(texts.GAME_BTN["ask_ai"], lang), "callback_data": f"predai:{episode.id}"},
        onward,
    ]])
    if sent and result["correct"]:
        reactions.send(link.chat_id, "predict_right")


def _on_explain_button(link, query, action, argument):
    """"Ask the AI" under an answer or a round."""
    asked = (_quiz_prompt if action == "quizai" else _round_prompt)(link, argument)
    if asked is None:
        api.answer_callback(query.get("id"), texts.pick(texts.ANSWER_FIRST, link.lang))
        return
    # A second tap while the first answer is on its way is the same question.
    fresh = security.hit("tg-explain", f"{link.chat_id}:{argument}", 1, 60)
    api.answer_callback(query.get("id"), texts.pick(texts.EXPLAINING, link.lang))
    if fresh:
        prompt, onward = asked
        _ask_ai(link, prompt, lambda _link: GAME_CONTEXT, title=texts.EXPLAIN_TITLE, keyboard=[[onward]])


def _quiz_prompt(link, question_id):
    """
    (prompt, next button) about a question the learner has answered — None
    before that, or the explanation would give the answer away.
    """
    pk = _uuid(question_id)
    attempt = (
        PracticeAttempt.objects.filter(user=link.user, question_id=pk).select_related("question")
        .order_by("-created_at").first() if pk else None
    )
    if attempt is None:
        return None
    text = attempt.question.text(link.lang)
    options = text.get("options", [])
    wrong = not attempt.correct and attempt.choice is not None  # None: the answer was looked up on the site
    chosen = texts.pick(texts.QUIZ_AI_CHOSEN, link.lang).format(chosen=_option(options, attempt.choice)) if wrong else ""
    prompt = texts.pick(texts.QUIZ_AI, link.lang).format(
        question=text.get("question", ""), options="; ".join(options),
        correct=_option(options, attempt.question.answer), chosen=chosen,
    )
    return prompt, {"text": "➡️ " + texts.pick(texts.GAME_BTN["next_question"], link.lang), "callback_data": f"quiz:{pk}"}


def _round_prompt(link, episode_id):
    """(prompt, next button) about a round the learner has played; None for one they have not."""
    pk = _uuid(episode_id)
    attempt = (
        PredictionAttempt.objects.filter(user=link.user, episode_id=pk).select_related("episode").first()
        if pk else None
    )
    if attempt is None:
        return None
    episode = attempt.episode
    text = episode.text(link.lang)
    prompt = texts.pick(texts.PREDICT_AI, link.lang).format(
        asset=episode.asset, when=text.get("when", ""), headline=text.get("headline", ""),
        direction=texts.pick(texts.DIRECTION[episode.direction], link.lang),
        start=charts.price(episode.before[-1], episode.unit), end=charts.price(episode.after[-1], episode.unit),
        change=_change_suffix(episode),
    )
    return prompt, {"text": "➡️ " + texts.pick(texts.GAME_BTN["next_round"], link.lang), "callback_data": "pred:next"}


# --------------------------------------------------------------------------- #
# Settings
def _send_settings(link):
    text = texts.pick(texts.SETTINGS_OFF if link.nudges == "off" else texts.SETTINGS, link.lang).format(
        mode=texts.pick(texts.MODES[link.nudges], link.lang), hour=link.nudge_hour
    )
    cards.show(link, "settings", text, keyboard=_settings_keyboard(link))


HOUR_CHOICES = (9, 13, 19, 21)


def _settings_keyboard(link):
    def mode_button(mode):
        mark = "✓ " if link.nudges == mode else ""
        return {"text": mark + texts.pick(texts.BTN[mode], link.lang), "callback_data": f"nudge:{mode}"}

    rows = [[mode_button("daily"), mode_button("weekly"), mode_button("off")]]
    if link.nudges != "off":
        rows.append([
            {"text": ("✓ " if link.nudge_hour == hour else "") + f"{hour}:00", "callback_data": f"hour:{hour}"}
            for hour in HOUR_CHOICES
        ])
    rows.append([{"text": "🔗 " + texts.pick(texts.EXTRA["unlink"], link.lang), "callback_data": "go:stop"}])
    return rows


# --------------------------------------------------------------------------- #
# Buttons
def _on_callback(query):
    data = query.get("data") or ""
    message = query.get("message") or {}
    chat_id = _chat_of(message)
    link = _link_for(chat_id) if chat_id else None
    if link is None:
        api.answer_callback(query.get("id"))
        return
    languages.activate(link.lang)
    if not security.hit("tg-msg", chat_id, MAX_MESSAGES_PER_MINUTE, 60):
        api.answer_callback(query.get("id"), texts.pick(texts.TOO_FAST, link.lang))
        return

    action, _, argument = data.partition(":")
    message_id = message.get("message_id")

    if action in ("save", "drop", "cat", "set", "back", "kind"):
        _on_draft_button(link, query, action, argument, message_id)
    elif action in ("nudge", "hour"):
        _on_nudge_button(link, query, f"{action}:{argument}", message_id)
    elif action == "show":
        _show_feature(link, argument)
        api.answer_callback(query.get("id"))
    elif action == "go":
        _go(link, argument, message_id)
        api.answer_callback(query.get("id"))
    elif action == "stop":
        _on_stop_button(link, query, argument, message_id)
    elif action == "undo":
        _undo_entry(link, query, argument, message_id)
    elif action == "quiz":
        api.answer_callback(query.get("id"))
        _send_quiz(link, after=argument)
    elif action == "pred":
        _on_predict_button(link, query, argument, message_id)
    elif action in ("quizai", "predai"):
        _on_explain_button(link, query, action, argument)
    else:
        api.answer_callback(query.get("id"))


def _show_feature(link, key):
    """One of the four illustrated "what I can do" screens."""
    if key == "help":
        cards.send(link.chat_id, "commands", caption=texts.pick(texts.HELP, link.lang),
                   keyboard=_feature_keyboard(link.lang))
        return
    table = texts.FEATURES.get(key)
    if table:
        cards.send(link.chat_id, key, caption=texts.pick(table, link.lang), keyboard=[[
            {"text": "← " + texts.pick(texts.BTN["back"], link.lang), "callback_data": "show:help"},
        ]])


def _go(link, where, message_id):
    """Cross-links between screens, so nothing is a dead end."""
    if where == "money":
        _send_money(link)
    elif where == "today":
        _send_today(link)
    elif where == "league":
        _send_league(link)
    elif where == "settings":
        _send_settings(link)
    elif where == "quiz":
        _send_quiz(link, intro=True)
    elif where == "predict":
        _send_predict(link)
    elif where == "rules":
        from learning import league as league_service

        api.send_message(link.chat_id, texts.pick(texts.LEAGUE_RULES, link.lang).format(
            lesson=league_service.POINTS_PER_LESSON,
            test=league_service.POINTS_PER_TEST,
            day=league_service.POINTS_PER_ACTIVE_DAY,
            promote=league_service.PROMOTE,
            demote=league_service.DEMOTE,
        ))
    elif where == "stop":
        cards.send(
            link.chat_id, "stop",
            caption=texts.pick(texts.STOP_CONFIRM, link.lang),
            keyboard=[
                [{"text": "🔗 " + texts.pick(texts.EXTRA["yes_unlink"], link.lang), "callback_data": "stop:yes"}],
                [{"text": texts.pick(texts.EXTRA["cancel"], link.lang), "callback_data": "stop:no"}],
            ],
        )


def _on_stop_button(link, query, argument, message_id):
    lang, chat_id = link.lang, link.chat_id
    if argument == "yes":
        link.delete()
        api.send_message(chat_id, texts.pick(texts.UNLINKED, lang))
        reactions.send(chat_id, "unlinked")
    api.answer_callback(query.get("id"))


def _undo_entry(link, query, entry_id, message_id):
    """Take back an entry that was just written — the misread receipt case."""
    removed = CashFlowEntry.objects.filter(pk=entry_id, user=link.user).delete()[0]
    if removed:
        api.edit_message(link.chat_id, message_id, texts.pick(texts.UNDONE, link.lang))
        reactions.send(link.chat_id, "undone")
    api.answer_callback(query.get("id"), texts.pick(texts.UNDONE, link.lang) if removed else "")


def _on_draft_button(link, query, action, argument, message_id):
    key, _, extra = argument.partition(":")
    row = TelegramDraft.objects.filter(link=link, key=key, used_at__isnull=True).first()
    if row is None:
        api.answer_callback(query.get("id"))
        return
    draft = row.payload

    if action == "drop":
        row.used_at = timezone.now()
        row.save(update_fields=["used_at"])
        api.edit_message(link.chat_id, message_id, texts.pick(texts.DROPPED, link.lang))
        reactions.send(link.chat_id, "dropped")
        api.answer_callback(query.get("id"))
        return

    if action == "kind":
        if extra not in ("spending", "revenue"):
            api.answer_callback(query.get("id"))
            return
        draft["kind"] = extra
        entry = _save_entry(link, draft, draft_row=row)
        api.edit_message(
            link.chat_id, message_id,
            texts.pick(texts.SAVED, link.lang).format(**_saved_context(link, draft)),
            keyboard=_saved_keyboard(link, entry),
        )
        reactions.send(link.chat_id, "saved")
        api.answer_callback(query.get("id"))
        return

    if action == "cat":
        api.edit_message(
            link.chat_id, message_id,
            texts.pick(texts.PICK_CATEGORY, link.lang).format(amount=_money(draft["amount"])),
            keyboard=_category_keyboard(key, link.lang),
        )
        api.answer_callback(query.get("id"))
        return

    if action == "back":
        api.edit_message(link.chat_id, message_id, _draft_text(draft, link.lang), keyboard=_draft_keyboard(key, link.lang))
        api.answer_callback(query.get("id"))
        return

    if action == "set":
        try:
            draft["category"] = brain.CATEGORIES[int(extra)]
        except (ValueError, IndexError):
            api.answer_callback(query.get("id"))
            return
        row.payload = draft
        row.save(update_fields=["payload"])
        api.edit_message(link.chat_id, message_id, _draft_text(draft, link.lang), keyboard=_draft_keyboard(key, link.lang))
        api.answer_callback(query.get("id"))
        return

    # save
    entry = _save_entry(link, draft, draft_row=row)
    api.edit_message(
        link.chat_id, message_id,
        texts.pick(texts.SAVED, link.lang).format(**_saved_context(link, draft)),
        keyboard=_saved_keyboard(link, entry),
    )
    reactions.send(link.chat_id, "saved")
    api.answer_callback(query.get("id"))


def _on_nudge_button(link, query, data, message_id):
    action, _, argument = data.partition(":")

    if action == "hour":
        try:
            hour = int(argument)
        except ValueError:
            api.answer_callback(query.get("id"))
            return
        link.nudge_hour = max(0, min(23, hour))
        link.save(update_fields=["nudge_hour"])
        api.answer_callback(query.get("id"), texts.pick(texts.SETTINGS_SAVED, link.lang))
        _refresh_settings(link, message_id, is_photo=bool((query.get("message") or {}).get("photo")))
        return

    if argument == "later":
        link.snooze_until = timezone.now() + timedelta(hours=1)
        link.save(update_fields=["snooze_until"])
        api.answer_callback(query.get("id"), texts.pick(texts.LATER, link.lang))
        reactions.send(link.chat_id, "later")
        return
    if argument == "skip":
        link.snooze_until = timezone.now() + timedelta(hours=14)
        link.save(update_fields=["snooze_until"])
        api.answer_callback(query.get("id"), texts.pick(texts.NOT_TODAY, link.lang))
        reactions.send(link.chat_id, "not_today")
        return
    if argument in ("daily", "weekly", "off"):
        link.nudges = argument
        link.save(update_fields=["nudges"])
        api.answer_callback(query.get("id"), texts.pick(texts.SETTINGS_SAVED, link.lang))
        _refresh_settings(link, message_id, is_photo=bool((query.get("message") or {}).get("photo")))
        return
    api.answer_callback(query.get("id"))


def _refresh_settings(link, message_id, is_photo=False):
    """Redraw the settings card in place after a tap."""
    edit = api.edit_caption if is_photo else api.edit_message
    edit(
        link.chat_id, message_id,
        texts.pick(texts.SETTINGS_OFF if link.nudges == "off" else texts.SETTINGS, link.lang).format(
            mode=texts.pick(texts.MODES[link.nudges], link.lang), hour=link.nudge_hour
        ),
        keyboard=_settings_keyboard(link),
    )
