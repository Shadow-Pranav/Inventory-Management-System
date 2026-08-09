---
description: Audit the codebase for tenant-isolation leaks
---

Run a full tenancy audit. Do this at the end of every phase from Phase 2 onward, and any time
a new view, form or API endpoint touching tenant data is added.

## 1. Static scan

```bash
# Unscoped querysets on tenant models — every hit needs justification
docker compose exec web grep -rn "\.objects\.all()\|\.objects\.filter(" apps/ \
  --include="*.py" | grep -v "test\|migrations\|tenancy/"

# get_object_or_404 not going through the tenant helper — the likeliest leak,
# because it looks completely ordinary
docker compose exec web grep -rn "get_object_or_404" apps/ --include="*.py" \
  | grep -v "for_request\|get_tenant_object"

# organization taken from user input — always a bug
docker compose exec web grep -rn "organization" apps/ --include="*.py" \
  | grep -i "request.POST\|request.GET\|kwargs\[.organization"

# hardcoded org slugs — policy belongs on the Organization row
docker compose exec web grep -rniE "cet|ims|nursing|riddhima|hotel_mgmt" apps/ \
  --include="*.py" | grep -v "migrations\|fixtures\|test"

# escape-hatch manager usage
docker compose exec web grep -rn "all_objects" apps/ --include="*.py"
```

## 2. Dynamic checks

```bash
docker compose exec web pytest -k isolation -vv
docker compose exec web python manage.py check_tenancy   # custom command; write it in Phase 2
```

`check_tenancy` should walk `apps.get_models()` and report any model that has an
`organization` field but does not inherit `TenantOwnedModel`, and any tenant model whose
unique constraints omit `organization`.

## 3. Manual spot check

Log in as an Org Admin of one institution and attempt, by direct URL, to reach another
institution's item detail, PO, GRN, report export and uploaded compliance certificate.
Every one must return **404** — a 403 confirms the object exists, which is itself a small leak.

## 4. Report

```
── TENANCY AUDIT ────────────────────────
Tenant models:        N
Covered by isolation: N
Unscoped querysets:   N   (list any, with justification)
Bare get_object_or_404: N (list any)
all_objects uses:     N   (each must be in tenancy layer / admin / command / task)
Hardcoded slugs:      N
Verdict:              PASS | FAIL
─────────────────────────────────────────
```

Any FAIL blocks the phase. There is no "fix it next phase" for this.
