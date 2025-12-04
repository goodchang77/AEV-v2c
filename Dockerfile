# Multi-stage build for production optimization
FROM python:3.11-slim AS builder

# Set build arguments
ARG BUILD_ENV=production
ARG VERSION=1.0.0

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first (for better caching)
COPY requirements.txt .
COPY requirements-prod.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-prod.txt

# Production stage
FROM python:3.11-slim AS production

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    BUILD_ENV=production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code (only copy what exists)
COPY src/ ./src/
COPY scripts/ ./scripts/

# Copy configuration files if they exist
COPY config/ ./config/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY main.py ./
COPY .env* ./

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/uploads /app/temp && \
    chown -R appuser:appuser /app && \
    chmod +x ./scripts/healthcheck.py

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python scripts/healthcheck.py

# Expose port
EXPOSE 8000

# Start command - simplified for better compatibility
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]