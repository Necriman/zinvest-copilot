"""
Load the course units from learning/content/units/uNN.json (made from the
unit PDFs) into the database. Idempotent: run it again after editing a file.

    python manage.py import_units            # every unit file
    python manage.py import_units --only 3   # one unit
    python manage.py import_units --dry-run  # report, change nothing

Each file holds one unit in up to three languages (en, ru, uz): its title and
subtitle, one lesson per section ("3.1 …") as editor HTML, the glossary, and
the review test. English is stored on the rows, the other languages in their
i18n, exactly like the rest of the course (see learning.models.Translated).

Units are matched by their position (order) and lessons by their position in
the unit, and updated in place, so ids, progress and study plans survive. A
lesson whose text changed loses the learner copies saved from the old text
(they would otherwise hide the new lesson); lessons beyond the new count are
removed.
"""
import json
import re
from html import unescape
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from learning.models import Lesson, LessonProgress, Unit

DIR = Path(__file__).resolve().parents[2] / "content" / "units"
LANGS = ("ru", "uz")

# Slug, icon and accent per unit number. Slugs are stable keys (the study map's
# scenery is keyed by them), so they are fixed here rather than taken from a title.
UNIT_META = {
    1: ("what-is-finance", "book", "brand"),
    2: ("time-value-of-money", "trending", "invest"),
    3: ("personal-budgeting", "wallet", "budget"),
    4: ("saving-and-growing-money", "coin", "invest"),
    5: ("credit-and-debt", "target", "risk"),
    6: ("banking-system", "store", "brand"),
    7: ("income-and-earning", "sparkles", "budget"),
    8: ("insurance-basics", "shield", "risk"),
    9: ("taxes-for-beginners", "map", "brand"),
    10: ("financial-goal-setting", "target", "budget"),
    11: ("introduction-to-economics", "globe", "invest"),
}
GLOSSARY_TITLE = {"en": "Key Terms Glossary", "ru": "Глоссарий терминов", "uz": "Atamalar lug‘ati"}

# The PDFs draw ticks and crosses in ZapfDingbats, which text extraction reads
# as control codes; emoji the font lacked come out as NUL. Postgres rejects NUL
# in JSON, so every string is cleaned on the way in.
DINGBATS = {"\x14": "✓", "\x16": "✗"}
LOST_ICON = re.compile(r"\x00\s*|(?:(?<=^)|(?<=[\s>]))️\s*")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# Ticked/crossed items that extraction ran into one paragraph: one per paragraph.
MERGED_ITEM = re.compile(r"(?<=[^>\s])\s+([✓✗])\s+")


def clean(value):
    """Strings with the dingbats mapped, lost icons dropped and other control codes removed."""
    if isinstance(value, str):
        for code, char in DINGBATS.items():
            value = value.replace(code, char)
        value = CONTROL.sub("", LOST_ICON.sub("", value))
        return MERGED_ITEM.sub(r"</p><p>\1 ", value) if "<p>" in value else value
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    return value


def words(html):
    return len(re.findall(r"\w+", unescape(re.sub(r"<[^>]+>", " ", html or ""))))


def minutes(html):
    return max(3, min(30, round(words(html) / 180)))


def lesson_rows(lang_data):
    """The lessons of one language, glossary last: [(title, html)]."""
    rows = [(item["title"], item["html"]) for item in lang_data.get("lessons") or []]
    glossary = lang_data.get("glossary")
    if glossary and glossary.get("html"):
        rows.append((glossary.get("title") or "", glossary["html"]))
    return rows


def questions(unit_no, lang_data):
    out = []
    for q in lang_data.get("test") or []:
        if len(q.get("choices") or []) < 2 or q.get("answer_index") is None:
            continue
        out.append({
            "id": f"u{unit_no:02d}-q{int(q['n']):02d}",
            "prompt": q["prompt"],
            "choices": q["choices"],
            "answer_index": q["answer_index"],
            "explanation": q.get("explanation", ""),
        })
    return out


class Command(BaseCommand):
    help = "Import the course units from learning/content/units/*.json."

    def add_arguments(self, parser):
        parser.add_argument("--only", type=int, help="Import just this unit number.")
        parser.add_argument("--dry-run", action="store_true", help="Report what would change and change nothing.")

    def handle(self, *args, only=None, dry_run=False, **opts):
        files = sorted(DIR.glob("u*.json"))
        if only:
            files = [f for f in files if f.name == f"u{only:02d}.json"]
        if not files:
            raise CommandError(f"No unit files in {DIR}")
        with transaction.atomic():
            for path in files:
                self.import_unit(clean(json.loads(path.read_text(encoding="utf-8"))))
            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry run: nothing was saved."))

    def import_unit(self, data):
        no = int(data["unit"])
        langs = data["langs"]
        en = langs.get("en")
        if not en:
            raise CommandError(f"Unit {no}: English is required (it is the base language).")
        slug, icon, accent = UNIT_META.get(no, (slugify(en["title"])[:64], "book", "brand"))

        unit = Unit.objects.filter(order=no).first() or Unit.objects.filter(code=f"{no:02d}").first()
        created = unit is None
        if created:
            unit = Unit(order=no)
        # Another unit may hold this slug or code from an older course layout.
        Unit.objects.filter(slug=slug).exclude(pk=unit.pk).update(slug=f"old-{no}-{slug}"[:64])
        Unit.objects.filter(code=f"{no:02d}").exclude(pk=unit.pk).update(code=f"x{no:02d}")
        unit.code = f"{no:02d}"
        unit.slug = slug
        unit.title = en["title"][:120]
        unit.subtitle = en.get("subtitle", "")[:200]
        unit.icon = icon
        unit.accent_color = accent
        unit.test_questions = questions(no, en)
        i18n = {}
        for lang in LANGS:
            if lang in langs:
                d = langs[lang]
                i18n[lang] = {"title": d["title"], "subtitle": d.get("subtitle", ""), "test_questions": questions(no, d)}
        unit.i18n = i18n
        unit.save()

        en_rows = lesson_rows(en)
        other = {lang: lesson_rows(langs[lang]) for lang in LANGS if lang in langs}
        existing = {l.order: l for l in unit.lessons.all()}
        # Free the target slugs/orders first: an old lesson may sit on them.
        if existing:
            for lesson in existing.values():
                lesson.slug = f"tmp-{lesson.pk.hex[:12]}"
                lesson.save(update_fields=["slug"])
        changed = 0
        for k, (title, html) in enumerate(en_rows, start=1):
            is_glossary = k == len(en_rows) and en.get("glossary")
            lesson = existing.pop(k, None) or Lesson(unit=unit, order=k)
            old_html = lesson.content_html
            lesson.slug = ("glossary" if is_glossary else f"{no}-{k}-{slugify(title)}")[:80]
            lesson.title = (title or GLOSSARY_TITLE["en"])[:140]
            lesson.content_html = html
            lesson.canvas_payload = {}
            lesson.estimated_minutes = minutes(html)
            lesson.coin_reward = 5 if is_glossary else 10
            tr = {}
            for lang, rows in other.items():
                if k <= len(rows):
                    t, h = rows[k - 1]
                    tr[lang] = {"title": (t or GLOSSARY_TITLE[lang])[:140], "content_html": h}
            if not lesson._state.adding and (old_html != html or (lesson.i18n or {}) != tr):
                changed += 1
                # Copies saved from the old text would hide the new lesson.
                LessonProgress.objects.filter(lesson=lesson).exclude(edited_content="").update(edited_content="")
            lesson.i18n = tr
            lesson.save()
        removed = 0
        for lesson in existing.values():
            lesson.delete()
            removed += 1
        self.stdout.write(
            f"Unit {no:02d} {'created' if created else 'updated'}: {unit.title} — "
            f"{len(en_rows)} lessons ({', '.join(['en'] + list(other))}), "
            f"{len(unit.test_questions)} test questions, {changed} lessons rewritten, {removed} removed"
        )
