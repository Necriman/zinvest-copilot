"""
Point Telegram at this deployment (or look at where it points now).

    python manage.py telegram_webhook --set https://your-domain.example/api/telegram/webhook
    python manage.py telegram_webhook --show
    python manage.py telegram_webhook --delete

The secret header comes from TELEGRAM_WEBHOOK_SECRET; without it the webhook
view answers 404, so set it before pointing Telegram here.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from telegrambot import api


class Command(BaseCommand):
    help = "Set, show or delete the Telegram webhook."

    def add_arguments(self, parser):
        parser.add_argument("--set", dest="url", help="Public https URL of /api/telegram/webhook")
        parser.add_argument("--delete", action="store_true")
        parser.add_argument("--show", action="store_true")

    def handle(self, *args, **options):
        if not api.enabled():
            self.stderr.write("TELEGRAM_BOT_TOKEN is not set.")
            return
        if options["url"]:
            if not settings.TELEGRAM_WEBHOOK_SECRET:
                self.stderr.write("Set TELEGRAM_WEBHOOK_SECRET first — the webhook view refuses calls without it.")
                return
            ok = api.set_webhook(options["url"], settings.TELEGRAM_WEBHOOK_SECRET)
            self.stdout.write("webhook set" if ok else "could not set the webhook")
        elif options["delete"]:
            self.stdout.write("webhook deleted" if api.delete_webhook() else "could not delete the webhook")
        info = api.webhook_info() or {}
        self.stdout.write(f"url: {info.get('url') or '(none)'} · pending: {info.get('pending_update_count', 0)}")
        if info.get("last_error_message"):
            self.stdout.write(f"last error: {info['last_error_message']}")
