# PROGRESS.md — SITS Build Status

> **Read this first, every session.** Update it last, every session.
> Statuses: `NOT STARTED` · `IN PROGRESS` · `BLOCKED` · `DONE`

---

## RESUME HERE

| | |
|---|---|
| **Last session** | Session 1 (2026-08-09) — confirmed greenfield build (D-11), scaffolded the whole Phase 0 stack, stack is up and healthy |
| **Current phase** | Phase 0 — Bootstrap the project |
| **Phase status** | `IN PROGRESS` — one item left (see below) |
| **Next action** | Run the cold-start check (`docker compose down -v && docker compose up --build`, needs explicit confirmation — destroys the dev volumes), then Phase 0 is done and Phase 1 (tenancy foundation) can start. |
| **Blockers** | None for finishing Phase 0. Q1–Q3 (org names, store structure, approval thresholds) are open; answer before Phase 1 starts. |
| **Branch** | `main` — 2 commits (`824a109` scaffold, `2a35217` entrypoint.sh exec-bit fix) |

---

## Phase board

| # | Phase | Status | Started | Done | Notes |
|---|---|---|---|---|---|
| 0 | Bootstrap the project | `IN PROGRESS` | 2026-08-09 | — | Greenfield (D-11); stack up and healthy, cold-start check outstanding |
| 1 | Tenancy foundation | `NOT STARTED` | — | — | Custom User must land here |
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

**Overall: 0 / 13 phases complete.**

---

## Phase 0 — task checklist

- [x] `git init` (no commit yet — commits are made only when you ask)
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
- [ ] Cold-start verified: `docker compose down -v && docker compose up --build` — **not yet
      run**; the tool call was denied when attempted this session. Run it before calling
      Phase 0 done.

Phases 1–12 checklists get expanded when each phase starts. Do not pre-expand them —
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
| Q1 | Exact legal names of all organisations under SRMS Trust? Current list is 7 — is it complete? | **OPEN** | |
| Q2 | Does each institution have one central store or several sub-stores per department? | **OPEN** | |
| Q3 | Approval thresholds for POs — fixed Trust-wide, or per institution? | **OPEN** | |
| Q4 | Is the hospital's pharmacy/drug inventory in scope, or does it use a separate HMIS? | **OPEN** | |
| Q5 | Existing supplier/item master data to import, or start clean? | **OPEN** | |
| Q6 | Do institutions ever share stock, or is inter-org transfer purely theoretical? | **OPEN** | |
| Q7 | Deployment target — Trust's own server, cloud VM, or local network only? | **OPEN** | |
| Q8 | Barcode scanners available, or is a phone camera the realistic input device? | **OPEN** | |

Ask Q1–Q3 before Phase 1. Q4–Q8 can wait but should be resolved before Phase 5.

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
- Cold-start check (`down -v && up --build`) not yet run — attempted, tool call was denied.
- Next: get the cold-start check approved and run, then close Phase 0 and start Phase 1
  (after Q1–Q3 are answered).

### 2026-XX-XX — Session 0 (setup)
- Audited the original repo; produced `ANALYSIS.md`
- Created `CLAUDE.md`, `INSTRUCTIONS.md`, `PROMPTS.md`, `MEMORY.md`, context files, slash commands
- Next: Phase 0
