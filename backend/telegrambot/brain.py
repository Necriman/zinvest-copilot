"""
What the bear understands: a photo of a receipt, a voice note, or a question.

Receipts and voice notes come back as one small dict the chat can confirm
before anything is written to the books:

    {"kind": "spending"|"revenue", "amount": 45000.0, "currency": "UZS",
     "category": "Ingredients", "description": "Korzinka", "date": "2026-09-20",
     "confidence": 0.82, "note": "what the bear wants to say about it"}

Every call goes through ai_engine so it lands in the learner's AI quota and the
usage log — the bot must not be a way around either.
"""
import json
import logging
import os
import time
from datetime import date

from django.utils import timezone
from django.conf import settings

from ai_engine import gemini
from ai_engine.models import AIUsageLog
from ai_engine.quota import consume_and_log

log = logging.getLogger("telegrambot")

# Categories the app already uses, so a receipt lands where the learner expects.
CATEGORIES = [
    "Продукты", "Сырьё и товары", "Аренда", "Зарплаты", "Транспорт", "Реклама",
    "Оборудование", "Коммунальные", "Налоги", "Связь и интернет", "Прочее",
]

RECEIPT_PROMPT = """You read a photo of a receipt, an invoice or a payment screenshot for a small
business owner and return ONE JSON object, nothing else:

{"kind": "spending" or "revenue",
 "amount": number (the TOTAL paid, no currency symbol, dot as decimal separator),
 "currency": "UZS" | "USD" | "RUB" | "EUR" | "" ,
 "category": one of %s,
 "description": the shop or counterparty name, up to 60 characters,
 "date": "YYYY-MM-DD" if the receipt shows one, else "",
 "confidence": 0..1 — how sure you are of the amount,
 "note": one short sentence in %s about what this looks like}

Rules: a shop receipt is "spending"; a sales report or an incoming payment is
"revenue". If you cannot find a total, set amount to 0 and say so in note.
Never invent a number you cannot see."""

VOICE_PROMPT = """Listen to this short voice note from a small business owner and return ONE JSON
object, nothing else:

{"transcript": what was said, verbatim,
 "kind": "spending" or "revenue" or "question",
 "amount": number (0 if the note is a question),
 "currency": "UZS" | "USD" | "RUB" | "EUR" | "",
 "category": one of %s,
 "description": what it was for, up to 60 characters,
 "date": "YYYY-MM-DD" if a date is named, else "",
 "confidence": 0..1,
 "note": one short sentence in %s}

"I spent 50 thousand on flour" is spending. "How do I price my bread?" is a
question — then only transcript, kind and note matter."""

LANG_NAME = {"ru": "Russian", "en": "English", "uz": "Uzbek"}


def _json_config():
    """Ask the SDK for JSON when it is available; harmless when it is not."""
    try:
        from google.genai import types
    except ImportError:
        return None
    return _config(json_mode=True)


def model_name():
    return os.environ.get("TELEGRAM_AI_MODEL") or settings.GEMINI_MODEL_FLASH


def _config(json_mode=False):
    """Small bot replies use bounded generation; the website's config is untouched."""
    from google.genai import types

    timeout = max(5, min(60, int(os.environ.get("TELEGRAM_AI_TIMEOUT_SECONDS", "25"))))
    options = {
        "http_options": types.HttpOptions(timeout=timeout * 1000),
        "max_output_tokens": 1400 if json_mode else 900,
        "temperature": 0.2 if json_mode else 0.4,
    }
    if json_mode:
        options["response_mime_type"] = "application/json"
    # Only these known models support disabling thinking. Custom models keep
    # their native defaults rather than receiving an incompatible parameter.
    if model_name() in ("gemini-2.5-flash", "gemini-2.5-flash-lite"):
        options["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    return types.GenerateContentConfig(**options)


def _generate(contents, *, json_mode=False):
    """Reuse the configured client, with separate model/latency settings for the bot."""
    started = time.monotonic()
    model = model_name()
    try:
        if gemini._get_client() is None:
            return gemini.GeminiResult("", "unavailable", 0, 0, is_stub=True)
        # run_model retries on the fallback if this id has been retired.
        response, model = gemini.run_model(model, contents, config=_config(json_mode=json_mode))
    except Exception as exc:
        # Avoid logging prompt contents, credentials or provider URLs.
        log.warning("bot_ai_failed model=%s error=%s code=%s seconds=%.2f",
                    model, type(exc).__name__, getattr(exc, "code", None), time.monotonic() - started)
        raise gemini.GeminiError("Bot AI provider request failed") from exc
    usage = getattr(response, "usage_metadata", None)
    return gemini.GeminiResult(
        text=getattr(response, "text", "") or "", model_version=model,
        input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
        output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
    )


def _part(data, mime_type):
    from google.genai import types

    return types.Part.from_bytes(data=data, mime_type=mime_type)


def _parse(text):
    """Pull the JSON object out of a model answer, tolerating code fences."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _clean(data, lang):
    """Normalise whatever the model said into the shape the chat expects."""
    if not isinstance(data, dict):
        return None
    kind = str(data.get("kind") or "").lower()
    if kind not in ("spending", "revenue", "question"):
        kind = "spending"
    try:
        amount = round(float(str(data.get("amount") or 0).replace(" ", "").replace(",", ".")), 2)
    except (TypeError, ValueError):
        amount = 0.0
    when = str(data.get("date") or "")[:10]
    try:
        when = date.fromisoformat(when).isoformat() if when else timezone.localdate().isoformat()
    except ValueError:
        when = timezone.localdate().isoformat()
    if when > timezone.localdate().isoformat():  # a misread year must not book the future
        when = timezone.localdate().isoformat()
    category = str(data.get("category") or "").strip()[:80] or CATEGORIES[-1]
    try:
        confidence = min(1.0, max(0.0, float(data.get("confidence", 0.5))))
    except (TypeError, ValueError):
        confidence = 0.5
    return {
        "kind": kind,
        "amount": max(0.0, amount),
        "currency": str(data.get("currency") or "").strip()[:8],
        "category": category,
        "description": str(data.get("description") or "").strip()[:60],
        "date": when,
        "confidence": confidence,
        "note": str(data.get("note") or "").strip()[:300],
        "transcript": str(data.get("transcript") or "").strip()[:600],
        "lang": lang,
    }


def _run(user, feature, contents):
    """One model call, charged to the learner's quota."""
    try:
        result = _generate(contents, json_mode=True)
    except gemini.GeminiError:
        return gemini.GeminiResult("", "unavailable", 0, 0, is_stub=True)
    if result.is_stub or not result.text:
        return result
    try:
        consume_and_log(user, feature, result)
    except Exception:  # noqa: BLE001 — accounting must not swallow the answer
        log.exception("could not record AI usage for %s", user.pk)
    return result


def read_receipt(user, image_bytes, mime_type, lang="ru"):
    """A photo of a receipt → a draft entry, or None when it could not be read."""
    prompt = RECEIPT_PROMPT % (CATEGORIES, LANG_NAME.get(lang, "Russian"))
    try:
        contents = [_part(image_bytes, mime_type), prompt]
    except ImportError:
        return None
    result = _run(user, AIUsageLog.Feature.ONBOARDING_PARSE, contents)
    if result.is_stub:
        return None
    return _clean(_parse(result.text), lang)


def read_voice(user, audio_bytes, mime_type, lang="ru"):
    """A voice note → a draft entry, or a question the advisor should answer."""
    prompt = VOICE_PROMPT % (CATEGORIES, LANG_NAME.get(lang, "Russian"))
    try:
        contents = [_part(audio_bytes, mime_type), prompt]
    except ImportError:
        return None
    result = _run(user, AIUsageLog.Feature.ONBOARDING_PARSE, contents)
    if result.is_stub:
        return None
    return _clean(_parse(result.text), lang)


def answer(user, question, context, lang="ru"):
    """A question from the chat → the advisor's short answer (plain text)."""
    prompt = (
        f"You are the Zinvest bear, a calm business coach for a small business owner.\n"
        f"Answer in {LANG_NAME.get(lang, 'Russian')}, in at most 120 words, in plain words,\n"
        f"no lists unless they help, no markdown headings. Be concrete and practical.\n\n"
        f"About them: {context}\n\nTheir question: {question}"
    )
    result = _generate(prompt)
    if result.is_stub or not result.text:
        return result
    try:
        consume_and_log(user, AIUsageLog.Feature.ADVISOR, result)
    except Exception:  # noqa: BLE001
        log.exception("could not record AI usage for %s", user.pk)
    return result
