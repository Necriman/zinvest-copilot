"""Gunicorn config for the Django auth backend (behind Nginx)."""
import multiprocessing
import os

# Unix socket for the systemd/bare-metal deployment. In Docker Compose, override
# with `-b 0.0.0.0:8000` (see docker-compose.yml).
bind = os.environ.get("GUNICORN_BIND", "unix:/run/auth-app/gunicorn.sock")

workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"            # native Django WSGI views; no async needed
timeout = 30
graceful_timeout = 30
keepalive = 5

max_requests = 1000              # recycle workers to bound memory
max_requests_jitter = 100

accesslog = "-"                  # -> stdout / journald
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")

# Trust X-Forwarded-* only from the local Nginx.
forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1")
