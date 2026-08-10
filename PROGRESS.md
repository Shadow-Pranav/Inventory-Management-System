# PROGRESS.md — SITS Build Status

> **Read this first, every session.** Update it last, every session.
> Statuses: `NOT STARTED` · `IN PROGRESS` · `BLOCKED` · `DONE`

---

## RESUME HERE

| | |
|---|---|
| **Last session** | Session 2 (2026-08-10) — Phase 2 gated closed (cold-start + full gate green, user-run down -v); Phase 3 opened |
| **Current phase** | Phase 3 — Access control & org administration |
| **Phase status** | `IN PROGRESS` — checklist expanded, no code yet |
| **Next action** | Start Task 1: `require_role` applied to every existing view + permission-matrix test fixture |
| **Blockers** | None. Q4–Q8 still open, needed before Phase 5. |
| **Branch** | `main` — 9 commits (`824a109` … `88f29cc` Phase 2 gate close); tree clean, 86/86 tests passing |

---

## Phase board

| # | Phase | Status | Started | Done | Notes |
|---|---|---|---|---|---|
| 0 | Bootstrap the project | `DONE` | 2026-08-09 | 2026-08-09 | Greenfield (D-11); cold-start verified |
| 1 | Tenancy foundation | `DONE` | 2026-08-09 | 2026-08-09 | Gate passed cold-start, 19/19 tests, DoD walked |
| 2 | Catalogue & inventory models | `DONE` | 2026-08-09 | 2026-08-10 | Gate passed cold-start (user-run), 86/86 tests, isolation 55/55, ruff clean |
| 3 | Access control & org admin | `IN PROGRESS` | 2026-08-10 | — | Stale note removed: `Item.quantity` never existed (D-05/D-11, greenfield) — nothing to drop |
| 4 | Master data & catalogue | `NOT STARTED` | — | — | |
| 5 | Procurement (Req→PO→GRN) | `NOT STARTED` | — | — | |
| 6 | Issuance, returns, transfers | `NOT STARTED` | — | — | |
| 7 | Assets & compliance | `NOT STARTED` | — | — | |
| 8 | Intelligence layer | `NOT STARTED` | — | — | Celery comes up here |
| 9 | Alerts & notifications | `NOT STARTED` | — | — | |
| 10 | Dashboards & reporting | `NOT STARTED` | — | — | Trust dashboard is the flagship |
| 11 | API & integrations | `NOT STARTED` | — | — | Optional for v1 |
| 12 | Hardening & deployment | `NOT STARTED` | — | — | |

**Overall: 3 / 13 phases complete.**

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

## Phase 2 — task checklist (DONE, 2026-08-10)

<details><summary>All 6 tasks complete, gate passed — expand for the record</summary>

All 6 tasks complete, phase gate passed 2026-08-10.

- [x] `apps/catalog/`: `Category`, `Item` (no `quantity`), `UnitOfMeasure`, `Supplier`
      (+ `blacklist_reason`, not in the original spec but paired with `is_blacklisted`),
      `ItemSupplier` — org-scoped `UniqueConstraint`s on `Item.name`, `Item.sku`,
      `Category.name` from the first migration (F-01's lesson, applied proactively)
- [x] `apps/inventory/`: `Location` (real hierarchy per D-12/Q2 — multiple stores per org,
      not a single `MAIN_STORE` default), `StockLevel` (with a *second*, partial unique
      constraint — Postgres doesn't dedupe `NULL` batches, see D-14), `StockMovement` (the
      ledger, `balance_after` per F-03, `save()` raises on update — "append-only" enforced,
      not just documented), `Batch`, `SerialUnit` (`asset` O2O deferred to Phase 7)
- [x] `apps/inventory/services.py::apply_movement()` per context 04 §2 — the only writer of
      `StockLevel.quantity`, `transaction.atomic()` + `select_for_update()`, uses
      `.for_organization()` not the ambient contextvar (D-14). Moving-average cost update
      is item-level, `RECEIPT`/`OPENING` only. 6 service tests including the **10-parallel-
      issues-from-5 concurrency test from this phase's acceptance criteria — passes**
- [x] `apps/issuance/`: `IssueRequest`, `IssueItem` (built directly — no `Order` to rename).
      `issue_number` deliberately left unconstrained — Phase 5 owns doc numbering (X-08)
- [x] Views/forms/templates: category tree (flat list — Phase 4 does the real tree UI), item
      CRUD + detail, stock level view, manual stock adjustment (routed through
      `apply_movement()`), issue-request raise/list — `TenantModelForm` with `tenant_fields`,
      templates at `apps/<app>/templates/<app>/`. **Found and fixed a major bug in the
      process**: every `TenantModelForm` subclass with a FK field crashed at import time
      (G-09) — Django's `ModelFormMetaclass` calls the strict manager before any request
      exists. Fixed with a custom metaclass; `context/02-tenancy.md` corrected to match.
      13 new form/view tests, including real end-to-end Client-based login→view cycles
- [x] `Membership.stores` M2M to `inventory.Location` filled in now that the app exists
      (X-06 closed, D-14)
- [x] Isolation suite auto-extended: 5 catalog + 5 inventory + 2 issuance models × 4 checks
      = 55 isolation assertions, all via `<Model>Factory` per app (G-06's convention)
- [x] Phase gate: cold-start (`down -v && up --build`, user-run — G-05), `makemigrations
      --check` (no changes), `pytest` (86/86), `pytest -k isolation` (55/55), `ruff
      check`/`format --check` clean, `seed_demo` clean — all re-run against the fresh volume,
      not just the pre-existing one. CLAUDE.md §7 DoD walked item by item, no gaps (including
      a grep for stray `.objects.all()` outside the tenancy layer — the one hit is
      `test_isolation.py`'s own assertion that it *raises*, not a leak).

</details>

## Phase 3 — task checklist (IN PROGRESS, started 2026-08-10)

- [x] `require_role` applied to every existing view (catalog, inventory, issuance); permission
      matrix (role × view × read/write) built as a test fixture so the matrix *is* the test.
      Found and fixed one real gap: `issue_request_create` only had `require_org_context`, no
      `write=True` role check — any authenticated member (including auditors) could POST it.
      New `apps/tenancy/tests/test_permission_matrix.py` (6 tests, drives 10 views × 4 roles
      + trust-admin-bypass + auditor-forbidden through real URLs via the test client, not the
      decorator in isolation) — 92/92 total tests green
- [x] `AUDITOR` write-blocking: `require_role(..., write=True)` rejects auditors regardless of
      role list — already true of the decorator since Phase 1 (G-07); confirmed end-to-end by
      `test_permission_matrix_auditor_forbidden_on_every_write_view` above, not just unit-tested
- [x] Org Admin UI: `apps/tenancy/views.py` — `member_list`/`member_invite`/`member_update`
      (role + department + `is_active` in one form — no separate "deactivate" endpoint),
      `department_list`/`create`/`update`, `audit_log_list` (`ORG_ADMIN` + `AUDITOR`, per the
      role table — auditors read logs too). New `apps/tenancy/forms.py`
      (`MembershipInviteForm`, `MembershipRoleForm`, `DepartmentForm`) and
      `apps/tenancy/emails.py::send_password_setup_email` — **not** Django's built-in
      `PasswordResetForm`, which silently skips any user without a usable password
      (`get_users()` filters on `has_usable_password()`); a freshly invited user always has
      one, by design, so that form would drop every invite email. Built the same
      token/uid/link by hand instead. Full `registration/password_reset_*` template set
      added since the invite flow depends on it (`registration/password_reset_confirm.html`,
      `_complete.html`, `_email.html`, `_subject.txt`, plus `_form.html`/`_done.html` for
      the self-service "forgot password" entry point Task 6 needs). 12 new tests in
      `apps/tenancy/tests/test_org_admin_views.py`. **Deferred, flagged in code and
      `MEMORY.md`:** `Membership` isn't a `TenantOwnedModel` (predates it, different
      `on_delete` semantics) so it has no `.for_request()`/`get_tenant_object()` — scoped by
      hand in a `_membership_queryset()` helper instead, same pattern `switch_organization`
      already used. 113/113 tests green
- [ ] Trust Admin UI: organisation CRUD, assign first Org Admin, org switcher, cross-org user
      search
- [x] `apps/core/audit.py` — `pre_save`/`post_save`/`post_delete` receivers connected from
      `CoreConfig.ready()` for every model in `settings.AUDITED_MODELS` (currently
      `Organization`, `Department`, `Membership`, `Item`, `Category`, `Supplier`).
      `AuditLog` (new `apps/core` model, append-only like `StockMovement`) records
      field-level diffs (`{field: [old, new]}` for CREATE/UPDATE, last-known state for
      DELETE); actor and `actor_scope` come from new context-var plumbing
      (`apps/core/context.py::set_current_actor`, set by `OrganizationMiddleware`) since
      signals have no `request`. `Organization` itself is audited against its own row
      (no separate org to attribute a creation to). M2M fields (`Membership.stores`) are
      **not** captured — `post_save`/`pre_save` don't see `m2m_changed`; deferred, see
      `MEMORY.md`. 9 new tests in `apps/core/tests/test_audit.py`; `AuditLog` excluded from
      the generic isolation suite with an explained reason (auditing `Organization` itself
      breaks that suite's "factory calls are side-effect-free for other models" assumption)
      — its own isolation is asserted directly instead. 101/101 tests green
- [ ] Password reset via email (Mailhog in dev), `django-axes` login rate limiting, session
      expiry, forced password change on first login for seeded accounts
- [ ] Navbar/sidebar renders only permitted links (UX only — decorator remains the actual
      security boundary)

**Acceptance:** permission matrix test passes for all 5 roles × all views; Org Admin of
Nursing gets 404 (not 403) on a CET item URL; auditor gets 403 on every POST/PUT/DELETE;
audit log records who changed what, from what, to what; a trust admin editing IMS data
produces a row visible to the IMS Org Admin.

---

## Files created so far

```
manage.py, pyproject.toml, uv.lock, compose.yaml, Makefile, README.md
.env.example, .env (gitignored), .gitignore, .gitattributes, .dockerignore
docker/web/Dockerfile, docker/entrypoint.sh, docker/nginx/default.conf
config/{__init__,celery,urls,wsgi,asgi}.py
config/settings/{__init__,base,dev,prod,test}.py
templates/base.html, templates/partials/navbar.html
templates/registration/login.html, password_reset_{form,done,confirm,complete,email}.html,
  password_reset_subject.txt

apps/__init__.py
apps/core/{__init__,apps,models,views,urls,admin,audit}.py
apps/core/{managers,context,exceptions,forms,factories,context_processors}.py
apps/core/migrations/{__init__,0001_initial}.py
apps/core/tests/{__init__,test_healthz,factories,test_audit}.py

apps/tenancy/{__init__,apps,models,admin,middleware,decorators,views,urls,forms,emails,context_processors}.py
apps/tenancy/migrations/{__init__,0001_initial,0002_seed_organizations,0003_membership_stores}.py
apps/tenancy/fixtures/organizations.json
apps/tenancy/management/commands/{seed_demo,create_trust_admin}.py
apps/tenancy/tests/{__init__,factories,test_isolation,test_decorators,test_permission_matrix,test_org_admin_views}.py
apps/tenancy/templates/tenancy/{no_access,switch_organization,member_list,member_form,
  member_role_form,department_list,department_form,audit_log_list}.html

apps/catalog/{__init__,apps,models,admin,forms,views,urls}.py
apps/catalog/migrations/{__init__,0001_initial}.py
apps/catalog/tests/{__init__,factories,test_forms,test_views}.py
apps/catalog/templates/catalog/{category_list,category_form,item_list,item_detail,item_form}.html

apps/inventory/{__init__,apps,models,admin,forms,views,urls,services,exceptions}.py
apps/inventory/migrations/{__init__,0001_initial}.py
apps/inventory/tests/{__init__,factories,test_services,test_views}.py
apps/inventory/templates/inventory/{stock_level_list,stock_adjustment_form}.html

apps/issuance/{__init__,apps,models,admin,forms,views,urls}.py
apps/issuance/migrations/{__init__,0001_initial}.py
apps/issuance/tests/{__init__,factories,test_views}.py
apps/issuance/templates/issuance/{issue_request_list,issue_request_form}.html
```

Update this tree as apps are created. It is how the next session knows the layout without
scanning the repo.

---

## Test status

| Suite | Tests | Passing | Coverage |
|---|---|---|---|
| core (`/healthz/`, `test_audit.py`) | 10 | 10 | `AuditLog` create/update/delete/no-op/trust-scope/org-scoping/append-only |
| tenancy isolation (`test_isolation.py`) | 7 | 7 | `Department` (`AuditLog` covered in core instead — see `MEMORY.md` D-16) |
| tenancy access control (`test_decorators.py`) | 11 | 11 | `require_org_context`, `require_role`, `require_trust_admin`, `get_tenant_object` |
| tenancy permission matrix (`test_permission_matrix.py`) | 6 | 6 | 10 views × 4 roles + trust-admin bypass + auditor-forbidden, through real URLs |
| tenancy org admin UI (`test_org_admin_views.py`) | 12 | 12 | invite (+ email sent, + duplicate rejection), role/dept/active update, department CRUD, audit log (org-scoped, auditor-visible, non-admin-forbidden) |
| catalog | 28 | 28 | Isolation ×5 models (20), `TenantModelForm` regression (G-09) ×3, views ×5 |
| inventory | 29 | 29 | Isolation ×5 models (20), `apply_movement()` ×6 (incl. concurrency), views ×3 |
| procurement | 0 | — | Phase 5 |
| issuance | 10 | 10 | Isolation ×2 models, views ×2 |
| assets | 0 | — | Phase 7 |
| intelligence | 0 | — | Phase 8 |
| alerts | 0 | — | Phase 9 |
| **Total** | **113** | **113** | — |

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

### 2026-08-10 — Session 2
- Docker Desktop wasn't running at session start; started it, brought the stack up (`docker
  compose up -d --build`), confirmed `/healthz/` → 200.
- Ran the Phase 2 gate on the live stack (migrations/tests/isolation/ruff/seed_demo, all
  green), then the user ran the cold-start check (`down -v && up --build`, G-05) themselves
  and confirmed it worked; re-ran the full gate against the fresh volume — still 86/86 tests,
  55/55 isolation, ruff clean. **Phase 2 closed.**
- Fixed a stale Phase 3 board note ("Drop `Item.quantity` at the end") — that field never
  existed per D-05/D-11 (greenfield); nothing to drop.
- Phase 3 (access control & org admin) opened, checklist expanded from `PROMPTS.md`. No
  blockers; Q4–Q8 still open but don't block this phase.

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
- `/checkpoint`: `web` container crashed on a Docker Desktop Windows file-sharing glitch
  (`OSError: No such device`, then a stuck mount path) — unrelated to app code. Restarting
  Docker Desktop fixed it; `db`/`redis` data untouched throughout. Recorded as G-08.
- `/session-start` (same day, continued): fixed a stale context 04 reference to
  `templates/ims_app/base.html` (doesn't exist — greenfield, D-11), then built all 6 Phase 2
  tasks: `apps/catalog` (5 models), `apps/inventory` (5 models + `apply_movement()`),
  `apps/issuance` (2 models), `Membership.stores`, and views/forms/templates for all three
  apps.
- Found and fixed a major bug: every `TenantModelForm` subclass with a FK field crashed at
  *import time* — Django's `ModelFormMetaclass` calls the strict `TenantManager` before any
  request or contextvar exists. Fixed via a custom metaclass in `apps/core/forms.py`
  (G-09); `context/02-tenancy.md` corrected, since the bug traced back to its code sample.
- Concurrency test from Phase 2's own acceptance criteria (10 parallel issues from a stock
  of 5 → exactly 5 succeed) passes. 86/86 tests green, ruff clean, no pending migrations.
  Smoke-tested all 4 new list views end-to-end via curl login.
- Next: run `/next-phase` to gate Phase 2 closed (user-run cold-start, G-05), then open
  Phase 3 (access control & org admin).

### 2026-XX-XX — Session 0 (setup)
- Audited the original repo; produced `ANALYSIS.md`
- Created `CLAUDE.md`, `INSTRUCTIONS.md`, `PROMPTS.md`, `MEMORY.md`, context files, slash commands
- Next: Phase 0
