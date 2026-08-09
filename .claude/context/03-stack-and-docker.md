# Context 03 — Stack & Docker

Hard requirement: **no local environment.** A contributor clones the repo, copies `.env.example`
to `.env`, runs `docker compose up`, and has a working system with seeded demo data. Nothing
else. No Python on the host, no MySQL install, no venv.

---

## 1. Stack decisions

| Concern | Choice | Rationale |
|---|---|---|
| Framework | Django 5.0 LTS | Upgrade from 4.2.10. Same idioms, better async, `db_default`. |
| Database | PostgreSQL 16 | Replaces MySQL. Window functions and `FILTER` clauses carry the analytics layer; `psycopg[binary]` needs no system build deps (`mysqlclient` does). JSONB for `settings`/`context` fields. |
| Cache / broker | Redis 7 | Session cache, Celery broker + result backend, alert dedupe keys. |
| Async | Celery 5 + beat | Nightly forecasts, alert scans, digests, report generation. |
| WSGI | Gunicorn | Prod. `runserver` in dev via a compose override. |
| Reverse proxy | Nginx | Serves `/static/` and `/media/`, terminates TLS in prod. |
| Static | WhiteNoise | Belt-and-braces so the app works even without Nginx. |
| Deps | `pyproject.toml` + `uv` | Fast, lockfile-backed, reproducible. |
| Lint/format | Ruff | Replaces flake8 + black + isort. |
| Tests | pytest + pytest-django + factory-boy | `tests.py` migrates to `apps/*/tests/`. |
| Frontend | Keep Bootstrap 5 + Chart.js, add HTMX | HTMX gives live stock and inline edits with no build step. **No Node, no bundler.** |
| PDF | WeasyPrint | PO printouts, GRNs, compliance certificates. |
| Excel | openpyxl | Report exports. |

**Removed:** `mysqlclient`, `plotly` (verify unused first — Chart.js does the charting
client-side), and all 14 `.bat`/`.ps1`/`.sh` scripts.

---

## 2. Services

| Service | Image / build | Purpose | Profile |
|---|---|---|---|
| `db` | `postgres:16-alpine` | Primary database | default |
| `redis` | `redis:7-alpine` | Cache + broker | default |
| `web` | `./docker/web` | Django | default |
| `worker` | same image | Celery worker | `async` |
| `beat` | same image | Celery beat | `async` |
| `nginx` | `nginx:1.27-alpine` | Static + proxy | `prod` |
| `mailhog` | `mailhog/mailhog` | Catches dev email at :8025 | `dev` |

Compose profiles keep Phase 0 light — `worker`/`beat` only come up from Phase 8 onward.

---

## 3. `compose.yaml` (reference — write this verbatim in Phase 0)

```yaml
name: sits

x-app: &app
  build:
    context: .
    dockerfile: docker/web/Dockerfile
    target: ${BUILD_TARGET:-dev}
  env_file: [.env]
  volumes:
    - .:/app
    - static_volume:/app/staticfiles
    - media_volume:/app/media
  depends_on:
    db: {condition: service_healthy}
    redis: {condition: service_healthy}

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${DB_NAME:-sits}
      POSTGRES_USER: ${DB_USER:-sits}
      POSTGRES_PASSWORD: ${DB_PASSWORD:?set DB_PASSWORD in .env}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-sits} -d ${DB_NAME:-sits}"]
      interval: 5s
      timeout: 5s
      retries: 10
    ports: ["${DB_PORT_HOST:-5432}:5432"]   # host port only for dev DB tools

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes: [redisdata:/data]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 10

  web:
    <<: *app
    command: /app/docker/entrypoint.sh
    ports: ["${WEB_PORT:-8000}:8000"]

  worker:
    <<: *app
    command: celery -A config worker -l info --concurrency=2
    profiles: [async]

  beat:
    <<: *app
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    profiles: [async]

  mailhog:
    image: mailhog/mailhog
    ports: ["8025:8025"]
    profiles: [dev]

  nginx:
    image: nginx:1.27-alpine
    volumes:
      - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - static_volume:/app/staticfiles:ro
      - media_volume:/app/media:ro
    ports: ["80:80"]
    depends_on: [web]
    profiles: [prod]

volumes: {pgdata: {}, redisdata: {}, static_volume: {}, media_volume: {}}
```

---

> **Corrected in Phase 0** (see G-01, G-02 in `MEMORY.md`): the venv lives at `/opt/venv`,
> not `/app/.venv`, because the dev bind-mount (`.:/app`) would otherwise shadow it; and the
> Dockerfile pre-creates `/app/staticfiles`/`/app/media` with `appuser` ownership before the
> named volumes first mount, or `collectstatic` gets a `PermissionError`. The Dockerfile
> below reflects both fixes — it is not the original reference verbatim.

## 4. `docker/web/Dockerfile` (multi-stage)

```dockerfile
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
```

Pango/Cairo libs are there for WeasyPrint. Note the non-root `appuser` — required.

---

## 5. `docker/entrypoint.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  python manage.py seed_demo || echo "seed_demo skipped (already seeded)"
fi

if [ "${DJANGO_ENV:-dev}" = "dev" ]; then
  exec python manage.py runserver 0.0.0.0:8000
else
  exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
fi
```

Must be `chmod +x` and committed with the executable bit, or it fails on Linux hosts
after a Windows clone. Set `core.autocrlf=false` / add a `.gitattributes` with
`*.sh text eol=lf` — this bites Windows contributors every time.

---

## 6. `.env.example`

```ini
# ── Django ──────────────────────────────────────────
DJANGO_ENV=dev
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=change-me-generate-with-get_random_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CSRF_TRUSTED_ORIGINS=http://localhost:8000
TIME_ZONE=Asia/Kolkata

# ── Database ────────────────────────────────────────
DB_NAME=sits
DB_USER=sits
DB_PASSWORD=change-me
DB_HOST=db
DB_PORT=5432
DB_PORT_HOST=5432

# ── Redis / Celery ──────────────────────────────────
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# ── Email ───────────────────────────────────────────
EMAIL_HOST=mailhog
EMAIL_PORT=1025
DEFAULT_FROM_EMAIL=sits@srms.local

# ── App ─────────────────────────────────────────────
SEED_DEMO_DATA=false
STRICT_TENANCY=True
BUILD_TARGET=dev
WEB_PORT=8000
TRUST_NAME=Shri Ram Murti Smarak Trust
```

`DB_PASSWORD` has no default in `compose.yaml` (`:?` syntax) — the stack refuses to start
without one rather than silently using a weak default.

---

## 7. Settings split

```
config/settings/__init__.py
config/settings/base.py     # everything shared
config/settings/dev.py      # DEBUG, django-debug-toolbar, mailhog, STRICT_TENANCY=True
config/settings/prod.py     # SECURE_*, HSTS, cookie flags, Sentry hook, STRICT_TENANCY=True
config/settings/test.py     # in-memory-ish, fast hasher, eager Celery, STRICT_TENANCY=True
```

`STRICT_TENANCY` stays `True` everywhere. It is a safety net, not a dev convenience.

Preserve the existing `python-decouple` `config()` pattern from `config/settings.py` —
port it, do not replace it with a different config library.

---

## 8. Makefile (thin wrapper, optional but recommended)

```makefile
up:        ; docker compose up --build
down:      ; docker compose down
reset:     ; docker compose down -v && docker compose up --build
sh:        ; docker compose exec web bash
mm:        ; docker compose exec web python manage.py makemigrations
migrate:   ; docker compose exec web python manage.py migrate
test:      ; docker compose exec web pytest -q
lint:      ; docker compose exec web ruff check . --fix && docker compose exec web ruff format .
seed:      ; docker compose exec web python manage.py seed_demo
async:     ; docker compose --profile async up -d worker beat
psql:      ; docker compose exec db psql -U sits -d sits
```

---

## 9. Health, logging, gotchas

- `/healthz/` returns 200 only when DB and Redis both answer. Compose healthcheck hits it.
- Log JSON to stdout in prod. Never log to files inside a container.
- Bind-mounting `.:/app` in dev means code edits hot-reload; a `pyproject.toml` change still
  requires `docker compose build`.
- `.dockerignore` must exclude `.git`, `__pycache__`, `*.sqlite3`, `media/`, `staticfiles/`,
  `.venv`, `node_modules`. Without it the build context is enormous and slow.
- Windows + WSL2: keep the repo inside the WSL filesystem, not `/mnt/c/...`. Bind-mount I/O
  across the boundary is roughly 10× slower and will make the test suite miserable.
- Never `docker compose down -v` against anything holding real data. It deletes the volume.
