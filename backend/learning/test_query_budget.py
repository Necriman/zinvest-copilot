"""The learning pages read the whole course: their query count must not grow
with the number of units and lessons (11 units, ~75 lessons today)."""
import uuid
from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from accounts.jwt_utils import encode_access_token
from accounts.models import User
from learning.models import Lesson, LessonProgress

ENDPOINTS = (
    "/api/learning/units",
    "/api/learning/study-plan",
    "/api/learning/lessons",
    "/api/learning/next-step",
    "/api/learning/today",
    "/api/learning/stats",
)
BUDGET = 25


class QueryBudgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_units", stdout=StringIO())
        cls.user = User.objects.create_user(email="reader@example.test", password="Str0ng-Passphrase!")
        for lesson in Lesson.objects.filter(unit__order__lte=2):
            LessonProgress.objects.create(user=cls.user, lesson=lesson, status=LessonProgress.Status.COMPLETED)

    def test_course_pages_stay_within_a_fixed_number_of_queries(self):
        auth = {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(self.user, uuid.uuid4())}
        report = {}
        for path in ENDPOINTS:
            with CaptureQueriesContext(connection) as ctx:
                res = self.client.get(path, **auth)
            if res.status_code == 404:
                continue
            self.assertEqual(res.status_code, 200, (path, res.content[:200]))
            report[path] = len(ctx.captured_queries)
        over = {p: n for p, n in report.items() if n > BUDGET}
        self.assertEqual(over, {}, f"queries per page: {report}")
