"""Check bot AI connectivity without reading user data or sending Telegram messages."""
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from telegrambot import brain


class Command(BaseCommand):
    help = "Check the bot AI configuration; --probe sends one generic test prompt to Gemini."

    def add_arguments(self, parser):
        parser.add_argument("--probe", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write(f"Model: {brain.model_name()}")
        if not settings.GEMINI_API_KEY:
            raise CommandError("GEMINI_API_KEY is missing. Set it in the backend environment and restart the bot.")
        try:
            config = brain._config()
        except ImportError:
            raise CommandError("google-genai is missing from this Python environment.")
        self.stdout.write(f"Key: configured (hidden); timeout: {config.http_options.timeout} ms")
        if not options["probe"]:
            return
        started = time.monotonic()
        try:
            result = brain._generate("Answer in Russian, in one sentence: how do revenue and profit differ?")
        except Exception as exc:
            cause = exc.__cause__ or exc
            code = getattr(cause, "code", None)
            hint = {400: "Check the API key and model configuration.",
                    403: "Check API key permissions and region availability.",
                    404: "The configured model is unavailable for this key.",
                    429: "Gemini quota or rate limit reached; check the project's API quota and billing."}.get(code, "Check network access to Gemini and server logs.")
            raise CommandError(f"Provider check failed ({type(cause).__name__}, code={code}). {hint}") from None
        if result.is_stub or not result.text.strip():
            raise CommandError("The provider returned no answer. Check the API configuration and safety settings.")
        self.stdout.write(self.style.SUCCESS(
            f"OK: non-empty answer, {time.monotonic() - started:.2f} seconds, "
            f"{result.input_tokens} input / {result.output_tokens} output tokens. No Telegram messages sent."))
