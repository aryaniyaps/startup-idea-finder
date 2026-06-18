# Stage 1: Build Vite React frontend
FROM node:22-alpine AS web-builder
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2: Python API server
FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy Python project
COPY scout/pyproject.toml .
COPY scout/scout/ ./scout/

# Copy built frontend from web-builder
COPY --from=web-builder /app/web/dist /app/web/dist

# Install Python deps
RUN uv sync --no-dev

# Expose port
EXPOSE 8765

# Default: serve API + SPA
CMD ["uv", "run", "scout", "web", "--host", "0.0.0.0", "--port", "8765"]
