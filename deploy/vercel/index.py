"""
Vercel entry point: the whole Django app as one Python function.

bundle.py copies this to api/index.py next to the frontend, and vercel.json
rewrites /api/*, /media/* and the Django admin here; Django routes the
original path as usual.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
