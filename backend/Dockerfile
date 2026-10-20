FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# psycopg[binary] needs no build deps, but keep the layer lean.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "psycopg[binary]==3.2.9"

COPY . .

# Compose binds Gunicorn to TCP :8000 (Nginx upstream -> web:8000).
ENV GUNICORN_BIND=0.0.0.0:8000
EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "-c", "gunicorn.conf.py"]
