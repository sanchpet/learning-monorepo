# syntax=docker/dockerfile:1.7
# --- Build stage: install deps into an isolated .venv from the lockfile ---
FROM python:3.12-slim AS builder

# Take the uv binary from the official image — no pip or uv in the runtime.
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /bin/uv

# UV_COMPILE_BYTECODE — precompile .pyc (faster startup);
# UV_LINK_MODE=copy — install by copying (cache mount lives on another FS).
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# 1) Manifest + lock first -> the dependency layer stays cached until
#    pyproject.toml / uv.lock change.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# 2) Then the project code (changes more often than dependencies).
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- Runtime stage: only the venv + code, no uv and no caches ---
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Non-root: a system user with no login and no write access to the system.
RUN useradd --system --no-create-home --uid 10001 appuser

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app ./app

USER appuser
EXPOSE 8000

# Liveness check: hit /health without curl (not present in slim).
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
