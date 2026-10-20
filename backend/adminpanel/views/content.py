"""
Course content: units, lessons and unit tests, plus importing a unit from JSON.

Import format (one unit object, or a list of them):

  {
    "code": "05", "slug": "marketing", "title": "Marketing", "subtitle": "...",
    "order": 5, "icon": "", "accent_color": "brand", "test_pass_threshold": 0.7,
    "test_questions": [{"id": "q1", "prompt": "...", "choices": ["a", "b"],
                        "answer_index": 1, "explanation": "..."}],
    "lessons": [
      {"slug": "what-is-marketing", "title": "...", "order": 1,
       "coin_reward": 10, "estimated_minutes": 5,
       "canvas_payload": {...}                      # the full lesson layout, or
       "intro": "...", "bullets": ["..."], "table": [["Role", "Example"], ...],
       "table_title": "At a glance"}
    ]
  }

Units and lessons are matched by slug and updated in place, so learners keep
their progress. Nothing is ever deleted by an import; lessons that exist but
are missing from the file are reported as warnings.
"""
import re

from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify

from config import languages
from learning.html_clean import clean_lesson_html
from learning.models import Lesson, LessonProgress, Unit, UnitProgress

from ..audit import audit
from ..permissions import staff_required
from .common import body, method_not_allowed

MAX_IMPORT_BYTES = 2 * 1024 * 1024


def _question_errors(questions, where):
    errors = []
    if not isinstance(questions, list):
        return [f"{where}: test_questions must be a list"]
    if len(questions) > 100:
        errors.append(f"{where}: at most 100 test questions")
    seen = set()
    for i, q in enumerate(questions, 1):
        label = f"{where}, question {i}"
        if not isinstance(q, dict):
            errors.append(f"{label}: must be an object")
            continue
        qid = str(q.get("id") or "").strip()
        if not qid:
            errors.append(f"{label}: id is required")
        elif qid in seen:
            errors.append(f"{label}: id {qid} is used twice")
        seen.add(qid)
        if not str(q.get("prompt") or "").strip():
            errors.append(f"{label}: prompt is required")
        choices = q.get("choices")
        if not isinstance(choices, list) or not 2 <= len(choices) <= 8 or not all(isinstance(c, str) and c.strip() for c in choices):
            errors.append(f"{label}: 2 to 8 non-empty choices")
            continue
        answer = q.get("answer_index")
        if not isinstance(answer, int) or not 0 <= answer < len(choices):
            errors.append(f"{label}: answer_index must point at one of the choices (0-{len(choices) - 1})")
    return errors


def _clean_questions(questions):
    return [
        {"id": str(q["id"]).strip(), "prompt": str(q["prompt"]).strip(), "choices": [str(c).strip() for c in q["choices"]],
         "answer_index": int(q["answer_index"]), "explanation": str(q.get("explanation") or "").strip()}
        for q in questions
    ]


def _unit_dict(u):
    lessons = list(u.lessons.annotate(done=Count("progress", filter=Q(progress__status=LessonProgress.Status.COMPLETED))).order_by("order"))
    return {
        "id": str(u.id), "code": u.code, "slug": u.slug, "title": u.title, "subtitle": u.subtitle, "order": u.order,
        "test_pass_threshold": u.test_pass_threshold, "test_questions": u.test_questions,
        "passed": UnitProgress.objects.filter(unit=u, test_passed=True).count(),
        "lessons": [
            {"id": str(l.id), "slug": l.slug, "title": l.title, "order": l.order, "coin_reward": l.coin_reward,
             "estimated_minutes": l.estimated_minutes, "completions": l.done}
            for l in lessons
        ],
    }


@staff_required("content.view")
def content(request):
    if request.method != "GET":
        return method_not_allowed()
    return JsonResponse({"units": [_unit_dict(u) for u in Unit.objects.order_by("order")]})


@staff_required("content.manage", write=True)
def unit_detail(request, unit_id):
    """PATCH {title, subtitle, test_pass_threshold, test_questions}"""
    if request.method != "PATCH":
        return method_not_allowed()
    unit = get_object_or_404(Unit, pk=unit_id)
    data, err = body(request)
    if err:
        return err
    changes = {}
    if "title" in data:
        title = str(data["title"] or "").strip()
        if not 1 <= len(title) <= 120:
            return JsonResponse({"detail": "Title: 1-120 characters."}, status=400)
        changes["title"] = title
    if "subtitle" in data:
        changes["subtitle"] = str(data["subtitle"] or "").strip()[:200]
    if "test_pass_threshold" in data:
        try:
            threshold = float(data["test_pass_threshold"])
        except (TypeError, ValueError):
            return JsonResponse({"detail": "Pass mark must be a number."}, status=400)
        if not 0.1 <= threshold <= 1:
            return JsonResponse({"detail": "Pass mark must be between 10% and 100%."}, status=400)
        changes["test_pass_threshold"] = threshold
    if "test_questions" in data:
        errors = _question_errors(data["test_questions"], unit.title)
        if errors:
            return JsonResponse({"detail": "Fix the questions first.", "errors": errors[:20]}, status=400)
        changes["test_questions"] = _clean_questions(data["test_questions"])
    for key, value in changes.items():
        setattr(unit, key, value)
    unit.save()
    audit(request, "content.unit_updated", target_type="unit", target_id=unit.pk, summary=f"Edited unit {unit.code} · {unit.title}", fields=sorted(changes))
    return JsonResponse(_unit_dict(unit))


@staff_required("content.manage", write=True)
def lesson_detail(request, lesson_id):
    """PATCH {title, coin_reward, estimated_minutes}"""
    if request.method != "PATCH":
        return method_not_allowed()
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    data, err = body(request)
    if err:
        return err
    changes = {}
    if "title" in data:
        title = str(data["title"] or "").strip()
        if not 1 <= len(title) <= 140:
            return JsonResponse({"detail": "Title: 1-140 characters."}, status=400)
        changes["title"] = title
    for key, low, high in (("coin_reward", 0, 1000), ("estimated_minutes", 1, 240)):
        if key in data:
            try:
                value = int(data[key])
            except (TypeError, ValueError):
                return JsonResponse({"detail": f"{key} must be a whole number."}, status=400)
            if not low <= value <= high:
                return JsonResponse({"detail": f"{key} must be between {low} and {high}."}, status=400)
            changes[key] = value
    for key, value in changes.items():
        setattr(lesson, key, value)
    lesson.save()
    audit(request, "content.lesson_updated", target_type="lesson", target_id=lesson.pk, summary=f"Edited lesson {lesson.title}", fields=sorted(changes))
    return JsonResponse({"ok": True})


@staff_required("content.manage", write=True)
def lesson_body(request, lesson_id):
    """
    POST {lang, html, title?} -> the lesson's text (and title) in one language,
    as every learner will see it. Written from the lesson page itself, in the
    same editor learners use. English is the base row; ru/uz go to i18n.
    """
    if request.method != "POST":
        return method_not_allowed()
    lesson = get_object_or_404(Lesson.objects.select_related("unit"), pk=lesson_id)
    data, err = body(request)
    if err:
        return err
    lang = languages.normalize(data.get("lang"))
    if not lang:
        return JsonResponse({"detail": "Choose the language of this version: en, ru or uz."}, status=400)
    try:
        html = clean_lesson_html(data.get("html"))
    except ValueError:
        return JsonResponse({"detail": "The lesson is too long to save."}, status=400)
    if not re.sub(r"<[^>]+>", "", html).strip():
        return JsonResponse({"detail": "The lesson cannot be empty."}, status=400)
    title = str(data.get("title") or "").strip() if "title" in data else None
    if title is not None and not 1 <= len(title) <= 140:
        return JsonResponse({"detail": "Title: 1-140 characters."}, status=400)

    if lang == languages.BASE:
        if not lesson.content_html and lesson.canvas_payload:
            lesson.canvas_payload = {}
        lesson.content_html = html
        if title:
            lesson.title = title
    else:
        i18n = dict(lesson.i18n or {})
        words = dict(i18n.get(lang) or {})
        words["content_html"] = html
        if title:
            words["title"] = title
        i18n[lang] = words
        lesson.i18n = i18n
    lesson.save()
    from ai_engine import course

    course.forget()
    audit(request, "content.lesson_text_updated", target_type="lesson", target_id=lesson.pk,
          summary=f"Edited the {lang} text of {lesson.unit.code}.{lesson.order} {lesson.title}", lang=lang)
    return JsonResponse({"ok": True, "lang": lang, "title": lesson.tr("title", lang), "content_html": html})


# --------------------------------------------------------------------------- #
# Import
def _lesson_payload(item):
    payload = item.get("canvas_payload")
    if isinstance(payload, dict) and payload:
        return payload
    from learning.management.commands.seed_learning import canvas

    table = item.get("table")
    if isinstance(table, list) and table and all(isinstance(row, list) for row in table):
        # Plain rows ([["Role", "Example"], ["Exchange", "Groceries"]]): even columns, first row is the header.
        cols = max(len(row) for row in table)
        table = {"title": str(item.get("table_title") or "At a glance"), "colWidths": [720 // cols] * cols,
                 "rows": [[str(cell) for cell in row] + [""] * (cols - len(row)) for row in table]}
    elif isinstance(table, dict) and isinstance(table.get("rows"), list) and table["rows"]:
        cols = max(len(row) for row in table["rows"] if isinstance(row, list)) if any(isinstance(r, list) for r in table["rows"]) else 1
        table = {"title": str(table.get("title") or "At a glance"),
                 "colWidths": table.get("colWidths") if isinstance(table.get("colWidths"), list) else [720 // cols] * cols,
                 "rows": [[str(cell) for cell in row] for row in table["rows"] if isinstance(row, list)]}
    else:
        table = None
    return canvas(str(item.get("title") or ""), str(item.get("intro") or ""), [str(b) for b in item.get("bullets") or []], table)


def _validate_unit(doc, index):
    where = f"Unit {index}"
    errors, warnings = [], []
    if not isinstance(doc, dict):
        return [f"{where}: must be an object"], []
    title = str(doc.get("title") or "").strip()
    where = f"Unit {index} ({title or 'untitled'})"
    slug = slugify(str(doc.get("slug") or title))
    if not title or len(title) > 120:
        errors.append(f"{where}: title is required (up to 120 characters)")
    if not slug:
        errors.append(f"{where}: slug is required")
    code = str(doc.get("code") or "").strip()
    if not code or len(code) > 8:
        errors.append(f"{where}: code is required (up to 8 characters, e.g. \"05\")")
    order = doc.get("order")
    if not isinstance(order, int) or not 1 <= order <= 999:
        errors.append(f"{where}: order must be a whole number from 1")
    threshold = doc.get("test_pass_threshold", 0.7)
    if not isinstance(threshold, (int, float)) or not 0.1 <= threshold <= 1:
        errors.append(f"{where}: test_pass_threshold must be between 0.1 and 1")
    errors += _question_errors(doc.get("test_questions", []), where)
    lessons = doc.get("lessons")
    if not isinstance(lessons, list) or not lessons:
        errors.append(f"{where}: lessons must be a non-empty list")
        return errors, warnings
    if len(lessons) > 60:
        errors.append(f"{where}: at most 60 lessons per unit")
    slugs, orders = set(), set()
    for i, item in enumerate(lessons, 1):
        label = f"{where}, lesson {i}"
        if not isinstance(item, dict):
            errors.append(f"{label}: must be an object")
            continue
        ltitle = str(item.get("title") or "").strip()
        lslug = slugify(str(item.get("slug") or ltitle))
        if not ltitle or len(ltitle) > 140:
            errors.append(f"{label}: title is required (up to 140 characters)")
        if not lslug or lslug in slugs:
            errors.append(f"{label}: slug is missing or repeated")
        slugs.add(lslug)
        lorder = item.get("order", i)
        if not isinstance(lorder, int) or lorder < 1 or lorder in orders:
            errors.append(f"{label}: order is missing or repeated")
        orders.add(lorder)
        if not (isinstance(item.get("canvas_payload"), dict) and item["canvas_payload"]) and not item.get("intro") and not item.get("bullets"):
            warnings.append(f"{label}: no content (canvas_payload, intro or bullets)")
    return errors, warnings


@staff_required("content.manage", write=True)
def content_import(request):
    """POST {document: <unit or list>, dry_run: bool}"""
    if request.method != "POST":
        return method_not_allowed()
    if len(request.body or b"") > MAX_IMPORT_BYTES:
        return JsonResponse({"detail": "The file is larger than 2 MB."}, status=400)
    data, err = body(request)
    if err:
        return err
    document = data.get("document")
    units = document if isinstance(document, list) else [document]
    errors, warnings, plan = [], [], []
    codes, orders = {}, {}
    for index, doc in enumerate(units, 1):
        e, w = _validate_unit(doc, index)
        errors += e
        warnings += w
        if e:
            continue
        slug = slugify(str(doc.get("slug") or doc["title"]))
        existing = Unit.objects.filter(slug=slug).first()
        # Codes and orders are unique across units: check against other units.
        clash_code = Unit.objects.filter(code=doc["code"]).exclude(slug=slug).first()
        clash_order = Unit.objects.filter(order=doc["order"]).exclude(slug=slug).first()
        if clash_code or codes.get(doc["code"]):
            errors.append(f"Unit {index}: code {doc['code']} is already used by another unit")
        if clash_order or orders.get(doc["order"]):
            errors.append(f"Unit {index}: order {doc['order']} is already used by another unit")
        codes[doc["code"]] = orders[doc["order"]] = True
        lesson_plan = []
        for i, item in enumerate(doc["lessons"], 1):
            lslug = slugify(str(item.get("slug") or item["title"]))
            current = existing.lessons.filter(slug=lslug).first() if existing else None
            lesson_plan.append({"slug": lslug, "title": str(item["title"]).strip(), "action": "update" if current else "create"})
        if existing:
            kept = set(existing.lessons.values_list("slug", flat=True)) - {l["slug"] for l in lesson_plan}
            if kept:
                warnings.append(f"Unit {index}: {len(kept)} lesson(s) already on the site are not in the file and stay as they are: {', '.join(sorted(kept))}")
        plan.append({"unit": str(doc["title"]).strip(), "slug": slug, "action": "update" if existing else "create",
                     "lessons": lesson_plan, "questions": len(doc.get("test_questions") or [])})
    if errors or data.get("dry_run", True):
        return JsonResponse({"ok": not errors, "dry_run": True, "errors": errors[:50], "warnings": warnings[:50], "plan": plan}, status=200 if not errors else 400)

    with transaction.atomic():
        for doc in units:
            slug = slugify(str(doc.get("slug") or doc["title"]))
            unit, created = Unit.objects.update_or_create(
                slug=slug,
                defaults={
                    "code": str(doc["code"]).strip(), "title": str(doc["title"]).strip(), "subtitle": str(doc.get("subtitle") or "").strip()[:200],
                    "order": doc["order"], "icon": str(doc.get("icon") or "")[:40], "accent_color": str(doc.get("accent_color") or "brand")[:20],
                    "test_pass_threshold": float(doc.get("test_pass_threshold", 0.7)), "test_questions": _clean_questions(doc.get("test_questions") or []),
                },
            )
            # Park every lesson on a temporary order first, so reordering cannot
            # collide with the (unit, order) uniqueness.
            incoming = {slugify(str(item.get("slug") or item["title"])) for item in doc["lessons"]}
            for offset, lesson in enumerate(unit.lessons.order_by("order")):
                Lesson.objects.filter(pk=lesson.pk).update(order=10000 + offset)
            last = 0
            for i, item in enumerate(doc["lessons"], 1):
                last = max(last, item.get("order", i))
                Lesson.objects.update_or_create(
                    unit=unit, slug=slugify(str(item.get("slug") or item["title"])),
                    defaults={
                        "title": str(item["title"]).strip()[:140], "order": item.get("order", i),
                        "coin_reward": int(item.get("coin_reward", 10)), "estimated_minutes": int(item.get("estimated_minutes", 5)),
                        "canvas_payload": _lesson_payload(item),
                    },
                )
            # Lessons that are on the site but not in the file keep their place after the imported ones.
            for offset, lesson in enumerate(unit.lessons.exclude(slug__in=incoming).order_by("order"), 1):
                Lesson.objects.filter(pk=lesson.pk).update(order=last + offset)
    audit(request, "content.imported", summary=f"Imported {len(units)} unit(s): " + ", ".join(p["unit"] for p in plan), plan=plan)
    return JsonResponse({"ok": True, "dry_run": False, "errors": [], "warnings": warnings, "plan": plan})
