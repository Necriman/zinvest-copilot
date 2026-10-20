"""
Assemble one Vercel deployment: the SPA (Vercel builds it) plus the Django
backend as a single Python function behind /api.

    cd backend && python manage.py collectstatic --noinput   # Django admin CSS/JS
    python deploy/vercel/bundle.py <out-dir>
    cd <out-dir> && CI=1 vercel deploy --prod

Layout of <out-dir>:
    (frontend files)      built by Vercel with `npm run build` -> dist/
    public/static/        backend/staticfiles, served as /static/ (Django admin)
    backend/              the Django project, without venvs, databases or .env
    api/index.py          deploy/vercel/index.py: WSGI entry
    requirements.txt      backend/requirements.txt
    .python-version       the Python the function runs on (3.12, as in development)
    vercel.json           frontend/vercel.json + the function, rewrites and crons

The copy has no .git (a commit by an author outside the Vercel team stalls the
build) and keeps frontend/.vercel, so it deploys to the same `zinvest` project.
Environment variables (DATABASE_URL, SECRET_KEY, ...) live in the Vercel
project, never in the bundle: see README.md here.
"""
import fnmatch
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FRONTEND = REPO / "frontend"
BACKEND = REPO / "backend"
ADMIN_PATH = "admin"  # settings.DJANGO_ADMIN_PATH
PYTHON = "3.12"
REGION = "bom1"  # Vercel's Mumbai region, where the Supabase database lives

SKIP = [
    ".git", "node_modules", "dist", "__pycache__", ".venv*", ".DS_Store",
    ".env", ".env.*", "*.sqlite3", "*.log", "media", "staticfiles",
]


def ignore(_dir, names):
    return {n for n in names if any(fnmatch.fnmatch(n, p) for p in SKIP)}


def main(out):
    out = Path(out).resolve()
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(FRONTEND, out, ignore=ignore)
    shutil.copytree(BACKEND, out / "backend", ignore=ignore)

    static = BACKEND / "staticfiles"
    if not (static / "admin").is_dir():
        sys.exit("backend/staticfiles/admin is missing: run `python manage.py collectstatic` first")
    shutil.copytree(static, out / "public" / "static")

    (out / "api").mkdir()
    shutil.copy(HERE / "index.py", out / "api" / "index.py")
    shutil.copy(BACKEND / "requirements.txt", out / "requirements.txt")
    # The Python the backend is developed and tested on. Left to itself Vercel
    # picks the newest, and psycopg-binary 3.2.9 has no wheels for 3.14.
    # Bytes, not text: on Windows write_text adds "\r", and "3.12\r" is not a
    # version the builder recognises (it silently took 3.14 instead).
    (out / ".python-version").write_bytes(f"{PYTHON}\n".encode())

    config = json.loads((FRONTEND / "vercel.json").read_text(encoding="utf-8"))
    # Run the function next to the database (Supabase ap-south-1, Mumbai). From
    # the default Washington region every query crossed the world and back,
    # and a sign-in took 3-6 s of round trips.
    config["regions"] = [REGION]
    config["functions"] = {
        "api/index.py": {
            # Gemini answers are capped at AI_REQUEST_TIMEOUT_SEC (30 s).
            "maxDuration": 60,
            # The function needs Django only, not the SPA's sources.
            "excludeFiles": "{node_modules/**,src/**,public/**,dist/**,scripts/**,index.html,package*.json,vite.config.js}",
        }
    }
    config["rewrites"] = [
        {"source": "/api/(.*)", "destination": "/api/index"},
        {"source": "/media/(.*)", "destination": "/api/index"},
        {"source": f"/{ADMIN_PATH}", "destination": "/api/index"},
        {"source": f"/{ADMIN_PATH}/(.*)", "destination": "/api/index"},
        # Everything else is the SPA (static files are matched before rewrites).
        {"source": f"/((?!api/|media/|{ADMIN_PATH}/|static/).*)", "destination": "/index.html"},
    ]
    # Vercel Cron sends "Authorization: Bearer $CRON_SECRET" (config/cron.py).
    # The hourly Telegram nudges run from pg_cron in the database instead:
    # Vercel's free plan allows daily jobs only.
    config["crons"] = [
        {"path": "/api/cron/cleanup", "schedule": "30 3 * * *"},
        {"path": "/api/cron/league", "schedule": "15 0 * * 1"},
    ]
    (out / "vercel.json").write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    ignore_file = out / ".vercelignore"
    lines = ignore_file.read_text(encoding="utf-8").splitlines() if ignore_file.exists() else []
    for pattern in ("**/__pycache__", "**/*.sqlite3", "**/.env", "**/.env.*"):
        if pattern not in lines:
            lines.append(pattern)
    ignore_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("bundle ready:", out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
