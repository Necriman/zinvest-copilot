"""
The three languages the product speaks, and which one a request wants.

The interface language is whatever the learner picked in the switcher: the
site sends it with every call as Accept-Language (a few endpoints also take an
explicit ?lang= or "lang", which wins). The middleware makes it the current
language for the whole request, so content stored in several languages — the
course, the Drills, the onboarding questions — is picked with `current()`
without threading a parameter through every service, and the bot does the same
with `using(link.lang)` around what it sends.

Base content is written in English; a missing translation falls back to it.
"""
import contextvars
from contextlib import contextmanager

LANGS = ("ru", "en", "uz")
BASE = "en"

# How the AI is told which language to answer in. Uzbek needs the script
# spelled out, or a model may well answer in Cyrillic.
NAMES = {"ru": "Russian", "en": "English", "uz": "Uzbek (Latin script)"}

_current = contextvars.ContextVar("zinvest_lang", default=BASE)


def normalize(value):
    """'ru-RU' → 'ru'; anything we do not speak → None."""
    code = str(value or "").strip().lower()[:2]
    return code if code in LANGS else None


def from_request(request, default=BASE):
    """An explicit ?lang= first, then Accept-Language (the switcher), then `default`."""
    explicit = normalize(request.GET.get("lang"))
    if explicit:
        return explicit
    for part in (request.headers.get("Accept-Language") or "").split(","):
        code = normalize(part.split(";")[0])
        if code:
            return code
    return default


def current():
    return _current.get()


def activate(lang):
    """Switch the current language until `deactivate(token)`; for code that
    only learns the language halfway through (the bot finds the chat first)."""
    return _current.set(normalize(lang) or BASE)


def deactivate(token):
    _current.reset(token)


@contextmanager
def using(lang):
    """Make `lang` the current language for a block (the bot, commands, tests)."""
    token = _current.set(normalize(lang) or BASE)
    try:
        yield
    finally:
        _current.reset(token)


def name(lang=None):
    return NAMES.get(normalize(lang) or current(), NAMES[BASE])


def pick(value, lang=None):
    """A {lang: text} mapping → the text in `lang`, else English, else any; a plain value as is."""
    if isinstance(value, dict):
        lang = normalize(lang) or current()
        return value.get(lang) or value.get(BASE) or next(iter(value.values()), "")
    return value


class LanguageMiddleware:
    """Makes the request's language the current one for everything it calls."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with using(from_request(request)):
            return self.get_response(request)
