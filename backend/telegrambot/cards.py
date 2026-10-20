"""
The illustrated cards the bot sends: one banner per screen.

A photo is uploaded to Telegram once; after that we send the `file_id` it gave
back, which costs nothing and arrives instantly. The ids live in the database
(TelegramAsset), so a restart does not start re-uploading.

All screens display their matching banner on every visit. Cached file IDs
avoid uploading the same image again. Captions contain the current data.
"""
import logging
import os
from pathlib import Path

from . import api, reactions
from .models import TelegramAsset

log = logging.getLogger("telegrambot")

FOLDER = Path(__file__).resolve().parent / "cards"

# Card key → file. JPEG, because Telegram reads .webp as a sticker, not a photo.
FILES = {
    "skills": "skills.jpg",        # what I can do
    "commands": "commands.jpg",    # the command list
    "receipt": "receipt.jpg",
    "voice": "voice.jpg",
    "quick": "quick.jpg",
    "question": "question.jpg",
    "money": "money.jpg",
    "today": "today.jpg",
    "quiz": "quiz.jpg",          # the practice trainer
    "predict": "predict.jpg",    # "Up or down?", when there is no round to play
    "league": "league.jpg",
    "settings": "settings.jpg",
    "stop": "stop.jpg",
}

CAPTION_LIMIT = 1024


def illustrated():
    """All existing banners are enabled by default."""
    return os.environ.get("TELEGRAM_ILLUSTRATED_CARDS", "true").lower() in ("1", "true", "on")


def path_for(key):
    name = FILES.get(key)
    return FOLDER / name if name else None


def _file_id(key):
    row = TelegramAsset.objects.filter(key=key).first()
    return row.file_id if row else None


def _remember(key, message):
    """Keep the id Telegram gave the upload, so the next send is free."""
    photos = (message or {}).get("photo") or []
    if not photos:
        return
    best = max(photos, key=lambda p: p.get("file_size") or 0)
    TelegramAsset.objects.update_or_create(key=key, defaults={"file_id": best["file_id"]})


def send(chat_id, key, caption="", keyboard=None, markup=None, scene=None):
    sent = _send(chat_id, key, caption=caption, keyboard=keyboard, markup=markup)
    if sent:
        reactions.send(chat_id, scene or key)
    return sent


def _send(chat_id, key, caption="", keyboard=None, markup=None):
    """Send one card. Falls back to a plain message if the photo will not go."""
    if not illustrated():
        return api.send_message(chat_id, caption, keyboard=keyboard, markup=markup) if caption else None
    known = _file_id(key)
    if known:
        sent = api.send_photo(chat_id, known, caption=caption, keyboard=keyboard, markup=markup)
        if sent:
            return sent
        TelegramAsset.objects.filter(key=key).delete()  # stale id: upload again

    path = path_for(key)
    if path and path.exists():
        sent = api.upload_photo(chat_id, path, caption=caption, keyboard=keyboard, markup=markup)
        if sent:
            _remember(key, sent)
            return sent
        log.warning("could not send the %s card", key)
    return api.send_message(chat_id, caption, keyboard=keyboard, markup=markup) if caption else None


def show(link, key, text, keyboard=None, always=False, scene=None):
    """
    Display the section banner on each visit.

    Long text cannot ride along as a caption (Telegram caps it at 1024), so it
    follows the picture as its own message.
    """
    if not illustrated():
        return send(link.chat_id, key, caption=text, keyboard=keyboard, scene=scene)
    if len(text) <= CAPTION_LIMIT:
        return send(link.chat_id, key, caption=text, keyboard=keyboard, scene=scene)
    _send(link.chat_id, key)
    sent = api.send_message(link.chat_id, text, keyboard=keyboard)
    if sent:
        reactions.send(link.chat_id, scene or key)
    return sent
