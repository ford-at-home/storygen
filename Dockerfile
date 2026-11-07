# Multi-stage Dockerfile for Richmond Storyline Generator

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./
COPY frontend/yarn.lock* ./

# Install dependencies
RUN npm ci --quiet

# Copy frontend source
COPY frontend/ ./

# Build frontend with production optimizations
RUN npm run build

# Stage 2: Python base with optimizations
FROM python:3.11-slim AS python-base

# Install system dependencies and security updates
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    gnupg2 \
    ca-certificates \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r storygen && useradd -r -g storygen storygen

# Stage 3: Python dependencies
FROM python-base AS python-deps

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements-lock.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements-lock.txt

# Stage 4: Final production image
FROM python-base AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8080 \
    WORKERS=4 \
    THREADS=2 \
    WORKER_CLASS=gthread \
    WORKER_CONNECTIONS=1000 \
    MAX_REQUESTS=1000 \
    MAX_REQUESTS_JITTER=50

WORKDIR /app

# Copy Python dependencies from deps stage
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Copy built frontend from frontend-builder
COPY --from=frontend-builder /app/frontend/dist ./static

# Create necessary directories with correct permissions
RUN mkdir -p /app/logs /app/data /app/cache /app/uploads && \
    chown -R storygen:storygen /app

# Install gunicorn for production
RUN pip install --no-cache-dir gunicorn[gevent] prometheus-client

# Switch to non-root user
USER storygen

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Use gunicorn for production with optimized settings
CMD exec gunicorn app:app \
    --bind 0.0.0.0:${PORT} \
    --workers ${WORKERS} \
    --threads ${THREADS} \
    --worker-class ${WORKER_CLASS} \
    --worker-connections ${WORKER_CONNECTIONS} \
    --max-requests ${MAX_REQUESTS} \
    --max-requests-jitter ${MAX_REQUESTS_JITTER} \
    --timeout 120 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --statsd-host localhost:9125 \
    --statsd-prefix storygen