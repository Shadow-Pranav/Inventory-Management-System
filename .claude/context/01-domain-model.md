# Context 01 — Domain Model

Target schema. Keep this file in sync with the code; when they disagree, the code is right
and this file is a bug. Update it in the same commit that changes a model.

Legend: `*` = tenant-owned (inherits `TenantOwnedModel`, carries `organization` FK)

---

## apps/core

```python
class TimeStampedModel(models.Model):          # abstract
    created_at, updated_at
    created_by = FK(User, null=True, on_delete=SET_NULL, related_name="+")

class TenantOwnedModel(TimeStampedModel):      # abstract
    organization = FK("tenancy.Organization", on_delete=PROTECT, related_name="+")
    objects = TenantManager()
    all_objects = models.Manager()             # unscoped; tenancy layer + admin only
    class Meta: abstract = True

class AuditLog                                 # append-only, never updated or deleted
    organization (nullable — trust-level actions have none)
    actor, action, model_label, object_id, object_repr
    changes = JSONField          # {"field": {"from": x, "to": y}}
    ip_address, user_agent, occurred_at
```

`AuditLog` is written by a post-save/post-delete receiver registered against every model
listed in `settings.AUDITED_MODELS`. Do not write audit rows by hand in views.

---

## apps/tenancy

```python
class Organization                             # NOT tenant-owned — it IS the tenant
    name, short_name, slug (unique), org_type ∈ {COLLEGE, HOSPITAL, INSTITUTE, HOTEL,
                                                 BUSINESS_SCHOOL, VENTURE, TRUST_OFFICE}
    address, city, state, pincode, contact_email, contact_phone
    logo, theme_color                          # per-org branding on the dashboard
    fiscal_year_start_month = 4                # April, Indian FY
    currency = "INR"
    settings = JSONField        # per-org policy: approval thresholds, GST defaults,
                                # low-stock lead time, whether asset tagging is required
    is_active
    # Never hardcode a slug in application code. Read policy from .settings.

class Department *                             # e.g. "Anatomy", "Civil Engineering", "OT-2"
    name, code, parent = FK("self", null=True)  # supports sub-departments
    head = FK(User, null=True)
    cost_centre_code
    Meta: UniqueConstraint(["organization", "code"])

class User(AbstractUser)                       # custom from day one
    email (unique, used as the login identifier)
    phone, employee_code
    is_trust_admin = BooleanField(default=False)   # the only cross-org flag
    default_organization = FK(Organization, null=True, on_delete=SET_NULL)

class Membership                               # user × organisation, carries the role
    user, organization
    role ∈ {ORG_ADMIN, STORE_MANAGER, DEPT_STAFF, AUDITOR}
    department = FK(Department, null=True)     # required when role == DEPT_STAFF
    # stores = M2M("inventory.Location", blank=True)   # STORE_MANAGER scope narrowing
    # ^ deferred until apps.inventory exists (Phase 2) — inventory.Location can't be
    #   referenced before the app is installed. Add the field + a migration in Phase 2.
    is_active
    Meta: UniqueConstraint(["user", "organization"])
```

**Why `Membership` and not a role field on `User`:** a Trust IT lead may run stores in CET
while holding read-only audit access in IMS. A single global role cannot express that.

---

## apps/catalog

```python
class UnitOfMeasure *          # piece, box, litre, kg, pack-of-100
    name, symbol, decimal_places (0 for countable items)
    Meta: UniqueConstraint(["organization", "symbol"])

class Category *
    name, code, parent = FK("self", null=True)   # tree: Consumables > Chemicals > Solvents
    Meta: UniqueConstraint(["organization", "name", "parent"])

class Item *                   # was `Product`
    name, sku, barcode, description, category, uom
    item_type ∈ {CONSUMABLE, ASSET, SPARE, SERVICE}
    tracking_mode ∈ {NONE, BATCH, SERIAL}       # drives Batch / SerialUnit creation
    is_perishable, shelf_life_days
    unit_cost                   # moving average, maintained by apply_movement()
    reorder_level               # manual floor; the engine may propose a higher one
    reorder_level_source ∈ {MANUAL, COMPUTED}
    min_order_qty, lead_time_days
    hsn_code, gst_rate          # Indian tax fields — needed for PO printing
    image, is_active
    Meta: UniqueConstraint(["organization", "sku"])
          UniqueConstraint(["organization", "name"])
    # NOTE: no `quantity` field. Quantity is derived from StockLevel. See 04-conventions.

class Supplier *
    name, code, contact_person, email, phone, address
    gstin, pan
    payment_terms_days, rating (0–5), is_blacklisted
    Meta: UniqueConstraint(["organization", "code"])
    # Suppliers are per-org by default. A shared Trust vendor registry is deliberately
    # deferred — see MEMORY.md "Deferred decisions".

class ItemSupplier *           # price list / preferred vendor
    item, supplier, supplier_sku, unit_price, lead_time_days, is_preferred, valid_until
```

---

## apps/inventory

```python
class Location *               # a physical store, sub-store or department store
    name, code, location_type ∈ {MAIN_STORE, SUB_STORE, DEPT_STORE, LAB, WARD, KITCHEN}
    department = FK(Department, null=True)
    parent = FK("self", null=True)
    is_active
    Meta: UniqueConstraint(["organization", "code"])

class StockLevel *             # the current-quantity table; one row per (item, location, batch)
    item, location, batch (null)
    quantity = Decimal
    reserved_quantity = Decimal    # committed to an approved-but-unissued request
    Meta: UniqueConstraint(["organization", "item", "location", "batch"])
    @property available = quantity - reserved_quantity
    # Only ever mutated inside apply_movement() with select_for_update().

class Batch *
    item, batch_number, manufacture_date, expiry_date, supplier
    Meta: UniqueConstraint(["organization", "item", "batch_number"])

class SerialUnit *             # one physical asset instance
    item, serial_number, batch (null), current_location, current_holder = FK(User, null)
    status ∈ {IN_STOCK, ISSUED, IN_REPAIR, RETIRED, LOST}
    asset = O2O("assets.Asset", null=True)
    Meta: UniqueConstraint(["organization", "serial_number"])

class StockMovement *          # THE LEDGER. Append-only. Was `InventoryLog`.
    item, location, batch (null), serial_unit (null)
    movement_type ∈ {RECEIPT, ISSUE, RETURN, TRANSFER_OUT, TRANSFER_IN,
                     ADJUSTMENT_UP, ADJUSTMENT_DOWN, DAMAGE, EXPIRY, DISPOSAL, OPENING}
    quantity                   # always positive; direction comes from movement_type
    balance_after              # snapshot for fast audit, mirrors old previous/new_quantity
    unit_cost, total_value
    source_content_type + source_object_id   # GenericFK → GRN / Issue / Adjustment
    reason, notes
    Meta: indexes on (organization, item, created_at), (organization, movement_type, created_at)
    # Never updated. Never deleted. A mistake is corrected by a compensating movement.
```

---

## apps/procurement

```
Requisition *          dept raises a need
    → requisition_number, department, requested_by, required_by_date,
      status ∈ {DRAFT, SUBMITTED, APPROVED, REJECTED, CONVERTED, CLOSED}
RequisitionItem *      item, quantity_requested, quantity_approved, notes

PurchaseOrder *        po_number, supplier, expected_date, status ∈ {DRAFT, PENDING_APPROVAL,
                       APPROVED, PARTIALLY_RECEIVED, RECEIVED, CANCELLED},
                       subtotal, tax_amount, total_amount, approved_by, approved_at,
                       terms, delivery_location
POItem *               item, quantity_ordered, quantity_received, unit_price, gst_rate,
                       line_total
GoodsReceipt *         grn_number, purchase_order, received_by, received_at,
                       invoice_number, invoice_date, status ∈ {DRAFT, POSTED, CANCELLED}
GRNItem *              po_item, quantity_accepted, quantity_rejected, rejection_reason,
                       batch_number, expiry_date, serial_numbers = ArrayField
```

Posting a GRN is the **only** way stock enters via procurement, and it emits one
`StockMovement(RECEIPT)` per line inside a single transaction.

---

## apps/issuance

```
IssueRequest *         was `Order`. issue_number, department, requested_by, purpose,
                       status ∈ {PENDING, APPROVED, PARTIALLY_ISSUED, ISSUED,
                                 RETURNED, CANCELLED, REJECTED},
                       approved_by, issued_by, total_items, total_value
IssueItem *            item, quantity_requested, quantity_issued, batch, unit_cost
ReturnNote *           issue_request, returned_by, condition ∈ {GOOD, DAMAGED, EXPIRED},
                       restock (bool)
StockTransfer *        from_location, to_location, from_org, to_org, status,
                       initiated_by, approved_by
                       # Cross-org transfer requires TRUST_ADMIN approval.
DisposalRecord *       item/serial_unit, reason, approved_by, disposal_date,
                       method ∈ {SCRAP, RETURN_TO_VENDOR, DONATE, DESTROY}, certificate
```

---

## apps/assets

Covers the "compliance regarding technical and non-technical resources" half of the brief.

```
Asset *                serial_unit (O2O), asset_tag (unique per org), item,
                       purchase_date, purchase_cost, warranty_expiry,
                       depreciation_method, salvage_value, useful_life_years,
                       current_book_value, custodian = FK(User), location, department,
                       status ∈ {ACTIVE, UNDER_MAINTENANCE, RETIRED, DISPOSED}
AMCContract *          asset(s) M2M, vendor, start_date, end_date, cost, contact,
                       renewal_reminder_days
MaintenanceLog *       asset, maintenance_type ∈ {PREVENTIVE, BREAKDOWN, CALIBRATION},
                       performed_on, performed_by, cost, downtime_hours, next_due_date
ComplianceRequirement * name, applies_to ∈ {ASSET, ITEM, LOCATION, ORGANIZATION},
                       category ∈ {LICENCE, CALIBRATION, INSPECTION, SAFETY_AUDIT,
                                   FIRE_SAFETY, BIOMEDICAL_WASTE, ACCREDITATION},
                       frequency_days, regulator, is_mandatory
ComplianceRecord *     requirement, subject (GenericFK), due_date, completed_date,
                       status ∈ {PENDING, COMPLETED, OVERDUE, WAIVED},
                       certificate_file, verified_by
```

Compliance is where a hospital and a hotel management college diverge sharply — biomedical
waste rules vs food-safety licensing. `ComplianceRequirement` is per-org so each institution
defines its own register.

---

## apps/intelligence

```
ItemAnalytics *        item (O2O), computed_at,
                       avg_daily_consumption, consumption_stddev,
                       forecast_30d, forecast_confidence,
                       days_of_stock_remaining, projected_stockout_date,
                       suggested_reorder_level, suggested_order_qty,
                       abc_class ∈ {A,B,C}, xyz_class ∈ {X,Y,Z},
                       turnover_ratio, is_dead_stock, last_movement_at
ForecastRun *          organization, run_at, model_version, items_processed, duration_ms
ReorderSuggestion *    item, suggested_qty, suggested_supplier, rationale (text),
                       status ∈ {OPEN, ACCEPTED, DISMISSED, CONVERTED_TO_PO},
                       acted_by, acted_at
```

Nightly Celery beat task recomputes `ItemAnalytics` per org. Dashboards read the cached rows
— they never compute forecasts on request.

---

## apps/alerts

```
AlertRule *            name, alert_type ∈ {LOW_STOCK, STOCKOUT, EXPIRY_SOON, EXPIRED,
                                          OVERSTOCK, DEAD_STOCK, PO_OVERDUE,
                                          AMC_EXPIRING, COMPLIANCE_DUE, ANOMALY},
                       threshold_config = JSONField, severity ∈ {INFO, WARNING, CRITICAL},
                       channels = ArrayField[EMAIL, IN_APP, DIGEST],
                       recipients_roles = ArrayField, is_active
Alert *                rule, subject (GenericFK), severity, title, message, context JSON,
                       status ∈ {OPEN, ACKNOWLEDGED, RESOLVED, SUPPRESSED},
                       acknowledged_by, resolved_at, fingerprint (dedupe key)
Notification *         alert, recipient, channel, sent_at, read_at, delivery_status
```

`fingerprint` prevents the same low-stock condition generating a fresh alert every hour.
Re-firing an open alert updates `last_seen_at`; it does not create a row.

---

## apps/reporting

```
ReportDefinition *     name, report_type, query_config JSON, columns, filters,
                       allowed_roles, is_scheduled, schedule_cron
ReportRun *            definition, run_by, params, row_count, file (CSV/XLSX/PDF),
                       status, error_message
DashboardWidget *      dashboard_scope ∈ {ORG, TRUST}, widget_type, position, config JSON
```

Standard reports: stock ledger, valuation, consumption by department, supplier performance,
PO ageing, expiry register, asset register, compliance status, dead-stock, ABC analysis,
cross-org comparison (Trust Admin only).
