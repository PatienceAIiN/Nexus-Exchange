# --- Stage 1: Build Frontend ---
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build -- --output-path=dist

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

# Create static directory and copy frontend build
RUN mkdir -p static
COPY --from=frontend-builder /app/frontend/dist/browser/ ./static/
# Fallback for different Angular versions
COPY --from=frontend-builder /app/frontend/dist/ ./static/ 2>/dev/null || true

# Set environment variables
ENV APP_ENV=production
ENV FRONTEND_DIST_PATH=./static
ENV PORT=10000

# Expose port
EXPOSE 10000

# Start command
CMD gunicorn main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
