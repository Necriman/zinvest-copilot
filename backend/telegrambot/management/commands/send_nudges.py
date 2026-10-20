"""
The bear's round. Run it hourly — it works out who is due:

    python manage.py send_nudges          # send
    python manage.py send_nudges --dry    # say who would get one, send nothing

Cron (server local time):
    0 * * * * cd /opt/zinvest/backend && .venv/bin/python manage.py send_nudges
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from telegrambot import api, nudges


class Command(BaseCommand):
    help = "Send the Telegram nudges due this hour."

    def add_arguments(self, parser):
        parser.add_argument("--dry", action="store_true", help="List who is due without sending")

    def handle(self, *args, **options):
        if not api.enabled():
            self.stderr.write("TELEGRAM_BOT_TOKEN is not set — nothing to send.")
            return
        now = timezone.localtime()
        if options["dry"]:
            due = list(nudges.due(now))
            for link in due:
                self.stdout.write(f"{link.user.email} · chat {link.chat_id} · {link.nudges} · {link.nudge_hour}:00")
            self.stdout.write(f"{len(due)} due at {now:%H:%M}")
            return
        counts = nudges.run(now)
        self.stdout.write(f"{now:%H:%M}: {counts['nudge']} nudge(s), {counts['weekly']} weekly summary(ies)")
