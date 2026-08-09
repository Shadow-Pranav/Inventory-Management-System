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

---

## Section E — User preferences & context

- Building via **Claude Code in VS Code**. Prefers containerised, zero-local-setup workflows.
- Has built this project once before in Django — familiar with the framework, so explanations
  can assume Django fluency and skip the basics.
- Wants **maximum reuse** of the existing codebase. Rewrites need justification; refactors
  do not.
- Wants the system to work identically on any machine via Docker.
- Institution names are user-supplied and unverified — confirm before treating as canonical.
- Timezone `Asia/Kolkata`; currency INR; Indian fiscal year (April–March); GST applies to
  procurement documents.
