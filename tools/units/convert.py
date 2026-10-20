"""
Convert the Zinvest unit PDFs into lesson HTML the app's editor understands.

For every PDF: the unit title and subtitle, one lesson per section ("3.1 …"),
the glossary as a last lesson, and the review test as structured questions.
Text is copied as it is in the PDF (only joined into paragraphs); tables come
from PyMuPDF's table finder; the few real figures (unit 1) are saved as PNGs
under frontend/public/units/. A developer tool, not part of the app (it needs
`pip install pymupdf`). To add or replace a unit:

    1. put the PDFs in one folder and list them in FILES below (unit -> lang -> file)
    2. UNITS_PDF_DIR=<folder> python convert.py        # -> out/uNN.json
       UNITS_PDF_DIR=<folder> python convert.py 3 en   # one file, with a preview
    3. python finalize.py                              # -> backend/learning/content/units/
    4. python manage.py import_units [--only N]        # into the database
"""
import html
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import fitz

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SRC = Path(os.environ.get("UNITS_PDF_DIR") or REPO.parents[1])
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
PUBLIC = REPO / "frontend" / "public" / "units"

FILES = {
    1: {"en": "Unit 1 Eng.pdf", "ru": "Unit 1 Rus.pdf", "uz": "Unit 1 UZB.pdf"},
    2: {"en": "Unit 2 ENG.pdf", "ru": "Unit 2 RUS.pdf", "uz": "Unit 2 UZB.pdf"},
    3: {"en": "Unit 3 ENG (3).pdf", "ru": "Unit 3 RUS (2).pdf", "uz": "Unit 3 UZB (4).pdf"},
    4: {"en": "Unit 4 ENG (3).pdf", "ru": "Unit 4 RUS (3).pdf", "uz": "Unit 4 UZB (3).pdf"},
    5: {"en": "Unir 5 ENG.pdf", "ru": "Unit 5 RUS.pdf", "uz": "Unit 5 UZB.pdf"},
    6: {"en": "Unit 6 ENG.pdf", "uz": "Unit 6 UZB.pdf"},
    7: {"en": "Unit 7 ENG.pdf", "ru": "Unti 7 RUS.pdf", "uz": "Unit 7 UZB.pdf"},
    8: {"en": "Unit 8 ENG (3).pdf", "ru": "Unit 8 RUS (3).pdf", "uz": "Unit 8 UZB (3).pdf"},
    9: {"en": "Unit 9 ENG (3).pdf", "ru": "Unit 9 RUS (3).pdf", "uz": "Unit 9 UZB (3).pdf"},
    10: {"en": "Unit 10 ENG.pdf", "ru": "Unit 10 RUS.pdf", "uz": "Unit 10 UZB.pdf"},
    11: {"en": "Unit 11 ENG.pdf"},
}

GLOSSARY = re.compile(r"(glossary|глоссарий|ключевые термины|key terms|lug['‘’ʻ`]?at|atamalar|асосий атамалар|словарь)", re.I)
TEST = re.compile(r"(review test|итоговый тест|проверочный тест|^тест\b|test savollari|yakuniy test|sinov testi|^test\b|takrorlash testi|тест по блоку|тест для повторения|nazorat testi)", re.I)
QSTART = re.compile(r"^(?:Q|В|S|ВОПРОС\s*|Вопрос\s*|SAVOL\s*|Savol\s*)(\d{1,2})\b\s*(?:\[[^\]]*\])?\s*[.:)]?\s*(.*)$")
OPTION = re.compile(r"^([A-DА-Г])\s*[)\.]\s*(.*)$")
KEY = re.compile(r"^(?:Q|В|S|ВОПРОС\s*|Вопрос\s*|SAVOL\s*|Savol\s*)?(\d{1,2})\s*[:：\-–]\s*([A-DА-ГVG])\b\)?\s*[—–\-:.]?\s*(.*)$")
# "V" and "G" are the Russian В and Г transliterated in the Uzbek answer keys.
LETTER = {"A": 0, "B": 1, "C": 2, "D": 3, "А": 0, "Б": 1, "В": 2, "Г": 3, "V": 2, "G": 3}
SKIP_LINE = re.compile(r"^(page \d+|страница \d+|sahifa \d+|\d+-sahifa|zinvest|a zinvest|i zinvest|[I/]|\d{1,2})$", re.I)
PUA = re.compile(r"[\ue000-\uf8ff\u25a0-\u25ff\u2600-\u27bf]")


def esc(s):
    return html.escape(s, quote=False)


def clean(s):
    s = PUA.sub("", s).replace("\u00ad", "")
    return re.sub(r"[ \t]+", " ", s).strip()


class Line:
    __slots__ = ("page", "x", "y", "x1", "y1", "size", "bold", "italic", "spans", "text", "raw", "order")

    def __init__(self, page, l, order):
        spans = []
        for s in l["spans"]:
            if "dingbat" in s["font"].lower():
                continue
            t = PUA.sub("", s["text"])
            if not t.strip():
                if spans:
                    spans.append((" ", False, False))
                continue
            spans.append((t, bool(s["flags"] & 16) or "bold" in s["font"].lower(), bool(s["flags"] & 2) or "oblique" in s["font"].lower() or "italic" in s["font"].lower()))
        self.page = page
        self.x, self.y, self.x1, self.y1 = l["bbox"]
        main = max(l["spans"], key=lambda s: len(s["text"].strip()))
        self.size = round(main["size"], 1)
        self.spans = spans
        self.text = clean("".join(t for t, _, _ in spans))
        self.raw = self.text
        textual = [b for t, b, _ in spans if t.strip()]
        self.bold = bool(textual) and all(textual)
        self.italic = bool(spans) and all(i for t, _, i in spans if t.strip())
        self.order = order

    def html(self):
        out = []
        for t, b, i in self.spans:
            t = esc(t)
            if b and t.strip():
                t = f"<strong>{t}</strong>"
            if i and t.strip():
                t = f"<em>{t}</em>"
            out.append(t)
        s = "".join(out)
        s = re.sub(r"</strong>(\s*)<strong>", r"\1", s)
        return re.sub(r"\s+", " ", s).strip()


def table_html(rows, header):
    def cell(text, tag, single_row):
        lines = [clean(l) for l in (text or "").split("\n") if clean(l)]
        if not lines:
            return f"<{tag}><p></p></{tag}>"
        parts, bullets = [], []
        for i, l in enumerate(lines):
            if l.startswith(("•", "- ", "– ")):
                bullets.append(l.lstrip("•-– ").strip())
                continue
            if bullets:
                parts.append("<ul>" + "".join(f"<li><p>{esc(b)}</p></li>" for b in bullets) + "</ul>")
                bullets = []
            # In a side-by-side box (one row) the first line is the box's title.
            if single_row and i == 0 and tag == "td":
                parts.append(f"<p><strong>{esc(l)}</strong></p>")
            elif parts and not parts[-1].startswith("<ul") and not (single_row and i == 1 and tag == "td"):
                parts[-1] = parts[-1][:-4] + " " + esc(l) + "</p>"
            else:
                parts.append(f"<p>{esc(l)}</p>")
        if bullets:
            parts.append("<ul>" + "".join(f"<li><p>{esc(b)}</p></li>" for b in bullets) + "</ul>")
        return f"<{tag}>{''.join(parts)}</{tag}>"

    single = len(rows) == 1
    out = ["<table><tbody>"]
    for r, row in enumerate(rows):
        tag = "th" if header and r == 0 and not single else "td"
        out.append("<tr>" + "".join(cell(c, tag, single) for c in row) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def convert(unit, lang, verbose=False):
    path = SRC / FILES[unit][lang]
    doc = fitz.open(path)
    lines, extras = [], []  # extras: (page, y, html)
    order = 0
    fig_no = 0
    header_title = ""
    for pno, page in enumerate(doc):
        H = page.rect.height
        tables = []
        if pno >= 2:
            try:
                tables = page.find_tables().tables
            except Exception:  # noqa: BLE001
                tables = []
        boxes = []
        # A section title in a coloured band ("1.1 | Definition of Finance")
        # looks like a table to the finder: a box holding a big heading is not one.
        big = []
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                sp = [s for s in l["spans"] if s["text"].strip()]
                if sp and max(s["size"] for s in sp) >= 13.5:
                    x0, y0, x1, y1 = l["bbox"]
                    big.append(((x0 + x1) / 2, (y0 + y1) / 2))
        for t in tables:
            x0, y0, x1, y1 = t.bbox
            if any(x0 <= cx <= x1 and y0 <= cy <= y1 for cx, cy in big):
                continue
            rows = [[c or "" for c in r] for r in t.extract()]
            rows = [r for r in rows if any(clean(c) for c in r)]
            if not rows:
                continue
            ncols = max(len(r) for r in rows)
            boxes.append(t.bbox)
            if ncols == 1:
                body = " ".join(clean(c) for r in rows for c in r if clean(c))
                extras.append((pno, y0, f'<blockquote><p>{esc(body)}</p></blockquote>', "table"))
            else:
                extras.append((pno, y0, table_html(rows, header=len(rows) > 1), "table"))
        # Figures: wide images; the square 640px ones are the watermark logo.
        for info in page.get_image_info(xrefs=True):
            x0, y0, x1, y1 = info["bbox"]
            if (x1 - x0) < 250 or info.get("width", 0) in (640,) and info.get("height", 0) == 640:
                continue
            if info.get("width", 0) < 500:
                continue
            fig_no += 1
            dest = PUBLIC / f"u{unit:02d}" / lang
            dest.mkdir(parents=True, exist_ok=True)
            pix = fitz.Pixmap(doc, info["xref"])
            if pix.n - pix.alpha >= 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            name = f"fig-{fig_no}.png"
            pix.save(dest / name)
            extras.append((pno, y0, f'<img src="/units/u{unit:02d}/{lang}/{name}" alt="">', "image"))
        for b in page.get_text("dict")["blocks"]:
            if b["type"] != 0:
                continue
            for l in b["lines"]:
                ln = Line(pno, l, order)
                order += 1
                if not ln.text:
                    continue
                if ln.size <= 8.6 and (ln.y < 60 or ln.y > H - 60):
                    if not header_title and ":" in ln.text and ("|" in ln.text):
                        header_title = ln.text.split(":", 1)[1].strip()
                    continue
                if SKIP_LINE.match(ln.text) and ln.size < 40:
                    if ln.text.lower() in ("zinvest", "a zinvest", "i zinvest", "i", "/") or ln.size > 14:
                        continue
                if ln.text.lower() == "zinvest" or (ln.text.upper() == "ZINVEST" and ln.size >= 14):
                    continue
                cx = (ln.x + l["bbox"][2]) / 2
                cy = (ln.y + ln.y1) / 2
                if any(bx0 - 2 <= cx <= bx1 + 2 and by0 - 2 <= cy <= by1 + 2 for bx0, by0, bx1, by1 in boxes):
                    ln.text = ""  # inside a table: the table carries it
                    ln.order = order
                    lines.append(ln)
                    continue
                lines.append(ln)

    texts = [l for l in lines if l.text]
    body = Counter(l.size for l in texts if not l.bold and len(l.text) > 30).most_common(1)[0][0]
    # The main text column: the leftmost x that a good share of long body lines start at.
    right_edge = sorted(l.x1 for l in texts if l.size == body)[int(len([1 for l in texts if l.size == body]) * 0.9)]
    xs = Counter(round(l.x) for l in texts if l.size == body and not l.bold and len(l.text) > 50)
    top = xs.most_common(1)[0][1]
    body_x = min(x for x, n in xs.items() if n >= top * 0.25)

    # Page 1: title (largest text) and the description under it.
    first = [l for l in texts if l.page == 0]
    title, subtitle = header_title, ""
    if first:
        big = max(l.size for l in first if l.text.lower() != "zinvest")
        idx = [i for i, l in enumerate(first) if l.size == big]
        after = first[idx[-1] + 1:] if idx else []
        desc = []
        for l in after:
            if re.match(r"^(sections|разделы|bo['‘’]?limlar|includes|включает|o['‘’]?z ichiga|unit \d|блок \d)", l.text, re.I) or l.size >= big:
                break
            if l.size >= body - 0.5 and not l.text.lower().startswith("finance"):
                desc.append(l.text)
        subtitle = " ".join(desc)
    if len(subtitle) > 200:
        subtitle = subtitle[:197].rsplit(" ", 1)[0] + "…"

    # Walk the flow: sections, then glossary, then test.
    items = []  # (page, order, kind, payload)
    for l in lines:
        items.append((l.page, l.order, "line", l))
    for pno, y, h, kind in extras:
        nxt = [l for l in lines if l.page == pno and l.y >= y - 1]
        o = min((l.order for l in nxt), default=max((l.order for l in lines if l.page == pno), default=0) + 0.5) - 0.1
        items.append((pno, o, kind, h))
    items.sort(key=lambda it: (it[0], it[1]))

    sections, glossary, test_lines = [], None, []
    current = None
    mode = "intro"
    heading_sizes = sorted({l.size for l in texts if l.bold and body + 0.4 < l.size < 14 and len(l.text) < 90}, reverse=True)
    h2_size = heading_sizes[0] if heading_sizes else 99

    # Big bold headings (14pt+) from page 2 on, with a heading that runs over
    # several lines ("Словарь / ключевых / терминов") merged into one.
    heads, consumed = [], set()
    flow = [l for l in lines if l.text]
    for i, l in enumerate(flow):
        if id(l) in consumed or not (l.bold and l.size >= 14 and l.page >= 1 and re.search(r"[A-Za-zА-Яа-яЁё]", l.text)):
            continue
        if l.text.lower() == "zinvest":
            continue
        text = l.text
        last = l
        for nxt in flow[i + 1:i + 4]:
            if nxt.page == l.page and nxt.bold and abs(nxt.size - l.size) < 0.2 and 0 < nxt.y - last.y < l.size * 1.7 and abs(nxt.x - l.x) < 6:
                text += " " + nxt.text
                consumed.add(id(nxt))
                last = nxt
            else:
                break
        heads.append((l, clean(text)))

    is_gloss = lambda t: re.search(r"(glossar|глоссар|словар|термин|lug['‘’ʻ`]?at|atamalar|key terms)", t, re.I)
    is_test = lambda t: re.search(r"(\btest|quiz|тест|вопрос|savol|sinov)", t, re.I)
    numbered = [(l, t) for l, t in heads if re.match(rf"^{unit}\.\d", t)]
    section_ids = {}
    if len(numbered) >= 3:
        for l, t in numbered:
            m = re.match(rf"^({unit})\.(\d)\s*(.*)$", t)
            section_ids[id(l)] = (f"{unit}.{m.group(2)}", m.group(3).strip())
    else:
        # No numbers in the titles: the sections are the heading size used most,
        # leaving out the unit's own title and the table of contents.
        norm = lambda s: re.sub(r"[^a-zа-яё0-9ўқғҳ]", "", re.sub(r"^\d+\s*", "", s.lower()))
        cover = [norm(title), norm(" ".join(l.text for l in texts if l.page == 0 and l.size >= 20))]
        is_toc = lambda t: re.search(r"(contents|содержание|mundarija|оглавление)", t, re.I)
        first_page = min((l.page for l, t in heads if not is_toc(t)), default=0)

        def is_title(l, t):
            # The unit title, whole, or its first line on the first content page;
            # a heading that merely starts with the same words later on
            # ("Оценка активов", "Moliya nima uchun…") is a section.
            n = norm(t)
            return bool(n) and any(c and (n == c or (l.page == first_page and len(n) >= 8 and c.startswith(n))) for c in cover)
        usable = [(l, t) for l, t in heads if not is_gloss(t) and not is_test(t) and not is_title(l, t) and not is_toc(t)]
        sizes = Counter(l.size for l, t in usable)
        sec_size = sizes.most_common(1)[0][0] if sizes else None
        k = 0
        for l, t in usable:
            if l.size == sec_size:
                k += 1
                section_ids[id(l)] = (f"{unit}.{k}", re.sub(r"^\d{1,2}\.\d\s*", "", t))
    special = {id(l): ("gloss" if is_gloss(t) else "test", t) for l, t in heads
               if id(l) not in section_ids and (is_gloss(t) or is_test(t))}

    for page, _, kind, payload in items:
        if kind == "line" and mode == "test" and payload.raw:
            test_lines.append(payload.raw)
            continue
        if kind != "line":
            if mode == "test":
                continue
            if current is not None:
                current["blocks"].append(("raw", payload))
            continue
        l = payload
        if not l.text or id(l) in consumed:
            continue
        if id(l) in section_ids:
            num, ttl = section_ids[id(l)]
            mode = "section"
            current = {"num": num, "title": ttl, "blocks": []}
            sections.append(current)
            continue
        if id(l) in special and sections:
            what, ttl = special[id(l)]
            if what == "test":
                mode = "test"
                continue
            mode = "glossary"
            glossary = {"num": "", "title": ttl, "blocks": []}
            current = glossary
            continue
        if mode == "intro" or current is None:
            continue
        # Number boxes next to a section title ("1.1", "2." "1") carry nothing more.
        if re.fullmatch(r"\d{1,2}\.?\d?", l.text) and l.bold:
            continue
        current["blocks"].append(("line", l))

    def render(blocks):
        out = []
        para = None  # dict(kind, x, last_y, size, html, indented)

        def flush():
            nonlocal para
            if para:
                out.append(para)
            para = None

        for kind, p in blocks:
            if kind == "raw":
                flush()
                out.append({"kind": "raw", "html": p})
                continue
            l = p
            t = l.text
            is_bullet = t.startswith(("•", "▪", "◦"))
            gap = (l.y - para["last_y"]) if para and para["page"] == l.page else 999
            if l.bold and l.size > body + 0.4 and len(t) < 90:
                flush()
                level = "h2" if l.size >= h2_size else "h3"
                out.append({"kind": level, "html": esc(t), "x": l.x})
                continue
            new = (
                para is None
                or is_bullet
                or gap > l.size * 1.9
                or gap < -2
                or abs(l.size - para["size"]) > 0.6
                or (para["kind"] != "li" and abs(l.x - para["x"]) > 4)
                or (para["kind"] == "li" and l.x < para["x"] + 2)
                or (para["bold_only"] and not l.bold)
                or (l.bold and not para["bold_only"] and len(t) < 70 and para["html"].endswith((".", ":", "!", "?")))
                # The previous line stopped well short of the column: that was a paragraph end.
                or (para["kind"] == "p" and para["last_x1"] < right_edge - 70 and re.match(r"^[A-ZА-ЯЁЎҚҒҲ0-9$€£\"«(]", t))
            )
            h = l.html()
            if is_bullet:
                h = re.sub(r"^(<strong>)?\s*[•▪◦]\s*", r"\1", h)
            if new:
                flush()
                para = {"kind": "li" if is_bullet else "p", "x": l.x, "page": l.page, "last_y": l.y, "last_x1": l.x1, "size": l.size,
                        # An italic line set in from the margin is a figure caption, not a callout.
                        "html": h, "bold_only": l.bold, "indented": l.x >= body_x + 10 and not l.italic, "italic": l.italic}
            else:
                prev = para["html"]
                if re.search(r"[A-Za-zА-Яа-я]-$", prev) and re.match(r"^[a-zа-я]", t):
                    para["html"] = prev[:-1] + h
                else:
                    para["html"] = prev + " " + h
                para["last_y"] = l.y
                para["last_x1"] = l.x1
                para["bold_only"] = para["bold_only"] and l.bold
        flush()

        # Group into HTML: lists, callouts (indented runs) and the rest.
        html_out = []
        i = 0
        while i < len(out):
            b = out[i]
            if b["kind"] == "raw":
                html_out.append(b["html"]); i += 1; continue
            if b["kind"] in ("h2", "h3"):
                html_out.append(f"<{b['kind']}>{b['html']}</{b['kind']}>"); i += 1; continue
            if b.get("indented") and b["kind"] == "p":
                run = []
                while i < len(out) and out[i].get("indented") and out[i]["kind"] in ("p", "li"):
                    run.append(out[i]); i += 1
                html_out.append("<blockquote>" + group(run) + "</blockquote>")
                continue
            run = []
            while i < len(out) and out[i]["kind"] in ("p", "li") and not (out[i].get("indented") and out[i]["kind"] == "p"):
                run.append(out[i]); i += 1
            html_out.append(group(run))
        return "".join(html_out)

    def group(run):
        s, lis = [], []
        for b in run:
            if b["kind"] == "li":
                lis.append(b["html"]); continue
            if lis:
                s.append("<ul>" + "".join(f"<li><p>{x}</p></li>" for x in lis) + "</ul>"); lis = []
            h = re.sub(r"^(<strong>|<em>)\s+", lambda m: m.group(1), b["html"].strip())
            if b.get("bold_only") and not h.startswith("<strong>"):
                h = f"<strong>{h}</strong>"
            if b.get("italic") and not h.startswith("<em>"):
                h = f"<em>{h}</em>"
            s.append(f"<p>{h}</p>")
        if lis:
            s.append("<ul>" + "".join(f"<li><p>{x}</p></li>" for x in lis) + "</ul>")
        return "".join(s)

    lessons = [{"num": s["num"], "title": s["title"], "html": render(s["blocks"])} for s in sections]
    gloss = {"title": glossary["title"], "html": render(glossary["blocks"])} if glossary else None
    questions = parse_test(test_lines)
    return {"unit": unit, "lang": lang, "title": title, "subtitle": subtitle, "lessons": lessons,
            "glossary": gloss, "test": questions, "body_size": body, "body_x": body_x}


def parse_test(lines):
    # Re-join "ВОПРОС" / "2: Б" that the key table split over two lines.
    joined = []
    for t in lines:
        if joined and re.fullmatch(r"(ВОПРОС|Вопрос|SAVOL|Savol)", joined[-1]) and re.match(r"^\d{1,2}\s*:", t):
            joined[-1] = joined[-1] + " " + t
        else:
            joined.append(t)
    qs, keys = {}, {}
    cur, opt, mode = None, None, "q"
    last_key = None
    for t in joined:
        if re.match(r"^(score guide|оценка|шкала|natijalarni baholash|baholash|ballar)", t, re.I):
            break
        k = KEY.match(t)
        if k and (mode == "key" or len(qs) >= 12 or (k.group(1) in qs and qs[k.group(1)]["choices"])):
            mode = "key"
            last_key = k.group(1)
            keys[last_key] = {"letter": k.group(2), "explanation": clean(k.group(3))}
            continue
        if mode == "key":
            if last_key:
                keys[last_key]["explanation"] = (keys[last_key]["explanation"] + " " + t).strip()
            continue
        q = QSTART.match(t)
        if q and not OPTION.match(t):
            cur = {"n": q.group(1), "prompt": clean(q.group(2)), "choices": []}
            if re.fullmatch(r"\[[^\]]*\]", cur["prompt"] or ""):
                cur["prompt"] = ""
            qs[cur["n"]] = cur
            opt = None
            continue
        o = OPTION.match(t)
        if cur is not None and o and len(cur["choices"]) < 4 and LETTER.get(o.group(1)) == len(cur["choices"]):
            cur["choices"].append(clean(o.group(2)))
            opt = True
            continue
        if cur is not None:
            if opt:
                cur["choices"][-1] = (cur["choices"][-1] + " " + t).strip()
            else:
                cur["prompt"] = (cur["prompt"] + " " + t).strip()
    out = []
    for n in sorted(qs, key=int):
        q = qs[n]
        key = keys.get(n) or {}
        out.append({"n": int(n), "prompt": q["prompt"], "choices": q["choices"],
                    "answer_index": LETTER.get(key.get("letter", ""), None), "explanation": key.get("explanation", "")})
    return out


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        r = convert(int(sys.argv[1]), sys.argv[2])
        print("TITLE:", r["title"], "| SUB:", r["subtitle"][:120], "| body", r["body_size"], r["body_x"])
        for les in r["lessons"]:
            print(f"--- {les['num']} {les['title']}  ({len(les['html'])} chars)")
        if r["glossary"]:
            print("--- GLOSSARY", r["glossary"]["title"], len(r["glossary"]["html"]))
        print("TEST:", len(r["test"]), "parsed;", sum(1 for q in r["test"] if len(q["choices"]) == 4 and q["answer_index"] is not None), "complete")
        if len(sys.argv) > 3:
            idx = int(sys.argv[3])
            print(r["lessons"][idx]["html"][:6000])
        sys.exit()
    for unit, langs in FILES.items():
        data = {"unit": unit, "langs": {}}
        for lang in langs:
            data["langs"][lang] = convert(unit, lang)
        (OUT / f"u{unit:02d}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        summary = {lang: (len(d["lessons"]), len(d["test"]), bool(d["glossary"])) for lang, d in data["langs"].items()}
        print(unit, summary)
