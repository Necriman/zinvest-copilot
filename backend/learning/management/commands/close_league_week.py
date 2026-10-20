"""
Settle the finished league week: freeze points, rank the groups, move people
between divisions and pay the podium.

Run it once after each week turns over (a Monday-morning cron is enough):

    python manage.py close_league_week

Running it twice is harmless — seats already closed are skipped.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from learning import league


class Command(BaseCommand):
    help = "Close the previous league week (safe to re-run)."

    def add_arguments(self, parser):
        parser.add_argument("--week", help="Monday of the week to close (YYYY-MM-DD); default: the one just finished")

    def handle(self, *args, **options):
        if options.get("week"):
            start = timezone.datetime.strptime(options["week"], "%Y-%m-%d").date()
        else:
            start = league.week_start(timezone.localdate() - timedelta(days=7))
        result = league.close_week(start)
        self.stdout.write(f"{start}: {result['learners']} learner(s) in {result['groups']} group(s), {result.get('prizes', 0)} prize(s)")
