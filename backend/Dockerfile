# ============================================================
# ZAMIN X — Production Dockerfile
# Multi-stage build: builder + slim runtime
# ============================================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-tam \
    tesseract-ocr-hin \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps in a virtualenv
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy system libs needed at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    tesseract-ocr \
    tesseract-ocr-tam \
    tesseract-ocr-hin \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create non-root user for security
RUN addgroup --system zaminx && adduser --system --group zaminx
RUN chown -R zaminx:zaminx /app
USER zaminx

# Create directories
RUN mkdir -p models data/raw data/processed reports

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Use the shell form of CMD to allow environment variable expansion ($PORT)
CMD uvicorn api.app:app --host 0.0.0.0 --port $PORT
