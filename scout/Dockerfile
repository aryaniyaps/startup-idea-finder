FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .
COPY scout/ ./scout/

# Install deps (no lockfile needed with --no-dev)
RUN uv sync --no-dev

# Expose dashboard port
EXPOSE 8765

# Default: run dashboard
CMD ["uv", "run", "scout", "web", "--host", "0.0.0.0", "--port", "8765"]
