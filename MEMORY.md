# MEMORY.md — Decision Log & Project Memory

**Append-only.** Never delete an entry. If a decision is reversed, add a new entry that
supersedes it and mark the old one `SUPERSEDED by D-NN`.

Purpose: so a future session never has to re-derive *why* something is the way it is, and
never relitigates a settled question. If you find yourself thinking "why on earth is it done
this way" — the answer should be here. If it isn't, that is a gap worth filling.

---

## Section A — Architectural decisions

### D-01 · Shared-database, row-level multi-tenancy
**Date:** Session 0 · **Status:** Active
**Decision:** One PostgreSQL database and schema; `organization_id` on every tenant table.
**Why:** The Trust Admin's cross-org dashboard is the headline feature. Schema-per-tenant
turns "compare all seven institutions" into N fanned-out queries merged in Python. Seven
tenants do not justify the ops cost of stronger isolation.
**Trade-off:** Isolation lives in application code, so one missing filter leaks data.
Mitigated by `TenantManager` raising on unscoped access + an auto-discovering isolation suite.
**Revisit if:** the Trust ever needs certified physical data separation between institutions.

### D-02 · PostgreSQL replaces MySQL
**Date:** Session 0 · **Status:** Active
**Why:** Window functions and `FILTER` clauses carry the analytics layer; JSONB for
`Organization.settings` and alert context; `psycopg[binary]` needs no system build deps
whereas `mysqlclient` does, which matters for "runs on any system".
**Cost:** Original `.env.example` MySQL config is discarded. No production data exists, so
migration cost is zero.

### D-03 · Custom `AUTH_USER_MODEL` in Phase 1
**Date:** Session 0 · **Status:** Active
**Why:** Swapping the user model after data exists is Django's most painful migration.
Doing it before any real data is nearly free.
**Consequence:** Phase 1 cannot be skipped or reordered.

### D-04 · Roles live on `Membership`, not `User`
**Why:** A Trust IT lead may be `STORE_MANAGER` in CET and `AUDITOR` in IMS. A single global
role cannot express that. `is_trust_admin` stays on `User` because it is inherently cross-org.

### D-05 · Stock quantity is derived, never stored on the item
**Why:** The original repo's `Product.quantity` was mutated by read-modify-write, which loses
updates under concurrency. `StockMovement` is an append-only ledger and `StockLevel` the
materialised balance, mutated only inside `apply_movement()` with `select_for_update()`.
**Consequence:** Per D-11 (greenfield build, no legacy `Product.quantity` to migrate off of),
`Item` never gets a `quantity` field at all — `StockLevel` is the balance from `Item`'s first
migration. No parallel-run, no parity check, no later drop step.

### D-06 · `Order` splits into two concepts
**Why:** The original repo's `Order` conflates procurement and consumption. It is actually an
*outbound issue request*. Modelled directly as `issuance.IssueRequest`; `PurchaseOrder` is a
separate, inbound concept (procurement app).
**Consequence:** Per D-11, both are built fresh — no `Order` model or `RenameModel` step
exists in this repo.

### D-07 · EWMA before ML for forecasting
**Why:** Explainable, cheap, and adequate for institutional consumption patterns. A store
clerk will not act on a suggestion they cannot understand. Revisit only if measured MAPE is
unacceptable — and record the measurement here before switching.

### D-08 · Celery deferred to Phase 8 behind a compose profile
**Why:** Nothing needs async work until the intelligence layer. Keeping `worker`/`beat` down
until then makes Phases 0–7 faster to start and easier to debug.

### D-09 · HTMX, no JS build step
**Why:** The original is server-rendered Bootstrap. Adding Node, a bundler and a build step
would be the largest single increase in project complexity for the smallest gain. HTMX gives
live stock updates and inline edits with a single script tag.

### D-11 · Greenfield build — no legacy `ims_app` codebase exists
**Date:** Session 1 (2026-08-09) · **Status:** Active
**Decision:** The planning bundle (`CLAUDE.md`/`PROMPTS.md`/`PROGRESS.md`/`MEMORY.md`/
`ANALYSIS.md`) was written assuming a clone of `Shadow-Pranav/Inventory-Management-System`
already existed in this directory and would be containerised then progressively migrated
onto tenancy. At session start, the directory contained only the planning bundle — no
`ims_app`, no `manage.py`, no `.bat`/`.ps1` scripts, and it was not a git repository. Asked
the user directly; they confirmed: **build fresh, no original repo to preserve or migrate.**
**Consequence:**
- Phase 0 is "bootstrap a new Django project" rather than "containerise the existing app and
  verify unchanged behaviour." There is nothing to verify unchanged.
- Phase 2 is "build `catalog`/`inventory` models directly, tenancy-scoped from the first
  migration" rather than "`RenameModel` migration off `ims_app.Product`/`Category`/etc."
  `F-01` through `F-07` in Section B below describe facts about a codebase that does not
  exist here — kept for historical reference (they may still hold if the original repo is
  ever consulted for design ideas) but do not treat them as facts about *this* repo.
- `ANALYSIS.md` (the original-repo audit) is design reference only, not a migration map.
- Phases 1, 3–12 are largely unaffected: they already describe target-state behaviour, not
  migration steps.
- Git was not initialised for this project before this session; initialised now.
**Revisit if:** the user later supplies the original repo and wants specific pieces ported —
treat that as new, scoped work, not a reversal of this decision.

### D-12 · Answers to Q1–Q3 (org names, store structure, approval thresholds)
**Date:** Session 1 (2026-08-09) · **Status:** Active
**Q1 — Organisation names:** the 7 organisations in `CLAUDE.md` §1 are final, used verbatim
in the seed fixture. No 8th org, no name changes.
**Q2 — Store structure:** institutions run **multiple stores per org**, not one central
store each. **Consequence:** `inventory.Location` (Phase 2) must be a real hierarchy from
its first migration — do not build a single `MAIN_STORE`-per-org default and generalise
later; the "opening stock against a default location" step in old Phase 2 drafts doesn't
apply as written. `seed_demo` (Phase 1) should create more than one `Location` per demo org
so Phase 2+ testing exercises multi-store from the start, not as an afterthought.
**Q3 — Approval thresholds:** Trust-wide default, per-org override. **Consequence:**
`organization.settings["approval_thresholds"]` (already anticipated in Phase 5 of
`PROMPTS.md`) holds the *override*; a Trust-wide default lives outside any single org's
settings — likely a Django setting or a Trust-scoped config row, not yet decided which.
**Revisit at:** Phase 5, when `PurchaseOrder` approval is actually built — decide then
whether the Trust-wide default is a `settings.py` constant or a proper model (matters if the
Trust Admin should be able to change it without a deploy).

### D-13 · Phase 1 implementation decisions
**Date:** Session 1 (2026-08-09) · **Status:** Active
**AUTH_USER_MODEL swap required a DB reset.** Phase 0 had already applied Django's default
`auth.User` migrations. Swapping `AUTH_USER_MODEL` after that is the exact painful migration
D-03 warned about (the `admin_logentry` FK was already bound to the old `auth_user` table).
With no real data yet, dropped and recreated the `sits` database via `psql` (not
`docker compose down -v` — narrower, and not blocked by G-05) and ran `migrate` fresh.
**`USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = ["username"]`** on `tenancy.User` — context
01 says email is "the login identifier"; this is the literal Django mechanism for that.
`username` stays as a required-but-secondary field (Django admin/`createsuperuser`
conventions expect *some* unique display handle), not removed.
**`Organization.org_type` for Riddhima is a guess (`VENTURE`).** Nothing in `CLAUDE.md` or
the user's Q1 answer specifies what kind of entity Riddhima is — the other six orgs map
cleanly to the `OrgType` choices, Riddhima doesn't obviously. Flagged, not blocking (org_type
isn't load-bearing for anything yet), but confirm with the user before it drives any
type-specific behaviour (e.g. Phase 7's compliance template seeding "per org_type").
**"DEFAULT_ORG" from the original Phase 1 brief is N/A.** That task was about migrating
legacy `UserProfile.role` rows into `Membership` against a fallback org — moot per D-11
(greenfield, no legacy rows). No `DEFAULT_ORG` concept exists in this codebase.
**`Membership.stores` (M2M to `inventory.Location`) is deferred to Phase 2** — the app
doesn't exist yet to reference. Noted inline in `apps/tenancy/models.py` and in context 01.
**Resolved in Phase 2** (D-14) once `apps.inventory` existed — X-06 closed.

### D-14 · Phase 2 implementation decisions
**Date:** Session 1 (2026-08-09) · **Status:** Active
**`apply_movement()` uses `.for_organization(org)`, not `all_objects` or the ambient
contextvar.** Context 04 §2's reference implementation reads `StockLevel.objects...` bare,
implicitly relying on the contextvar already being set. `apply_movement()` is a *service*
function per context 04 §1 ("services take primitives... never `request`") and receives
`organization` explicitly — mutating the ambient thread-local as a side effect of a stateless
service call would be surprising, and actively wrong for Phase 6's cross-org transfer (one
call touching two organisations' stock in one transaction — the contextvar can only ever
hold one org at a time). `.for_organization()` (added in G-07) is stateless and exactly
matches "explicit organization in, scoped queryset out."
**`StockLevel`'s partial unique constraint.** Postgres treats `NULL` as distinct in a unique
index, so `UniqueConstraint(["organization","item","location","batch"])` alone would let
multiple rows exist for the same `(org, item, location)` whenever `batch` is `NULL`
(untracked items — the common case). Added a second constraint,
`condition=Q(batch__isnull=True)`, closing that gap. Caught before it could ever produce a
duplicate row, not a gotcha hit in production — but exactly the kind of stock-arithmetic
correctness issue CLAUDE.md §3 rule 5 cares about, so recorded here rather than left as an
undocumented "just how it is."
**Moving average is item-level, weighted by total on-hand across all locations** — `Item`
has one `unit_cost`, not one per location, and context 04 §2's `update_moving_average(item,
quantity, unit_cost)` signature (no `location` arg) confirms that's the intended scope.
Implemented as: aggregate current total `StockLevel.quantity` for the item *after* the
receiving level is saved, back out `total_before = total_after - received_qty`, then the
standard weighted-average formula. Only `RECEIPT` and `OPENING` are `COST_BEARING` — never
`TRANSFER_IN` (the cost basis moves with the stock, it isn't re-priced) and never `ISSUE`
(explicit in context 04 §4: "on receipt only").
**`StockMovement.save()` raises if `self.pk` is already set** — belt-and-braces enforcement
of "never updated, never deleted" (context 04 §2), not speculative: the ledger's integrity
*is* the audit trail: a silent `.save()` on an existing row would be invisible corruption.
**`IssueRequest.issue_number` has no uniqueness constraint yet** — Phase 5 owns the
per-org-per-FY sequence generator (`select_for_update()` on a sequence row, per context 04
§3). Adding a constraint now against an unpopulated/blank field would either block on empty
strings colliding or need a throwaway numbering scheme Phase 5 would just replace. Left
blank and unconstrained; do not add ad hoc numbering here when Phase 5 starts — build the
real generator.

### D-10 · Compliance registers are per-organisation
**Why:** A hospital's biomedical-waste obligations and a hotel-management college's FSSAI
licensing have nothing in common. A Trust-wide fixed register would be wrong for every
institution simultaneously. `ComplianceRequirement` is tenant-owned; templates are seeded
per `org_type`.

---

## Section B — Codebase facts worth remembering

Things learned by reading the code, so nobody has to read it again.

> **F-01 through F-07 describe the *original* `Shadow-Pranav/Inventory-Management-System`
> repo, which is not present in this project** (see D-11 above). They are design
> reference, not facts about files that exist here.

### F-01 · Three global unique constraints block tenancy
`Product.name`, `Product.sku`, `Category.name` are all `unique=True`. Each must become a
composite `UniqueConstraint` including `organization`. Missing one means two institutions
silently cannot both stock the same item.

### F-02 · ~40 unscoped querysets in `ims_app/views.py`
`dashboard()` alone has five (`Product.objects.filter(...)`, `Order.objects.all()[:10]`,
`UserProfile.objects.filter(role='staff')`, and two low-stock queries). Every one is a leak
under multi-tenancy. Rewrite view by view, running tests between each.

### F-03 · `InventoryLog` is already a ledger in embryo
It records `previous_quantity` and `new_quantity`. Preserve that pattern in `StockMovement`
as `balance_after` — it makes audit reconciliation trivial.

### F-04 · `role_required` is the single access-control chokepoint
All role checking flows through one decorator in `views.py`. That is genuinely good design in
the original and makes Phase 3 far cheaper than it would otherwise be. Rewrite the decorator,
not fifty views.

### F-05 · Templates use CDN Bootstrap 5.1.3, Font Awesome 6, Chart.js 3.9.1
No build step, no `package.json`. Keep it that way. `plotly` is in `requirements.txt` but
appears unused by any template — verify with `grep -rn plotly` before removing.

### F-06 · `signals.py` has two no-op receivers
`update_product_timestamp` does nothing (`pass`). Delete it during migration rather than
carrying it forward.

### F-07 · Windows line endings will break `entrypoint.sh`
The repo has `.bat`/`.ps1` files, so it has been developed on Windows. Add
`.gitattributes` with `*.sh text eol=lf` in Phase 0 or the container fails to start on Linux
with an opaque `exec format error`.

---

## Section C — Gotchas hit during the build

Append as they happen. Format: symptom → cause → fix.

### G-01 · `web` container: `ModuleNotFoundError: No module named 'django'`
**Phase:** 0 · **Date:** 2026-08-09
**Symptom:** Image built fine (`uv sync` succeeded), but the running container couldn't
import Django at all.
**Cause:** `compose.yaml`'s dev bind-mount (`.:/app`) mounts the *host* directory over
`/app` at container start, which shadows the `/app/.venv` that `uv sync` created inside the
image during build. The venv the image built simply isn't there once the bind-mount lands.
This affects the reference `compose.yaml` in context 03 verbatim — it wasn't SITS-specific,
it's a mismatch between "bind-mount the whole app dir" and "install deps into `/app/.venv`".
**Fix:** `docker/web/Dockerfile` now sets `UV_PROJECT_ENVIRONMENT=/opt/venv` and
`PATH=/opt/venv/bin:$PATH` so the venv lives outside the mounted path.
**Watch for:** any future change to `compose.yaml`'s dev volumes, or to where `uv sync`
installs, can silently reintroduce this. If `web` ever fails with a missing-module error
right after a clean rebuild, check this first.

### G-02 · `collectstatic`: `PermissionError: /app/staticfiles/admin`
**Phase:** 0 · **Date:** 2026-08-09
**Symptom:** After fixing G-01, `entrypoint.sh` still failed — this time on `collectstatic`,
writing to the `static_volume` named volume.
**Cause:** Named volumes (`static_volume`, `media_volume`) get created root-owned by Docker
on first use unless the image already has non-empty, correctly-owned directories at those
exact paths — Docker seeds a fresh named volume's initial content (and permissions) from the
image at that path. The image never created `/app/staticfiles` or `/app/media` before
switching to the non-root `appuser`, so Docker seeded the volumes as root-owned, and
`appuser` couldn't write to them.
**Fix:** `Dockerfile` now does `mkdir -p /app/staticfiles /app/media && chown -R appuser ...`
before `USER appuser`, so the *first* volume creation seeds correct ownership.
**Watch for:** this only self-heals on a volume that has never been created. An already-
existing root-owned volume from a prior broken build needs `docker compose down -v` (or
delete just that volume) to pick up the fix — rebuilding the image alone won't touch a
volume that already exists.

### G-03 · `ghcr.io/astral-sh/uv:latest` can't run `uv lock` standalone
**Phase:** 0 · **Date:** 2026-08-09
**Symptom:** `docker run ... ghcr.io/astral-sh/uv:latest lock` failed:
`Failed to discover managed Python installations... Failed to find any common binaries`.
**Cause:** `uv:latest` is a distroless image containing only the `uv` binary (meant to be
`COPY --from=`'d into another image, which is exactly how `docker/web/Dockerfile` uses it)
— it has no Python and almost no userland, so it can't manage a Python installation itself.
**Fix:** generated `uv.lock` with `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` instead,
which bundles both `uv` and Python. Only needed for bootstrapping/regenerating the lockfile
outside the app image; the app `Dockerfile` correctly uses `uv:latest` as a copy source.

### G-04 · `git add`/commit silently dropped `entrypoint.sh`'s executable bit
**Phase:** 0 · **Date:** 2026-08-09
**Symptom:** `chmod +x docker/entrypoint.sh` was run and confirmed locally (`ls -la` showed
`-rwxr-xr-x`), but after `git add -A && git commit`, `git ls-files -s` showed mode `100644`
(non-executable) for the file — exactly the F-07 failure mode this repo was warned about.
**Cause:** `core.fileMode` is `false` on this Windows checkout (Git for Windows' usual
default, since NTFS doesn't natively track the Unix executable bit the way git wants). With
it `false`, git ignores the filesystem's executable bit entirely when diffing/staging, so a
host-level `chmod` never reaches the index.
**Fix:** `git update-index --chmod=+x docker/entrypoint.sh` sets the mode bit directly in
git's index regardless of `core.fileMode`, then commit normally.
**Watch for:** any new script that needs to be executable inside the container (future
management commands invoked directly, other entrypoints) needs the same
`git update-index --chmod=+x` treatment on this machine — a plain `chmod` will not survive
the next commit. Worth checking with `git ls-files -s <path>` (look for `100755`) after
adding any new `*.sh` file, not just trusting the local filesystem.

### G-05 · `docker compose down -v` cannot be run by Claude, ever, in this project
**Phase:** 0 · **Date:** 2026-08-09
**Symptom:** Attempted `docker compose down -v` for the Phase 0 cold-start gate check twice
(once mid-session, once at `/next-phase`); both times the Bash tool call was denied, even
after the user explicitly approved it via an in-chat question.
**Cause:** `.claude/settings.json` has `"Bash(docker compose down -v)"` in the **deny** list,
not the ask-list. A deny-list entry is enforced by the harness itself and cannot be overridden
by an in-conversation approval — `AskUserQuestion` and the actual tool-permission gate are
different mechanisms. `SETUP-README.md`'s description ("Claude will ask you first each time")
does not match this behaviour; the file is aspirational/stale on this point.
**Fix:** there is no fix that keeps the deny rule intact — the user has to run this exact
command themselves in their own terminal and report back. That's what happened here.
**Watch for:** every future phase's gate check (`/next-phase`, `/verify-tenancy`) calls for a
cold-start check. Don't spend a turn retrying it — ask the user to run it directly the first
time a phase gate needs it, same as this session did. Only remove the deny rule if the user
explicitly asks to relax it (they were offered that option this session and declined).

### G-06 · factory-boy's default `_create` can't create `TenantOwnedModel` rows
**Phase:** 1 · **Date:** 2026-08-09
**Symptom:** `DepartmentFactory()` in a test raised `UnscopedQueryError`, even though the
test never called `Department.objects` directly.
**Cause:** `factory.django.DjangoModelFactory._create` calls `model_class._default_manager
.create(...)`, i.e. `Department.objects.create(...)`. `objects` is the strict
`TenantManager`, which raises with no active-organization contextvar set — exactly right
for application code, but factories legitimately have no request/contextvar at all.
**Fix:** `apps/core/factories.py::TenantModelFactory` is now the required base for any
`TenantOwnedModel` factory; it overrides `_create` to go through `all_objects` instead.
**Watch for:** every new tenant-owned model's factory (Phase 2 onward: `Item`, `Category`,
`StockLevel`, ...) must inherit `TenantModelFactory`, not `factory.django.DjangoModelFactory`
directly, or it hits this same wall.

### G-07 · `TenantManager.for_request()`/`.for_organization()` were unreachable
**Phase:** 1 · **Date:** 2026-08-09
**Symptom:** Isolation suite tests calling `Model.objects.for_request(request)` with
`is_trust_scope=True` (and no contextvar set) raised `UnscopedQueryError` instead of
returning the unscoped trust-admin queryset context 02 documents.
**Cause:** `TenantManager(models.Manager.from_queryset(TenantQuerySet))`'s auto-generated
`for_request`/`for_organization` wrapper methods call `self.get_queryset()` first (my
strict override), then chain the real `TenantQuerySet` method onto the *result*. Since
`get_queryset()` raises whenever the contextvar is unset and `STRICT_TENANCY` is on, the
manager-level `.for_request()`/`.for_organization()` calls documented in context 02 as "the
Trust Admin path" could never run their own `is_trust_scope` logic — they'd raise first,
every time, unless the contextvar happened to already agree with what you were asking for.
**Fix:** `TenantManager` now explicitly overrides both methods to build a fresh
`TenantQuerySet(self.model, using=self._db)` and call the real method on *that*, bypassing
`get_queryset()` entirely. `context/02-tenancy.md` §2 updated to match — the code block
there was the literal source of the bug, not just this repo's implementation of it.
**Watch for:** any other `TenantQuerySet` method meant to be an explicit, self-scoping entry
point (not dependent on the ambient contextvar) needs the same override treatment on
`TenantManager`, or it will silently inherit the strict `get_queryset()` gate.

### G-08 · `web` container crashes with `OSError: No such device` on the Windows host
**Phase:** 2 · **Date:** 2026-08-09
**Symptom:** `docker compose exec web pytest` failed with `service "web" is not running`.
`docker compose ps -a` showed `web` `Exited (1)`. Logs: Django's dev-server autoreloader
crashed — `OSError: [Errno 19] No such device: '/app/apps/tenancy/templates'` — while
`snapshot_files()` was mid-glob over a bind-mounted directory. Restarting just the `web`
service then failed too, with `Error response from daemon: error while creating mount
source path '/run/desktop/mnt/host/h/...': mkdir ... file exists`.
**Cause:** Docker Desktop's Windows file-sharing layer (the `/run/desktop/mnt/host/...`
bind-mount plumbing) got into a bad state — not caused by anything in this repo's code or
config. `runserver`'s autoreloader is especially exposed to this because it polls the whole
bind-mounted tree every second; any hiccup in the host↔container filesystem bridge surfaces
there first, well before a normal request would notice.
**Fix:** Restarting Docker Desktop itself (not just the container) cleared the stuck mount
path. `docker compose up -d web` then started cleanly. `db`/`redis` volumes and data were
untouched throughout — this is a file-sharing plumbing issue, not a data issue.
**Watch for:** if `web` (or any bind-mounted service) exits unexpectedly with an `OSError`
mentioning `/run/desktop/mnt/host/...` or "No such device", don't debug it as an app bug —
restart Docker Desktop first and retry. Seen after the machine had been idle; may correlate
with sleep/resume or long idle periods on this Windows host.

### G-09 · Every `TenantModelForm` subclass with a FK field crashed on import
**Phase:** 2 · **Date:** 2026-08-09
**Symptom:** `python manage.py check` (and just importing any view module) crashed with
`UnscopedQueryError: Category.objects accessed with no active organization` — not from a
view running, from the `class CategoryForm(TenantModelForm):` statement itself, at module
import time. Every `TenantModelForm` subclass with any FK/M2M field hit this — not a
one-off, a systemic break of the whole `TenantModelForm` mechanism built in Phase 1.
**Cause:** Three-layer problem, each layer looking like a fix for the previous one until it
wasn't:
1. Django's `ModelFormMetaclass` builds a `ModelChoiceField` for every FK by calling
   `field.formfield()` **at class-definition time** — before any request, before any
   contextvar is set.
2. `ForeignKey.formfield()`'s own `defaults` dict has a literal entry
   `"queryset": self.remote_field.model._default_manager.using(using)` — evaluated
   unconditionally while the dict is built. `_default_manager` is `objects`, the strict
   `TenantManager` (deliberately, per G-07's reasoning — it must stay the default manager
   for other Django internals). With no contextvar set, this raises immediately.
3. Passing `queryset=...` in `formfield_callback`'s kwargs does **not** prevent step 2 —
   Django evaluates its own default queryset expression before ever looking at the kwargs
   dict to override it. The crash happens constructing Django's `defaults`, not after.
   `Model.validate_constraints()` (run by `full_clean()`, i.e. every `form.is_valid()`) has
   the same `_default_manager` dependency for `UniqueConstraint` checks — that part isn't a
   bug, it's the same contextvar contract `test_isolation.py` already follows; a real
   request has it set by `OrganizationMiddleware` before the view runs.
**Fix:** `apps/core/forms.py` — `TenantModelFormMetaclass` injects a `formfield_callback`
that never calls `field.formfield()` for FK/M2M-to-`TenantOwnedModel` fields at all;
it constructs `forms.ModelChoiceField`/`ModelMultipleChoiceField` directly with
`remote_model.all_objects.none()`. `.none()`, not `.all()` — fails closed: a field left out
of `tenant_fields` renders as an empty, obviously-broken dropdown in dev, not a cross-org
leak. `context/02-tenancy.md` §3 updated with the corrected `TenantModelForm`.
**Watch for:** any plain (non-`TenantModelForm`) form with a class-body
`SomeTenantModel.objects.none()` for a queryset default has the exact same problem —
`apps/inventory/forms.py::StockAdjustmentForm` hit this too; use `.all_objects.none()` in
form class bodies, always. If a *new* Django/DRF integration ever needs
`Model._default_manager` for something else at import/class time, expect the same crash and
apply the same "don't touch the strict manager before a request exists" fix.

Template:

```
### G-NN · <one-line symptom>
**Phase:** N · **Date:** YYYY-MM-DD
**Symptom:** what you saw
**Cause:** what was actually wrong
**Fix:** what you did
**Watch for:** where this class of bug can recur
```

---

## Section D — Deferred decisions

Things deliberately not decided yet, so nobody assumes they were overlooked.

| ID | Question | Deferred because | Decide by |
|---|---|---|---|
| X-01 | Trust-wide shared vendor registry? | Per-org suppliers cover the real need; sharing adds a cross-tenant write path | Phase 5 |
| X-02 | FIFO vs moving-average valuation as the reporting default? | Needs the Trust's accountant's input, not a technical call | Phase 10 |
| X-03 | Fiscal-year rollover / opening-balance carry-forward mechanics | Needs Q3 answered | Phase 5 |
| X-04 | Whether the hospital pharmacy is in scope or a separate HMIS owns it | Needs Q4 answered | Phase 5 |
| X-05 | Data retention for `StockMovement` and `AuditLog` | No regulatory input yet | Phase 12 |
| X-07 | Is Riddhima's `org_type` really `VENTURE`? Guessed, not confirmed (see D-13) | Not load-bearing yet | Before Phase 7 (compliance templates key off `org_type`) |
| X-08 | `IssueRequest.issue_number` — per-org-per-FY sequence generator | Belongs with the rest of the doc-numbering convention (context 04 §3), not built ahead of it | Phase 5 |

**Resolved:** X-06 (`Membership.stores` M2M) — done in Phase 2, see D-14.

### D-15 · Phase 2 gate closed on a genuine cold start
**Date:** Session 2 (2026-08-10) · **Status:** Active
**Decision:** Phase 2 gated `DONE` after the full `CLAUDE.md` §7 Definition of Done was
walked against a *fresh* volume, not just the already-running stack. Docker Desktop was down
at session start (not running at all, not just the compose stack) — started it, then
`docker compose up -d --build`, confirmed `/healthz/` → 200. Ran the non-destructive gate
checks (migrations/tests/isolation/ruff/seed_demo) on that stack first — all green — then the
user ran `docker compose down -v && docker compose up --build -d` themselves (G-05: still
hard-denied for Claude) and confirmed success; re-ran the identical checks against the fresh
volume — same result, 86/86 tests, 55/55 isolation. Also grepped `apps/` for stray
`.objects.all()` outside the tenancy layer per the DoD's explicit item — the only hit is
`test_isolation.py`'s own assertion that it *raises* `UnscopedQueryError`, not a leak.
**Why recorded:** the previous two phase gates (D-13/G-05 notes) didn't spell out re-running
the full check suite twice (once live, once post-cold-start) — worth being explicit that
"the gate passed" means both, not just the cold-start boot succeeding.

---

## Section E — User preferences & context

- Building via **Claude Code in VS Code**. Prefers containerised, zero-local-setup workflows.
- Has built this project once before in Django — familiar with the framework, so explanations
  can assume Django fluency and skip the basics.
- Wants **maximum reuse** of the existing codebase. Rewrites need justification; refactors
  do not.
- Wants the system to work identically on any machine via Docker.
- Institution names confirmed 2026-08-09 (Q1, D-12) — the 7 in `CLAUDE.md` §1 are final.
- Timezone `Asia/Kolkata`; currency INR; Indian fiscal year (April–March); GST applies to
  procurement documents.
