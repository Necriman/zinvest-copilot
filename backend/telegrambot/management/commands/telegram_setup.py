"""
Dress the bot: the command menu, the description people see before pressing
Start, the name, and the menu button next to the message box.

    python manage.py telegram_setup

Safe to re-run — it just overwrites what is there. Everything is set in the
three languages the app speaks, so a Russian, English or Uzbek user sees the
bot in their own.
"""
from django.core.management.base import BaseCommand

from telegrambot import api, texts

COMMANDS = ("money", "today", "quiz", "predict", "league", "settings", "help", "stop")


class Command(BaseCommand):
    help = "Publish the bot's command menu, description and name to Telegram."

    def handle(self, *args, **options):
        if not api.enabled():
            self.stderr.write("TELEGRAM_BOT_TOKEN is not set.")
            return

        for lang in texts.LANGS:
            commands = [
                {"command": name, "description": texts.pick(texts.COMMANDS[name], lang)}
                for name in COMMANDS
            ]
            # Russian is also the default for anyone whose language we have no
            # translation for, so it goes out twice: once tagged, once plain.
            api.set_commands(commands, language_code=lang)
            api.set_description(texts.pick(texts.ABOUT, lang), texts.pick(texts.ABOUT_SHORT, lang), language_code=lang)
            if lang == "ru":
                api.set_commands(commands)
                api.set_description(texts.pick(texts.ABOUT, lang), texts.pick(texts.ABOUT_SHORT, lang))
            self.stdout.write(f"{lang}: {len(commands)} commands, description set")

        api.set_menu_button()
        who = api.me() or {}
        self.stdout.write(f"done · @{who.get('username')}")
        self.stdout.write("The profile photo can only be set in BotFather: /setuserpic")
