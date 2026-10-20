"""
Simple tests for the Zinvest Copilot logic, runnable without a database or an
AI key:  python -m unittest discover -s tests -t .   (from the repository root)

They load the Django project from ./backend so the Copilot modules import as
they do in the app. The full suite (249 tests, with a test database) runs with
`cd backend && python manage.py test`.
"""
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("SQLITE_PATH", ":memory:")
os.environ.setdefault("GEMINI_API_KEY", "")

import django  # noqa: E402

django.setup()
