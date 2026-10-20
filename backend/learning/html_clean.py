"""
Allow-list cleaning for lesson HTML written by staff in the lesson editor.

Lesson bodies are shown to every learner, so what the server keeps is limited
to what the editor itself produces (see lesson_authoring_prompt.md): headings,
paragraphs, lists, task lists, quotes, code, maths, tables, images, links and
the inline marks, with only the attributes and style properties those use.
Everything else (scripts, event handlers, iframes, unknown tags, javascript:
links) is dropped; the text inside a dropped tag is kept unless the tag is one
whose content is code (script, style, …).
"""
import re
from html import escape, unescape
from html.parser import HTMLParser

TAGS = {
    "p", "h1", "h2", "h3", "h4", "strong", "b", "em", "i", "u", "s", "code", "pre", "mark", "span", "a", "br",
    "ul", "ol", "li", "blockquote", "hr", "img", "div", "label", "input",
    "table", "colgroup", "col", "thead", "tbody", "tr", "th", "td",
}
VOID = {"br", "hr", "img", "col", "input"}
DROP_WITH_CONTENT = {"script", "style", "iframe", "object", "embed", "noscript", "template", "svg", "math", "head", "title"}
ATTRS = {
    "*": {"style", "data-type", "data-color", "data-background-color", "data-text-align", "data-spacing"},
    "a": {"href", "target", "rel"},
    "img": {"src", "alt", "title", "width", "height", "data-width", "data-align"},
    "code": {"class"},
    "blockquote": {"data-quote-color"},
    "td": {"colspan", "rowspan", "colwidth"},
    "th": {"colspan", "rowspan", "colwidth"},
    "col": {"style", "span"},
    "ul": {"data-type"},
    "li": {"data-type", "data-checked"},
    "input": {"type", "checked", "disabled"},
    "div": {"data-latex"},
    "span": {"data-latex"},
    "ol": {"start", "type"},
}
STYLE_PROPS = {"color", "background-color", "font-size", "font-family", "text-align", "--quote-color",
               "line-height", "margin-top", "margin-bottom", "padding-left", "width", "min-width"}
SAFE_URL = re.compile(r"^(https?://|/(?!/)|#|mailto:)", re.I)
SAFE_VALUE = re.compile(r"^[#(),.%\-\w\s'\"]+$")
MAX_BYTES = 600_000


class _Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.stack = []  # open allowed tags
        self.drop = 0  # depth inside a tag dropped with its content

    def _attrs(self, tag, attrs):
        allowed = ATTRS["*"] | ATTRS.get(tag, set())
        kept = []
        for name, value in attrs:
            name = (name or "").lower()
            if name not in allowed or name.startswith("on"):
                continue
            value = value if value is not None else ""
            if name in ("href", "src"):
                value = value.strip()
                if not SAFE_URL.match(value) or value.lower().startswith(("javascript:", "data:")):
                    continue
            elif name == "style":
                value = self._style(value)
                if not value:
                    continue
            elif name == "class":
                value = " ".join(c for c in value.split() if c.startswith("language-"))
                if not value:
                    continue
            elif name == "target":
                value = "_blank"
            elif name == "rel":
                value = "noopener noreferrer nofollow"
            kept.append(f' {name}="{escape(value, quote=True)}"')
        if tag == "a" and any(a.startswith(" target=") for a in kept) and not any(a.startswith(" rel=") for a in kept):
            kept.append(' rel="noopener noreferrer nofollow"')
        return "".join(kept)

    @staticmethod
    def _style(value):
        parts = []
        for decl in value.split(";"):
            if ":" not in decl:
                continue
            prop, val = decl.split(":", 1)
            prop, val = prop.strip().lower(), val.strip()
            if prop in STYLE_PROPS and SAFE_VALUE.match(val) and "url" not in val.lower() and "expression" not in val.lower():
                parts.append(f"{prop}: {val}")
        return "; ".join(parts)

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self.drop or tag in DROP_WITH_CONTENT:
            if tag not in VOID:
                self.drop += 1
            return
        if tag not in TAGS:
            return
        self.out.append(f"<{tag}{self._attrs(tag, attrs)}>")
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if self.drop or tag not in TAGS:
            return
        self.out.append(f"<{tag}{self._attrs(tag, attrs)}>")
        if tag not in VOID:
            self.out.append(f"</{tag}>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.drop:
            if tag in DROP_WITH_CONTENT or tag not in VOID:
                self.drop -= 1
            return
        if tag in VOID or tag not in self.stack:
            return
        while self.stack:
            open_tag = self.stack.pop()
            self.out.append(f"</{open_tag}>")
            if open_tag == tag:
                break

    def handle_data(self, data):
        if not self.drop:
            self.out.append(escape(data, quote=False))

    def close(self):
        super().close()
        while self.stack:
            self.out.append(f"</{self.stack.pop()}>")
        return "".join(self.out)


def clean_lesson_html(html):
    """The allowed part of `html`. Raises ValueError when it is too big."""
    html = str(html or "")
    if len(html.encode("utf-8")) > MAX_BYTES:
        raise ValueError("too_big")
    cleaner = _Cleaner()
    cleaner.feed(html)
    return cleaner.close().strip()


def plain_text(html):
    """The words of a lesson body, for search and the AI's reading."""
    text = re.sub(r"<(br|/p|/h[1-6]|/li|/tr|/blockquote|/pre)\b[^>]*>", "\n", html or "", flags=re.I)
    text = re.sub(r"<(td|th)\b[^>]*>", " | ", text, flags=re.I)
    text = unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{2,}", "\n", text).strip()
