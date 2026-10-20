import json
import shutil
import struct
import tempfile
import uuid
from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings

from accounts.jwt_utils import encode_access_token
from accounts.models import User

from . import gemini, tts
from .models import AIUsageLog


def fake_pcm(seconds=0.3):
    # A quiet sine-ish ramp is enough for the encoders.
    frames = int(tts.SAMPLE_RATE * seconds)
    return b"".join(struct.pack("<h", (i % 200) * 50) for i in range(frames))


class TTSTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        media = override_settings(MEDIA_ROOT=self.media)
        media.enable()
        self.addCleanup(media.disable)
        self.user = User.objects.create_user(email="listener@example.test", password="Str0ng-Passphrase!")
        self.auth = {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(self.user, uuid.uuid4())}

    def post(self, data):
        return self.client.post("/api/ai/tts", data=json.dumps(data), content_type="application/json", **self.auth)

    @override_settings(GEMINI_API_KEY="")
    def test_without_a_key_the_server_says_it_has_no_voice(self):
        self.assertEqual(self.client.get("/api/ai/tts", **self.auth).json(), {"available": False})
        self.assertEqual(self.post({"text": "Hello"}).status_code, 503)
        self.assertEqual(self.client.get("/api/ai/tts").status_code, 401)

    @override_settings(GEMINI_API_KEY="test-key", TTS_DAILY_LIMIT=2, TTS_MAX_CHARS=50)
    def test_speaks_stores_and_reuses_clips(self):
        with mock.patch.object(tts, "_sdk_ready", return_value=True), \
                mock.patch.object(tts, "_gemini_pcm", return_value=(fake_pcm(), 12, 30)) as model:
            self.assertEqual(self.client.get("/api/ai/tts", **self.auth).json(), {"available": True})

            first = self.post({"text": "  Money is a tool.  ", "lang": "en"})
            self.assertEqual(first.status_code, 200)
            self.assertIn(first["Content-Type"], ("audio/mpeg", "audio/wav"))
            self.assertGreater(len(first.content), 100)

            # Same text (whitespace aside): served from storage, no new generation.
            again = self.post({"text": "Money is a tool.", "lang": "en"})
            self.assertEqual(again.content, first.content)
            self.assertEqual(model.call_count, 1)
            log = AIUsageLog.objects.get(user=self.user, feature=AIUsageLog.Feature.TTS)
            self.assertEqual((log.input_tokens, log.output_tokens), (12, 30))

            self.assertEqual(self.post({"text": ""}).status_code, 400)
            self.assertEqual(self.post({"text": "x" * 51}).status_code, 400)

            # The daily limit counts new clips only.
            self.assertEqual(self.post({"text": "Second text."}).status_code, 200)
            self.assertEqual(self.post({"text": "Third text."}).status_code, 429)
            self.assertEqual(self.post({"text": "Money is a tool.", "lang": "en"}).status_code, 200)

    def test_wav_fallback_is_a_valid_file(self):
        with mock.patch.object(tts, "_encoder", return_value=None):
            audio, ctype = tts.encode(fake_pcm(0.1))
        self.assertEqual(ctype, "audio/wav")
        self.assertTrue(audio.startswith(b"RIFF"))


class ModelRoutingTests(TestCase):
    """Google retires model ids on its own schedule — the advisor keeps answering."""

    def setUp(self):
        gemini._retired.clear()
        self.addCleanup(gemini._retired.clear)

    def _client(self, *answers):
        client = mock.Mock()
        client.models.generate_content.side_effect = answers
        return mock.patch.object(gemini, "_get_client", return_value=client), client

    def test_a_retired_model_answers_on_the_fallback_and_is_not_dialled_again(self):
        gone = Exception("404 NOT_FOUND. This model models/gemini-2.5-pro is no longer available to new users.")
        reply = mock.Mock(text="ok", usage_metadata=None)
        patcher, client = self._client(gone, reply, reply)
        with patcher:
            _, used = gemini.run_model("gemini-2.5-pro", "hi")
            self.assertEqual(used, settings.GEMINI_MODEL_FALLBACK)
            gemini.run_model("gemini-2.5-pro", "again")
        asked = [call.kwargs["model"] for call in client.models.generate_content.call_args_list]
        fallback = settings.GEMINI_MODEL_FALLBACK
        self.assertEqual(asked, ["gemini-2.5-pro", fallback, fallback])

    def test_a_busy_model_is_retried_once_on_the_same_model(self):
        busy = Exception("503 UNAVAILABLE. The model is overloaded. Please try again later.")
        patcher, client = self._client(busy, mock.Mock(text="ok", usage_metadata=None))
        with patcher, mock.patch.object(gemini.time, "sleep"):
            _, used = gemini.run_model("gemini-2.5-flash", "hi")
        self.assertEqual(used, "gemini-2.5-flash")
        self.assertEqual(client.models.generate_content.call_count, 2)

    @override_settings(GEMINI_MODEL_FLASH="m-flash", GEMINI_MODEL_FLASH_LITE="m-lite", GEMINI_MODEL_FALLBACK="m-flash", GEMINI_MODEL_PRO="m-lite")
    def test_a_model_out_of_quota_hands_over_to_another_model(self):
        spent = Exception("429 RESOURCE_EXHAUSTED. You exceeded your current quota. limit: 5, model: m-flash")
        patcher, client = self._client(spent, mock.Mock(text="ok", usage_metadata=None))
        with patcher:
            _, used = gemini.run_model("m-flash", "hi")
        self.assertEqual(used, "m-lite")
        asked = [call.kwargs["model"] for call in client.models.generate_content.call_args_list]
        self.assertEqual(asked, ["m-flash", "m-lite"])

    @override_settings(GEMINI_MODEL_FLASH="m-flash", GEMINI_MODEL_FLASH_LITE="m-lite", GEMINI_MODEL_FALLBACK="m-flash", GEMINI_MODEL_PRO="m-lite")
    def test_when_every_model_is_out_of_quota_the_error_is_reported(self):
        spent = Exception("429 RESOURCE_EXHAUSTED. You exceeded your current quota.")
        patcher, client = self._client(spent, spent, spent)
        with patcher, self.assertRaises(gemini.GeminiError):
            gemini.generate(gemini.FEATURE_COPILOT, "hi")
        self.assertEqual(client.models.generate_content.call_count, 2)  # each model once

    def test_a_real_failure_is_still_reported(self):
        patcher, client = self._client(Exception("400 INVALID_ARGUMENT: bad request"))
        with patcher, self.assertRaises(gemini.GeminiError):
            gemini.generate(gemini.FEATURE_ADVISOR, "hi")
        self.assertEqual(client.models.generate_content.call_count, 1)


class AIContextTests(TestCase):
    """What the AI screen knows before a question: real activity, no model call."""

    def setUp(self):
        from learning.models import Lesson, Unit

        self.user = User.objects.create_user(email="ctx@example.test", password="Str0ng-Passphrase!")
        self.auth = {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(self.user, uuid.uuid4())}
        self.unit = Unit.objects.create(
            code="01", slug="basics", title="Basics", order=1,
            test_questions=[{"id": "q1", "prompt": "Risk?", "choices": ["none", "some"], "answer_index": 1, "explanation": "Always some."}],
        )
        self.lesson = Lesson.objects.create(unit=self.unit, slug="one", title="Risk and return", order=1)

    def get(self, query=""):
        return self.client.get("/api/ai/context" + query, **self.auth)

    def test_an_overlong_question_is_refused_before_the_model(self):
        ask = lambda data: self.client.post("/api/ai/advisor", data=json.dumps(data), content_type="application/json", **self.auth)
        with mock.patch.object(gemini, "generate") as generate:
            self.assertEqual(ask({"question": "x" * 2001}).status_code, 413)
            self.assertEqual(ask({"question": "Why?", "context": {"notes": "y" * 20000}}).status_code, 413)
        generate.assert_not_called()

    def test_it_names_the_current_lesson_and_spends_nothing(self):
        body = self.get().json()
        self.assertEqual(body["learning"]["title"], "Risk and return")
        self.assertFalse(body["from_lesson"])
        self.assertIsNone(body["mistake"])
        self.assertFalse(AIUsageLog.objects.exists())
        self.assertEqual(self.client.get("/api/ai/context").status_code, 401)

    def test_a_lesson_asked_about_wins_and_a_bad_id_is_ignored(self):
        self.assertTrue(self.get(f"?lesson={self.lesson.id}").json()["from_lesson"])
        body = self.get("?lesson=not-a-uuid").json()
        self.assertFalse(body["from_lesson"])
        self.assertEqual(body["learning"]["title"], "Risk and return")

    def test_the_latest_wrong_test_answer_is_the_mistake(self):
        from learning.models import UnitTestResult

        UnitTestResult.objects.create(
            user=self.user, unit=self.unit, score=0, correct_count=0, total_count=1, passed=False,
            answers=[{"question_id": "q1", "choice_index": 0}],
        )
        mistake = self.get().json()["mistake"]
        self.assertEqual(
            (mistake["source"], mistake["question"], mistake["chosen"], mistake["correct"]),
            ("test", "Risk?", "none", "some"),
        )

    def test_a_wrong_daily_answer_counts_too(self):
        from learning.models import DailyQuestion, DailyRun

        question = DailyQuestion.objects.create(
            slug="d1", topic=DailyQuestion.Topic.INVESTING, answer=1,
            body={"en": {"question": "Diversify?", "options": ["no", "yes"], "explain": "Spread the risk."}},
        )
        DailyRun.objects.create(user=self.user, questions=[str(question.id)], answers=[0])
        mistake = self.get("?lang=en").json()["mistake"]
        self.assertEqual(
            (mistake["source"], mistake["question"], mistake["chosen"], mistake["correct"]),
            ("daily", "Diversify?", "no", "yes"),
        )
