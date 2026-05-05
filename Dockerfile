# --- Stage 1: Build Frontend ---
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Robust normalization: Find the directory containing index.html and move its contents to dist-final
RUN mkdir -p dist-final && \
    INDEX_DIR=$(find dist -name "index.html" -exec dirname {} \;) && \
    if [ -n "$INDEX_DIR" ]; then \
        echo "Found index.html in $INDEX_DIR, copying contents..."; \
        cp -r $INDEX_DIR/* dist-final/; \
    else \
        echo "Warning: index.html not found, falling back to dist/"; \
        cp -r dist/* dist-final/ 2>/dev/null || true; \
    fi

# --- Stage 2: Final Image ---
FROM python:3.10-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/cache/*

# Copy backend requirements and install
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Create static directory and copy normalized frontend build
RUN mkdir -p static
COPY --from=frontend-builder /app/frontend/dist-final/ ./static/

# Set environment variables
ENV APP_ENV=production
ENV FRONTEND_DIST_PATH=./static
ENV PORT=10000

# Expose port
EXPOSE 10000

# Start command
CMD gunicorn main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
