# syntax=docker/dockerfile:1

# Using a slim Python base for smaller image
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (psycopg2-binary does not require build tools, keep minimal)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy project files
COPY . .

# Set Django settings module (can be overridden at deploy time)
ENV DJANGO_SETTINGS_MODULE=BoltAbacus.settings

# Collect static at build time (does not require DB)
RUN python manage.py collectstatic --noinput || true

# Cloud Run listens on $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

# Start via Gunicorn
CMD ["gunicorn", "BoltAbacus.wsgi:application", "--bind", "0.0.0.0:${PORT}"]
