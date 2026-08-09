# ANALYSIS.md — Audit of `Shadow-Pranav/Inventory-Management-System`

Audited at `main`. This document explains **what exists**, **what breaks under multi-tenancy**,
and **what the minimum viable change set is**. Read it once; after that `.claude/context/`
is the working reference.

---

## 1. What is actually in the repo

| Area | Files | Assessment |
|---|---|---|
| Project config | `config/settings.py` (159 L), `urls.py`, `wsgi.py` | Clean, `python-decouple`-driven, SQLite/MySQL toggle. Good bones. |
| App | `ims_app/` — `models.py` (145 L), `views.py` (592 L), `forms.py` (175 L), `admin.py` (87 L), `signals.py` (27 L), `urls.py` (44 L), `tests.py` (107 L) | Small, readable, conventional function-based views. |
| Templates | 17 files under `templates/ims_app/` | Bootstrap 5.1.3 + Font Awesome 6 + Chart.js 3.9.1, all via CDN. Server-rendered, no JS build step. |
| Tooling | 14 × `.bat` / `.ps1` / `.sh` setup scripts | To be deleted. Replaced entirely by Compose. |
| Deps | `Django==4.2.10`, `Pillow`, `plotly`, `python-decouple`, `mysqlclient` | `plotly` appears unused by templates (Chart.js is used client-side). Verify before keeping. |

### Existing models

```
UserProfile  (user 1:1, role ∈ {admin, staff, customer}, phone, address, department:CharField)
Category     (name UNIQUE, description)
Product      (name UNIQUE, sku UNIQUE, category FK, quantity, reorder_level, unit_price,
              image, is_active, created_by)
InventoryLog (product FK, transaction_type ∈ {in,out,adjustment,damage},
              quantity, previous_quantity, new_quantity, notes, created_by)
Order        (order_number UNIQUE, user FK, status ∈ {pending,approved,fulfilled,cancelled},
              total_items, total_amount, approved_by)
OrderItem    (order FK, product FK, quantity, unit_price, total_price)
```

**What is genuinely good and must be kept:**
- `InventoryLog` already records `previous_quantity` / `new_quantity`. That is a real ledger
  in embryo — it becomes `StockMovement`.
- `Order.refresh_totals()` recomputes from line items rather than trusting cached values.
- `Product.is_low_stock()` and `inventory_value` are the right shape, just static.
- `role_required` decorator already centralises access control in one place — one decorator
  to rewrite, not fifty views.

---

## 2. Blocking defects for the SRMS use case

### 2.1 There is no tenancy. At all.

Not "weak" tenancy — none. `UserProfile.department` is a free-text `CharField`, which is the
only nod to organisational structure in the entire schema.

Three unique constraints make multi-tenancy **impossible without a migration**:

| Constraint | Why it breaks |
|---|---|
| `Product.name` unique | CET and the Nursing College cannot both stock "Surgical Gloves". |
| `Product.sku` unique | Two institutions cannot both use SKU `CHEM-001`. |
| `Category.name` unique | Only one org may own a category called "Consumables". |

**Fix:** replace each with `UniqueConstraint(fields=["organization", "<field>"])`.

### 2.2 Every query is unscoped

`views.py` runs `Product.objects.filter(is_active=True).count()`,
`Order.objects.all()[:10]`, `UserProfile.objects.filter(role='staff').count()` and similar
throughout the dashboard. Under multi-tenancy each of these is a data leak. There are
roughly 40 such call sites.

**Fix:** a `TenantManager` whose default `get_queryset()` raises unless scoped, plus
`.for_request(request)`. Making the *unsafe* path noisy is what prevents regressions six
months from now.

### 2.3 Role model is too flat and lives in the wrong place

`role` is a single `CharField` on `UserProfile`, so a user has exactly one role globally.
The Trust needs a person to be a store manager in CET and a read-only auditor in IMS.

**Fix:** roles move to a `Membership` model keyed on (user, organisation). `is_trust_admin`
becomes a boolean on a custom `User`.

> **Do this in Phase 1, not later.** Swapping to `AUTH_USER_MODEL` after the fact is one of
> the most painful migrations in Django. It is cheap now, expensive in three weeks.

### 2.4 The procurement half of the brief does not exist

Your functionality list says *"Products and Suppliers are added"* and *"Stock is received
through purchase orders"*. The repo has neither a `Supplier` model nor a `PurchaseOrder`.
`Order` is a **consumption/issue request** (`user` raises it, `approved_by` clears it), which
is the *outbound* flow. The inbound flow is entirely missing.

**Fix:** new `procurement` app — `Requisition → PurchaseOrder → GoodsReceipt (GRN) → StockMovement(IN)`.
Rename the existing `Order` to `IssueRequest` so the two are never confused.

### 2.5 "Smart" is not implemented

`reorder_level` is a hand-typed integer, and low-stock detection is a `filter(quantity__lte=F('reorder_level'))`
computed synchronously on page load. There is no history-aware logic anywhere.

**Fix:** an `intelligence` app computing consumption velocity, EWMA forecast, dynamic reorder
point (`avg_daily_demand × lead_time + safety_stock`), ABC/XYZ classification, dead-stock and
anomaly detection — run on a Celery beat schedule, cached to `ItemAnalytics` rows so the
dashboard stays fast.

### 2.6 Stock arithmetic is not concurrency-safe

`adjust_inventory` reads `product.quantity`, computes, and writes back. Two simultaneous
issues will lose one of them.

**Fix:** all mutations go through a single `apply_movement()` service inside
`transaction.atomic()` with `select_for_update()` on the `StockLevel` row. Item quantity
becomes a **derived** value, never written directly.

### 2.7 Environment assumes Windows + local venv

14 scripts, `mysqlclient` (needs system build deps), MySQL default. Contradicts your
"runs on any system" requirement.

**Fix:** delete all of them. PostgreSQL 16 instead of MySQL — better window functions and
`FILTER` clauses, which the analytics layer leans on heavily, plus no client-library build
step. `psycopg[binary]` installs cleanly everywhere.

---

## 3. What to keep vs change vs add

### Keep (touch only where forced)
- All 17 templates, Bootstrap styling, the base layout and navbar
- `forms.py` structure and widget-class conventions
- The function-based-view style — do not convert to CBVs for its own sake
- `python-decouple` config pattern
- `Order.refresh_totals()` logic (moves to `IssueRequest`)

### Change (in place, minimally)
| From | To |
|---|---|
| `Product` | `Item` — add `organization`, `uom`, `item_type`, `is_asset`, `tracking_mode`; drop `quantity` (derived) |
| `Category` | keep name, add `organization`, `parent` (self-FK for a tree) |
| `InventoryLog` | `StockMovement` — add `organization`, `location`, `batch`, `source_document` (generic FK), `unit_cost` |
| `Order` | `IssueRequest` — add `organization`, `department`, richer status flow |
| `UserProfile.role` | `Membership.role` (user × org) |
| `role_required` | `require_role(...)` reading from `request.membership` |
| MySQL / SQLite | PostgreSQL 16 |
| `.bat`/`.ps1` | `compose.yaml` + `Makefile` |

### Add (new apps)
`tenancy`, `procurement`, `issuance`, `assets`, `intelligence`, `alerts`, `reporting`, `core`

---

## 4. Migration risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Swapping `AUTH_USER_MODEL` mid-project | **High** | Do it in Phase 1, before any real data exists. |
| Back-filling `organization` on existing rows | Medium | Data migration assigns everything to a `DEFAULT_ORG` placeholder; document it in `MEMORY.md`. |
| Dropping `Product.quantity` in favour of derived stock | Medium | Keep the column one release longer, populate both, verify parity, then drop. |
| Renaming `Order` → `IssueRequest` | Medium | `migrations.RenameModel`, not drop-and-create. Update all `related_name`s. |
| 40 unscoped querysets, easy to miss one | **High** | Manager raises on unscoped access + a `test_tenant_isolation.py` that iterates every tenant model automatically. |
| Celery added before it is needed | Low | Introduce in Phase 8, not Phase 0. Compose profile keeps it optional until then. |

---

## 5. Recommended build order (rationale)

Tenancy first, because every later model needs an `organization` FK and retrofitting one is
strictly more expensive than adding it up front. Access control immediately after, so that
every subsequent feature is built against a working permission layer rather than bolted onto
one. Procurement before issuance, because you cannot issue stock you never received.
Intelligence late, because forecasting needs movement history to forecast from — building it
early means building it against no data.

Docker comes first of all, so that from day one there is exactly one way to run the project
and no session ever burns time on environment drift.

Full breakdown: `PROMPTS.md`. Live status: `PROGRESS.md`.
