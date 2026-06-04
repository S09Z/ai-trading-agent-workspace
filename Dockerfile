FROM python:3.12-slim

WORKDIR /app

# System deps required by sentence-transformers / torch
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Install Python dependencies (cached layer — only invalidated when lockfile changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY . .
RUN uv sync --frozen --no-dev

# Default command — override per-service in docker-compose.prod.yml
CMD ["uv", "run", "uvicorn", "cockpit.app:app", "--host", "0.0.0.0", "--port", "8000"]
