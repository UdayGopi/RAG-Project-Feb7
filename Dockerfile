# =============================================================================
# DEFAULT DOCKERFILE - CarePolicy Hub (use this for standard deploy)
# =============================================================================
# Build:  docker build -t carepolicy-hub:latest .
# Uses:   requirements.txt, .env.example (copied as .env)
# Image:  ~1.2GB, full RAG (HuggingFace embeddings, local vector store, S3 optional)
# For a smaller image (<300MB, API-only embeddings), use: docker build -f Dockerfile.ultralight -t carepolicy-hub:latest .
# =============================================================================

# Multi-stage build for smaller final image

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY config/ ./config/
COPY core/ ./core/
COPY agents/ ./agents/
COPY storage/ ./storage/
COPY models/ ./models/
COPY retrieval/ ./retrieval/
COPY database/ ./database/
COPY api/ ./api/
COPY utils/ ./utils/
COPY ingestion/ ./ingestion/
COPY static/ ./static/
COPY app.py .
COPY rag_agent.py .
# Default env (placeholders). Override in production via ECS/App Runner env or Secrets Manager.
COPY .env.example .env

# Create necessary directories
RUN mkdir -p data/documents data/storage data/cache data/models logs

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Run with gunicorn in production
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "--timeout", "300", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
