"""
Premium (custom) emoji.

Telegram lets a bot send emoji from a custom pack as
``<tg-emoji emoji-id="…">🐻</tg-emoji>``. The bot owner needs Premium (or an
eligible Fragment username); recipients do not need Premium to see them.

The ids belong to a specific pack, so they are configuration, not code: they
live in ``premium_emoji.json`` next to this file. With no file (or a missing
key) ``em()`` simply returns the plain emoji and nothing looks broken.

To fill it: send the emoji you want to the bot in one message prefixed with
/emoji — it answers with the ids, ready to paste.
"""
import json
import logging
import os
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

log = logging.getLogger("telegrambot")

FILE = Path(__file__).resolve().parent / "premium_emoji.json"


@lru_cache(maxsize=1)
def _map():
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError):
        log.warning("premium_emoji.json could not be read; using plain emoji")
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if str(v).isascii() and str(v).isdigit() and int(v) > 0}


def reload():
    _map.cache_clear()


# The plain emoji each name stands for. Messages are written with these, and
# decorate() swaps in the animated version wherever an id is configured — so
# nothing has to be rewritten when the pack changes.
PLAIN = {
    "bear": "🐻",
    "money": "💵",
    "book": "📚",
    "trophy": "🏆",
    "gear": "⚙️",
    "receipt": "🧾",
    "mic": "🎙",
    "pencil": "✍️",
    "chat": "💬",
    "fire": "🔥",
    "check": "✅",
    "chart": "📊",
    "camera": "📷",
    "link": "🔗",
    "bell": "🔔",
    "clock": "⏰",
    "play": "▶️",
    "info": "ℹ️",
    "tag": "🏷",
    "calendar": "🗓",
    "wallet": "👛",
    "wave": "👋",
    "handshake": "🤝",
    "telegram": "✈️",
    "income": "↗️",
    "expense": "↘️",
    "coin": "🪙",
    "moneybag": "💰",
    "target": "🎯",
    "undo": "↩️",
    "mute": "🔕",
    "warning": "⚠️",
    "gold": "🥇",
    "silver": "🥈",
    "bronze": "🥉",
}


def enabled():
    return os.environ.get("TELEGRAM_PREMIUM_EMOJI", "true").lower() not in ("0", "false", "off")


def em(key, fallback=""):
    """The custom emoji for `key`, or the plain one when it is not configured."""
    plain = fallback or PLAIN.get(key, "")
    emoji_id = _map().get(key) if enabled() else None
    if not emoji_id:
        return plain
    return f'<tg-emoji emoji-id="{emoji_id}">{plain}</tg-emoji>'


def decorate(text):
    """Decorate text nodes, preserving existing emoji, HTML attributes and code."""
    if not text or not enabled() or not _map():
        return text
    replacements = {}
    for key, plain in PLAIN.items():
        if _map().get(key):
            replacements[plain] = key
            replacements[plain.rstrip("\ufe0f") + "\ufe0f"] = key
    if not replacements:
        return text
    pattern = re.compile("|".join(re.escape(p) for p in sorted(replacements, key=len, reverse=True)))
    parts = re.split(r'(<tg-emoji\b[^>]*>.*?</tg-emoji>|<code\b[^>]*>.*?</code>|<pre\b[^>]*>.*?</pre>|<[^>]+>)', text, flags=re.S)
    return "".join(part if part.startswith("<") else pattern.sub(lambda m: em(replacements[m[0]], m[0]), part) for part in parts)


def decorate_markup(markup):
    """Native button icons and restrained semantic colours, without mutating callers."""
    if not markup:
        return markup
    result = deepcopy(markup)
    for field in ("inline_keyboard", "keyboard"):
        for row in result.get(field, []):
            for button in row:
                if not isinstance(button, dict):
                    continue
                label = button.get("text", "")
                if enabled():
                    for key, plain in PLAIN.items():
                        if label.startswith(plain) and _map().get(key):
                            button["icon_custom_emoji_id"] = _map()[key]
                            button["text"] = label[len(plain):].lstrip("\ufe0f ") or plain
                            break
                action = button.get("callback_data", "")
                if action.startswith("save:") or label.startswith("✓ "):
                    button.setdefault("style", "success")
                elif action == "stop:yes":
                    button.setdefault("style", "danger")
                elif button.get("url") or action in ("go:money", "show:quick"):
                    button.setdefault("style", "primary")
    return result


def plain_params(params):
    """Strip only premium decorations for a confirmed Telegram rejection retry."""
    result = deepcopy(params)
    for field in ("text", "caption"):
        if isinstance(result.get(field), str):
            result[field] = re.sub(r'<tg-emoji\b[^>]*>(.*?)</tg-emoji>', r'\1', result[field], flags=re.S)
    markup = result.get("reply_markup")
    encoded = isinstance(markup, str)
    if encoded:
        markup = json.loads(markup)
    if isinstance(markup, dict):
        reverse = {value: PLAIN[key] for key, value in _map().items() if key in PLAIN}
        for field in ("inline_keyboard", "keyboard"):
            for row in markup.get(field, []):
                for button in row:
                    if isinstance(button, dict):
                        icon = button.pop("icon_custom_emoji_id", None)
                        if icon in reverse:
                            button["text"] = reverse[icon] + " " + button["text"]
        result["reply_markup"] = json.dumps(markup) if encoded else markup
    return result


def is_rejection(code, description):
    detail = str(description).lower()
    return code == 400 and any(word in detail for word in ("emoji", "premium", "document_invalid"))


def ids_in(message):
    """[(emoji, id)] for the custom emoji inside one incoming message."""
    text = message.get("text") or message.get("caption") or ""
    entities = message.get("entities") or message.get("caption_entities") or []
    found = []
    # Telegram counts offsets in UTF-16 code units, so slice in that space.
    units = text.encode("utf-16-le")
    for entity in entities:
        if entity.get("type") != "custom_emoji":
            continue
        start, length = entity["offset"] * 2, entity["length"] * 2
        found.append((units[start : start + length].decode("utf-16-le"), str(entity.get("custom_emoji_id"))))
    return found
