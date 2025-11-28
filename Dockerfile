# FixtureCast Docker Image
# Multi-stage build for optimized production image

# ==========================================
# Stage 1: Python Dependencies
# ==========================================
FROM python:3.12-slim as python-deps

WORKDIR /app

# Install system dependencies for ML libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==========================================
# Stage 2: Frontend Build (optional)
# ==========================================
FROM node:20-alpine as frontend-build

WORKDIR /app/frontend

# Copy frontend files
COPY frontend/package*.json ./
RUN npm ci --silent 2>/dev/null || echo "No package-lock.json, using npm install" && npm install

COPY frontend/ ./
RUN npm run build || echo "Frontend build skipped"

# ==========================================
# Stage 3: Production Image
# ==========================================
FROM python:3.12-slim as production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from deps stage
COPY --from=python-deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/ ./backend/
COPY ml_engine/ ./ml_engine/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Create necessary directories
RUN mkdir -p ml_engine/trained_models

# Copy built frontend (if exists)
# Note: Frontend build is optional - the COPY may fail if not built
RUN mkdir -p ./frontend/dist

# Copy .env template and startup scripts
COPY .env.example .env.example
COPY start.sh .
RUN chmod +x start.sh

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8001
ENV ML_PORT=8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8001}/health || exit 1

# Expose ports
EXPOSE 8001 8002

# Run the appropriate API based on SERVICE_TYPE env variable
CMD ["./start.sh"]
