"""Uploads kept in the database are served as what the server says they are."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase

from .models import StoredFile
from .storage import DatabaseStorage
from .views import serve


class ServeTests(TestCase):
    def fetch(self, name):
        return serve(RequestFactory().get(f"/media/{name}"), name)

    def test_a_page_disguised_as_a_photo_is_served_as_a_photo_in_a_sandbox(self):
        # Passes the magic-byte check, but the uploader's browser claims text/html.
        upload = SimpleUploadedFile("x.gif", b"GIF89a<html><script>alert(1)</script></html>", content_type="text/html")
        name = DatabaseStorage().save("avatars/u/photo.gif", upload)
        self.assertEqual(StoredFile.objects.get(name=name).content_type, "image/gif")
        r = self.fetch(name)
        self.assertEqual(r["Content-Type"], "image/gif")
        self.assertIn("sandbox", r["Content-Security-Policy"])
        self.assertEqual(r["Cross-Origin-Resource-Policy"], "same-origin")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")

    def test_an_old_row_with_a_bad_type_is_no_longer_trusted(self):
        StoredFile.objects.create(name="products/p/image.png", content=b"\x89PNG", size=4, content_type="text/html")
        self.assertEqual(self.fetch("products/p/image.png")["Content-Type"], "image/png")

    def test_unknown_extensions_download_instead_of_opening(self):
        StoredFile.objects.create(name="misc/page.html", content=b"<script>", size=8, content_type="text/html")
        r = self.fetch("misc/page.html")
        self.assertEqual((r["Content-Type"], r["Content-Disposition"]), ("application/octet-stream", "attachment"))
