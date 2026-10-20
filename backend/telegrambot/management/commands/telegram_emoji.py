"""Inspect a Telegram custom emoji pack and import matching, verified icons."""
import json

from django.core.management.base import BaseCommand, CommandError

from telegrambot import api, premium


class Command(BaseCommand):
    help = "Inspect a custom emoji pack; --write imports matching icons into premium_emoji.json."

    def add_arguments(self, parser):
        parser.add_argument("pack", help="The name after t.me/addemoji/")
        parser.add_argument("--write", action="store_true")

    def handle(self, *args, **options):
        if not api.enabled():
            raise CommandError("TELEGRAM_BOT_TOKEN is not set.")
        result = api.call("getStickerSet", name=options["pack"])
        if not result or result.get("sticker_type") != "custom_emoji":
            raise CommandError("Could not load a custom emoji pack.")
        icons = {}
        for sticker in result.get("stickers", []):
            emoji_id = str(sticker.get("custom_emoji_id") or "")
            if emoji_id.isascii() and emoji_id.isdigit():
                icons.setdefault((sticker.get("emoji") or "").rstrip("\ufe0f"), emoji_id)
        matched = {key: icons[plain.rstrip("\ufe0f")] for key, plain in premium.PLAIN.items()
                   if plain.rstrip("\ufe0f") in icons}
        self.stdout.write(json.dumps({"pack": options["pack"], "matched": matched, "icons": icons}, ensure_ascii=True, indent=2))
        if options["write"]:
            data = json.loads(premium.FILE.read_text(encoding="utf-8"))
            data.update(matched)
            premium.FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            premium.reload()
            self.stdout.write(f"Imported {len(matched)} verified icons.")
