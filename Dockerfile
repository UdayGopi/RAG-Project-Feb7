# syntax=docker/dockerfile:1
# Multi-stage, production-ready image for Flask + Gunicorn on AWS ECS

ARG PYTHON_VERSION=3.12

##########################
# ------ Builder -------- #
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

# Use BuildKit cache for pip to speed up subsequent builds
# Requires DOCKER_BUILDKIT=1 (Docker Desktop usually has it enabled)
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/venv \
 && . /opt/venv/bin/activate \
 && pip install --upgrade pip \
 && pip install --prefer-binary -r requirements.txt

##########################
# -------- App ---------- #
FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=5001

# Feature toggles (keep defaults lean for smallest image)
ARG INCLUDE_JAVA=false       # Tabula (Java) for table extraction
ARG INCLUDE_PDF_TOOLS=false  # poppler/ghostscript for some PDF pipelines
ARG INCLUDE_OPENCV=false     # OpenCV GUI-related libs

# Minimal runtime deps first
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl libmagic1 tini \
    && rm -rf /var/lib/apt/lists/*

# Optional PDF tools
RUN if [ "$INCLUDE_PDF_TOOLS" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends ghostscript poppler-utils && \
      rm -rf /var/lib/apt/lists/* ; \
    fi

# Optional OpenCV GUI-related libs
RUN if [ "$INCLUDE_OPENCV" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 && \
      rm -rf /var/lib/apt/lists/* ; \
    fi

# Optional Java for tabula
RUN if [ "$INCLUDE_JAVA" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends default-jre && \
      rm -rf /var/lib/apt/lists/* ; \
    fi

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Prune caches/tests in venv to reduce image size
RUN find /opt/venv -type d -name "__pycache__" -prune -exec rm -rf {} + \
 && find /opt/venv -type f -name "*.pyc" -delete \
 && find /opt/venv/lib -type d -regex '.*site-packages/.*/tests' -prune -exec rm -rf {} + \
 && find /opt/venv/lib -type d -regex '.*site-packages/.*/test' -prune -exec rm -rf {} + || true

# Copy app source
COPY . .

EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://127.0.0.1:${PORT}/auth.html || exit 1

# Proper signal handling and env expansion
ENTRYPOINT ["tini", "--"]
# Use sh -c so ${PORT} expands at runtime; default to 5001 if unset
CMD ["sh", "-c", "exec gunicorn app:app --bind 0.0.0.0:${PORT:-5001} --timeout 180 --workers 2 --threads 4"]
