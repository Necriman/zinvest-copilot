"""
One account must never read, change or delete another account's data.

Every endpoint that takes an object id is asked, as account A, about an object
that belongs to account B. The answer has to be 404 (the object "does not
exist" for A, so its id leaks nothing), and B's object has to be untouched
afterwards. A new endpoint with an id in its path belongs in this file.
"""
import json
import uuid
from datetime import timedelta

from django.test import TestCase
from django.urls import resolve
from django.utils import timezone

from accounts.jwt_utils import encode_access_token
from accounts.models import RefreshToken, User
from learning.models import Lesson, LessonProgress, Task, Unit
from notes.models import Note
from startup.models import (
    Assignment,
    BusinessPost,
    CashFlowEntry,
    Employee,
    FounderConnection,
    Product,
    StartupProfile,
    StartupTodo,
)

PASSWORD = "Str0ng-Passphrase!"


class DataIsolationTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user(email="a@example.test", password=PASSWORD)
        self.b = User.objects.create_user(email="b@example.test", password=PASSWORD)
        self.c = User.objects.create_user(email="c@example.test", password=PASSWORD)
        StartupProfile.objects.create(user=self.a, name="A company")
        StartupProfile.objects.create(user=self.b, name="B company")

    def as_a(self, method, path, data=None):
        token = encode_access_token(self.a, uuid.uuid4())
        kwargs = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        if method in ("get", "delete") and data is None:
            return getattr(self.client, method)(path, **kwargs)
        return getattr(self.client, method)(path, data=json.dumps(data or {}), content_type="application/json", **kwargs)

    def assert_hidden(self, method, path, data=None):
        # A mistyped path would also answer 404; make sure it reaches a view,
        # so the 404 below comes from the ownership check.
        resolve(path)
        r = self.as_a(method, path, data)
        self.assertEqual(r.status_code, 404, f"{method.upper()} {path} answered {r.status_code}")
        return r

    # --- learning and notes ------------------------------------------------
    def test_notes(self):
        note = Note.objects.create(user=self.b, title="B diary", content="<p>B secret</p>")
        path = f"/api/notes/{note.pk}"
        self.assert_hidden("get", path)
        self.assert_hidden("patch", path, {"title": "taken"})
        self.assert_hidden("put", path, {"title": "taken", "content": ""})
        self.assert_hidden("delete", path)
        note.refresh_from_db()
        self.assertEqual(note.title, "B diary")
        self.assertNotIn("B secret", self.as_a("get", "/api/notes").content.decode())

    def test_tasks(self):
        task = Task.objects.create(user=self.b, title="B task")
        path = f"/api/learning/tasks/{task.pk}"
        self.assert_hidden("patch", path, {"done": True})
        self.assert_hidden("delete", path)
        task.refresh_from_db()
        self.assertFalse(task.done)

    def test_lesson_copy_is_per_person(self):
        unit = Unit.objects.create(code="01", slug="basics", title="Basics", order=1)
        lesson = Lesson.objects.create(unit=unit, slug="one", title="Lesson one", order=1)
        LessonProgress.objects.create(user=self.b, lesson=lesson, edited_content="<p>B private copy</p>")
        r = self.as_a("get", f"/api/learning/lessons/{lesson.pk}")
        self.assertNotIn("B private copy", r.content.decode())
        self.as_a("post", f"/api/learning/lessons/{lesson.pk}/save", {"content": "<p>A writes</p>"})
        self.assertEqual(LessonProgress.objects.get(user=self.b, lesson=lesson).edited_content, "<p>B private copy</p>")

    # --- my startup --------------------------------------------------------
    def test_cashflow(self):
        entry = CashFlowEntry.objects.create(user=self.b, entry_type="spending", category="rent", amount=100)
        self.assert_hidden("delete", f"/api/startup/cashflow/{entry.pk}")
        self.assertTrue(CashFlowEntry.objects.filter(pk=entry.pk).exists())
        self.assertNotIn("rent", self.as_a("get", "/api/startup/cashflow").content.decode())

    def test_employees_and_assignments(self):
        emp = Employee.objects.create(user=self.b, full_name="Bobur", salary=500)
        job = Assignment.objects.create(employee=emp, title="B job")
        path = f"/api/startup/employees/{emp.pk}"
        self.assert_hidden("get", path)
        self.assert_hidden("put", path, {"full_name": "taken"})
        self.assert_hidden("delete", path)
        self.assert_hidden("post", f"/api/startup/employees/{emp.pk}/photo")
        self.assert_hidden("patch", f"/api/startup/assignments/{job.pk}", {"done": True})
        self.assert_hidden("delete", f"/api/startup/assignments/{job.pk}")
        emp.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(emp.full_name, "Bobur")
        self.assertFalse(job.done)

    def test_products(self):
        prod = Product.objects.create(user=self.b, name="B product", price=10)
        path = f"/api/startup/products/{prod.pk}"
        self.assert_hidden("get", path)
        self.assert_hidden("put", path, {"name": "taken"})
        self.assert_hidden("delete", path)
        self.assert_hidden("post", f"/api/startup/products/{prod.pk}/image")
        prod.refresh_from_db()
        self.assertEqual(prod.name, "B product")

    def test_todos(self):
        todo = StartupTodo.objects.create(user=self.b, title="B todo")
        self.assert_hidden("patch", f"/api/startup/todos/{todo.pk}", {"done": True})
        self.assert_hidden("delete", f"/api/startup/todos/{todo.pk}")
        todo.refresh_from_db()
        self.assertFalse(todo.done)

    def test_founder_network(self):
        conn = FounderConnection.objects.create(sender=self.b, recipient=self.c, accepted=True)
        self.assert_hidden("patch", f"/api/startup/network/connections/{conn.pk}")
        self.assert_hidden("delete", f"/api/startup/network/connections/{conn.pk}")
        self.assert_hidden("get", f"/api/startup/network/connections/{conn.pk}/messages")
        self.assert_hidden("post", f"/api/startup/network/connections/{conn.pk}/messages", {"text": "hi"})
        self.assertTrue(FounderConnection.objects.filter(pk=conn.pk).exists())
        self.assertFalse(conn.messages.exists())

        post = BusinessPost.objects.create(user=self.b, title="B post")
        self.assert_hidden("delete", f"/api/startup/network/posts/{post.pk}")
        self.assert_hidden("post", f"/api/startup/network/posts/{post.pk}")
        self.assertTrue(BusinessPost.objects.filter(pk=post.pk).exists())

    def test_owner_still_gets_through(self):
        # The same lookups answer the owner, so the 404s above are not a blanket "no".
        note = Note.objects.create(user=self.a, title="A diary")
        emp = Employee.objects.create(user=self.a, full_name="Aziz")
        prod = Product.objects.create(user=self.a, name="A product")
        for path in (f"/api/notes/{note.pk}", f"/api/startup/employees/{emp.pk}", f"/api/startup/products/{prod.pk}"):
            self.assertNotEqual(self.as_a("get", path).status_code, 404, path)
        task = Task.objects.create(user=self.a, title="A task")
        self.assertEqual(self.as_a("patch", f"/api/learning/tasks/{task.pk}", {"done": True}).status_code, 200)

    # --- account ------------------------------------------------------------
    def test_sessions(self):
        family = uuid.uuid4()
        RefreshToken.objects.create(
            user=self.b, token_hash="b" * 64, family_id=family, expires_at=timezone.now() + timedelta(days=1)
        )
        self.assert_hidden("delete", f"/api/auth/sessions/{family}")
        self.assertFalse(RefreshToken.objects.get(family_id=family).is_revoked)

    def test_admin_endpoints_are_staff_only(self):
        for path in (f"/api/admin/users/{self.b.pk}", f"/api/admin/users/{self.b.pk}/export"):
            r = self.as_a("get", path)
            self.assertIn(r.status_code, (403, 404), path)
            self.assertNotIn("b@example.test", r.content.decode())

    def test_export_holds_only_your_own_data(self):
        Note.objects.create(user=self.a, title="A note")
        Note.objects.create(user=self.b, title="B note")
        CashFlowEntry.objects.create(user=self.b, entry_type="spending", category="B rent", amount=1)
        r = self.as_a("get", "/api/auth/me/export")
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r["Content-Disposition"])
        body = r.content.decode()
        self.assertIn("A note", body)
        self.assertNotIn("B note", body)
        self.assertNotIn("B rent", body)
        self.assertNotIn("b@example.test", body)
        # no secrets in the file
        self.assertNotIn("password", body)
        self.assertNotIn("totp_secret", body)
