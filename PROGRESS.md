# PROGRESS.md — SITS Build Status

> **Read this first, every session.** Update it last, every session.
> Statuses: `NOT STARTED` · `IN PROGRESS` · `BLOCKED` · `DONE`

---

## RESUME HERE

| | |
|---|---|
| **Last session** | Session 1 (2026-08-09) — Phase 0 closed (cold-start verified by the user manually — see G-05 in `MEMORY.md`); Phase 1 opened |
| **Current phase** | Phase 1 — Tenancy foundation |
| **Phase status** | `IN PROGRESS` — not yet started coding |
| **Next action** | Ask the user Q1–Q3, then start Phase 1 task 1: `apps/tenancy` models (`Organization`, `Department`, `User`, `Membership`), setting `AUTH_USER_MODEL` before the first migration. |
| **Blockers** | **Q1–Q3 open** — org legal names, store structure, approval thresholds. Task 6 (org fixture) and any org-name-displaying UI cannot proceed without Q1; the rest of Phase 1 can. |
| **Branch** | `main` — 3 commits (`824a109` scaffold, `2a35217` exec-bit fix, `38173b4` docs) |

---

## Phase board

| # | Phase | Status | Started | Done | Notes |
|---|---|---|---|---|---|
| 0 | Bootstrap the project | `DONE` | 2026-08-09 | 2026-08-09 | Greenfield (D-11); cold-start verified |
| 1 | Tenancy foundation | `IN PROGRESS` | 2026-08-09 | — | Custom User must land here — **blocked on Q1–Q3, see below** |
| 2 | Migrate models to tenancy | `NOT STARTED` | — | — | The big structural phase |
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

**Overall: 1 / 13 phases complete.**

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

## Phase 1 — task checklist (IN PROGRESS, started 2026-08-09)

> **Blocked on Q1–Q3** (see Open questions below) before task 6 (org fixture) and any UI
> that displays org names. Tasks 1–5, 7–8 (models, core tenancy machinery, middleware,
> decorators, forms, management command shells, isolation suite scaffold) do not need the
> answers and can proceed first.

- [ ] `apps/tenancy/`: `Organization`, `Department`, `User(AbstractUser)`, `Membership`
      models; `AUTH_USER_MODEL = "tenancy.User"` set before any migration runs
- [ ] `apps/core/`: `TenantOwnedModel`, `TenantQuerySet`, `TenantManager`,
      `UnscopedQueryError`, `contextvars`-based `get_current_organization` /
      `set_current_organization` / `clear_current_organization`
- [ ] `apps/tenancy/middleware.py` — `OrganizationMiddleware` with `try/finally` clear,
      registered after `AuthenticationMiddleware`
- [ ] `apps/tenancy/decorators.py` — `require_org_context`, `require_role(*roles,
      write=False)`, `require_trust_admin`, `get_tenant_object`
- [ ] `apps/core/forms.py` — `TenantModelForm` with `tenant_fields` narrowing loop
- [ ] **Data migration** — seven SRMS organisations from a fixture (needs Q1); migrate any
      seed `UserProfile.role` values into `Membership` against a `DEFAULT_ORG` (N/A —
      greenfield, no legacy data to migrate, but `DEFAULT_ORG` decision for `seed_demo` still
      needs recording); superusers get `is_trust_admin=True`
- [ ] Management commands: `seed_demo`, `create_trust_admin`
- [ ] `apps/tenancy/tests/test_isolation.py` — auto-discovering parametrised suite (finds 0
      tenant models right now; that's fine, it must exist and pass)
- [ ] Org switcher view + navbar dropdown (only when >1 membership or trust admin)

Phases 2–12 checklists get expanded when each phase starts. Do not pre-expand them —
they go stale and cost tokens to read.

---

## Files created so far

```
manage.py, pyproject.toml, uv.lock, compose.yaml, Makefile, README.md
.env.example, .env (gitignored), .gitignore, .gitattributes, .dockerignore
docker/web/Dockerfile, docker/entrypoint.sh, docker/nginx/default.conf
config/{__init__,celery,urls,wsgi,asgi}.py
config/settings/{__init__,base,dev,prod,test}.py
apps/__init__.py
apps/core/{__init__,apps,models,views,urls}.py
apps/core/migrations/__init__.py
apps/core/tests/{__init__,test_healthz}.py
```

Update this tree as apps are created. It is how the next session knows the layout without
scanning the repo.

---

## Test status

| Suite | Tests | Passing | Coverage |
|---|---|---|---|
| core (`/healthz/`) | 1 | 1 | — |
| tenancy isolation | 0 | — | — |
| catalog | 0 | — | — |
| inventory | 0 | — | — |
| procurement | 0 | — | — |
| issuance | 0 | — | — |
| assets | 0 | — | — |
| intelligence | 0 | — | — |
| alerts | 0 | — | — |
| **Total** | **1** | **1** | — |

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
- Next: ask Q1–Q3, then start `apps/tenancy` models.

### 2026-XX-XX — Session 0 (setup)
- Audited the original repo; produced `ANALYSIS.md`
- Created `CLAUDE.md`, `INSTRUCTIONS.md`, `PROMPTS.md`, `MEMORY.md`, context files, slash commands
- Next: Phase 0
