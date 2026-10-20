"""
Seed the "Up or down?" market episodes (idempotent).

    python manage.py seed_market

The prices are built from the anchors in learning/content/market.py — the
real levels, with a smoothed line between them — so a reseed always produces
exactly the same charts.
"""
from django.core.management.base import BaseCommand, CommandError

from learning.content.market import EPISODES, build
from learning.models import MarketEpisode

LANGS = ("ru", "en", "uz")
FIELDS = ("when", "headline", "question", "explain", "lesson")


class Command(BaseCommand):
    help = "Load the 'Up or down?' market episodes."

    def handle(self, *args, **options):
        made = updated = 0
        for order, episode in enumerate(EPISODES, start=1):
            for lang in LANGS:
                missing = [f for f in FIELDS if not episode.get(lang, {}).get(f)]
                if missing:
                    raise CommandError(f"{episode['slug']} [{lang}]: missing {', '.join(missing)}")
            before, after = build(episode)
            ends_up = after[-1] > before[-1]
            if ends_up != (episode["direction"] == "up"):
                raise CommandError(f"{episode['slug']}: the prices say the opposite of its answer")
            _, created = MarketEpisode.objects.update_or_create(
                slug=episode["slug"],
                defaults={
                    "asset": episode["asset"],
                    "unit": episode["unit"],
                    "before": before,
                    "after": after,
                    "direction": episode["direction"],
                    "body": {lang: {f: episode[lang][f] for f in FIELDS} for lang in LANGS},
                    "order": order,
                    "active": True,
                },
            )
            made += created
            updated += not created
        self.stdout.write(self.style.SUCCESS(f"market episodes: +{made} new, {updated} refreshed"))
