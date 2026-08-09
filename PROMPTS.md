# PROMPTS.md — The SITS Build Brief

Thirteen phases. Each block is a self-contained brief: paste it, or say
`"Start Phase N"` and Claude Code will read the block itself.

**Before any phase:** read `CLAUDE.md`, `PROGRESS.md`, `MEMORY.md`, then only the context
files this phase's *Context* line names.
**After any phase:** run `/session-end`.

Each phase states: Goal · Context to load · Tasks · Acceptance · Do-not.

---

## Phase 0 — Bootstrap the project, containers-only from day one

> **Greenfield build.** There is no existing `ims_app` codebase in this repo (see D-11 in
> `MEMORY.md`) — Phase 0 creates a new Django project from scratch, not a container wrapper
> around code that already exists. `ANALYSIS.md` and Section B facts in `MEMORY.md` describe
> the *original* `Shadow-Pranav/Inventory-Management-System` repo as design reference only.

**Goal:** `git clone && cp .env.example .env && docker compose up` yields a healthy, empty
Django project on PostgreSQL, on Windows, macOS and Linux, with no host-level Python.

**Context:** `03-stack-and-docker.md`

**Tasks**
1. `git init` if not already a repo; first commit is this planning bundle as-is.
2. Create `pyproject.toml` (project metadata, deps, ruff config, pytest config). Deps:
   `django~=5.0`, `psycopg[binary]`, `python-decouple`, `Pillow`, `redis`, `celery`,
   `django-celery-beat`, `whitenoise`, `gunicorn`, `django-htmx`, `weasyprint`, `openpyxl`,
   `django-extensions`. Dev group: `pytest`, `pytest-django`, `pytest-cov`, `factory-boy`,
   `ruff`, `django-debug-toolbar`, `ipdb`. Generate `uv.lock`.
3. Write `docker/web/Dockerfile`, `docker/entrypoint.sh` (executable bit), `compose.yaml`,
   `docker/nginx/default.conf`, `.dockerignore`, `.gitattributes` (`*.sh text eol=lf`).
4. `django-admin startproject config .` inside the container (or equivalent scaffolding),
   then split `config/settings.py` → `config/settings/{base,dev,prod,test}.py` using the
   `python-decouple` `config()` pattern from context 03 §7. PostgreSQL only, no MySQL/SQLite
   fallback.
5. Add `config/celery.py` and wire it in `config/__init__.py`, but keep `worker`/`beat`
   behind the `async` compose profile — they stay down until Phase 8.
6. Add `apps/core/` with `TimeStampedModel` and a `/healthz/` view checking DB + Redis.
7. Write `README.md` from scratch: prerequisites (Docker Desktop only), quick start, command
   table, troubleshooting. No venv instructions anywhere.
8. Write `.gitignore`: `.env`, `*.sqlite3`, `staticfiles/`, `media/`, `.venv`, `__pycache__`.
9. `docker compose up --build` → `migrate` runs clean against an empty schema, `/healthz/`
   returns 200, `createsuperuser` works, admin site loads.

**Acceptance**
- `docker compose down -v && docker compose up --build` → healthy in one command, empty DB
- `docker compose exec web pytest` runs (even with zero tests collected) without error
- `grep -r "venv\|\.bat\|\.ps1" --include="*.md" .` returns nothing in docs
- No file outside `docker/` mentions a host Python install

**Do not:** add any domain model in this phase — no `Organization`, no `Item`, nothing.
Infrastructure and an empty, healthy Django project only. Domain modelling starts Phase 1.

---

## Phase 1 — Tenancy foundation

**Goal:** organisations, departments, memberships and a custom user exist; the scoping
machinery is in place and tested. No feature code uses it yet.

**Context:** `02-tenancy.md`, `01-domain-model.md` (tenancy + core sections)

> Do this before any other model work. Swapping `AUTH_USER_MODEL` later is the single most
> expensive migration in Django and there is no reason to accept that cost.

**Tasks**
1. `apps/tenancy/`: `Organization`, `Department`, `User(AbstractUser)`, `Membership`.
   Set `AUTH_USER_MODEL = "tenancy.User"` **now**, before any real data exists.
2. `apps/core/`: `TenantOwnedModel`, `TenantQuerySet`, `TenantManager`, `UnscopedQueryError`,
   and the thread-local helpers `get_current_organization` / `set_current_organization` /
   `clear_current_organization` (use `contextvars`, not `threading.local` — it is correct
   under ASGI too).
3. `apps/tenancy/middleware.py` — `OrganizationMiddleware` exactly as specified in context 02,
   including the `try/finally` clear. Register after `AuthenticationMiddleware`.
4. `apps/tenancy/decorators.py` — `require_org_context`, `require_role(*roles, write=False)`,
   `require_trust_admin`, and the `get_tenant_object` helper.
5. `apps/core/forms.py` — `TenantModelForm` with the `tenant_fields` narrowing loop.
6. Data migration: create the seven SRMS organisations from a fixture; migrate existing
   `UserProfile.role` values into `Membership` rows against a `DEFAULT_ORG`; set
   `is_trust_admin=True` for existing superusers. Record the `DEFAULT_ORG` decision in
   `MEMORY.md`.
7. Management commands: `seed_demo` (orgs, departments, users per role, sample masters) and
   `create_trust_admin`.
8. `apps/tenancy/tests/test_isolation.py` — the auto-discovering parametrised suite from
   context 02 §6. It will find zero tenant models right now. That is fine; it must exist and
   pass so that Phase 2 lights it up.
9. Org switcher view + navbar dropdown, rendered only when the user has >1 membership or is
   a trust admin.

**Acceptance**
- `Membership` role changes take effect without re-login
- `Item.objects.all()` with no active org raises `UnscopedQueryError` (assert on a temporary
  throwaway tenant model if `Item` does not exist yet)
- A user with no active membership is redirected, never shown empty-but-unscoped data
- The thread-local is provably cleared: a test that sets it, raises inside the view, and
  asserts it is `None` afterwards
- `seed_demo` produces logins for every role in at least two organisations

**Do not:** touch `ims_app` models yet. Build the machinery, prove it, then apply it.

---

## Phase 2 — Catalogue & inventory models, tenancy-scoped from the first migration

> **Greenfield build** (see D-11 in `MEMORY.md`): there is no `ims_app` to migrate off of.
> Models below are new; `RenameModel`/data-migration steps from earlier drafts of this brief
> don't apply. Design them as the target shape directly — org-scoped from their first
> migration, no parallel legacy field, no parity check.

**Goal:** the core catalogue and inventory domain exists, fully org-scoped, with working
views and templates (new, Bootstrap 5 + HTMX per D-09).

**Context:** `01-domain-model.md`, `02-tenancy.md`, `04-conventions.md`

**Tasks**
1. Create `apps/catalog/` and `apps/inventory/`:
   - `catalog.Category` (`organization`, `parent`, `code`, `name`)
   - `catalog.Item` (`organization`, `uom`, `item_type`, `tracking_mode`, `hsn_code`,
     `gst_rate`, `sku`, `name`, …) — **no `quantity` field on `Item`**; stock is derived
     (D-05) from day one, so there is nothing to keep in parallel or drop later.
   - `catalog.UnitOfMeasure`, `catalog.Supplier`, `catalog.ItemSupplier`
   - `inventory.Location`, `inventory.StockLevel`, `inventory.StockMovement` (the ledger;
     `balance_after` per F-03's pattern), `inventory.Batch`, `inventory.SerialUnit`
   - `issuance.IssueRequest`, `issuance.IssueItem` (the outbound-request concept from D-06,
     built directly — there is no `Order`/`OrderItem` to rename)
2. `Item.name` / `Item.sku` / `Category.name` uniqueness is an org-scoped
   `UniqueConstraint` from the first migration (F-01's lesson, applied proactively).
3. Implement `apply_movement()` in `apps/inventory/services.py` per context 04 §2; every
   stock mutation (opening balance included) goes through it inside
   `transaction.atomic()` + `select_for_update()` — never a direct field write.
4. Build the views/forms/templates for: category tree, item CRUD + detail, stock level view,
   manual stock adjustment (routed through `apply_movement()`), issue-request raise/list.
   Forms use `TenantModelForm` with `tenant_fields` (context 02).
5. Templates live at `apps/<app>/templates/<app>/` from the start — Bootstrap 5 + HTMX,
   no separate "move templates later" step.

**Acceptance**
- The isolation suite now covers ≥10 models and is green
- Two organisations can both hold an item named "Surgical Gloves" with SKU `MED-001`
- Every view lists/creates/edits only within `request`'s active organisation
- Concurrency test: 10 parallel issues of 1 unit from a stock of 5 → exactly 5 succeed

**Do not:** add a `quantity` field to `Item`, even temporarily — there is no legacy value to
preserve in parallel, so `StockLevel` is the balance from the first migration onward.

---

## Phase 3 — Access control, users and org administration

**Goal:** the five roles are fully enforced and administrable through the UI.

**Context:** `02-tenancy.md`, `04-conventions.md`

**Tasks**
1. Apply `require_role` to every view. Build a permission matrix (role × view × read/write)
   as a test fixture, so the matrix *is* the test.
2. `AUDITOR` write-blocking: `require_role(..., write=True)` rejects auditors regardless of
   the role list.
3. Org Admin UI: invite/create users, assign roles, manage departments, deactivate
   memberships, view the org's audit log.
4. Trust Admin UI: organisation CRUD, assign first Org Admin, org switcher, cross-org user
   search.
5. `apps/core/audit.py` — post-save/post-delete receivers writing `AuditLog` for every model
   in `settings.AUDITED_MODELS`. Capture field-level diffs. Mark trust-admin cross-org writes
   with `actor_scope="TRUST"`.
6. Password reset via email (Mailhog in dev), `django-axes` login rate limiting, session
   expiry, forced password change on first login for seeded accounts.
7. Navbar/sidebar renders only permitted links — but the decorator, not the template, is the
   security boundary. Hiding a link is UX, not access control.

**Acceptance**
- Permission matrix test passes for all 5 roles × all views
- An Org Admin of Nursing gets 404 (not 403) on a CET item URL
- An auditor gets 403 on every POST/PUT/DELETE
- Audit log records who changed what, from what, to what
- A trust admin editing IMS data produces a row visible to the IMS Org Admin

---

## Phase 4 — Master data & catalogue

**Goal:** rich, per-org master data with import/export, ready to feed procurement.

**Context:** `01-domain-model.md` (catalog + inventory), `04-conventions.md`

**Tasks**
1. Category tree UI (nested list, drag-free — parent select is fine), breadcrumb display,
   cycle prevention on save.
2. Full `Supplier` CRUD: GSTIN validation (regex + checksum), rating, blacklisting with a
   reason, contact history. Blacklisted suppliers cannot be selected on a new PO.
3. `ItemSupplier` price list with validity windows; surface "preferred supplier + last price"
   on the item detail page.
4. `UnitOfMeasure` per org with sensible defaults seeded (piece, box, kg, litre, pack, set).
5. Item detail page: current stock across locations, movement history (paginated), price
   history, suppliers, open POs, analytics placeholder.
6. Bulk CSV/XLSX import for items, suppliers and opening stock: preview → validate → row-level
   error report → commit atomically. **Import must respect tenancy**: the org comes from
   `request`, never from a column in the file.
7. Barcode/QR generation per item and per serial unit; printable label sheets (WeasyPrint).
8. Location hierarchy management with a tree view.

**Acceptance**
- Importing 500 items with 3 bad rows commits nothing and reports exactly those 3 rows
- Category cycles rejected with a clear message
- Labels print correctly at 38×25mm
- Item search covers name, SKU, barcode and is org-scoped

---

## Phase 5 — Procurement: requisition → PO → GRN

**Goal:** stock enters the system only through an auditable receipt trail.

**Context:** `01-domain-model.md` (procurement), `04-conventions.md`

**Tasks**
1. `Requisition` flow: department staff raise → Org Admin approves/partially approves/rejects
   with a reason → approved lines convert to a PO.
2. `PurchaseOrder`: multi-line, GST per line, subtotal/tax/total computed server-side (never
   from a hidden form field), delivery location, terms. Draft → Pending Approval → Approved.
3. Approval thresholds read from `organization.settings["approval_thresholds"]` — e.g. above
   ₹50,000 requires Org Admin, above ₹5,00,000 requires Trust Admin. **Data, not code.**
4. `GoodsReceipt`: receive against a PO, full or partial; record accepted vs rejected quantity
   with a rejection reason; capture batch number and expiry for `tracking_mode=BATCH`; capture
   serial numbers for `tracking_mode=SERIAL`. Posting a GRN emits one
   `StockMovement(RECEIPT)` per line inside one transaction and updates the moving average.
5. PO status auto-transitions on receipt: `PARTIALLY_RECEIVED` → `RECEIVED`.
6. PDF outputs for PO and GRN with org letterhead, logo and authorised-signatory block.
7. Document numbering per org per fiscal year with a `select_for_update()` sequence row.
8. Supplier performance metrics: on-time %, rejection %, average lead time — computed from
   GRN history and surfaced on the supplier page.

**Acceptance**
- Over-receipt beyond the ordered quantity is rejected (configurable tolerance in org settings)
- Posting a GRN twice does not double stock (idempotency key on the GRN)
- Two concurrent GRN postings produce unique, gapless document numbers
- Cancelling a posted GRN creates reversing movements; it never deletes them
- Cross-org check: a CET user cannot select an IMS supplier or receive against an IMS PO

---

## Phase 6 — Issuance, returns, transfers, disposal

**Goal:** the outbound half — stock leaves only through an auditable trail too.

**Context:** `01-domain-model.md` (issuance), `04-conventions.md`

**Tasks**
1. Refactor the migrated `IssueRequest` into the full flow: raise → approve → issue (full or
   partial) → acknowledge receipt.
2. Reservation: approval sets `StockLevel.reserved_quantity`; issue converts reservation to
   an `ISSUE` movement; cancellation releases it. `available = quantity - reserved`.
3. Batch selection strategy: FEFO (first-expiry-first-out) default for perishables, FIFO
   otherwise; allow manual override with a mandatory reason.
4. Serial-tracked issues: pick specific `SerialUnit`s, set `current_holder` and status.
5. `ReturnNote`: return with condition; `GOOD` restocks, `DAMAGED`/`EXPIRED` route to
   disposal rather than back into stock.
6. `StockTransfer`: intra-org between locations (Store Manager approves), and **inter-org**
   (requires Trust Admin approval, and writes movements in both organisations inside one
   transaction). This is the one legitimate cross-tenant write path — test it hard.
7. `DisposalRecord` with approval, method, and certificate upload.
8. Consumption capture for departments: per-department ledger and monthly consumption report.

**Acceptance**
- Issuing more than available fails with a clear message and zero partial writes
- FEFO picks the nearest-expiry batch; expired batches are never auto-picked
- Inter-org transfer produces exactly two movements, balances in both orgs, and one audit row
- Reserved stock is invisible to another department's availability check
- Concurrency test: two departments issuing the last unit — one succeeds, one gets `InsufficientStock`

---

## Phase 7 — Assets & compliance

**Goal:** deliver the "compliance regarding technical and non-technical resources" mandate.

**Context:** `01-domain-model.md` (assets), `02-tenancy.md`

**Tasks**
1. `Asset` records auto-created when a `SERIAL`-tracked item is received; asset tag generated
   per org (`SRMS/CET/LAB/00123`).
2. Custodian assignment and transfer with an acceptance step; custodian history retained.
3. Depreciation: straight-line and WDV, scheduled monthly, with a book-value report.
4. `AMCContract` and `MaintenanceLog`; preventive maintenance schedules generating due dates.
5. `ComplianceRequirement` / `ComplianceRecord`: per-org registers. Seed realistic templates
   per org type — biomedical waste and fire safety for the hospital and IMS, lab safety and
   equipment calibration for CET, food safety (FSSAI) for hotel management, drug licence for
   nursing/hospital pharmacy.
6. Recurring compliance auto-generates the next `ComplianceRecord` on completion using
   `frequency_days`.
7. Certificate upload with permission-checked serving — **never** a bare `MEDIA_URL` link.
8. Compliance dashboard: due / overdue / completed, by department and by category, with a
   trust-wide roll-up for the Trust Admin.

**Acceptance**
- Overdue compliance is flagged the day after `due_date`, with no timezone off-by-one
- Completing a recurring requirement creates exactly one next record
- Certificates are inaccessible to another org even with a direct URL
- Asset register reconciles: every `SERIAL` unit in stock has exactly one asset row

---

## Phase 8 — The intelligence layer

**Goal:** the "Smart" in SITS. Move from static thresholds to history-aware assistance.

**Context:** `01-domain-model.md` (intelligence), `03-stack-and-docker.md` (celery)

**Tasks**
1. Bring up `worker` and `beat` (`docker compose --profile async up -d`). Configure
   `django-celery-beat`.
2. Consumption analytics per item: average daily consumption, standard deviation, trend,
   seasonality flag — computed from `StockMovement` history over configurable windows
   (30/90/365 days).
3. Forecasting: start with EWMA and a moving average. **Do not reach for ML.** Compare the
   two on held-out history, store MAPE, pick per item. Document the choice in `MEMORY.md`.
   Items with fewer than 30 days of history fall back to the manual reorder level and are
   marked `forecast_confidence=LOW`.
4. Dynamic reorder point: `(avg_daily_consumption × lead_time_days) + safety_stock`, where
   `safety_stock = z × σ × √lead_time` and z comes from the org's target service level
   (default 95%). Surface it as a **suggestion** next to the manual value; never overwrite the
   manual value silently.
5. `ReorderSuggestion` generation with a plain-English rationale — "42 units. Consumption rose
   35% over the last 30 days; at the current rate you stock out in 6 days and the supplier
   lead time is 10." A suggestion nobody understands is a suggestion nobody acts on.
6. One-click conversion of suggestions into a draft PO, grouped by preferred supplier.
7. ABC (by annual consumption value) and XYZ (by demand variability) classification, refreshed
   monthly; the 3×3 matrix drives review frequency.
8. Dead stock and slow-mover detection; overstock detection (`days_of_stock > threshold`).
9. Expiry risk: items expiring within N days weighted by remaining quantity and consumption
   rate — flags what will actually be wasted, not merely what is dated.
10. Anomaly detection: a consumption spike >3σ, an unusual issue outside working hours, an
    adjustment above a value threshold. Flag for review; never auto-block.
11. `ItemAnalytics` cached per item, recomputed nightly per org. Dashboards read cache only.

**Acceptance**
- Nightly task processes all orgs, each scoped correctly (thread-local set per iteration)
- A cold-start item with no history does not produce a nonsense forecast
- Analytics for a 5,000-item org compute in under 2 minutes
- Every dashboard number traces back to a `StockMovement` — no unexplainable figures
- Suggestions carry a rationale a store clerk can read and act on

---

## Phase 9 — Alerts & notifications

**Goal:** the system tells the right person at the right time, without becoming noise.

**Context:** `01-domain-model.md` (alerts)

**Tasks**
1. `AlertRule` engine with the ten alert types; per-org thresholds in `threshold_config`.
   Trust-wide templates that orgs inherit and may tighten but not disable.
2. `fingerprint`-based deduplication: re-firing an open alert updates `last_seen_at`; it does
   not create a row. **This is what separates a useful system from one everyone mutes.**
3. Channels: in-app (bell with unread count), email, daily/weekly digest. Per-user preferences.
4. Routing by role and department — an expiry alert goes to the store manager holding that
   batch, not to all seven institutions.
5. Escalation: a `CRITICAL` alert unacknowledged for N hours escalates to the Org Admin, then
   to the Trust Admin.
6. Acknowledge / resolve / suppress with reason and duration; suppression expires.
7. Alert centre with filters, bulk acknowledge, and history.
8. Weekly digest email per org: low stock, expiring, pending approvals, overdue POs, compliance
   due.

**Acceptance**
- 100 items going low-stock produce one digest, not 100 emails
- Suppressing an alert for 7 days genuinely silences it and it returns on day 8
- Escalation fires exactly once per alert
- No alert crosses an org boundary
- Email failure is retried and logged; it does not crash the beat task

---

## Phase 10 — Dashboards & reporting

**Goal:** managers get the insight the brief asks for; the Trust Admin gets the cross-org view.

**Context:** `01-domain-model.md` (reporting), `04-conventions.md`

**Tasks**
1. **Org dashboard** — KPI cards (stock value, items below reorder, open POs, pending
   requisitions, compliance %, month's consumption); charts (consumption trend, category
   distribution, top 10 by value, stockout frequency, supplier performance); action queues
   (my approvals, open alerts, reorder suggestions).
2. **Trust dashboard** — org comparison table (stock value, spend, stockout rate, compliance %,
   dead-stock %), spend trend by org, org drill-down, outlier flagging, consolidated
   compliance status. This is the flagship screen; give it real design attention.
3. Department dashboard for `DEPT_STAFF`: my requisitions, my department's consumption, items
   issued to me.
4. Report builder over `ReportDefinition`: stock ledger, valuation (moving avg / FIFO), ABC,
   consumption by department, supplier performance, PO ageing, expiry register, dead stock,
   asset register, depreciation schedule, compliance status, audit trail, cross-org comparison.
5. Exports: CSV, XLSX (openpyxl, formatted), PDF (WeasyPrint, letterheaded). Large exports run
   as Celery tasks with an email-when-ready link.
6. Scheduled reports: monthly consumption to each Org Admin, quarterly trust summary.
7. Every dashboard query cached in Redis with sensible TTL and explicit invalidation on
   relevant movements.

**Acceptance**
- Org dashboard renders in <500ms at 10k items / 100k movements
- Trust dashboard aggregates all orgs in one query set, not N+1 per org
- An Org Admin cannot reach the trust dashboard, by URL or otherwise
- Exported figures match on-screen figures exactly
- Report permissions respect `allowed_roles`

---

## Phase 11 — API & integrations

**Goal:** programmatic access for scanners, mobile clients and future integrations.

**Tasks**
1. DRF with token/JWT auth. Tenancy enforced in a base `TenantViewSet` — the API must reuse
   the *same* managers and decorators as the web layer, not a parallel implementation.
2. Endpoints: items, stock levels, movements, requisitions, issues, GRNs, alerts, analytics.
3. Barcode-scanning endpoints: lookup by barcode, quick-issue, quick-receive, stock-take.
4. Stock-take / physical verification: generate a count sheet, capture counts, produce a
   variance report, post adjustments on approval.
5. OpenAPI schema (drf-spectacular) + Swagger UI.
6. Rate limiting per token, and API-key scoping to a single organisation.
7. Webhooks for critical events (stockout, compliance overdue).

**Acceptance**
- An API token for CET cannot read IMS data through any endpoint, including list filters
- Isolation suite extended to cover API routes
- Schema validates; Swagger UI reflects real permissions

---

## Phase 12 — Hardening, docs, deployment

**Goal:** production-ready for the Trust.

**Tasks**
1. Security pass: `manage.py check --deploy` clean; dependency audit (`pip-audit`); file-upload
   validation; SQL injection review of any `raw()`/`extra()`; CSRF and clickjacking verified.
2. Performance: kill N+1s (`django-debug-toolbar`, `nplusone`), add missing indexes, measure
   with 100k+ movements. Add `EXPLAIN ANALYZE` notes for the slowest three queries in `MEMORY.md`.
3. Backups: `pg_dump` cron in a sidecar, retention policy, **restore drill documented and
   actually performed once**. An untested backup is not a backup.
4. Observability: structured JSON logging, Sentry, `/healthz/` and `/readyz/`, Celery task
   monitoring.
5. Prod compose: Nginx + TLS, gunicorn tuning, `DEBUG=False`, secrets via environment,
   non-root containers, resource limits.
6. CI (GitHub Actions): lint → test → build image → smoke test compose stack.
7. Docs: `README.md`, `docs/deployment.md`, `docs/user-guide-org-admin.md`,
   `docs/user-guide-store-manager.md`, `docs/user-guide-trust-admin.md`, `docs/architecture.md`,
   ERD diagram.
8. UAT script per role; training data set; rollout plan (pilot with one organisation first —
   recommend CET or Riddhima, whichever has the simplest inventory — before Trust-wide).

**Acceptance**
- `check --deploy` clean
- CI green on a fresh clone
- Restore-from-backup drill completed and documented
- Load test: 50 concurrent users, no errors, p95 <1s
- A non-technical Org Admin completes the UAT script unaided

---

## Cross-cutting reminders

- **Never** trust `organization` from user input.
- **Never** mutate stock outside `apply_movement()`.
- **Never** hardcode an organisation slug.
- **Always** `select_for_update()` when reading a value you are about to write.
- **Always** add the isolation test with the model, not after.
- **Always** run `/session-end` before finishing.
