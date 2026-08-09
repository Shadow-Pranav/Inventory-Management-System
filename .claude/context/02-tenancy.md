# Context 02 — Tenancy & Access Control

The most important file in this repository. A bug here is a data breach between institutions,
not a cosmetic defect. Read it in full before touching anything in `apps/tenancy/`,
any manager, any middleware, or any view that queries tenant data.

---

## 1. Strategy: shared database, shared schema, row-level scoping

One PostgreSQL database, one schema, an `organization_id` column on every tenant-owned table.

**Why not schema-per-tenant or database-per-tenant:** the Trust Admin's core requirement is a
*cross-organisation dashboard*. With separate schemas that becomes N queries fanned out and
merged in Python — slow, awkward, and it makes "compare consumption across all seven
institutions" genuinely hard. With row-level scoping it is one `GROUP BY organization_id`.
Seven-ish tenants also does not justify the operational cost of schema isolation.

**The trade-off we accept:** isolation is enforced in application code, so a single missing
`.filter()` leaks data. The entire design below exists to make that mistake loud instead of
silent.

---

## 2. The three-layer defence

### Layer 1 — Middleware resolves the active organisation

`apps/tenancy/middleware.py`, placed **after** `AuthenticationMiddleware`.

```python
class OrganizationMiddleware:
    """Attach request.organization and request.membership. Never trust user input."""
    def __call__(self, request):
        request.organization = None
        request.membership = None
        request.is_trust_scope = False

        if request.user.is_authenticated:
            if request.user.is_trust_admin:
                # Trust admin may pin a view to one org via an explicit,
                # server-validated session key set by a dedicated switcher view.
                pinned = request.session.get("active_organization_id")
                if pinned:
                    request.organization = Organization.objects.filter(
                        pk=pinned, is_active=True).first()
                request.is_trust_scope = request.organization is None
            else:
                membership = (Membership.objects
                    .select_related("organization", "department")
                    .filter(user=request.user, is_active=True,
                            organization__is_active=True)
                    .first())          # multi-org users: see §5
                if membership:
                    request.membership = membership
                    request.organization = membership.organization

        set_current_organization(request.organization)   # thread-local, for signals/admin
        try:
            return self.get_response(request)
        finally:
            clear_current_organization()
```

**Rules:**
- The org is derived from the **session and membership records only**.
- A non-trust user with no active membership gets `request.organization = None` and is
  redirected to a "no access" page. They do not fall through to unscoped data.
- The org switcher view must re-verify: trust admin → any org; ordinary user → only orgs
  they hold an active `Membership` in.
- Always clear the thread-local in a `finally`. A leaked value poisons the next request
  served by that worker thread, which is the worst class of bug in this system.

### Layer 2 — Managers make unscoped access impossible by accident

`apps/core/managers.py`

> **Corrected in Phase 1** (see G-07 in `MEMORY.md`): `Manager.from_queryset()` generates
> manager methods that call `self.get_queryset()` first, then chain the requested
> `TenantQuerySet` method onto it. If `for_request`/`for_organization` are left to that
> auto-generated wrapper, calling `Model.objects.for_request(request)` hits the *strict*
> `get_queryset()` override and raises `UnscopedQueryError` before `for_request`'s own
> `is_trust_scope` handling ever runs — the documented "Trust Admin path" escape hatch is
> unreachable without the explicit overrides below.

```python
class TenantQuerySet(models.QuerySet):
    def for_organization(self, organization):
        return self.filter(organization=organization)

    def for_request(self, request):
        if getattr(request, "is_trust_scope", False):
            return self._unscoped()          # trust admin, all-orgs view
        if request.organization is None:
            return self.none()               # fail closed, never fail open
        return self.filter(organization=request.organization)

    def _unscoped(self):
        return self.__class__(self.model, using=self._db)._chain()


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    def get_queryset(self):
        org = get_current_organization()
        qs = super().get_queryset()
        if org is not None:
            return qs.filter(organization=org)
        if settings.STRICT_TENANCY:          # True in dev/test, True in prod
            raise UnscopedQueryError(
                f"{self.model.__name__}.objects accessed with no active organization. "
                f"Use .for_request(request), .for_organization(org), or all_objects."
            )
        return qs

    def for_request(self, request):
        # Bypasses get_queryset()'s strict check on purpose — see the note above.
        return TenantQuerySet(self.model, using=self._db).for_request(request)

    def for_organization(self, organization):
        return TenantQuerySet(self.model, using=self._db).for_organization(organization)
```

On `TenantOwnedModel` itself, `objects` (the strict `TenantManager`) must stay the
first-declared manager, ahead of `all_objects` — Django uses the first-declared manager as
`_default_manager` internally (some admin/reverse-relation code paths), and that must be the
strict one, never the unscoped `all_objects`. This is deliberately against Ruff's `DJ012`
style rule; the model file suppresses it with `# noqa: DJ012` and a comment, not silently.

Two escape hatches, both deliberate and both greppable:
- `Model.all_objects` — the plain manager. Permitted **only** in the tenancy layer, Django
  admin, management commands, and Celery tasks that explicitly loop organisations.
- `.for_request(request)` with `is_trust_scope` — the Trust Admin path.

Anything else raises. Loudly. In tests too.

### Layer 3 — Views declare their requirements

`apps/tenancy/decorators.py`

```python
@require_role(Role.STORE_MANAGER, Role.ORG_ADMIN)
def receive_stock(request, ...): ...

@require_trust_admin
def trust_dashboard(request): ...

@require_org_context          # any authenticated user with an active membership
def item_list(request):
    items = Item.objects.for_request(request).select_related("category", "uom")
```

`require_role` reads `request.membership.role`. `is_trust_admin` satisfies every role check.
`AUDITOR` satisfies read decorators only — `require_role` takes a `write=True` flag that
rejects auditors regardless of the role list.

**Object-level check, mandatory in every detail/edit/delete view:**

```python
def get_tenant_object(model, request, pk):
    return get_object_or_404(model.objects.for_request(request), pk=pk)
```

Never `get_object_or_404(Item, pk=pk)`. That is the single most likely leak in the codebase,
because it looks completely normal.

---

## 3. Forms and querysets

Every `ModelForm` with an FK to tenant data must narrow the choice queryset:

```python
class ItemForm(TenantModelForm):        # base class takes `request` in __init__
    tenant_fields = ["category", "uom", "supplier"]
```

`TenantModelForm.__init__` loops `tenant_fields` and rewrites each
`self.fields[f].queryset = field_model.objects.for_request(self.request)`.

Without this, a crafted POST sets `category_id` to another org's category and the FK
validates cleanly. A `clean()`-level check alone is not enough — the dropdown must also
never render foreign options.

---

## 4. Trust Admin dashboard

`is_trust_scope=True` means no org filter. Aggregate with `GROUP BY organization_id`:

```python
Item.all_objects.values("organization__short_name").annotate(
    total_items=Count("id"),
    low_stock=Count("id", filter=Q(stocklevel__quantity__lte=F("reorder_level"))),
    stock_value=Sum(F("stocklevel__quantity") * F("unit_cost")),
).order_by("-stock_value")
```

Trust Admin capabilities:
- Read and **edit** any organisation's data
- Compare institutions side by side (consumption, spend, stockout frequency, compliance %)
- Approve cross-organisation stock transfers
- Create organisations, assign the first `ORG_ADMIN` of each
- Define Trust-wide alert rule templates that orgs inherit and may tighten but not disable

Every trust-admin write against another org's data writes an `AuditLog` row with
`actor_scope="TRUST"`. Org admins can see those entries — visible oversight, not silent.

---

## 5. Users belonging to multiple organisations

Supported by the schema from day one; the UI ships in Phase 3.

- Middleware currently picks the first active membership. Replace with:
  `session["active_organization_id"]` → validate against the user's memberships → fall back
  to `user.default_organization` → fall back to first membership.
- Navbar renders an org switcher when `memberships.count() > 1`.
- Switching organisations **flushes** any cart/draft state held in session. Carrying a
  half-built requisition across an org boundary is a correctness bug waiting to happen.

---

## 6. Mandatory test suite

`apps/tenancy/tests/test_isolation.py` — parametrised over **every** model inheriting
`TenantOwnedModel`, discovered via `apps.get_models()`. Adding a new tenant model
automatically adds it to the suite; there is nothing to remember.

For each model, assert:
1. Org A's user gets `count() == 0` when only Org B rows exist
2. Org A's user gets 404, not 403, on Org B's object detail URL (403 confirms existence)
3. A POST from Org A with an FK pointing at an Org B row fails validation
4. Trust Admin sees rows from both
5. A user with no membership sees nothing and is redirected
6. `Model.objects.all()` with no active org raises `UnscopedQueryError`
7. An `AUDITOR` receives 403 on every write endpoint for that model
8. List endpoint `?search=` cannot surface another org's names via autocomplete

Also assert `Membership` role changes take effect without a re-login (no cached permissions
in the session).

**A phase is not done until these pass.**

---

## 7. Review checklist before any tenancy-touching commit

- [ ] Every new model with tenant data inherits `TenantOwnedModel`
- [ ] Every unique constraint includes `organization`
- [ ] No `get_object_or_404(Model, ...)` — all go through `get_tenant_object`
- [ ] No `organization` value read from POST/GET/URL kwargs
- [ ] All FK dropdowns in forms narrowed via `tenant_fields`
- [ ] `all_objects` used only in permitted layers; each use has a comment saying why
- [ ] Celery tasks loop organisations explicitly and set the thread-local per iteration
- [ ] New endpoints covered by the isolation suite
- [ ] Cross-org write paths emit `AuditLog`
