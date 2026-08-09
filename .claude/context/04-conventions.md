# Context 04 — Conventions

House style. Follow it so the codebase reads as though one person wrote it.

---

## 1. Layering

```
views.py       thin. parse request → call service → render. No business logic, no arithmetic.
services.py    all business logic. Pure-ish functions taking explicit args, not `request`.
selectors.py   read queries returning querysets/dicts. Where the scoping lives.
models.py      structure, constraints, cheap derived properties. No cross-model orchestration.
tasks.py       Celery entry points. Thin wrappers over services.
forms.py       validation + widget config. Tenant FK narrowing via TenantModelForm.
```

A view longer than ~40 lines means logic belongs in a service. Move it.

Services take primitives and model instances, never `request`:

```python
# good
def issue_stock(*, organization, item, location, quantity, issued_by, reason): ...

# bad — untestable, couples business logic to HTTP
def issue_stock(request, item_id): ...
```

---

## 2. Stock mutation — the one true path

**Every** change to on-hand quantity goes through `apps/inventory/services.py::apply_movement()`,
with no exceptions. **Built Phase 2** — the real implementation, kept in sync here:

```python
@transaction.atomic
def apply_movement(*, organization, item, location, movement_type, quantity,
                   batch=None, serial_unit=None, unit_cost=None,
                   source=None, actor=None, reason=""):
    """Append a StockMovement and update the StockLevel row. The only writer of quantity."""
    if quantity <= 0:
        raise ValidationError("quantity must be positive; direction comes from movement_type")

    level, _ = (
        StockLevel.objects.for_organization(organization)
        .select_for_update()
        .get_or_create(
            organization=organization, item=item, location=location, batch=batch,
            defaults={"quantity": Decimal(0)},
        )
    )
    delta = SIGN[movement_type] * quantity
    new_qty = level.quantity + delta
    if new_qty < 0:
        raise InsufficientStock(item=item, location=location,
                                available=level.quantity, requested=quantity)

    level.quantity = new_qty
    level.save(update_fields=["quantity", "updated_at"])

    effective_unit_cost = unit_cost if unit_cost is not None else item.unit_cost
    if movement_type in COST_BEARING and unit_cost is not None:
        item.unit_cost = _moving_average(item, quantity, unit_cost)  # item-level, not per-location
        item.save(update_fields=["unit_cost"])

    return StockMovement.objects.for_organization(organization).create(
        organization=organization, item=item, location=location, batch=batch,
        serial_unit=serial_unit, movement_type=movement_type, quantity=quantity,
        balance_after=new_qty, unit_cost=effective_unit_cost,
        total_value=quantity * effective_unit_cost,
        source_content_type=..., source_object_id=...,  # from `source`, via ContentType
        reason=reason, created_by=actor,
    )
```

Rules:
- `quantity` is always **positive**; direction comes from `movement_type` via the `SIGN` map.
- `select_for_update()` is mandatory. Without it, concurrent issues corrupt the balance.
- Never `item.quantity -= n`. `Item` has no `quantity` field, deliberately.
- Never `StockLevel.objects.filter(...).update(quantity=...)` — bypasses the ledger.
- Corrections are compensating movements, never edits or deletes of existing ones —
  `StockMovement.save()` raises if called on an already-persisted row, enforcing this.
- Uses `.for_organization(org)`, never the bare `objects` manager or the ambient
  contextvar — `apply_movement()` is a stateless service taking `organization` explicitly
  (context 04 §1), and Phase 6's cross-org transfer touches two organisations' stock in one
  call, which the single-value contextvar can't represent anyway. See G-07, D-14 in
  `MEMORY.md`.
- `COST_BEARING = {RECEIPT, OPENING}` only — never `TRANSFER_IN` (cost basis moves with the
  stock) or `ISSUE` (moving average updates on receipt only, §4 below).

---

## 3. Naming

| Thing | Convention | Example |
|---|---|---|
| App | plural lowercase | `procurement`, `alerts` |
| Model | singular PascalCase | `PurchaseOrder`, `StockMovement` |
| Status/type field | `TextChoices` in the model | `class Status(models.TextChoices)` |
| Boolean | `is_` / `has_` / `can_` | `is_perishable`, `has_expiry` |
| Date vs datetime | `_date` vs `_at` | `expiry_date`, `received_at` |
| Money | `Decimal(12, 2)` | never `float`. Ever. |
| Quantity | `Decimal(14, 3)` | supports 0.5 litre and 2.25 kg |
| Document number | `<PREFIX>/<ORG_SLUG>/<FY>/<SEQ>` | `PO/CET/2526/00042` |
| URL name | `<app>:<object>_<action>` | `procurement:po_detail` |
| Template | `<app>/<object>_<action>.html` | `procurement/po_detail.html` |
| Service function | verb-first | `post_grn`, `approve_requisition` |
| Selector function | `get_` / `list_` | `list_low_stock_items` |
| Test | `test_<action>_<condition>_<expectation>` | `test_issue_stock_insufficient_raises` |

Document numbers are generated inside a transaction using a per-org, per-FY sequence row with
`select_for_update()`. Do **not** use `max(id)+1` or a `uuid4()` slice — the first races, the
second is unreadable to a store clerk reading it over the phone.

---

## 4. Money and quantity

- `Decimal` everywhere. `float` in a financial field is a defect.
- Round only at display time, never in intermediate arithmetic.
- Store `gst_rate` as a percentage `Decimal(5,2)` (e.g. `18.00`), not `0.18`.
- Moving-average cost updates on receipt only, never on issue.
- Currency is `INR` throughout; the field exists on `Organization` for future-proofing, not
  because multi-currency is in scope. It is not.

---

## 5. Migrations

- One logical change per migration file.
- Data migrations are separate from schema migrations and always define `reverse_code`
  (use `migrations.RunPython.noop` only when reversal is genuinely a no-op).
- Use `RenameModel` / `RenameField`, never drop-and-recreate — that destroys data.
- Add indexes in their own migration; on large tables use
  `AddIndexConcurrently` with `atomic = False`.
- Never edit a migration that has been applied anywhere but your own machine.
- After every model change: `makemigrations --check --dry-run` must report nothing pending.

---

## 6. Tests

```
apps/<app>/tests/
    factories.py       factory-boy; every factory sets organization
    test_models.py     constraints, properties, validation
    test_services.py   business logic, the bulk of the value
    test_views.py      status codes, permissions, template context
    test_tenancy.py    isolation for this app's models
```

- Use `pytest.mark.django_db`, not `TestCase`, unless you need `TransactionTestCase`
  (concurrency tests of `apply_movement` do).
- Never `Model.objects.create()` directly in a test — use a factory, so adding a required
  field does not break 200 tests.
- Every permission decorator gets a matching negative test.
- Concurrency test for `apply_movement`: two threads issuing simultaneously must leave a
  consistent balance and one must raise `InsufficientStock`.
- Target ≥80% coverage on `services.py` and `selectors.py`. Templates need not be covered.

---

## 7. Templates & frontend

- `templates/base.html` (Phase 1, greenfield — see D-11 in `MEMORY.md`) is the project-wide
  layout: Bootstrap 5 + HTMX via CDN, `{% include "partials/navbar.html" %}` for the navbar
  (org switcher dropdown, login state). New templates extend `base.html`; don't fork it.
- Move templates into `apps/<app>/templates/<app>/` as each app is carved out.
- HTMX for partial updates. Return a fragment template, not JSON, for HTMX requests:
  `if request.headers.get("HX-Request"):`
- No inline `<script>` blocks with business logic. Chart config lives in `static/js/charts.js`,
  fed by `json_script`.
- Every list view: paginated (25/page), searchable, sortable, exportable. Build one
  `_list_toolbar.html` partial and reuse it.
- Org branding: `base.html` reads `request.organization.theme_color` into a CSS variable so
  each institution's portal is visually distinct. It also prevents the mistake of a user
  believing they are in the wrong org.

---

## 8. Security baseline

- CSRF on everything (Django default — do not exempt).
- `@login_required` on every view except login/signup/healthz.
- File uploads: validate extension **and** content type, cap size, store outside the
  webroot, serve through a permission-checking view — never a direct `MEDIA_URL` link for
  compliance certificates or invoices.
- Rate-limit login (`django-axes` or equivalent).
- Never log a password, token, or full session key.
- Prod: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS,
  `X_FRAME_OPTIONS=DENY`.
- Soft-delete (`is_active=False`) for masters; hard delete only for drafts. `PROTECT` on FKs
  so a category with items cannot vanish.

---

## 9. Commits

Conventional Commits, scoped by app:

```
feat(tenancy): add Membership model and org-scoped managers
fix(inventory): lock StockLevel row during movement to prevent lost updates
refactor(catalog): rename Product to Item, preserve data via RenameModel
test(tenancy): parametrise isolation suite across all tenant models
chore(docker): pin postgres to 16-alpine
docs(context): update 01-domain-model after Batch fields changed
```

One phase ≈ several commits. Never one giant commit per phase — it is unreviewable and
unrevertable.
