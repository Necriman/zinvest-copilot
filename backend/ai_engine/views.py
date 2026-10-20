"""
AI endpoints (native JsonResponse — no DRF).

  POST /api/ai/advisor           deep-reasoning financial advisor (PRO model)
  POST /api/ai/onboarding/parse  structured parse of a startup description (FLASH)
  GET  /api/ai/quota             current token allowance (no model call)
  GET  /api/ai/tts               {"available": bool}: does the server have a voice?
  POST /api/ai/tts               the bear's voice for a text: audio/mpeg (or audio/wav)

The generation endpoints are gated by @require_auth + @check_ai_quota. Decorator
order matters: require_auth runs first (sets request.auth_user), then
check_ai_quota (needs it). Usage is booked with consume_and_log after the call.
"""
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.auth import require_auth

from . import course, gemini, tts as voice
from config import languages

from .models import AIUsageLog, UserAIQuota
from .quota import check_ai_quota, consume_and_log, quota_dict

log = logging.getLogger("ai_engine")

# One question is a question, not a book: the model bills by the token.
MAX_QUESTION_CHARS = 2000
MAX_LESSON_TEXT_CHARS = 12000
MAX_CONTEXT_BYTES = 16000


def _json_body(request):
    try:
        return json.loads(request.body or b"{}"), None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"detail": "Malformed JSON body."}, status=400)


ADVISOR_SYSTEM = (
    "You are Zinvest's financial tutor. Give clear, practical, beginner-friendly "
    "guidance on investing, budgeting, cash flow, and startup finance. Be concise, "
    "use plain language, and never give personalized regulated financial advice — "
    "frame answers as education. Answer directly: no greeting and no "
    "self-introduction — the learner already knows who they are talking to. "
    "When Zinvest course material is given below, it is what the learner studies: "
    "base the answer on it, keep to its terms, numbers and examples, and point to "
    "the lesson by its number (for example \"see lesson 3.3\") so they can read more. "
    "If the question goes beyond the material, answer from general knowledge and say "
    "that this part is not covered in the course yet."
)


def _advisor_system(lang):
    """
    The tutor's brief plus the language to answer in: the one the learner has
    picked in the app, whatever language the question, a quoted passage or the
    lesson context happens to be in. With no language known at all (an API
    client that sends none), the question's own language is the best guess.
    """
    if lang:
        return (
            f"{ADVISOR_SYSTEM} Always answer in {languages.NAMES[lang]} — the language the "
            "learner has chosen in the app — even when the question, a quoted passage or the "
            "context is written in another language."
        )
    return f"{ADVISOR_SYSTEM} Reply in the language of the question."

ONBOARDING_SYSTEM = (
    "Extract structured startup details from the user's free-form description. "
    "Respond ONLY with a compact JSON object using these keys where present: "
    "name, industry, stage, revenue_model, target_market, monthly_revenue, "
    "monthly_spending, team_size, summary. Use null for unknown fields."
)


def _build_prompt(system, user_text, context=None, material=""):
    parts = [system, ""]
    if material:
        parts += [material, ""]
    parts.append(f"User: {user_text}")
    if context:
        parts.append(f"Context: {json.dumps(context, default=str)}")
    return "\n".join(parts)


@csrf_exempt
@require_POST
@require_auth
@check_ai_quota
def advisor(request):
    data, err = _json_body(request)
    if err:
        return err

    question = (data.get("question") or data.get("prompt") or "").strip()
    if not question:
        return JsonResponse({"detail": "A question is required."}, status=400)
    context = data.get("context") or {}
    if isinstance(context, dict) and isinstance(context.get("lesson_text"), str):
        context = {**context, "lesson_text": context["lesson_text"][:MAX_LESSON_TEXT_CHARS]}
    if len(question) > MAX_QUESTION_CHARS or len(json.dumps(context, ensure_ascii=False)) > MAX_CONTEXT_BYTES:
        return JsonResponse({"detail": "The question is too long. Please make it shorter.", "code": "too_long"}, status=413)
    lang = (
        languages.normalize(data.get("lang"))
        or languages.normalize(context.get("language") if isinstance(context, dict) else None)
        or languages.from_request(request, default=None)
    )

    # What the course itself says: the open lesson, or the passages that fit.
    try:
        material = course.material(question, context, lang or languages.BASE)
    except Exception:  # noqa: BLE001 — an answer must not fail over its sources
        material = ""
    if isinstance(context, dict) and material:
        # The server has the lesson text now; the client's copy would double it.
        context = {k: v for k, v in context.items() if k != "lesson_text"}
    prompt = _build_prompt(_advisor_system(lang), question, context, material)
    try:
        result = gemini.generate(gemini.FEATURE_ADVISOR, prompt)
    except gemini.GeminiError:
        log.exception("AI call failed")
        return JsonResponse({"detail": "AI service error."}, status=502)

    quota = consume_and_log(request.auth_user, gemini.FEATURE_ADVISOR, result)
    return JsonResponse(
        {
            "answer": result.text,
            "model": result.model_version,
            "is_stub": result.is_stub,
            "tokens": {"input": result.input_tokens, "output": result.output_tokens},
            "quota": quota_dict(quota),
        }
    )


@require_GET
@require_auth
def ai_context(request):
    """
    GET /api/ai/context?lesson=<id>&lang=ru — what the AI screen shows before
    the learner asks anything. No model call, so no quota is spent.
    """
    from .context import learner_context

    return JsonResponse(
        learner_context(request.auth_user, request.GET.get("lesson"), request.GET.get("lang", "ru"))
    )


@csrf_exempt
@require_POST
@require_auth
@check_ai_quota
def onboarding_parse(request):
    data, err = _json_body(request)
    if err:
        return err

    raw_text = (data.get("raw_text") or data.get("text") or "").strip()
    if not raw_text:
        return JsonResponse({"detail": "raw_text is required."}, status=400)

    prompt = _build_prompt(ONBOARDING_SYSTEM, raw_text)
    try:
        result = gemini.generate(gemini.FEATURE_ONBOARDING_PARSE, prompt)
    except gemini.GeminiError:
        log.exception("AI call failed")
        return JsonResponse({"detail": "AI service error."}, status=502)

    quota = consume_and_log(request.auth_user, gemini.FEATURE_ONBOARDING_PARSE, result)

    # Best-effort: parse the model's JSON; fall back to the raw text on failure.
    parsed = None
    try:
        parsed = json.loads(result.text)
    except (json.JSONDecodeError, TypeError):
        parsed = None

    return JsonResponse(
        {
            "parsed": parsed,
            "raw": result.text,
            "model": result.model_version,
            "is_stub": result.is_stub,
            "tokens": {"input": result.input_tokens, "output": result.output_tokens},
            "quota": quota_dict(quota),
        }
    )


def _audio(data, content_type):
    response = HttpResponse(data, content_type=content_type)
    response["Cache-Control"] = "private, max-age=86400"
    return response


@csrf_exempt
@require_http_methods(["GET", "POST"])
@require_auth
def tts(request):
    """
    Speech for lesson text the recorded voice pack does not cover. Clips are
    stored and shared by everyone who listens to the same text; generating a
    new one is limited per learner per day (settings.TTS_DAILY_LIMIT). It does
    not use the AI question quota: lessons never do.
    """
    from adminpanel.models import PlatformSettings

    on = voice.available() and PlatformSettings.current().tts_enabled
    if request.method == "GET":
        return JsonResponse({"available": on})
    if not on:
        return JsonResponse({"detail": "The server voice is not available."}, status=503)

    data, err = _json_body(request)
    if err:
        return err
    text = voice.normalize(data.get("text"))
    if not text:
        return JsonResponse({"detail": "Text is required."}, status=400)
    if len(text) > settings.TTS_MAX_CHARS:
        return JsonResponse({"detail": f"Text is longer than {settings.TTS_MAX_CHARS} characters."}, status=400)
    lang = data.get("lang") if data.get("lang") in voice.STYLE else "en"

    stored = voice.cached(text, lang)
    if stored:
        return _audio(*stored)

    today = timezone.localdate()
    made_today = AIUsageLog.objects.filter(
        user=request.auth_user, feature=AIUsageLog.Feature.TTS, created_at__date=today
    ).count()
    if made_today >= settings.TTS_DAILY_LIMIT:
        return JsonResponse({"detail": "Daily limit for new voice clips reached."}, status=429)

    try:
        audio, content_type, tokens_in, tokens_out = voice.synthesize(text, lang)
    except voice.TTSUnavailable:
        return JsonResponse({"detail": "The server voice is not configured."}, status=503)
    except gemini.GeminiError:
        log.exception("voice call failed")
        return JsonResponse({"detail": "Voice service error."}, status=502)

    AIUsageLog.objects.create(
        user=request.auth_user,
        feature=AIUsageLog.Feature.TTS,
        model_version=settings.GEMINI_TTS_MODEL,
        input_tokens=tokens_in,
        output_tokens=tokens_out,
    )
    return _audio(audio, content_type)


@require_GET
@require_auth
def quota_status(request):
    quota = UserAIQuota.get_or_create_for(request.auth_user)
    # Reflect a due rollover in the read (no lock needed for a read-only view).
    from django.utils import timezone

    if quota.maybe_rollover(timezone.localdate()):
        quota.save(update_fields=["tokens_used_this_cycle", "reset_date", "updated_at"])
    return JsonResponse(quota_dict(quota))
