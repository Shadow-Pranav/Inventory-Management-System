# SITS — Smart Inventory Assistance & Tracking System

Central compliance and inventory portal for the SRMS Trust, covering every institution and
department under it. See [`CLAUDE.md`](CLAUDE.md) for the full project brief and
[`PROMPTS.md`](PROMPTS.md) for the phase-by-phase build plan.

## Prerequisites

**Docker Desktop only.** There is no supported local Python setup — every command runs
inside a container.

## Quick start

```bash
git clone <this-repo>
cd Smart_Inventory_Management_System
cp .env.example .env        # then edit SECRET_KEY and DB_PASSWORD
docker compose up --build
```

The app is at [http://localhost:8000](http://localhost:8000). Health check:
[http://localhost:8000/healthz/](http://localhost:8000/healthz/) — returns `200` once the
database and Redis are both reachable.

Create an admin user:

```bash
docker compose exec web python manage.py createsuperuser
```

## Command reference

| Command | Purpose |
|---|---|
| `docker compose up --build` | Start db, redis, web |
| `docker compose down` | Stop, keep data |
| `docker compose down -v` | Stop and **destroy** volumes — never against real data |
| `docker compose --profile async up -d worker beat` | Start Celery worker + beat (Phase 8+) |
| `docker compose --profile dev up -d mailhog` | Start Mailhog at `:8025` for dev email |
| `docker compose exec web python manage.py <cmd>` | Any Django management command |
| `docker compose exec web pytest -q` | Run the test suite |
| `docker compose exec web ruff check . --fix` | Lint |
| `docker compose exec web ruff format .` | Format |
| `docker compose exec db psql -U sits -d sits` | Open a psql shell |

A `Makefile` wraps the common ones: `make up`, `make migrate`, `make test`, `make lint`,
`make sh`, `make psql`.

## Troubleshooting

- **`DB_PASSWORD` error on `docker compose up`** — `.env` is missing or `DB_PASSWORD` is
  unset. Copy `.env.example` to `.env` and set a value; the stack refuses to start with a
  default password.
- **`web` container exits immediately** — check `docker compose logs web`. A common cause on
  a fresh Windows clone is `docker/entrypoint.sh` losing its executable bit or gaining CRLF
  line endings; `.gitattributes` pins it to `LF`, but if you bypassed git for the copy,
  `chmod +x docker/entrypoint.sh` and re-save it with LF endings.
- **Port already in use** — another process is bound to `8000`, `5432`, `6379`, or `8025`.
  Override with `WEB_PORT` / `DB_PORT_HOST` in `.env`, or stop the conflicting process.
- **`docker compose down -v` was run by mistake** — the database volume is gone. There is no
  recovery apart from re-migrating and re-seeding; this is why it's a deliberate, confirmed
  action, never a routine one.
- **Stale migrations across a branch switch** — `docker compose exec web python manage.py
  showmigrations`, then `migrate` again. Never `--fake` a migration to make an error go away.

## Project status

This project is under active, phased development — see [`PROGRESS.md`](PROGRESS.md) for the
current phase and [`MEMORY.md`](MEMORY.md) for the decision log.
