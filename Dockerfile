# syntax=docker/dockerfile:1
# Multi-stage, production-ready image for Flask + Gunicorn on AWS ECS

ARG PYTHON_VERSION=3.12

# ------------------ Builder ------------------
FROM python:${PYTHON_VERSION}-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System build deps (removed in final image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN python -m venv /opt/venv \
 && . /opt/venv/bin/activate \
 && pip install --upgrade pip \
 && pip install -r requirements.txt

# ------------------ Final ------------------
FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=5001

# Runtime system deps for PDF/HTML processing and OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    default-jre \
    ghostscript poppler-utils \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy app source
COPY . .

EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://127.0.0.1:${PORT}/auth.html || exit 1

# Gunicorn (ECS-compatible)
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:${PORT}", "--timeout", "180", "--workers", "2", "--threads", "4"]
