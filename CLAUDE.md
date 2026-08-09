# CLAUDE.md — SITS (Smart Inventory Assistance & Tracking System)

> This file is auto-loaded by Claude Code at the start of every session in this repository.
> It is the single source of truth for **what** we are building and **how** you must behave.
> Keep it under ~500 lines. Detail lives in `.claude/context/`.

---

## 1. Project identity

| Field | Value |
|---|---|
| Name | SITS — Smart Inventory Assistance & Tracking System |
| Owner | Shri Ram Murti Smarak (SRMS) Trust |
| Origin repo | `Shadow-Pranav/Inventory-Management-System` (Django IMS) — **not present in this repo; see D-11 in MEMORY.md.** SITS is being built greenfield, informed by that design, not migrated from its code. |
| Stack | Django 5.x · PostgreSQL 16 · Redis · Celery · Docker Compose |
| Mode of work | Claude Code inside VS Code |
| Local Python/venv | **Forbidden.** Everything runs in containers. |

SITS is a **central compliance and inventory portal for the whole SRMS Trust**. It tracks
technical and non-technical resources at the department and institution level across
every organisation under the Trust.

### Tenants (organisations under the Trust)

Seeded in `apps/tenancy/fixtures/organizations.json`. Confirm exact legal names with the
user before treating them as final.

1. SRMS Institute of Medical Sciences (IMS)
2. SRMS College of Engineering & Technology (CET)
3. SRMS College of Nursing
4. SRMS College of Hotel Management
5. SRMS Business School
6. SRMS Hospital
7. Riddhima

The list must be **data, never code**. Never hardcode an organisation name, slug or ID in
a view, template, query or migration. Adding an 8th organisation must require zero code
changes.

---

## 2. The one rule that matters most

> **Every query against tenant-owned data must be scoped to an organisation, and the scoping
> must come from the request context — never from a URL parameter or form field the user controls.**

An Org Admin of the Nursing College must not be able to read, count, aggregate, export,
autocomplete, or infer the existence of a single row belonging to CET. A Trust Admin sees
everything. There is no third case.

If you are ever unsure whether a queryset is scoped, it is not scoped. Fix it.

---

## 3. Non-negotiable constraints

1. **No local environment.** No `venv`, no `pip install` on the host, no `python manage.py`
   run directly. Every command is `docker compose exec web ...` or `docker compose run --rm web ...`.
   Delete `.bat` / `.ps1` / `setup.sh` files as you migrate past them; do not add new ones.
2. **Build clean, don't churn.** There is no legacy `ims_app` codebase to preserve (see D-11
   in `MEMORY.md`) — models, views and templates are written directly against the tenancy
   architecture in this file from Phase 1 onward. Bootstrap 5 + HTMX styling stays the visual
   baseline (no design system rewrite mid-project), but there is no byte-identical-file
   constraint: build each app once, correctly, rather than migrating something that doesn't
   exist.
3. **Migrations are forward-only and reviewed.** Never edit an applied migration. Never
   `--fake` your way out of a problem. Data migrations get their own numbered file with a
   working `reverse_code`.
4. **No secrets in the repo.** `.env` is gitignored; `.env.example` carries placeholders only.
5. **Tests accompany behaviour.** Any change to permissions, scoping, or stock arithmetic
   ships with a test in the same commit. Tenant isolation tests are mandatory, not optional.
6. **Ask before assuming.** If a requirement is genuinely ambiguous (approval hierarchies,
   fiscal-year boundaries, who signs off a write-off), stop and ask the user. Do not invent
   institutional policy.

---

## 4. Session protocol — follow this every time

### At session start
1. Read `PROGRESS.md` → find the first phase whose status is `IN PROGRESS`, else the first `NOT STARTED`.
2. Read `MEMORY.md` → load prior decisions so you do not relitigate them.
3. Read the matching phase block in `PROMPTS.md` → that is your brief.
4. Read only the `.claude/context/` files that phase's brief names.
5. State in one short paragraph: which phase you are on, what you will do, what you will touch.
6. **Do not scan the whole codebase.** The context files exist so you do not have to. If they
   are wrong or stale, fix them — that is a bug, and fixing it is part of the work.

### While working
- Work in the smallest coherent slice: models → migration → admin → views → templates → tests.
- Run the test suite after each slice: `docker compose exec web pytest -q`
- If you discover something surprising about the codebase, append it to `MEMORY.md`
  **immediately**, not at the end.

### At session end — mandatory, never skip
Run `/session-end`, which will:
1. Update `PROGRESS.md` — tick tasks, set phase status, write the "next action" line.
2. Append to `MEMORY.md` — decisions made, gotchas found, things deliberately deferred.
3. Update `.claude/context/*.md` if the architecture, schema or conventions changed.
4. Update this file only if a project-wide rule changed.
5. Print a 5-line handoff summary.

If the user ends abruptly, do this unprompted before your final message. A session that
ends without updating `PROGRESS.md` has to be re-derived next time, which costs more than
the update.

---

## 5. Repository layout (target)

```
.
├── CLAUDE.md                  ← you are here
├── INSTRUCTIONS.md            ← working protocol, coding standards, command reference
├── PROMPTS.md                 ← the phase-by-phase build brief
├── PROGRESS.md                ← live status; the resume point
├── MEMORY.md                  ← decision log; append-only
├── ANALYSIS.md                ← original-repo audit and migration rationale
├── .claude/
│   ├── settings.json
│   ├── commands/              ← /session-start /session-end /checkpoint /next-phase /verify-tenancy
│   └── context/
│       ├── 01-domain-model.md
│       ├── 02-tenancy.md
│       ├── 03-stack-and-docker.md
│       └── 04-conventions.md
├── docker/
│   ├── web/Dockerfile
│   ├── nginx/default.conf
│   └── entrypoint.sh
├── compose.yaml
├── compose.override.yaml      ← dev only, gitignored-ish
├── .env.example
├── pyproject.toml
├── config/                    ← Django project (settings split into base/dev/prod)
└── apps/
    ├── tenancy/               ← Organization, Department, Membership, User, middleware
    ├── catalog/               ← Category, UoM, Item, Supplier, ItemSupplier
    ├── inventory/             ← StockLevel, StockMovement, Batch, SerialUnit, Location
    ├── procurement/           ← Requisition, PurchaseOrder, GRN
    ├── issuance/              ← Issue, Return, Transfer, Disposal
    ├── assets/                ← Asset, AMC, Calibration, Compliance registers
    ├── intelligence/          ← forecasting, reorder engine, ABC/XYZ, anomaly detection
    ├── alerts/                ← Alert, AlertRule, notification dispatch
    ├── reporting/             ← report definitions, exports, dashboards
    └── core/                  ← abstract bases, audit log, mixins, utils
```

There is no `ims_app` to dissolve — `apps/*` is written directly, greenfield, from Phase 1
onward (see D-11 in `MEMORY.md`).

---

## 6. Role model

| Role | Scope | Can do |
|---|---|---|
| `TRUST_ADMIN` | All organisations | Everything, everywhere. Cross-org dashboard, cross-org edit, org CRUD, transfers between orgs. |
| `ORG_ADMIN` | One organisation | Everything within that org: users, departments, masters, approvals, reports. |
| `STORE_MANAGER` | One org, ≥1 store | Receive stock, issue stock, adjust, raise POs, resolve alerts. |
| `DEPT_STAFF` | One org, one department | Raise requisitions, receive issued items, acknowledge returns, view own department's stock. |
| `AUDITOR` | One org, read-only | Read everything in the org including logs. Write nothing. |

Roles live on `Membership` (user × organisation), **not** on `User`. One human can hold
different roles in different organisations — a Trust IT lead may be `STORE_MANAGER` in CET
and `AUDITOR` in IMS. `TRUST_ADMIN` is a flag on `User`, since it is inherently cross-org.

---

## 7. Definition of Done (every phase)

- [ ] `docker compose up` starts clean from a fresh volume, no manual steps
- [ ] `makemigrations --check --dry-run` reports no missing migrations
- [ ] `pytest` green, including the tenant-isolation suite
- [ ] `ruff check .` and `ruff format --check .` clean
- [ ] Every new tenant-owned model inherits `TenantOwnedModel` and has a scoping test
- [ ] No `.objects.all()` on tenant data outside the tenancy layer itself
- [ ] `PROGRESS.md`, `MEMORY.md` and affected context files updated
- [ ] Seed/demo data still loads: `docker compose exec web python manage.py seed_demo`

---

## 8. Quick command reference

```bash
docker compose up --build              # start everything
docker compose exec web bash           # shell inside the app container
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web pytest -q
docker compose exec web ruff check . --fix
docker compose exec db psql -U sits -d sits
docker compose logs -f worker          # celery
docker compose down -v                 # nuke volumes, start over
```

---

## 9. Anti-patterns — reject these on sight

- `Product.objects.all()` in a view → use `Item.objects.for_request(request)`
- `organization_id` read from `request.POST` / `request.GET` / a URL kwarg
- `if org.slug == "cet":` → policy belongs in data, on the `Organization` row
- `quantity = quantity - n` written directly on the item row → stock changes go through
  `StockMovement` inside `transaction.atomic()` with `select_for_update()`
- A new `.bat` or `.ps1` script
- `pip install` in a shell instead of adding to `pyproject.toml` and rebuilding
- A migration that back-fills data without a `reverse_code`
- Silently widening a permission to make a test pass
