"""
A thin Telegram Bot API client — plain urllib, no new dependency.

Every call is best-effort: the bot going quiet must never break a web request
or a management command, so failures are logged and reported as False/None
rather than raised. Timeouts are short for the same reason.
"""
import json
import logging
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
import uuid

from django.conf import settings

from . import premium

log = logging.getLogger("telegrambot")

BASE = "https://api.telegram.org"
TIMEOUT = 20
# poll_answer is how a tap on a quiz poll reaches us; without it in the list
# Telegram never sends one, to the webhook or to long polling alike.
UPDATES = ["message", "callback_query", "poll_answer"]


def enabled():
    return bool(settings.TELEGRAM_BOT_TOKEN)


def _url(method, file_path=None):
    if file_path:
        return f"{BASE}/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}"
    return f"{BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"


def call(method, http_timeout=TIMEOUT, _plain_retry=False, **params):
    """POST a JSON call. Returns the `result` payload, or None on any failure."""
    if not enabled():
        log.debug("telegram call skipped (no token): %s", method)
        return None
    body = json.dumps({k: v for k, v in params.items() if v is not None}).encode()
    request = urllib.request.Request(_url(method), data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=http_timeout) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:200]
        plain = premium.plain_params(params)
        if not _plain_retry and premium.is_rejection(exc.code, detail) and plain != params:
            return call(method, http_timeout=http_timeout, _plain_retry=True, **plain)
        log.warning("telegram %s failed: %s %s", method, exc.code, detail)
        return None
    except Exception as exc:  # noqa: BLE001 — network, DNS, timeouts
        log.warning("telegram %s failed: %s", method, exc)
        return None
    if not payload.get("ok"):
        plain = premium.plain_params(params)
        if not _plain_retry and premium.is_rejection(payload.get("error_code"), payload.get("description")) and plain != params:
            return call(method, http_timeout=http_timeout, _plain_retry=True, **plain)
        log.warning("telegram %s refused: %s", method, payload.get("description"))
        return None
    return payload.get("result")


def _multipart(fields, file_field, filename, content):
    """Encode one file upload without pulling in a dependency."""
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        if value is None:
            continue
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {mime}\r\n\r\n".encode()
    )
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def upload(method, file_field, filename, content, http_timeout=TIMEOUT, _plain_retry=False, **fields):
    if not enabled():
        return None
    data, content_type = _multipart(fields, file_field, filename, content)
    request = urllib.request.Request(_url(method), data=data, headers={"Content-Type": content_type})
    try:
        with urllib.request.urlopen(request, timeout=http_timeout) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:200]
        plain = premium.plain_params(fields)
        if not _plain_retry and premium.is_rejection(exc.code, detail) and plain != fields:
            return upload(method, file_field, filename, content, http_timeout=http_timeout, _plain_retry=True, **plain)
        log.warning("telegram %s upload failed: %s %s", method, exc.code, detail)
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning("telegram %s upload failed: %s", method, exc)
        return None
    if not payload.get("ok"):
        plain = premium.plain_params(fields)
        if not _plain_retry and premium.is_rejection(payload.get("error_code"), payload.get("description")) and plain != fields:
            return upload(method, file_field, filename, content, http_timeout=http_timeout, _plain_retry=True, **plain)
        return None
    return payload.get("result")


# --------------------------------------------------------------------------- #
# The handful of methods the bot actually uses
def send_message(chat_id, text, *, keyboard=None, markup=None, preview=False, reply_to=None):
    """`keyboard` = inline buttons under the message; `markup` = a full
    reply_markup (the persistent keyboard under the chat)."""
    return call(
        "sendMessage",
        chat_id=chat_id,
        text=premium.decorate(text),
        parse_mode="HTML",
        link_preview_options={"is_disabled": not preview},
        reply_markup=premium.decorate_markup(markup or ({"inline_keyboard": keyboard} if keyboard else None)),
        reply_to_message_id=reply_to,
    )


def edit_message(chat_id, message_id, text, *, keyboard=None):
    return call(
        "editMessageText",
        chat_id=chat_id,
        message_id=message_id,
        text=premium.decorate(text),
        parse_mode="HTML",
        reply_markup=premium.decorate_markup({"inline_keyboard": keyboard or []}),
    )


def edit_caption(chat_id, message_id, caption, *, keyboard=None):
    return call(
        "editMessageCaption",
        chat_id=chat_id,
        message_id=message_id,
        caption=premium.decorate(caption),
        parse_mode="HTML",
        reply_markup=premium.decorate_markup({"inline_keyboard": keyboard or []}),
    )


def send_photo(chat_id, file_id, *, caption="", keyboard=None, markup=None):
    """Send a photo Telegram already holds (a cached file_id)."""
    return call(
        "sendPhoto",
        chat_id=chat_id,
        photo=file_id,
        caption=premium.decorate(caption) or None,
        parse_mode="HTML" if caption else None,
        reply_markup=premium.decorate_markup(markup or ({"inline_keyboard": keyboard} if keyboard else None)),
    )


def _photo_fields(chat_id, caption, keyboard, markup):
    fields = {"chat_id": chat_id}
    if caption:
        fields["caption"] = premium.decorate(caption)
        fields["parse_mode"] = "HTML"
    reply_markup = markup or ({"inline_keyboard": keyboard} if keyboard else None)
    if reply_markup:
        fields["reply_markup"] = json.dumps(premium.decorate_markup(reply_markup))
    return fields


def upload_photo(chat_id, path, *, caption="", keyboard=None, markup=None):
    """First send of a card: upload the file itself."""
    try:
        content = path.read_bytes()
    except OSError:
        return None
    return upload("sendPhoto", "photo", path.name, content, **_photo_fields(chat_id, caption, keyboard, markup))


def send_photo_bytes(chat_id, content, filename, *, caption="", keyboard=None):
    """A picture drawn on the spot (the "Up or down?" charts): nothing cached to reuse."""
    return upload("sendPhoto", "photo", filename, content, **_photo_fields(chat_id, caption, keyboard, None))


def send_quiz(chat_id, question, options, correct, explanation=""):
    """
    A native quiz poll: Telegram marks the answer right or wrong on the spot and
    shows the explanation. Not anonymous — an anonymous poll never tells the
    bot who answered, and the answer has to reach the learner's progress.
    """
    return call(
        "sendPoll",
        chat_id=chat_id,
        question=question[:300],
        options=[{"text": option[:100]} for option in options],
        type="quiz",
        is_anonymous=False,
        correct_option_id=correct,
        explanation=explanation[:200] or None,
    )


def send_sticker(chat_id, path):
    """Send a bear sticker (a .webp from telegrambot/stickers)."""
    try:
        content = path.read_bytes()
    except OSError:
        return None
    return upload("sendSticker", "sticker", path.name, content, http_timeout=3,
                  chat_id=chat_id, disable_notification=True)


def answer_callback(callback_id, text=""):
    return call("answerCallbackQuery", callback_query_id=callback_id, text=text or None)


def send_chat_action(chat_id, action="typing"):
    return call("sendChatAction", http_timeout=5, chat_id=chat_id, action=action)


def get_file(file_id):
    return call("getFile", file_id=file_id)


def download(file_path, max_bytes):
    """Fetch a user's photo or voice note, refusing anything oversized."""
    if not enabled():
        return None
    try:
        with urllib.request.urlopen(_url(None, file_path=file_path), timeout=TIMEOUT) as response:
            length = int(response.headers.get("Content-Length") or 0)
            if length and length > max_bytes:
                log.info("telegram file too big: %s bytes", length)
                return None
            # Read one byte past the limit so a missing Content-Length cannot
            # be used to stream something enormous into memory.
            data = response.read(max_bytes + 1)
    except Exception as exc:  # noqa: BLE001
        log.warning("telegram download failed: %s", exc)
        return None
    return None if len(data) > max_bytes else data


def get_updates(offset=None, poll_seconds=25):
    """Long polling, for local development (see the telegram_poll command)."""
    return call(
        "getUpdates",
        http_timeout=poll_seconds + 10,
        offset=offset,
        timeout=poll_seconds,  # Telegram holds the connection open this long
        allowed_updates=UPDATES,
    )


def set_webhook(url, secret):
    return call(
        "setWebhook",
        url=url,
        secret_token=secret,
        allowed_updates=UPDATES,
        drop_pending_updates=True,
    )


def delete_webhook():
    return call("deleteWebhook", drop_pending_updates=False)


def webhook_info():
    return call("getWebhookInfo")


def set_commands(commands, language_code=None):
    return call("setMyCommands", commands=commands, language_code=language_code)


def set_description(text, short_text, language_code=None):
    ok = call("setMyDescription", description=text, language_code=language_code)
    return call("setMyShortDescription", short_description=short_text, language_code=language_code) and ok


def set_name(name, language_code=None):
    return call("setMyName", name=name, language_code=language_code)


def set_menu_button():
    """The button next to the message box opens the command list."""
    return call("setChatMenuButton", menu_button={"type": "commands"})


def me():
    return call("getMe")
