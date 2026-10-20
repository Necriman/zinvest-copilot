"""
Server voice: text to speech with Gemini, for text the recorded voice pack in
the frontend does not cover (lesson parts, the learner's own notes, AI answers).

Every clip is stored once in the default file storage under ``tts/``, keyed by
a hash of the text, the model and the voice, so a lesson part is generated the
first time anyone listens to it and served from storage afterwards.

Audio comes back from Gemini as 24 kHz 16-bit mono PCM. It is encoded to MP3
when the ``lameenc`` package is installed (about 8 KB per second of speech)
and wrapped as WAV otherwise (48 KB per second).
"""
import hashlib
import io
import logging
import re
import wave

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from . import gemini

log = logging.getLogger("ai_engine")

SAMPLE_RATE = 24000

# How the bear reads. Gemini TTS takes the style as a plain instruction in the
# prompt and only speaks the text after it.
STYLE = {
    "en": "Read this aloud in a warm, friendly and clear voice, like a patient tutor, at a calm pace:",
    "ru": "Прочитай вслух тёплым, дружелюбным и понятным голосом, как терпеливый наставник, в спокойном темпе:",
    "uz": "Buni iliq, do'stona va aniq ovozda, sabrli ustozdek, xotirjam sur'atda ovoz chiqarib o'qing:",
}


class TTSUnavailable(Exception):
    """The server has no voice configured."""


def normalize(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _sdk_ready():
    try:
        from google.genai import types  # noqa: F401
    except ImportError:
        return False
    return True


def available():
    return bool(settings.GEMINI_API_KEY) and _sdk_ready()


def _encoder():
    try:
        import lameenc
    except ImportError:
        return None
    return lameenc


def _extension():
    return "mp3" if _encoder() else "wav"


def content_type_for(path):
    return "audio/mpeg" if path.endswith(".mp3") else "audio/wav"


def cache_path(text, lang):
    key = "|".join([settings.GEMINI_TTS_MODEL, settings.GEMINI_TTS_VOICE, STYLE.get(lang, STYLE["en"]), text])
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return f"tts/{digest[:2]}/{digest}.{_extension()}"


def cached(text, lang):
    """Stored audio for this text, or None."""
    path = cache_path(text, lang)
    if not default_storage.exists(path):
        return None
    with default_storage.open(path, "rb") as fh:
        return fh.read(), content_type_for(path)


def encode(pcm):
    lame = _encoder()
    if lame:
        enc = lame.Encoder()
        enc.set_bit_rate(64)
        enc.set_in_sample_rate(SAMPLE_RATE)
        enc.set_channels(1)
        enc.set_quality(2)
        return bytes(enc.encode(pcm) + enc.flush()), "audio/mpeg"
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    return buf.getvalue(), "audio/wav"


def _gemini_pcm(text, lang):
    """Raw PCM for ``text`` plus the token counts. Raises GeminiError."""
    client = gemini._get_client()
    if client is None:
        raise TTSUnavailable()
    from google.genai import types

    config = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=settings.GEMINI_TTS_VOICE)
            )
        ),
    )
    prompt = f"{STYLE.get(lang, STYLE['en'])}\n{text}"
    try:
        resp = client.models.generate_content(model=settings.GEMINI_TTS_MODEL, contents=prompt, config=config)
        pcm = resp.candidates[0].content.parts[0].inline_data.data
    except Exception as exc:  # SDK errors and empty answers alike
        log.error("gemini_tts_failed model=%s err=%s", settings.GEMINI_TTS_MODEL, exc)
        raise gemini.GeminiError(str(exc)) from exc
    usage = getattr(resp, "usage_metadata", None)
    return pcm, getattr(usage, "prompt_token_count", 0) or 0, getattr(usage, "candidates_token_count", 0) or 0


def synthesize(text, lang):
    """
    Generate, store and return ``(audio, content_type, input_tokens, output_tokens)``.
    Raises TTSUnavailable or GeminiError.
    """
    pcm, tokens_in, tokens_out = _gemini_pcm(text, lang)
    audio, ctype = encode(pcm)
    path = cache_path(text, lang)
    if not default_storage.exists(path):
        default_storage.save(path, ContentFile(audio))
    return audio, ctype, tokens_in, tokens_out
