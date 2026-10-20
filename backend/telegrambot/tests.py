"""
The bot, without Telegram: every outgoing call is recorded instead of sent, so
the whole conversation can be walked through offline.
"""
import json
import io
import os
import urllib.error
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from accounts.jwt_utils import encode_access_token
from accounts.models import User
from learning.models import DailyActivity, Lesson, Unit
from startup.models import CashFlowEntry

from . import handlers, nudges
from .models import TelegramDraft, TelegramLink, TelegramLinkCode

SECRET = "test-webhook-secret"
TOKEN = "123:test"
CHAT = 555001


class Recorder:
    """Stands in for the Telegram API and remembers what the bot tried to say."""

    def __init__(self):
        self.calls = []
        self.polls = 0  # poll ids are unique for good, not per test step

    def _result(self, method):
        # A photo answer carries the sizes Telegram stored, which is where the
        # reusable file_id comes from.
        message = {"message_id": len(self.calls)}
        if method == "sendPhoto":
            message["photo"] = [{"file_id": f"cached-{len(self.calls)}", "file_size": 1000}]
        if method == "sendSticker":
            message["sticker"] = {"file_id": f"sticker-{len(self.calls)}"}
        if method == "sendPoll":
            self.polls += 1
            message["poll"] = {"id": f"poll-{self.polls}"}
        return message

    def call(self, method, http_timeout=None, **params):
        self.calls.append((method, params))
        return self._result(method)

    def upload(self, method, *args, **fields):
        self.calls.append((method, fields))
        return self._result(method)

    def texts(self):
        return [p.get("text") or p.get("caption", "") for m, p in self.calls
                if m in ("sendMessage", "editMessageText", "sendPhoto", "editMessageCaption")]

    def last_keyboard(self):
        """Buttons of the last message that had any (uploads send them as JSON)."""
        for _method, params in reversed(self.calls):
            markup = params.get("reply_markup")
            if isinstance(markup, str):
                markup = json.loads(markup)
            if markup and "inline_keyboard" in markup:
                return markup["inline_keyboard"]
        return []


@override_settings(TELEGRAM_BOT_TOKEN=TOKEN, TELEGRAM_WEBHOOK_SECRET=SECRET)
class TelegramBotTests(TestCase):
    def setUp(self):
        cache.clear()
        self.update_id = 0
        self.user = User.objects.create_user(email="founder@example.test", password="Str0ng-Passphrase!")
        self.recorder = Recorder()
        patcher = patch("telegrambot.api.call", side_effect=self.recorder.call)
        patcher.start()
        self.addCleanup(patcher.stop)
        upload_patcher = patch("telegrambot.api.upload", side_effect=self.recorder.upload)
        upload_patcher.start()
        self.addCleanup(upload_patcher.stop)

    # ----- helpers -------------------------------------------------------
    def _next_id(self):
        self.update_id += 1
        return self.update_id

    def send(self, message, update_id=None):
        handlers.handle_update({"update_id": update_id or self._next_id(), "message": {
            "chat": {"id": CHAT, "type": "private"},
            "from": {"id": CHAT, "first_name": "Aziz", "language_code": "ru"},
            **message,
        }})

    def tap(self, data, update_id=None, photo=False):
        message = {"chat": {"id": CHAT, "type": "private"}, "message_id": 7}
        if photo:
            message["photo"] = [{"file_id": "a-chart"}]
        handlers.handle_update({"update_id": update_id or self._next_id(), "callback_query": {
            "id": "cb",
            "data": data,
            "message": message,
        }})

    def poll_answer(self, poll_id, option, user_id=CHAT, update_id=None):
        handlers.handle_update({"update_id": update_id or self._next_id(), "poll_answer": {
            "poll_id": poll_id, "user": {"id": user_id, "first_name": "Aziz"}, "option_ids": [option],
        }})

    def sent(self, method):
        return [params for name, params in self.recorder.calls if name == method]

    def buttons(self):
        return [button.get("callback_data") for row in self.recorder.last_keyboard() for button in row]

    def link_chat(self):
        code = TelegramLinkCode.objects.create(
            user=self.user, code="ABC12345", expires_at=timezone.now() + timedelta(minutes=15)
        )
        self.send({"text": f"/start {code.code}"})
        return TelegramLink.objects.get(chat_id=CHAT)

    # ----- linking -------------------------------------------------------
    def test_a_stranger_is_asked_to_link_first(self):
        self.send({"text": "сколько я потратил?"})
        self.assertIn("Настройки", " ".join(self.recorder.texts()))
        self.assertFalse(TelegramLink.objects.exists())

    def test_a_code_links_once_and_only_once(self):
        link = self.link_chat()
        self.assertEqual(link.user, self.user)
        # The same code cannot link a second chat.
        self.recorder.calls.clear()
        TelegramLink.objects.all().delete()
        self.send({"text": "/start ABC12345"})
        self.assertFalse(TelegramLink.objects.exists())
        self.assertIn("Код не подошёл", " ".join(self.recorder.texts()))

    def test_an_expired_code_is_refused(self):
        TelegramLinkCode.objects.create(
            user=self.user, code="OLD12345", expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.send({"text": "/start OLD12345"})
        self.assertFalse(TelegramLink.objects.exists())

    def test_stop_asks_before_unlinking(self):
        self.link_chat()
        self.send({"text": "/stop"})
        self.assertTrue(TelegramLink.objects.exists())  # it asks first

        self.tap("stop:no")
        self.assertTrue(TelegramLink.objects.exists())
        self.tap("stop:yes")
        self.assertFalse(TelegramLink.objects.exists())

    # ----- money ---------------------------------------------------------
    def test_a_typed_entry_is_saved_without_asking_the_model(self):
        self.link_chat()
        self.send({"text": "-50 000 мука"})
        entry = CashFlowEntry.objects.get(user=self.user)
        self.assertEqual((entry.entry_type, int(entry.amount), entry.category), ("spending", 50000, "мука"))
        self.assertIn("Записал", " ".join(self.recorder.texts()))

    def test_thousands_shorthand_and_income(self):
        self.link_chat()
        self.send({"text": "+300к выручка"})
        entry = CashFlowEntry.objects.get(user=self.user)
        self.assertEqual((entry.entry_type, int(entry.amount)), ("revenue", 300000))

    def test_an_entry_written_in_words_is_saved(self):
        """"Доход 300 тысяч" is how people actually write it — no sign in sight."""
        self.link_chat()
        self.send({"text": "доход 300 тысяч"})
        entry = CashFlowEntry.objects.get(user=self.user)
        self.assertEqual((entry.entry_type, int(entry.amount)), ("revenue", 300000))

    def test_a_bare_number_is_asked_about_before_it_is_written(self):
        link = self.link_chat()
        self.send({"text": "1 200 000 оборудование"})
        self.assertFalse(CashFlowEntry.objects.exists())  # guessing would book a wrong figure
        self.assertIn("расход или доход", " ".join(self.recorder.texts()).lower())

        key = TelegramDraft.objects.get(link=link).key
        self.tap(f"kind:{key}:spending")
        entry = CashFlowEntry.objects.get(user=self.user)
        self.assertEqual((entry.entry_type, int(entry.amount), entry.category),
                         ("spending", 1200000, "Оборудование"))

    def test_a_question_is_not_mistaken_for_an_entry(self):
        self.link_chat()
        with patch("telegrambot.handlers._on_question") as asked:
            self.send({"text": "50 на 50 — это нормальная наценка?"})
        asked.assert_called_once()
        self.assertFalse(CashFlowEntry.objects.exists())

    def test_a_receipt_is_only_saved_after_the_tap(self):
        link = self.link_chat()
        draft = {
            "kind": "spending", "amount": 84500.0, "currency": "UZS", "category": "Сырьё и товары",
            "description": "Korzinka", "date": timezone.localdate().isoformat(), "confidence": 0.9,
            "note": "Похоже на закупку продуктов.",
        }
        with patch("telegrambot.handlers._download", return_value=b"jpeg"), \
             patch("telegrambot.brain.read_receipt", return_value=draft):
            self.send({"photo": [{"file_id": "small", "file_size": 100}, {"file_id": "big", "file_size": 900}]})

        self.assertFalse(CashFlowEntry.objects.exists())  # nothing yet — it only asked
        self.assertIn("84 500", " ".join(self.recorder.texts()))
        key = TelegramDraft.objects.get(link=link).key

        self.tap(f"save:{key}")
        entry = CashFlowEntry.objects.get(user=self.user)
        self.assertEqual(int(entry.amount), 84500)
        self.assertEqual(entry.category, "Сырьё и товары")
        # Tapping the same button again does not double the entry.
        self.tap(f"save:{key}", update_id=4242)
        self.assertEqual(CashFlowEntry.objects.count(), 1)

    def test_discarding_a_draft_writes_nothing(self):
        link = self.link_chat()
        draft = {"kind": "spending", "amount": 1000.0, "currency": "", "category": "Прочее",
                 "description": "", "date": timezone.localdate().isoformat(), "confidence": 0.4, "note": ""}
        with patch("telegrambot.handlers._download", return_value=b"jpeg"), \
             patch("telegrambot.brain.read_receipt", return_value=draft):
            self.send({"photo": [{"file_id": "big", "file_size": 900}]})
        self.tap(f"drop:{TelegramDraft.objects.get(link=link).key}")
        self.assertFalse(CashFlowEntry.objects.exists())

    def test_a_voice_note_about_money_becomes_a_draft(self):
        self.link_chat()
        heard = {"kind": "revenue", "amount": 120000.0, "currency": "", "category": "Продукты",
                 "description": "продажи за день", "date": timezone.localdate().isoformat(),
                 "confidence": 0.8, "note": "", "transcript": "сегодня продал на 120 тысяч"}
        with patch("telegrambot.handlers._download", return_value=b"ogg"), \
             patch("telegrambot.brain.read_voice", return_value=heard):
            self.send({"voice": {"file_id": "v1", "mime_type": "audio/ogg"}})
        self.assertIn("120 000", " ".join(self.recorder.texts()))
        self.assertTrue(TelegramDraft.objects.exists())

    def test_a_spoken_question_goes_to_the_advisor(self):
        self.link_chat()
        heard = {"kind": "question", "amount": 0.0, "currency": "", "category": "Прочее", "description": "",
                 "date": timezone.localdate().isoformat(), "confidence": 0.9, "note": "",
                 "transcript": "как считать себестоимость?"}
        with patch("telegrambot.handlers._download", return_value=b"ogg"), \
             patch("telegrambot.brain.read_voice", return_value=heard), \
             patch("telegrambot.handlers._on_question") as asked:
            self.send({"voice": {"file_id": "v1", "mime_type": "audio/ogg"}})
        asked.assert_called_once()

    def test_the_same_update_twice_is_handled_once(self):
        self.link_chat()
        self.send({"text": "-1000 такси"}, update_id=99)
        self.send({"text": "-1000 такси"}, update_id=99)
        self.assertEqual(CashFlowEntry.objects.count(), 1)

    # ----- the webhook door ---------------------------------------------
    def test_the_webhook_refuses_calls_without_the_secret(self):
        body = json.dumps({"update_id": 1, "message": {"chat": {"id": CHAT, "type": "private"}, "text": "/help"}})
        self.assertEqual(self.client.post("/api/telegram/webhook", body, "application/json").status_code, 403)
        ok = self.client.post(
            "/api/telegram/webhook", body, "application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=SECRET,
        )
        self.assertEqual(ok.status_code, 200)

    def test_the_app_hands_out_a_one_time_code(self):
        auth = {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(self.user, uuid.uuid4())}
        response = self.client.post("/api/telegram/link", **auth)
        payload = response.json()
        self.assertTrue(payload["deep_link"].endswith(payload["code"]))
        self.assertFalse(payload["linked"])
        self.send({"text": f"/start {payload['code']}"})
        self.assertTrue(self.client.get("/api/telegram/link", **auth).json()["linked"])

    # ----- nudges --------------------------------------------------------
    def _weekday_evening(self):
        """An evening that is not Sunday — Sunday is the weekly summary."""
        now = timezone.localtime().replace(hour=19, minute=0)
        return now - timedelta(days=1) if now.weekday() == 6 else now

    def _lesson(self):
        unit = Unit.objects.create(code="01", slug="basics", title="Basics", order=1)
        return Lesson.objects.create(unit=unit, slug="one", title="Первый урок", order=1, estimated_minutes=5)

    def test_no_nudge_on_a_day_that_was_already_used(self):
        link = self.link_chat()
        self._lesson()
        evening = self._weekday_evening()
        DailyActivity.objects.create(user=self.user, date=evening.date())
        self.recorder.calls.clear()
        self.assertEqual(nudges.send_for(link, evening), "")
        self.assertEqual(self.recorder.texts(), [])

    def test_a_nudge_offers_the_lesson_and_a_way_out(self):
        link = self.link_chat()
        self._lesson()
        self.recorder.calls.clear()
        now = self._weekday_evening()
        self.assertEqual(nudges.send_for(link, now), "nudge")
        buttons = [b["text"] for row in self.recorder.last_keyboard() for b in row]
        self.assertTrue(any("5 минут" in b for b in buttons))
        self.assertTrue(any("Не сегодня" in b for b in buttons))
        link.refresh_from_db()
        self.assertEqual(link.last_nudge_on, now.date())

        # Once a day, whatever else happens.
        self.recorder.calls.clear()
        self.assertEqual(nudges.send_for(link, now), "")

    def test_not_today_keeps_the_bear_quiet(self):
        link = self.link_chat()
        self.tap("nudge:skip")
        link.refresh_from_db()
        self.assertGreater(link.snooze_until, timezone.now())
        self.assertNotIn(link, list(nudges.due(timezone.localtime().replace(hour=link.nudge_hour))))

    def test_turning_nudges_off_is_one_tap(self):
        link = self.link_chat()
        self.tap("nudge:off")
        link.refresh_from_db()
        self.assertEqual(link.nudges, "off")
        self.assertEqual(list(nudges.due(timezone.localtime().replace(hour=link.nudge_hour))), [])

    # ----- the illustrated cards ----------------------------------------
    @patch.dict(os.environ, {"TELEGRAM_ILLUSTRATED_CARDS": "true"})
    def test_a_card_is_uploaded_once_and_then_reused(self):
        from telegrambot.models import TelegramAsset

        link = self.link_chat()
        self.recorder.calls.clear()
        self.send({"text": "/money"})
        # The first send uploads the picture and keeps the id Telegram returns.
        self.assertIn("sendPhoto", [m for m, _ in self.recorder.calls])
        asset = TelegramAsset.objects.get(key="money")
        self.assertTrue(asset.file_id)

        # Every visit keeps the banner, using Telegram's cached file ID.
        self.recorder.calls.clear()
        self.send({"text": "/money"})
        sent = [p for m, p in self.recorder.calls if m == "sendPhoto"]
        self.assertEqual(sent[0]["photo"], asset.file_id)

    def test_help_offers_a_button_for_every_skill(self):
        self.link_chat()
        self.recorder.calls.clear()
        self.send({"text": "/help"})
        data = [b.get("callback_data") for row in self.recorder.last_keyboard() for b in row]
        self.assertTrue({"show:receipt", "show:voice", "show:quick", "show:question"} <= set(data))

        self.recorder.calls.clear()
        self.tap("show:receipt")
        self.assertIn("Фото чека", " ".join(self.recorder.texts()))

    def test_a_saved_entry_can_be_taken_back(self):
        self.link_chat()
        self.send({"text": "-70000 такси"})
        entry = CashFlowEntry.objects.get(user=self.user)
        undo = [b for row in self.recorder.last_keyboard() for b in row if b["callback_data"].startswith("undo:")]
        self.assertTrue(undo)

        self.tap(undo[0]["callback_data"])
        self.assertFalse(CashFlowEntry.objects.filter(pk=entry.pk).exists())

    def test_start_and_link_are_single_messages(self):
        self.link_chat()
        self.assertEqual(len(self.recorder.texts()), 1)
        self.recorder.calls.clear()
        self.send({"text": "/start"})
        self.assertEqual(len(self.recorder.texts()), 1)
        self.assertIn("Главное меню", self.recorder.texts()[0])

    def test_plain_label_from_premium_reply_button_still_routes(self):
        self.link_chat()
        with patch("telegrambot.handlers._send_settings") as opened:
            self.send({"text": "Настройки"})
        opened.assert_called_once()

    def test_previous_money_menu_label_still_routes(self):
        self.link_chat()
        with patch("telegrambot.handlers._send_money") as opened:
            self.send({"text": "💰 Деньги"})
        opened.assert_called_once()

    def test_question_answer_escapes_model_html(self):
        from ai_engine.gemini import GeminiResult
        self.link_chat()
        self.recorder.calls.clear()
        with patch("telegrambot.brain.answer", return_value=GeminiResult("Цена < 100 & прибыль > 20. <b>Пример</b>", "test", 1, 1)):
            self.send({"text": "Как выбрать цену?"})
        text = self.recorder.texts()[-1]
        self.assertIn("&lt; 100 &amp;", text)
        self.assertIn("&lt;b&gt;Пример&lt;/b&gt;", text)
        self.assertEqual(self.recorder.calls[-1][0], "sendSticker")

    def test_provider_failure_replies_instead_of_going_silent(self):
        from ai_engine.gemini import GeminiError
        self.link_chat()
        self.recorder.calls.clear()
        with patch("telegrambot.brain.answer", side_effect=GeminiError("upstream failure")):
            self.send({"text": "Как выбрать цену?"})
        self.assertIn("Не удалось получить ответ", self.recorder.texts()[-1])
        self.assertNotIn("upstream failure", self.recorder.texts()[-1])

    def test_empty_answer_and_missing_key_reply(self):
        from ai_engine.gemini import GeminiResult
        self.link_chat()
        for stub in (True, False):
            with patch("telegrambot.brain.answer", return_value=GeminiResult("", "test", 0, 0, is_stub=stub)):
                self.send({"text": "Как выбрать цену?"})
            self.assertIn("Сейчас не могу ответить", self.recorder.texts()[-1])

    def test_stickers_are_sent_after_content_and_reuse_file_ids(self):
        from .models import TelegramAsset
        self.link_chat()
        self.recorder.calls.clear()
        self.send({"text": "/money"})
        self.assertEqual(self.recorder.calls[0][0], "sendPhoto")
        self.assertEqual(self.recorder.calls[-1][0], "sendSticker")
        asset = TelegramAsset.objects.get(key="sticker:coin")
        self.recorder.calls.clear()
        self.send({"text": "/money"})
        method, fields = self.recorder.calls[-1]
        self.assertEqual((method, fields["sticker"]), ("sendSticker", asset.file_id))
        self.assertTrue(fields["disable_notification"])

    def test_sticker_failure_does_not_undo_a_saved_entry(self):
        self.link_chat()
        with patch("telegrambot.api.send_sticker", side_effect=OSError("offline")):
            self.send({"text": "-2000 такси"})
        self.assertEqual(CashFlowEntry.objects.filter(user=self.user).count(), 1)
        self.assertIn("Записал", self.recorder.texts()[-1])

    @patch.dict(os.environ, {"TELEGRAM_ILLUSTRATED_CARDS": "false"})
    def test_settings_edit_the_same_text_card(self):
        self.link_chat()
        self.recorder.calls.clear()
        self.send({"text": "/settings"})
        self.assertNotIn("sendPhoto", [m for m, _ in self.recorder.calls])
        self.tap("nudge:off")
        edited = [p for m, p in self.recorder.calls if m == "editMessageText"][-1]
        self.assertIn("Выключены", edited["text"])
        self.assertNotIn(":00", edited["text"])
        self.assertFalse(any(b.get("callback_data", "").startswith("hour:") for row in edited["reply_markup"]["inline_keyboard"] for b in row))

    def test_settings_buttons_edit_caption_and_keep_the_banner(self):
        self.link_chat()
        self.send({"text": "/settings"})
        self.recorder.calls.clear()
        for action in ("hour:13", "nudge:off"):
            handlers.handle_update({"update_id": self._next_id(), "callback_query": {
                "id": "cb", "data": action,
                "message": {"chat": {"id": CHAT, "type": "private"}, "message_id": 7,
                            "photo": [{"file_id": "settings-banner"}]},
            }})
        edits = [p for m, p in self.recorder.calls if m == "editMessageCaption"]
        self.assertEqual(len(edits), 2)
        self.assertIn("13:00", edits[0]["caption"])
        self.assertIn("Выключены", edits[1]["caption"])
        self.assertNotIn("editMessageText", [m for m, _ in self.recorder.calls])
        self.assertTrue(all(p["message_id"] == 7 for p in edits))

    def test_welcome_banner_keeps_the_persistent_menu(self):
        self.link_chat()
        sent = [p for m, p in self.recorder.calls if m == "sendPhoto"][-1]
        markup = sent["reply_markup"]
        if isinstance(markup, str):
            markup = json.loads(markup)
        self.assertTrue(markup["is_persistent"])
        self.assertEqual(len(markup["keyboard"]), 3)

    def test_draft_escapes_text_and_keeps_uncertainty_warning(self):
        text = handlers._draft_text({"kind": "spending", "amount": 10, "currency": "UZS",
                                    "category": "A & B", "description": "<shop>",
                                    "date": "2026-09-21", "confidence": 0.2, "note": "redundant"}, "ru")
        self.assertIn("A &amp; B", text)
        self.assertIn("&lt;shop&gt;", text)
        self.assertIn("проверьте", text)
        self.assertNotIn("redundant", text)


    # ----- practice and "Up or down?" -------------------------------------
    def make_questions(self, count=3):
        from learning.models import DailyQuestion

        return [
            DailyQuestion.objects.create(
                slug=f"bot-q{i}", topic=DailyQuestion.Topic.RISK, answer=1,
                body={"ru": {"question": f"Вопрос {i}: S&P?", "options": ["а", "б", "в", "г"],
                             "explain": f"Потому что {i} & так далее"}},
            )
            for i in range(count)
        ]

    def make_episodes(self, count=4):
        from learning.models import MarketEpisode

        return [
            MarketEpisode.objects.create(
                slug=f"bot-e{i}", asset="S&P 500", before=[100 + j for j in range(10)],
                after=[120, 140] if i % 2 == 0 else [80, 60], direction="up" if i % 2 == 0 else "down", order=i,
                body={"ru": {"when": "март 2020", "headline": "Паника & распродажа", "question": "Куда дальше?",
                             "explain": "Страх прошёл", "lesson": "Не продавайте на панике"}},
            )
            for i in range(count)
        ]

    def test_quiz_is_a_native_poll_graded_once_when_its_learner_answers(self):
        from learning.models import PracticeAttempt
        from .models import TelegramQuiz

        self.make_questions()
        self.link_chat()
        self.recorder.calls.clear()
        self.send({"text": "/quiz"})
        poll = self.sent("sendPoll")[0]
        self.assertEqual((poll["type"], poll["is_anonymous"], poll["correct_option_id"]), ("quiz", False, 1))
        self.assertEqual([option["text"] for option in poll["options"]], ["а", "б", "в", "г"])
        self.assertTrue(poll["explanation"].startswith("Потому что"))
        quiz = TelegramQuiz.objects.get()

        self.recorder.calls.clear()
        self.poll_answer(quiz.poll_id, 0)
        attempt = PracticeAttempt.objects.get()
        self.assertEqual((attempt.source, attempt.correct, attempt.choice), ("bot", False, 0))
        text = self.recorder.texts()[-1]
        self.assertIn("Правильный ответ: <b>б</b>", text)
        self.assertIn("&amp; так далее", text)
        self.assertEqual(self.buttons(), [f"quizai:{quiz.question_id}", f"quiz:{quiz.question_id}"])

        # Delivered twice, or voted on by someone the poll was forwarded to: nothing changes.
        self.poll_answer(quiz.poll_id, 1)
        self.poll_answer(quiz.poll_id, 1, user_id=CHAT + 1)
        self.assertEqual(PracticeAttempt.objects.count(), 1)

        # "Next question" never brings back the one just answered.
        self.tap(f"quiz:{quiz.question_id}")
        self.assertNotEqual(TelegramQuiz.objects.exclude(pk=quiz.pk).get().question_id, quiz.question_id)

    def test_the_menu_buttons_open_both_games(self):
        self.make_questions(1)
        self.make_episodes(1)
        self.link_chat()
        self.recorder.calls.clear()
        self.send({"text": "🧠 Тренажёр"})
        self.assertEqual(len(self.sent("sendPoll")), 1)
        self.send({"text": "📈 Вверх или вниз"})
        self.assertIn("Паника &amp; распродажа", self.sent("sendPhoto")[-1]["caption"])

    def test_the_ai_explains_a_question_only_after_it_is_answered(self):
        from ai_engine.gemini import GeminiResult
        from .models import TelegramQuiz

        self.make_questions(1)
        self.link_chat()
        self.send({"text": "/quiz"})
        quiz = TelegramQuiz.objects.get()
        with patch("telegrambot.brain.answer", return_value=GeminiResult("Разбор <тут>", "test", 1, 1)) as ai:
            self.tap(f"quizai:{quiz.question_id}")
            ai.assert_not_called()  # before the answer it would give the answer away
            self.assertIn("Сначала ответьте", self.sent("answerCallbackQuery")[-1]["text"])

            self.poll_answer(quiz.poll_id, 3)
            self.tap(f"quizai:{quiz.question_id}")
            self.tap(f"quizai:{quiz.question_id}")  # a double tap asks once
        self.assertEqual(ai.call_count, 1)
        prompt = ai.call_args[0][1]
        self.assertIn("Правильный ответ: б", prompt)
        self.assertIn("Я ответил: г", prompt)
        self.assertIn("Разбор &lt;тут&gt;", self.recorder.texts()[-1])

    def test_a_round_hides_its_ending_and_a_right_call_pays_once(self):
        from learning.models import PredictionAttempt, UserStats

        first, *_rest = self.make_episodes()
        self.link_chat()
        self.recorder.calls.clear()
        self.send({"text": "/predict"})
        intro, question = self.sent("sendPhoto")[-2:]  # the rules, once, then the round
        self.assertIn("3 раунда в день", intro["caption"])
        self.assertIn("раунд 1 из 3", question["caption"])
        self.assertNotIn("Страх прошёл", question["caption"])
        self.assertEqual(self.buttons(), [f"pred:{first.id}:up", f"pred:{first.id}:down"])

        self.recorder.calls.clear()
        self.tap(f"pred:{first.id}:up", photo=True)
        self.assertEqual(UserStats.objects.get(user=self.user).coins, 5)
        self.assertEqual(PredictionAttempt.objects.get().source, "bot")
        frozen = self.sent("editMessageCaption")[0]
        self.assertIn("Ваш прогноз: <b>Вверх</b>", frozen["caption"])
        self.assertEqual(frozen["reply_markup"], {"inline_keyboard": []})
        reveal = self.sent("sendPhoto")[-1]
        self.assertIn("В точку!", reveal["caption"])
        self.assertIn("$109 → <b>$140</b> (+28%)", reveal["caption"])
        self.assertIn("Не продавайте на панике", reveal["caption"])
        self.assertEqual(self.buttons(), [f"predai:{first.id}", "pred:next"])

        self.tap(f"pred:{first.id}:down", photo=True)
        self.assertIn("уже сыгран", self.sent("answerCallbackQuery")[-1]["text"])
        self.assertEqual(UserStats.objects.get(user=self.user).coins, 5)

    def test_three_rounds_a_day_then_come_back_tomorrow(self):
        episodes = self.make_episodes()
        self.link_chat()
        for episode in episodes[:3]:
            self.tap(f"pred:{episode.id}:down", photo=True)
        self.assertEqual(self.buttons(), [f"predai:{episodes[2].id}", "quiz:new"])

        self.recorder.calls.clear()
        self.send({"text": "/predict"})
        self.assertIn("все 3 раунда сыграны", " ".join(self.recorder.texts()))
        self.assertNotIn("3 раунда в день", " ".join(self.recorder.texts()))  # no rules for a player
        self.tap(f"pred:{episodes[3].id}:down", photo=True)
        self.assertIn("закончились", self.sent("answerCallbackQuery")[-1]["text"])

    def test_the_ai_explains_a_round_only_after_it_is_played(self):
        from ai_engine.gemini import GeminiResult

        episode, *_rest = self.make_episodes(1)
        self.link_chat()
        with patch("telegrambot.brain.answer", return_value=GeminiResult("Паника прошла", "test", 1, 1)) as ai:
            self.tap(f"predai:{episode.id}")
            ai.assert_not_called()
            self.tap(f"pred:{episode.id}:down", photo=True)
            self.tap(f"predai:{episode.id}")
        prompt = ai.call_args[0][1]
        self.assertIn("пошла вверх: $109 → $140 (+28%)", prompt)
        self.assertIn("Паника прошла", self.recorder.texts()[-1])

    def test_quiz_answers_are_subscribed_to(self):
        from . import api

        api.get_updates(offset=1)
        api.set_webhook("https://example.test/hook", SECRET)
        for _method, params in self.recorder.calls[-2:]:
            self.assertIn("poll_answer", params["allowed_updates"])

@override_settings(TELEGRAM_BOT_TOKEN=TOKEN)
class TypedMoneyTests(SimpleTestCase):
    """The line between "book this" and "answer this" decides what lands in the books."""

    def test_the_ways_people_write_an_entry(self):
        from . import money
        cases = {
            "-50000 мука": ("spending", 50000.0),
            "-50 000 мука": ("spending", 50000.0),
            "+300к выручка": ("revenue", 300000.0),
            "доход 300 тысяяч": ("revenue", 300000.0),          # typo and all
            "потратил 50 тысяч на муку": ("spending", 50000.0),
            "заработал 1.5 млн": ("revenue", 1500000.0),
            "счет за интернет 89000": ("spending", 89000.0),
            "spent 45000 on flour": ("spending", 45000.0),
            "sotdim 200 ming": ("revenue", 200000.0),
            "1 200 000 оборудование": (None, 1200000.0),        # asks which way
            "300 тысяч": (None, 300000.0),
        }
        for text, (kind, amount) in cases.items():
            read = money.read(text)
            self.assertIsNotNone(read, text)
            self.assertEqual((read["kind"], read["amount"]), (kind, amount), text)

    def test_a_sentence_with_a_number_in_it_is_not_money(self):
        from . import money
        for text in ("У меня 3 сотрудника, что делать?", "Сколько я потратил?", "мне 25 лет",
                     "Что такое unit-экономика в 2026 году?", "Привет", "5 кг муки стоит сколько?"):
            self.assertIsNone(money.read(text), text)


class PremiumPresentationTests(SimpleTestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"TELEGRAM_PREMIUM_EMOJI": "true"})
        env.start()
        self.addCleanup(env.stop)
        mapping = patch("telegrambot.premium._map", return_value={"check": "123", "gear": "456"})
        mapping.start()
        self.addCleanup(mapping.stop)

    def test_every_icon_the_bot_writes_with_has_a_configured_id(self):
        """An icon added to PLAIN without an id silently loses its animation."""
        from . import premium
        configured = json.loads((Path(premium.__file__).parent / "premium_emoji.json").read_text(encoding="utf-8"))
        ids = {key: value for key, value in configured.items() if not key.startswith("_")}
        self.assertEqual(sorted(ids), sorted(premium.PLAIN), "premium_emoji.json and PLAIN disagree")
        for key, value in ids.items():
            self.assertRegex(value, r"^\d{10,25}$", f"{key} is not a custom_emoji_id")

    def test_html_decoration_is_idempotent_and_preserves_code_and_attributes(self):
        from . import premium
        source = '✅ <b>Saved</b> <code>✅ example</code> <a href="https://example.test/✅">link</a>'
        result = premium.decorate(source)
        self.assertEqual(premium.decorate(result), result)
        self.assertEqual(result.count("<tg-emoji"), 1)
        self.assertIn('<code>✅ example</code>', result)
        self.assertIn('href="https://example.test/✅"', result)

    def test_all_localized_menu_buttons_round_trip(self):
        from . import premium, texts
        for lang in texts.LANGS:
            source = texts.menu_keyboard(lang)
            rendered = premium.decorate_markup(source)
            for row in rendered["keyboard"]:
                for button in row:
                    self.assertTrue(texts.menu_command(button["text"]))
            self.assertEqual(source, texts.menu_keyboard(lang))

    def test_fallback_restores_readable_button_labels(self):
        from . import premium
        params = {"text": premium.decorate("✅ Saved"), "reply_markup": premium.decorate_markup({
            "inline_keyboard": [[{"text": "✅ Save", "callback_data": "save:test"}]]})}
        result = premium.plain_params(params)
        self.assertEqual(result["text"], "✅ Saved")
        button = result["reply_markup"]["inline_keyboard"][0][0]
        self.assertEqual(button["text"], "✅ Save")
        self.assertEqual(button["callback_data"], "save:test")
        self.assertEqual(button["style"], "success")
        self.assertIn("icon_custom_emoji_id", params["reply_markup"]["inline_keyboard"][0][0])

    def test_explicit_emoji_rejection_retries_once_without_premium(self):
        from . import api
        error = urllib.error.HTTPError("https://example.test", 400, "Bad Request", {}, io.BytesIO(b'CUSTOM_EMOJI_INVALID'))
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok": true, "result": {"message_id": 1}}'
        with patch("telegrambot.api.urllib.request.urlopen", side_effect=[error, response]) as opened:
            result = api.send_message(CHAT, "✅ Saved", keyboard=[[{"text": "✅ Save", "callback_data": "save:test"}]])
        self.assertEqual(result["message_id"], 1)
        self.assertEqual(opened.call_count, 2)
        retry = json.loads(opened.call_args.args[0].data)
        self.assertEqual(retry["text"], "✅ Saved")
        self.assertNotIn("icon_custom_emoji_id", retry["reply_markup"]["inline_keyboard"][0][0])

    def test_uncertain_network_failure_is_not_retried(self):
        from . import api
        with patch("telegrambot.api.urllib.request.urlopen", side_effect=TimeoutError("timeout")) as opened:
            self.assertIsNone(api.send_message(CHAT, "✅ Saved"))
        self.assertEqual(opened.call_count, 1)

    def test_uploaded_caption_falls_back_without_losing_buttons(self):
        from . import api, premium
        error = urllib.error.HTTPError("https://example.test", 400, "Bad Request", {}, io.BytesIO(b'CUSTOM_EMOJI_INVALID'))
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok": true, "result": {"message_id": 1}}'
        markup = premium.decorate_markup({"inline_keyboard": [[{"text": "✅ Save", "callback_data": "save:test"}]]})
        with patch("telegrambot.api.urllib.request.urlopen", side_effect=[error, response]) as opened:
            result = api.upload("sendPhoto", "photo", "test.jpg", b"jpeg", caption=premium.decorate("✅ Saved"), reply_markup=json.dumps(markup))
        self.assertEqual(result["message_id"], 1)
        body = opened.call_args.args[0].data.decode()
        self.assertNotIn("tg-emoji", body)
        self.assertNotIn("icon_custom_emoji_id", body)
        self.assertIn("save:test", body)

    def test_editing_without_buttons_clears_old_actions(self):
        from . import api
        with patch("telegrambot.api.call") as called:
            api.edit_message(CHAT, 7, "Cancelled")
        self.assertEqual(called.call_args.kwargs["reply_markup"], {"inline_keyboard": []})

    @patch.dict(os.environ, {"TELEGRAM_PREMIUM_EMOJI": "false"})
    def test_premium_can_be_disabled_without_losing_styles(self):
        from . import premium
        self.assertEqual(premium.decorate("✅ Saved"), "✅ Saved")
        rendered = premium.decorate_markup({"inline_keyboard": [[{"text": "✅ Save", "callback_data": "save:test"}]]})
        self.assertNotIn("icon_custom_emoji_id", rendered["inline_keyboard"][0][0])
        self.assertEqual(rendered["inline_keyboard"][0][0]["style"], "success")


@override_settings(GEMINI_MODEL_FLASH="gemini-2.5-flash", GEMINI_MODEL_PRO="gemini-2.5-pro")
class BotAIClientTests(SimpleTestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"TELEGRAM_AI_MODEL": "", "TELEGRAM_AI_TIMEOUT_SECONDS": "25"})
        env.start()
        self.addCleanup(env.stop)

    def test_bot_uses_flash_and_bounded_generation_but_logs_advisor_usage(self):
        from types import SimpleNamespace
        from . import brain
        client = MagicMock()
        client.models.generate_content.return_value = SimpleNamespace(
            text="Короткий ответ", usage_metadata=SimpleNamespace(prompt_token_count=12, candidates_token_count=20))
        with patch("telegrambot.brain.gemini._get_client", return_value=client), \
             patch("telegrambot.brain.consume_and_log") as consumed:
            result = brain.answer(SimpleNamespace(pk="test"), "Как считать прибыль?", "Demo", "ru")
        params = client.models.generate_content.call_args.kwargs
        self.assertEqual(params["model"], "gemini-2.5-flash")
        self.assertEqual(params["config"].http_options.timeout, 25000)
        self.assertEqual(params["config"].thinking_config.thinking_budget, 0)
        self.assertEqual(consumed.call_args.args[1], "ADVISOR")
        self.assertEqual((result.input_tokens, result.output_tokens), (12, 20))

    def test_receipt_generation_failure_does_not_charge_usage(self):
        from types import SimpleNamespace
        from . import brain
        client = MagicMock()
        client.models.generate_content.side_effect = TimeoutError("timeout")
        with patch("telegrambot.brain.gemini._get_client", return_value=client), \
             patch("telegrambot.brain.consume_and_log") as consumed:
            result = brain.read_receipt(SimpleNamespace(pk="test"), b"image", "image/jpeg")
        self.assertIsNone(result)
        consumed.assert_not_called()

    def test_missing_client_returns_unavailable_without_charging(self):
        from . import brain
        with patch("telegrambot.brain.gemini._get_client", return_value=None), \
             patch("telegrambot.brain.consume_and_log") as consumed:
            result = brain.answer(None, "Question", "Context")
        self.assertTrue(result.is_stub)
        consumed.assert_not_called()

    def test_custom_model_does_not_get_unsupported_thinking_options(self):
        from . import brain
        with patch.dict(os.environ, {"TELEGRAM_AI_MODEL": "another-model"}):
            self.assertIsNone(brain._config().thinking_config)
