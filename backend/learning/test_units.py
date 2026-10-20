"""The course units imported from the PDFs, editing a lesson from its page,
and what the AI is told about the course."""
import json
import uuid

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from accounts.jwt_utils import encode_access_token
from accounts.models import User
from ai_engine import course
from learning.html_clean import clean_lesson_html, plain_text
from learning.models import Lesson, Unit

PASSWORD = "Str0ng-Passphrase!"


def import_quietly(**opts):
    from io import StringIO

    call_command("import_units", stdout=StringIO(), **opts)


class ImportUnitsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        import_quietly()

    def test_every_unit_arrives_in_its_languages(self):
        units = list(Unit.objects.order_by("order"))
        self.assertEqual([u.order for u in units], list(range(1, 12)))
        budgeting = Unit.objects.get(order=3)
        self.assertEqual(budgeting.slug, "personal-budgeting")
        self.assertEqual(budgeting.lessons.count(), 7)  # six sections and the glossary
        self.assertEqual(len(budgeting.test_questions), 12)
        lesson = budgeting.lessons.get(order=3)
        self.assertIn("50/30/20", lesson.title)
        self.assertIn("<table>", lesson.content_html)
        self.assertIn("50/30/20", lesson.i18n["ru"]["title"])
        self.assertTrue(lesson.i18n["uz"]["content_html"])
        # Unit 6 has no Russian file and unit 11 is English only: they fall back.
        self.assertNotIn("ru", Unit.objects.get(order=6).i18n)
        self.assertEqual(Lesson.objects.filter(unit__order=11).first().tr("title", "ru"),
                         Lesson.objects.filter(unit__order=11).first().title)

    def test_running_it_again_keeps_the_ids(self):
        before = dict(Lesson.objects.values_list("unit__order", "id").order_by("unit__order", "order"))
        import_quietly()
        after = dict(Lesson.objects.values_list("unit__order", "id").order_by("unit__order", "order"))
        self.assertEqual(before, after)

    def test_a_translated_test_keeps_its_own_answers(self):
        unit = Unit.objects.get(order=2)  # the ru/uz test is a different set of questions
        en = {q["id"]: q["answer_index"] for q in unit.questions("en")}
        ru = {q["id"]: q["answer_index"] for q in unit.questions("ru")}
        self.assertEqual(en.keys(), ru.keys())
        self.assertNotEqual(en, ru)

    def test_the_test_is_graded_in_the_language_it_was_shown_in(self):
        user = User.objects.create_user(email="learner@example.test", password=PASSWORD)
        unit = Unit.objects.get(order=1)
        auth = {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(user, uuid.uuid4())}
        right = [{"question_id": q["id"], "choice_index": q["answer_index"]} for q in unit.questions("ru")]
        res = self.client.post(f"/api/learning/units/{unit.id}/test/submit", data=json.dumps({"answers": right}),
                               content_type="application/json", HTTP_ACCEPT_LANGUAGE="ru", **auth)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["correct_count"], 12)
        self.assertTrue(res.json()["passed"])

    def test_pdf_glyph_codes_are_cleaned_for_postgres(self):
        from learning.management.commands.import_units import clean

        raw = {"html": "<p><strong>\x00 Определение</strong></p><p>\x16 Car crash \x16 Fire</p><p>\x14 Covered</p>",
               "list": ["️ ПРИМЕР", "a\x07b"], "n": 3}
        self.assertEqual(clean(raw), {
            "html": "<p><strong>Определение</strong></p><p>✗ Car crash</p><p>✗ Fire</p><p>✓ Covered</p>",
            "list": ["ПРИМЕР", "ab"], "n": 3,
        })
        # Nothing imported carries a control code (json.dumps writes them as \u00XX).
        codes = r"[\x00-\x08\x0b\x0c\x0e-\x1f]|\\u00(0[0-8bcef]|1[0-9a-f])"
        for unit in Unit.objects.all():
            self.assertNotRegex(unit.title + json.dumps(unit.i18n) + json.dumps(unit.test_questions), codes)
        for lesson in Lesson.objects.all():
            self.assertNotRegex(lesson.content_html + json.dumps(lesson.i18n), codes)


class HtmlCleanTests(TestCase):
    def test_keeps_the_editor_markup_and_drops_the_rest(self):
        html = (
            '<h2>Title</h2><p onclick="x()">Text <mark data-color="#fef08a" style="background-color: #fef08a">key</mark>'
            '<script>alert(1)</script></p><table><tbody><tr><th colspan="2">A</th></tr></tbody></table>'
            '<a href="javascript:alert(1)">bad</a><a href="https://zinvest.uz" target="_blank">ok</a>'
            '<img src="x" onerror="alert(1)"><img src="/units/u01/en/fig-2.png" alt="">'
            '<p style="color: red; background: url(evil)">styled</p><iframe src="https://evil"></iframe>'
        )
        out = clean_lesson_html(html)
        for bad in ("<script", "onclick", "onerror", "javascript:", "iframe", "url(", 'src="x"'):
            self.assertNotIn(bad, out)
        for good in ("<h2>Title</h2>", "<mark", '<th colspan="2">', 'href="https://zinvest.uz"', 'rel="noopener',
                     '/units/u01/en/fig-2.png', "color: red", "Text"):
            self.assertIn(good, out)
        self.assertEqual(plain_text("<p>One</p><p>Two <strong>three</strong></p>"), "One\nTwo three")


class LessonEditingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        import_quietly(only=3)

    def setUp(self):
        cache.clear()
        self.lesson = Lesson.objects.get(unit__order=3, order=1)

    def _client_for(self, role):
        user = User.objects.create_user(email=f"{role or 'learner'}@example.test", password=PASSWORD)
        if role:
            user.staff_role = role
            user.save(update_fields=["staff_role"])
        auth = {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(user, uuid.uuid4())}

        def send(path, data):
            return self.client.post(path, data=json.dumps(data), content_type="application/json", **auth)
        return send

    def test_only_content_staff_save_and_the_text_is_cleaned(self):
        path = f"/api/admin/content/lessons/{self.lesson.id}/body"
        body = {"lang": "ru", "title": "Что такое бюджет", "html": "<p>Новый текст<script>x()</script></p><table><tbody><tr><td>1</td></tr></tbody></table>"}
        self.assertEqual(self._client_for("")(path, body).status_code, 403)
        self.assertEqual(self._client_for("analyst")(path, body).status_code, 403)
        editor = self._client_for("content")
        self.assertEqual(editor(path, body).json()["code"], "unlock_required")
        self.assertEqual(editor("/api/admin/unlock", {"password": PASSWORD}).status_code, 200)
        res = editor(path, body)
        self.assertEqual(res.status_code, 200, res.content)
        self.lesson.refresh_from_db()
        ru = self.lesson.i18n["ru"]
        self.assertEqual(ru["title"], "Что такое бюджет")
        self.assertIn("Новый текст", ru["content_html"])
        self.assertNotIn("script", ru["content_html"])
        self.assertIn("<table>", ru["content_html"])
        self.assertNotIn("Новый текст", self.lesson.content_html)  # English untouched
        self.assertEqual(editor(path, {"lang": "de", "html": "<p>x</p>"}).status_code, 400)
        self.assertEqual(editor(path, {"lang": "en", "html": "<p> </p>"}).status_code, 400)


class CourseKnowledgeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        import_quietly(only=3)

    def setUp(self):
        course.forget()

    def test_a_question_finds_the_lesson_that_teaches_it(self):
        found = course.search("Что такое правило 50/30/20?", "ru")
        self.assertTrue(found)
        self.assertEqual(found[0]["number"], "3.3")
        self.assertTrue(course.search("Favqulodda fond qancha bo'lishi kerak?", "uz"))

    def test_the_open_lesson_is_read_to_the_model(self):
        lesson = Lesson.objects.get(unit__order=3, order=4)
        text = course.material("Объясни проще", {"lesson_id": str(lesson.id)}, "ru")
        self.assertIn("3.4", text)
        self.assertIn(lesson.i18n["ru"]["title"], text)
        self.assertIn("Unit 3", text)
        self.assertEqual(course.material("zzz qqq", {}, "en"), "")
