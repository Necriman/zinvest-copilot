"""
Gemini client wrapper + feature→model routing (the unified ``google-genai`` SDK).

Model routing (env-overridable, see settings.GEMINI_MODEL_*):
  * ADVISOR          → PRO         (deep financial reasoning)
  * ONBOARDING_PARSE → FLASH       (fast startup-form parsing)
  * CEO_MATCH        → FLASH-LITE  (async CEO matchmaking, background task)
  * ROADMAP          → FLASH       (startup roadmap, structured JSON)
  * COPILOT          → FLASH       (Copilot finance work, structured JSON)

Graceful degradation: if GEMINI_API_KEY is unset OR the google-genai package is
not installed, ``generate`` returns a clearly-marked ``[STUB]`` result instead of
raising, so the quota + logging path still exercises end-to-end without a key.
Real (post-key) API/network failures raise ``GeminiError``.
"""
import logging
import time
from dataclasses import dataclass, field

from django.conf import settings

log = logging.getLogger("ai_engine")

# Feature identifiers — these strings are also the AIUsageLog.feature values.
FEATURE_ADVISOR = "ADVISOR"
FEATURE_ONBOARDING_PARSE = "ONBOARDING_PARSE"
FEATURE_CEO_MATCH = "CEO_MATCH"
FEATURE_STUDY_PLAN = "STUDY_PLAN"
FEATURE_ROADMAP = "ROADMAP"
FEATURE_COPILOT = "COPILOT"


class GeminiError(Exception):
    """A real (non-stub) Gemini call failed."""


@dataclass
class GeminiResult:
    text: str
    model_version: str
    input_tokens: int
    output_tokens: int
    is_stub: bool = False
    # Pages Google Search found when the call was grounded: [{"title", "url"}].
    sources: list = field(default_factory=list)


def resolve_model(feature):
    """Map a feature to its configured model id (env-overridable)."""
    return {
        FEATURE_ADVISOR: settings.GEMINI_MODEL_PRO,
        FEATURE_ONBOARDING_PARSE: settings.GEMINI_MODEL_FLASH,
        FEATURE_CEO_MATCH: settings.GEMINI_MODEL_FLASH_LITE,
        FEATURE_STUDY_PLAN: settings.GEMINI_MODEL_FLASH,
        FEATURE_ROADMAP: settings.GEMINI_MODEL_FLASH,
        FEATURE_COPILOT: settings.GEMINI_MODEL_FLASH,
    }.get(feature, settings.GEMINI_MODEL_FLASH)


_client = None
_client_tried = False


def _get_client():
    """Lazy singleton. Returns None when unavailable (no key / SDK not installed)."""
    global _client, _client_tried
    if _client is not None:
        return _client
    if _client_tried:
        return None
    _client_tried = True

    if not settings.GEMINI_API_KEY:
        return None
    try:
        from google import genai
    except ImportError:
        log.warning("google-genai not installed; AI engine running in stub mode.")
        return None

    _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


# Model ids this key may no longer call. Google retires them without warning —
# gemini-2.5-pro started answering "no longer available to new users" in 2026 —
# and an advisor that 404s is worse than one answering on a smaller model. The
# first refusal is remembered so the dead id is not dialled again this process.
_retired = set()


# A busy model answers 503/UNAVAILABLE; one retry turns that into an answer
# instead of an apology, and the chat is already showing "typing…".
TRANSIENT_RETRIES = 1
RETRY_PAUSE_SEC = 1.5


def _is_retired(exc):
    detail = str(exc).lower()
    return "no longer available" in detail and "model" in detail


def _is_transient(exc):
    detail = str(exc).lower()
    return any(word in detail for word in ("503", "unavailable", "overloaded", "500 internal", "deadline"))


def _is_quota(exc):
    """The key's per-minute or per-day allowance for this model is used up."""
    detail = str(exc).lower()
    return "resource_exhausted" in detail or ("429" in detail and "quota" in detail)


def _alternatives(model):
    """Other configured models, each with its own quota, to try when `model` is out of it."""
    seen = {model}
    out = []
    for m in (settings.GEMINI_MODEL_FLASH, settings.GEMINI_MODEL_FLASH_LITE, settings.GEMINI_MODEL_FALLBACK, settings.GEMINI_MODEL_PRO):
        if m and m not in seen and m not in _retired:
            seen.add(m)
            out.append(m)
    return out


def run_model(model, contents, *, config=None):
    """
    ``generate_content`` on `model`, retrying past a busy server, past a model
    Google has retired for this key, and past a model whose quota is used up
    (quotas are per model, so another configured model can still answer).

    Returns (response, model_actually_used) so the caller logs what answered.
    """
    client = _get_client()
    fallback = settings.GEMINI_MODEL_FALLBACK
    chosen = fallback if model in _retired else model
    retries_left = TRANSIENT_RETRIES
    spare = _alternatives(chosen)
    while True:
        try:
            return client.models.generate_content(model=chosen, contents=contents, config=config), chosen
        except Exception as exc:
            if _is_retired(exc) and chosen != fallback:
                _retired.add(chosen)
                log.warning("gemini_model_retired model=%s falling_back_to=%s", chosen, fallback)
                chosen = fallback
                continue
            if _is_quota(exc) and spare:
                log.warning("gemini_quota_exhausted model=%s trying=%s", chosen, spare[0])
                chosen = spare.pop(0)
                continue
            if _is_transient(exc) and retries_left:
                retries_left -= 1
                log.info("gemini_busy model=%s retrying err=%s", chosen, type(exc).__name__)
                time.sleep(RETRY_PAUSE_SEC)
                continue
            raise


def _estimate_tokens(text):
    # ~4 chars/token heuristic — only used by the stub path so the quota counter
    # still moves in a no-key demo.
    return max(1, len(text or "") // 4)


def _stub(feature, contents):
    model = resolve_model(feature)
    text = (
        "[STUB] The Gemini API key is not configured (or the SDK is unavailable), "
        "so this is a placeholder response that lets the app run end-to-end without "
        f"a key. Feature={feature}; the live model would be '{model}'."
    )
    return GeminiResult(
        text=text,
        model_version="stub",
        input_tokens=_estimate_tokens(contents if isinstance(contents, str) else str(contents)),
        output_tokens=_estimate_tokens(text),
        is_stub=True,
    )


def generate(feature, contents, *, config=None):
    """
    Run a single Gemini generation for ``feature``. Never raises for the missing
    -key case (returns a stub); wraps real API failures in ``GeminiError``.
    """
    client = _get_client()
    if client is None:
        return _stub(feature, contents)

    model = resolve_model(feature)
    try:
        resp, model = run_model(model, contents, config=config)
    except Exception as exc:  # SDK surfaces many error types; normalize to one.
        log.error("gemini_call_failed feature=%s model=%s err=%s", feature, model, exc)
        raise GeminiError(str(exc)) from exc

    usage = getattr(resp, "usage_metadata", None)
    return GeminiResult(
        text=getattr(resp, "text", "") or "",
        model_version=model,
        input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
        output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
        sources=_sources(resp),
    )


def _sources(resp, limit=8):
    """The web pages a Google-Search-grounded answer drew on, one per site."""
    try:
        meta = resp.candidates[0].grounding_metadata
        chunks = getattr(meta, "grounding_chunks", None) or []
    except (AttributeError, IndexError, TypeError):
        return []
    out, seen = [], set()
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        url = getattr(web, "uri", "") or ""
        title = (getattr(web, "title", "") or "").strip()
        if not url or title in seen:
            continue
        seen.add(title)
        out.append({"title": title or url, "url": url})
        if len(out) >= limit:
            break
    return out
