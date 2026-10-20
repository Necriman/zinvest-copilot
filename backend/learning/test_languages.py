"""The interface language reaches the course, the Drills, onboarding, errors and the AI."""
import io
import json
import os
import re
import uuid
from unittest import mock

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from accounts.jwt_utils import encode_access_token
from accounts.models import User
from ai_engine.gemini import GeminiResult
from config import languages, messages

from .models import Lesson, Unit


class CourseLanguageTests(TestCase):
    """The seeded course comes back in the language the switcher is on."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_learning", stdout=io.StringIO())

    def setUp(self):
        self.user = User.objects.create_user(email="lang@example.test", password="Str0ng-Passphrase!")
        self.auth = {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(self.user, uuid.uuid4())}
        self.lesson = Lesson.objects.get(slug="budgeting-basics")

    def get(self, url, lang=None):
        headers = {"HTTP_ACCEPT_LANGUAGE": lang} if lang else {}
        return self.client.get(url, **self.auth, **headers).json()

    def test_a_lesson_reads_in_the_switchers_language(self):
        url = f"/api/learning/lessons/{self.lesson.id}"
        english, russian, uzbek = self.get(url), self.get(url, "ru-RU,ru;q=0.9"), self.get(url, "uz")
        self.assertEqual(
            (english["title"], russian["title"], uzbek["title"]),
            ("Budgeting basics", "Основы бюджета", "Byudjet asoslari"),
        )
        texts = [el.get("text") for el in russian["canvas_payload"]["elements"] if el.get("type") == "text"]
        self.assertIn("Главное", texts)
        self.assertIn("•  50% — необходимое", texts)
        # An explicit ?lang= wins over the header.
        self.assertEqual(self.get(url + "?lang=uz", "ru")["title"], "Byudjet asoslari")

    def test_a_saved_copy_nobody_edited_does_not_pin_the_language(self):
        from .models import LessonProgress
        from .services import _canvas_words

        english = f"<h1>{_canvas_words(self.lesson.canvas_payload)}</h1>"
        progress = LessonProgress.objects.create(user=self.user, lesson=self.lesson, edited_content=english)
        russian = self.get(f"/api/learning/lessons/{self.lesson.id}", "ru")
        self.assertEqual(russian["edited_content"], "")  # the copy is the original: follow the switcher

        progress.edited_content = english.replace("Budgeting basics", "<strong>Budgeting basics</strong>", 1)
        progress.save()
        self.assertIn("<strong>", self.get(f"/api/learning/lessons/{self.lesson.id}", "ru")["edited_content"])

    def test_the_map_and_the_unit_test_are_translated_but_graded_the_same(self):
        units = self.get("/api/learning/units", "ru")
        titles = [u["title"] for u in (units if isinstance(units, list) else units.get("units", []))]
        self.assertIn("Основы финансов", titles)

        unit = Unit.objects.get(code="01")
        russian = unit.questions("ru")
        self.assertEqual(russian[0]["prompt"], "Чему равен чистый капитал?")
        self.assertEqual([q["answer_index"] for q in russian], [q["answer_index"] for q in unit.test_questions])
        self.assertEqual(unit.questions("fr")[0]["prompt"], unit.test_questions[0]["prompt"])  # no French: English

    def test_the_drills_and_onboarding_speak_the_language(self):
        drills = self.get("/api/learning/challenges", "uz")["challenges"]
        self.assertTrue(drills[0]["prompt"].startswith("Asoschida $4 000 bor"))
        self.assertEqual(drills[0]["unit_title"], "Moliya asoslari")
        onboarding = self.get("/api/learning/onboarding", "ru")
        self.assertEqual(onboarding["quiz"][0]["prompt"], "Что такое сложный процент?")
        self.assertNotIn("answer_index", onboarding["quiz"][0])


class MessageLanguageTests(TestCase):
    """What the server says in `detail` is translated on the way out."""

    def setUp(self):
        self.user = User.objects.create_user(email="msg@example.test", password="Str0ng-Passphrase!")
        self.auth = {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(self.user, uuid.uuid4())}

    def answer(self, lang):
        return self.client.post(
            "/api/learning/practice/answer", data=json.dumps({"id": "nope", "choice": 0}),
            content_type="application/json", HTTP_ACCEPT_LANGUAGE=lang, **self.auth,
        )

    def test_an_error_comes_back_in_the_readers_language(self):
        self.assertEqual(self.answer("en").json()["detail"], "No such question or option.")
        self.assertEqual(self.answer("ru").json()["detail"], "Такого вопроса или варианта нет.")
        self.assertEqual(self.answer("uz").json()["detail"], "Bunday savol yoki variant yo‘q.")

    def test_a_message_with_a_number_is_translated_around_it(self):
        self.assertEqual(messages.translate("Import up to 200 rows at a time.", "ru"), "За раз можно импортировать до 200 строк.")
        self.assertEqual(messages.translate("Something new.", "ru"), "Something new.")  # unknown: left in English


class EveryMessageIsTranslated(SimpleTestCase):
    """A `detail` added in English anywhere in the code needs its Russian and Uzbek."""

    APPS = ("accounts", "adminpanel", "ai_engine", "learning", "notes", "startup", "telegrambot", "config")
    DETAIL = re.compile(r"""["']detail["']\s*:\s*(f?)(["'])((?:(?!\2).)*)\2""")

    def test_every_detail_has_a_translation(self):
        missing = []
        for app in self.APPS:
            root = os.path.join(settings.BASE_DIR, app)
            for folder, _dirs, files in os.walk(root):
                if "migrations" in folder or "__pycache__" in folder:
                    continue
                for name in files:
                    if not name.endswith(".py") or name.startswith("test"):
                        continue
                    with open(os.path.join(folder, name), encoding="utf-8") as source:
                        for match in self.DETAIL.finditer(source.read()):
                            text = match.group(3)
                            if match.group(1):  # an f-string: try it with a sample value in each gap
                                text = re.sub(r"\{[^}]*\}", "7", text)
                            if messages.translate(text, "ru") == text or messages.translate(text, "uz") == text:
                                missing.append(f"{app}/{name}: {match.group(3)}")
        self.assertEqual(missing, [], "add these to config/messages.py")


class AdvisorLanguageTests(TestCase):
    """The AI answers in the interface language, whatever the question is written in."""

    def setUp(self):
        self.user = User.objects.create_user(email="ai-lang@example.test", password="Str0ng-Passphrase!")
        self.auth = {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(self.user, uuid.uuid4())}

    def ask(self, body, **headers):
        with mock.patch("ai_engine.gemini.generate", return_value=GeminiResult("ok", "test", 1, 1)) as generate:
            self.client.post("/api/ai/advisor", data=json.dumps(body), content_type="application/json",
                             **self.auth, **headers)
        return generate.call_args[0][1]

    def test_the_answer_follows_the_switcher_not_the_question(self):
        prompt = self.ask({"question": "What does “liquidity” mean?", "lang": "ru"})
        self.assertIn("Always answer in Russian", prompt)
        prompt = self.ask({"question": "Что такое ликвидность?"}, HTTP_ACCEPT_LANGUAGE="uz")
        self.assertIn("Always answer in Uzbek (Latin script)", prompt)
        # Nothing to go by at all: the question's own language.
        self.assertIn("Reply in the language of the question", self.ask({"question": "Liquidity?"}))

    def test_the_current_language_is_restored_after_a_request(self):
        self.ask({"question": "Hi"}, HTTP_ACCEPT_LANGUAGE="ru")
        self.assertEqual(languages.current(), languages.BASE)
