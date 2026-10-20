"""
What Zinvest AI knows of the course itself.

Two things go into a question's prompt:

  * the lesson the learner is reading, when the question comes from a lesson
    (its id is in the context): that lesson's text in the learner's language;
  * otherwise, the passages of the course that best fit the question, so a
    question asked in the chat ("what is the 50/30/20 rule?") is answered
    from the unit that teaches it, with the lesson number to go and read.

Lessons are cut into passages at their sub-headings and searched by word
overlap with a crude stem (the first letters of a word), which is enough for
Russian and Uzbek word endings. The index lives in memory per language and is
rebuilt after ten minutes or when a lesson is edited (forget()).
"""
import math
import re
import time
from collections import Counter

from learning.html_clean import plain_text

TTL_SECONDS = 600
PASSAGE_CHARS = 1400
LESSON_CHARS = 7000
_INDEX = {}  # lang -> {"built": t, "passages": [...], "idf": {...}}

STOP = set("""
the and for are with that this from your you what how why when which who can will not but its into than then them they there their
have has had was were been about more most much some such only also very just like over under each other our out
что как это для или его она они при так все уже его ему над под без про чем где кто если когда тоже также только очень
быть был была были есть нет вам вас ваш ваши вы мы нас наш себя свой своих этот эта эти того тем того чтобы
va bilan uchun bu nima qanday yoki ham emas edi esa lekin agar bilan shu har bir biz siz ular uning bor yo'q
""".split())


def forget():
    _INDEX.clear()


def _stem(word):
    return word[:6] if len(word) > 6 else word


def _tokens(text):
    words = re.findall(r"[a-zа-яёўқғҳ0-9][a-zа-яёўқғҳ0-9'‘’ʻ`/%]*", (text or "").lower())
    # Numbers count from two digits ("72", "50/30/20"); words from three letters.
    return [_stem(w) for w in words if (len(w) > 2 or (len(w) == 2 and w.isdigit())) and w not in STOP]


def _number(lesson):
    return f"{int(lesson.unit.code) if lesson.unit.code.isdigit() else lesson.unit.code}.{lesson.order}"


def _pieces(text, size=PASSAGE_CHARS):
    text = text.strip()
    while text:
        if len(text) <= size:
            yield text
            return
        cut = text.rfind("\n", 0, size)
        if cut < size // 2:
            cut = text.rfind(". ", 0, size)
        cut = cut + 1 if cut > 0 else size
        yield text[:cut].strip()
        text = text[cut:].strip()


def _build(lang):
    from learning.models import Lesson

    passages = []
    for lesson in Lesson.objects.select_related("unit").order_by("unit__order", "order"):
        html = lesson.tr("content_html", lang)
        if not html:
            continue
        title = lesson.tr("title", lang)
        unit_title = lesson.unit.tr("title", lang)
        for chunk in re.split(r"(?=<h2\b)", html):
            heading = re.search(r"<h2\b[^>]*>(.*?)</h2>", chunk, re.S)
            for piece in _pieces(plain_text(chunk)):
                passages.append({
                    "lesson_id": str(lesson.id),
                    "number": _number(lesson),
                    "lesson": title,
                    "unit": unit_title,
                    "heading": plain_text(heading.group(1)) if heading else "",
                    "text": piece,
                    "tf": Counter(_tokens(f"{title} {title} {piece}")),
                })
    df = Counter()
    for p in passages:
        df.update(p["tf"].keys())
    n = max(1, len(passages))
    idf = {term: math.log(1 + n / count) for term, count in df.items()}
    return {"built": time.monotonic(), "passages": passages, "idf": idf}


def _index(lang):
    entry = _INDEX.get(lang)
    if not entry or time.monotonic() - entry["built"] > TTL_SECONDS:
        entry = _INDEX[lang] = _build(lang)
    return entry


def search(question, lang, limit=3, min_score=2.5):
    """The passages that fit `question` best, most relevant first."""
    entry = _index(lang)
    terms = set(_tokens(question))
    if not terms:
        return []
    scored = []
    for p in entry["passages"]:
        score = sum((1 + math.log(p["tf"][t])) * entry["idf"].get(t, 0) for t in terms if p["tf"][t])
        if score >= min_score:
            scored.append((score, p))
    scored.sort(key=lambda s: -s[0])
    out, seen = [], set()
    for score, p in scored:
        key = (p["lesson_id"], p["heading"])
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
        if len(out) == limit:
            break
    return out


def lesson_text(lesson_id, lang):
    """(number, title, unit title, text) of one lesson, or None."""
    import uuid

    from learning.models import Lesson

    try:
        pk = uuid.UUID(str(lesson_id))
    except (TypeError, ValueError):
        return None
    lesson = Lesson.objects.select_related("unit").filter(pk=pk).first()
    if lesson is None:
        return None
    html = lesson.tr("content_html", lang)
    if not html:
        return None
    return _number(lesson), lesson.tr("title", lang), lesson.unit.tr("title", lang), plain_text(html)[:LESSON_CHARS]


def outline(lang):
    """One line per unit: the course at a glance."""
    from learning.models import Unit

    return "\n".join(f"Unit {u.order}: {u.tr('title', lang)}" for u in Unit.objects.order_by("order"))


def material(question, context, lang):
    """
    The course text to put in front of the model for this question: the open
    lesson when there is one, else the best passages. "" when nothing fits.
    """
    parts = []
    lesson_id = context.get("lesson_id") if isinstance(context, dict) else None
    opened = lesson_text(lesson_id, lang) if lesson_id else None
    if opened:
        number, title, unit_title, text = opened
        parts.append(f"The learner is reading lesson {number} \"{title}\" (unit \"{unit_title}\"):\n{text}")
        passages = [p for p in search(question, lang, limit=2) if p["lesson_id"] != str(lesson_id)]
    else:
        passages = search(question, lang, limit=3)
    for p in passages:
        head = f" — {p['heading']}" if p["heading"] else ""
        parts.append(f"From lesson {p['number']} \"{p['lesson']}\"{head} (unit \"{p['unit']}\"):\n{p['text']}")
    if not parts:
        return ""
    return "Zinvest course units:\n" + outline(lang) + "\n\n" + "\n\n".join(parts)
