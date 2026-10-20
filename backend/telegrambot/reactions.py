"""Bear stickers matched to each conversation, cached by Telegram file ID."""
import logging
import os
from pathlib import Path

from . import api
from .models import TelegramAsset

log = logging.getLogger("telegrambot")
FOLDER = Path(__file__).resolve().parent / "stickers"
SCENES = {
    "skills": "wave", "commands": "wave", "linked": "clap",
    "money": "coin", "quick": "coin", "saved": "happy",
    "receipt": "think", "draft": "think", "question": "think",
    "voice": "phone", "settings": "phone", "answer": "happy",
    "today": "book", "nudge": "book", "today_done": "celebrate",
    "league": "cheer", "weekly": "cheer", "milestone": "celebrate",
    "stop": "sleep", "unlinked": "sleep", "dropped": "sleep",
    "undone": "sleep", "error": "think", "rules": "book",
    "not_today": "sleep", "later": "sleep",
    "quiz": "think", "predict": "coin", "predict_right": "celebrate",
}


def send(chat_id, scene):
    """Decorations are best-effort and are sent after the useful response."""
    if os.environ.get("TELEGRAM_STICKERS", "true").lower() in ("0", "false", "off"):
        return None
    name = SCENES.get(scene)
    if not name:
        return None
    try:
        key = f"sticker:{name}"
        asset = TelegramAsset.objects.filter(key=key).first()
        if asset:
            # Do not upload again after an ambiguous network failure.
            return api.call("sendSticker", http_timeout=3, chat_id=chat_id,
                            sticker=asset.file_id, disable_notification=True)
        sent = api.send_sticker(chat_id, FOLDER / f"{name}.webp")
        file_id = ((sent or {}).get("sticker") or {}).get("file_id")
        if file_id:
            TelegramAsset.objects.update_or_create(key=key, defaults={"file_id": file_id})
        return sent
    except Exception as exc:
        log.warning("sticker skipped scene=%s error=%s", scene, type(exc).__name__)
        return None
