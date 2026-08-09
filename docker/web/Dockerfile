FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl \
        libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# NOTE: dev bind-mounts `.:/app` (compose.yaml), which would shadow a venv built at
# /app/.venv. UV_PROJECT_ENVIRONMENT=/opt/venv keeps it outside the mount so the image
# build survives the runtime bind-mount. See MEMORY.md G-01.

FROM base AS deps
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM base AS dev
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
COPY . .
RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R appuser /app /opt/venv
USER appuser
EXPOSE 8000
CMD ["/app/docker/entrypoint.sh"]

FROM base AS prod
COPY --from=deps /opt/venv /opt/venv
COPY . .
RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R appuser /app /opt/venv
USER appuser
RUN SECRET_KEY=build-only DEBUG=False DJANGO_SETTINGS_MODULE=config.settings.prod \
    python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", \
     "--workers", "3", "--timeout", "60", "--access-logfile", "-"]
