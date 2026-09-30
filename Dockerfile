# syntax=docker/dockerfile:1

# --- Builder stage: resolve and install dependencies into a virtualenv ---
FROM python:3.12-slim AS builder

# uv provides fast, lockfile-reproducible installs.
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install only runtime dependencies first so this layer caches across code changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# --- Runtime stage: minimal image with just the venv and application code ---
FROM python:3.12-slim AS runtime

# Run as an unprivileged user.
RUN groupadd --system app && useradd --system --gid app --home /app app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_PATH=/app/data/products.db \
    LOG_LEVEL=INFO

WORKDIR /app

# Copy the pre-built virtualenv from the builder stage.
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy application source.
COPY --chown=app:app src/ ./src/

# Writable location for the SQLite database; mount a volume here in production.
RUN mkdir -p /app/data && chown -R app:app /app/data

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/openapi.json')" || exit 1

CMD ["uvicorn", "app.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
