# PROGRESS.md — SITS Build Status

> **Read this first, every session.** Update it last, every session.
> Statuses: `NOT STARTED` · `IN PROGRESS` · `BLOCKED` · `DONE`

---

## RESUME HERE

| | |
|---|---|
| **Last session** | Session 1 (2026-08-09) — Phase 0 and Phase 1 both closed (gates passed, cold-start verified by the user each time); Phase 2 opened |
| **Current phase** | Phase 2 — Catalogue & inventory models |
| **Phase status** | `IN PROGRESS` — not yet started coding |
| **Next action** | Start Phase 2 task 1: `apps/catalog/` models (`Category`, `Item`, `UnitOfMeasure`, `Supplier`, `ItemSupplier`), org-scoped `UniqueConstraint`s from the first migration. |
| **Blockers** | None. Q4–Q8 still open, needed before Phase 5. |
| **Branch** | `main` — 5 commits (`824a109`, `2a35217`, `38173b4`, `74282ba`, `5b49348`) |

---

## Phase board

| # | Phase | Status | Started | Done | Notes |
|---|---|---|---|---|---|
| 0 | Bootstrap the project | `DONE` | 2026-08-09 | 2026-08-09 | Greenfield (D-11); cold-start verified |
| 1 | Tenancy foundation | `DONE` | 2026-08-09 | 2026-08-09 | Gate passed cold-start, 19/19 tests, DoD walked |
| 2 | Catalogue & inventory models | `IN PROGRESS` | 2026-08-09 | — | Tenancy-scoped from the first migration (greenfield, D-11) |
| 3 | Access control & org admin | `NOT STARTED` | — | — | Drop `Item.quantity` at the end |
| 4 | Master data & catalogue | `NOT STARTED` | — | — | |
| 5 | Procurement (Req→PO→GRN) | `NOT STARTED` | — | — | |
| 6 | Issuance, returns, transfers | `NOT STARTED` | — | — | |
| 7 | Assets & compliance | `NOT STARTED` | — | — | |
| 8 | Intelligence layer | `NOT STARTED` | — | — | Celery comes up here |
| 9 | Alerts & notifications | `NOT STARTED` | — | — | |
| 10 | Dashboards & reporting | `NOT STARTED` | — | — | Trust dashboard is the flagship |
| 11 | API & integrations | `NOT STARTED` | — | — | Optional for v1 |
| 12 | Hardening & deployment | `NOT STARTED` | — | — | |

**Overall: 2 / 13 phases complete.**

---

## Phase 0 — task checklist (DONE, 2026-08-09)

<details><summary>All 16 items complete — expand for the record</summary>

- [x] `git init`
- [x] `pyproject.toml` + `uv.lock`
- [x] `docker/web/Dockerfile` (multi-stage; venv at `/opt/venv`, see G-01/G-02 in `MEMORY.md`)
- [x] `docker/entrypoint.sh` (executable bit set, LF endings — had to be fixed in a follow-up
      commit; `core.fileMode=false` on this checkout ate the bit on first commit, see G-04)
- [x] `compose.yaml` with profiles
- [x] `docker/nginx/default.conf`
- [x] `.dockerignore`, `.gitattributes`
- [x] Hand-written `config/` project layout (no local Python to run `django-admin` with —
      see MEMORY.md), split settings → `base/dev/prod/test`
- [x] `config/celery.py` (wired, `worker`/`beat` behind `async` profile — not started)
- [x] `apps/core/` + `TimeStampedModel` + `/healthz/` (with a passing test)
- [x] Write `README.md`
- [x] `.gitignore`
- [x] `docker compose up --build` healthy: migrate, `/healthz/` → `{"status":"ok",...}` 200,
      admin site loads (superuser `admin` created locally; password was shown once in chat,
      not stored anywhere in the repo — reset it if lost:
      `docker compose exec web python manage.py changepassword admin`)
- [x] `Makefile`
- [x] `pytest -q` green (1 test), `ruff check .` clean, `ruff format --check .` clean,
      `makemigrations --check --dry-run` clean
- [x] Cold-start verified: `docker compose down -v && docker compose up --build` — this
      command is hard-denied in `.claude/settings.json` for Claude to run directly; the user
      ran it manually and confirmed a clean start. `/healthz/` re-checked afterward → 200.

</details>

## Phase 1 — task checklist (DONE, 2026-08-09)

<details><summary>All 9 tasks complete, gate passed — expand for the record</summary>

- [x] `apps/tenancy/`: `Organization`, `Department`, `User(AbstractUser)`, `Membership`
      models; `AUTH_USER_MODEL = "tenancy.User"` set before the first migration.
      `USERNAME_FIELD="email"` per context 01 (see D-13 in `MEMORY.md`)
- [x] `apps/core/`: `TenantOwnedModel`, `TenantQuerySet`, `TenantManager`,
      `UnscopedQueryError`, `contextvars`-based `get_current_organization` /
      `set_current_organization` / `clear_current_organization`. Also added
      `apps/core/forms.py`, `apps/core/factories.py` (G-06), `apps/core/context_processors.py`
- [x] `apps/tenancy/middleware.py` — `OrganizationMiddleware` with `try/finally` clear,
      registered after `AuthenticationMiddleware`; membership resolution follows context 02
      §5's pinned→default→first-membership order from the start
- [x] `apps/tenancy/decorators.py` — `require_org_context`, `require_role(*roles,
      write=False)`, `require_trust_admin`, `get_tenant_object` — all covered by
      `test_decorators.py` (11 tests)
- [x] `apps/core/forms.py` — `TenantModelForm` with `tenant_fields` narrowing loop
- [x] **Data migration** (`apps/tenancy/migrations/0002_seed_organizations.py`) — seven SRMS
      organisations loaded from `apps/tenancy/fixtures/organizations.json` at migration
      runtime (never hardcoded in the migration file itself — CLAUDE.md §1); superusers get
      `is_trust_admin=True`. `DEFAULT_ORG`/legacy-`UserProfile` migration step is N/A —
      greenfield, see D-13
- [x] Management commands: `seed_demo` (trust admin + 4 roles × 2 orgs, idempotent, verified),
      `create_trust_admin`
- [x] `apps/tenancy/tests/test_isolation.py` — auto-discovering parametrised suite; covers
      `Department` now (not zero — see the corrected note in `PROMPTS.md` Phase 1). Found and
      fixed two real bugs in the process — G-06, G-07 in `MEMORY.md`
- [x] Org switcher view + navbar dropdown (only when >1 membership or trust admin) — smoke
      tested end-to-end via curl login as a demo user, confirmed org resolves and renders
- [x] Phase gate: cold-start (`down -v && up --build`, user-run — G-05), `makemigrations
      --check`, `pytest` (19/19), `pytest -k isolation` (7/7), `ruff check`/`format --check`,
      `seed_demo` all clean on the fresh volume. CLAUDE.md §7 DoD walked, no gaps.

</details>

## Phase 2 — task checklist (IN PROGRESS, started 2026-08-09)

> Greenfield (D-11): building `catalog`/`inventory` directly, tenancy-scoped from the first
> migration — no `RenameModel` off a legacy `ims_app`. No `quantity` field on `Item`, ever
> (D-05) — `StockLevel` is the balance from day one.

- [ ] `apps/catalog/`: `Category`, `Item` (no `quantity`), `UnitOfMeasure`, `Supplier`,
      `ItemSupplier` — org-scoped `UniqueConstraint`s on `Item.name`, `Item.sku`,
      `Category.name` from the first migration (F-01's lesson, applied proactively)
- [ ] `apps/inventory/`: `Location` (real hierarchy per D-12/Q2 — multiple stores per org,
      not a single `MAIN_STORE` default), `StockLevel`, `StockMovement` (the ledger,
      `balance_after` per F-03), `Batch`, `SerialUnit`
- [ ] `apps/inventory/services.py::apply_movement()` per context 04 §2 — the only writer of
      `StockLevel.quantity`, `transaction.atomic()` + `select_for_update()`
- [ ] `apps/issuance/`: `IssueRequest`, `IssueItem` (built directly — no `Order` to rename)
- [ ] Views/forms/templates: category tree, item CRUD + detail, stock level view, manual
      stock adjustment (routed through `apply_movement()`), issue-request raise/list —
      `TenantModelForm` with `tenant_fields`, templates at `apps/<app>/templates/<app>/`
- [ ] Extend the isolation suite: add `<Model>Factory` for every new `TenantOwnedModel` in
      each app's `tests/factories.py` (the suite auto-discovers from there — see G-06)
- [ ] Extend `Membership` with the deferred `stores` M2M to `inventory.Location` (X-06)

Phases 3–12 checklists get expanded when each phase starts. Do not pre-expand them —
they go stale and cost tokens to read.

---

## Files created so far

```
manage.py, pyproject.toml, uv.lock, compose.yaml, Makefile, README.md
.env.example, .env (gitignored), .gitignore, .gitattributes, .dockerignore
docker/web/Dockerfile, docker/entrypoint.sh, docker/nginx/default.conf
config/{__init__,celery,urls,wsgi,asgi}.py
config/settings/{__init__,base,dev,prod,test}.py
templates/base.html, templates/registration/login.html, templates/partials/navbar.html

apps/__init__.py
apps/core/{__init__,apps,models,views,urls}.py
apps/core/{managers,context,exceptions,forms,factories,context_processors}.py
apps/core/migrations/__init__.py
apps/core/tests/{__init__,test_healthz}.py

apps/tenancy/{__init__,apps,models,admin,middleware,decorators,views,urls,context_processors}.py
apps/tenancy/migrations/{__init__,0001_initial,0002_seed_organizations}.py
apps/tenancy/fixtures/organizations.json
apps/tenancy/management/commands/{seed_demo,create_trust_admin}.py
apps/tenancy/tests/{__init__,factories,test_isolation,test_decorators}.py
apps/tenancy/templates/tenancy/{no_access,switch_organization}.html
```

Update this tree as apps are created. It is how the next session knows the layout without
scanning the repo.

---

## Test status

| Suite | Tests | Passing | Coverage |
|---|---|---|---|
| core (`/healthz/`) | 1 | 1 | — |
| tenancy isolation (`test_isolation.py`) | 7 | 7 | `Department`; other tenant models don't exist yet |
| tenancy access control (`test_decorators.py`) | 11 | 11 | `require_org_context`, `require_role`, `require_trust_admin`, `get_tenant_object` |
| catalog | 0 | — | — |
| inventory | 0 | — | — |
| procurement | 0 | — | — |
| issuance | 0 | — | — |
| assets | 0 | — | — |
| intelligence | 0 | — | — |
| alerts | 0 | — | — |
| **Total** | **19** | **19** | — |

No baseline to carry over — greenfield build, see D-11 in `MEMORY.md`.

---

## Open questions for the user

| # | Question | Status | Answer |
|---|---|---|---|
| Q1 | Exact legal names of all organisations under SRMS Trust? Current list is 7 — is it complete? | **ANSWERED** (2026-08-09) | Use the 7 names in `CLAUDE.md` §1 verbatim (IMS, CET, Nursing, Hotel Management, Business School, Hospital, Riddhima). |
| Q2 | Does each institution have one central store or several sub-stores per department? | **ANSWERED** (2026-08-09) | Multiple stores per org from day one — `inventory.Location` is a real hierarchy from Phase 2, not a single `MAIN_STORE` default. See D-12 in `MEMORY.md`. |
| Q3 | Approval thresholds for POs — fixed Trust-wide, or per institution? | **ANSWERED** (2026-08-09) | Trust-wide default, per-org override in `organization.settings["approval_thresholds"]`. Confirms the design already sketched in Phase 5 of `PROMPTS.md`. See D-12. |
| Q4 | Is the hospital's pharmacy/drug inventory in scope, or does it use a separate HMIS? | **OPEN** | |
| Q5 | Existing supplier/item master data to import, or start clean? | **OPEN** | |
| Q6 | Do institutions ever share stock, or is inter-org transfer purely theoretical? | **OPEN** | |
| Q7 | Deployment target — Trust's own server, cloud VM, or local network only? | **OPEN** | |
| Q8 | Barcode scanners available, or is a phone camera the realistic input device? | **OPEN** | |

Q1–Q3 answered — Phase 1 unblocked. Q4–Q8 can wait but should be resolved before Phase 5.

---

## Deferred / parked

| Item | Reason | Revisit at |
|---|---|---|
| Shared Trust-wide vendor registry | Per-org suppliers are simpler and cover the real need | Phase 5, if duplicate vendors become painful |
| Multi-currency | Not in scope; INR only | Never, unless the Trust internationalises |
| ML-based forecasting | EWMA is sufficient and explainable | Phase 8, only if MAPE is unacceptable |
| Mobile native app | HTMX + responsive Bootstrap covers it | Post-v1 |
| Schema-per-tenant isolation | Cross-org dashboard is the core requirement | Only if a compliance audit demands it |

---

## Session log

Newest first. Keep entries to three lines. Detail belongs in `MEMORY.md`.

### 2026-08-09 — Session 1
- Found no original-repo clone in the directory (planning bundle only, not a git repo) —
  asked the user; confirmed greenfield build. Recorded as D-11 in `MEMORY.md`.
- Updated `CLAUDE.md`, `PROMPTS.md` (Phases 0 & 2), `MEMORY.md` (D-05, D-06, D-11) to drop
  the migration framing.
- `git init`; scaffolded the entire Phase 0 stack by hand (no host Python for
  `django-admin startproject`): `pyproject.toml`/`uv.lock`, Docker files, `compose.yaml`,
  settings split, `config/celery.py`, `apps/core` with `/healthz/`.
- Hit and fixed three real bugs in the reference Dockerfile/compose from context 03 — see
  G-01 through G-04 in `MEMORY.md` (venv shadowed by the dev bind-mount; named volumes
  seeded root-owned; entrypoint.sh exec bit lost on commit). Context 03 updated to match.
- Stack is up and healthy: `/healthz/` → 200, admin loads, superuser `admin` created,
  `pytest`/`ruff`/`makemigrations --check` all clean. Committed in 2 commits (824a109,
  2a35217).
- `docker compose down -v` is hard-denied in `.claude/settings.json` (not just ask-listed —
  see G-05 in `MEMORY.md`); user ran the cold-start check manually and confirmed clean.
  **Phase 0 closed.**
- Phase 1 (tenancy foundation) opened, checklist expanded; blocked on Q1–Q3 before the org
  fixture task and any org-name UI — rest of Phase 1 can proceed.
- Asked and got Q1–Q3 answered (D-12): org names as-is, multiple stores per org from day
  one, Trust-wide default + per-org override for approval thresholds.
- Built all 9 Phase 1 tasks: tenancy models (custom `User`, `Organization`, `Department`,
  `Membership`), `apps/core` scoping machinery, `OrganizationMiddleware`, decorators,
  `TenantModelForm`, the org fixture + seed migration, `seed_demo`/`create_trust_admin`,
  the isolation suite, org switcher + navbar. AUTH_USER_MODEL swap required a DB reset
  (D-13) — approved, done via `psql` drop/recreate, not `docker compose down -v`.
- Found and fixed two real bugs while testing: factory-boy hitting the strict manager
  (G-06), and `TenantManager.for_request()`/`.for_organization()` being unreachable because
  Django's manager-method wrapper calls the strict `get_queryset()` first (G-07) — this was
  a bug in context 02's own reference code, now corrected there too.
- Added `test_decorators.py` (11 tests) since `require_role`/`require_org_context`/
  `require_trust_admin`/`get_tenant_object` had zero coverage otherwise — CLAUDE.md §3 rule
  5 territory. 19/19 tests green, ruff clean, no pending migrations.
- Smoke-tested the full login → middleware → org-switcher flow via curl as a demo user;
  confirmed org resolution and template rendering work end-to-end.
- `/next-phase`: user ran the cold-start check manually again (G-05 applies every phase, not
  just Phase 0). Full gate green on the fresh volume — migrations, 19/19 tests, isolation
  subset, ruff, `seed_demo`. CLAUDE.md §7 DoD walked, no gaps. **Phase 1 closed.**
- Phase 2 (catalogue & inventory models) opened, checklist expanded. No blockers.
- Next: `apps/catalog/` models.

### 2026-XX-XX — Session 0 (setup)
- Audited the original repo; produced `ANALYSIS.md`
- Created `CLAUDE.md`, `INSTRUCTIONS.md`, `PROMPTS.md`, `MEMORY.md`, context files, slash commands
- Next: Phase 0
