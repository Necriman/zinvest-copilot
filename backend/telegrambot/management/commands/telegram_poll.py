"""
Long polling for local development, so the bot works without a public URL.

    python manage.py telegram_poll

In production use a webhook instead (manage.py telegram_webhook --set URL);
Telegram refuses to do both at once, so this command deletes the webhook while
it runs and leaves it deleted — set it again when you deploy.
"""
import signal
import time

from django.core.management.base import BaseCommand

from telegrambot import api, handlers


class Command(BaseCommand):
    help = "Poll Telegram for updates (development)."

    def add_arguments(self, parser):
        parser.add_argument("--seconds", type=int, default=25, help="How long each poll waits (default 25)")

    def handle(self, *args, **options):
        if not api.enabled():
            self.stderr.write("TELEGRAM_BOT_TOKEN is not set — nothing to poll.")
            return
        who = api.me()
        if not who:
            self.stderr.write("Telegram refused the token.")
            return
        api.delete_webhook()  # polling and a webhook are mutually exclusive
        self.stdout.write(f"polling as @{who.get('username')} — Ctrl+C to stop")

        running = {"on": True}
        signal.signal(signal.SIGINT, lambda *_: running.update(on=False))

        offset = None
        while running["on"]:
            updates = api.get_updates(offset=offset, poll_seconds=options["seconds"])
            if updates is None:
                time.sleep(3)  # network hiccup: back off, keep going
                continue
            for update in updates:
                offset = update["update_id"] + 1
                handlers.handle_update(update)
        self.stdout.write("stopped")
