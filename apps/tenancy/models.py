from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TenantOwnedModel, TimeStampedModel


class Organization(TimeStampedModel):
    class OrgType(models.TextChoices):
        COLLEGE = "COLLEGE", "College"
        HOSPITAL = "HOSPITAL", "Hospital"
        INSTITUTE = "INSTITUTE", "Institute"
        HOTEL = "HOTEL", "Hotel Management"
        BUSINESS_SCHOOL = "BUSINESS_SCHOOL", "Business School"
        VENTURE = "VENTURE", "Venture"
        TRUST_OFFICE = "TRUST_OFFICE", "Trust Office"

    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    org_type = models.CharField(max_length=20, choices=OrgType.choices)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    logo = models.ImageField(upload_to="org_logos/", blank=True, null=True)
    theme_color = models.CharField(max_length=7, blank=True, help_text="Hex colour, e.g. #1a73e8")
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=4)
    currency = models.CharField(max_length=3, default="INR")
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.short_name or self.name


class Department(TenantOwnedModel):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    cost_centre_code = models.CharField(max_length=30, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], name="uniq_department_org_code"
            ),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.organization.short_name})"


class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    employee_code = models.CharField(max_length=30, blank=True)
    is_trust_admin = models.BooleanField(default=False)
    default_organization = models.ForeignKey(
        Organization, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.get_full_name() or self.username


class Membership(TimeStampedModel):
    class Role(models.TextChoices):
        ORG_ADMIN = "ORG_ADMIN", "Org Admin"
        STORE_MANAGER = "STORE_MANAGER", "Store Manager"
        DEPT_STAFF = "DEPT_STAFF", "Department Staff"
        AUDITOR = "AUDITOR", "Auditor"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL, related_name="memberships"
    )
    stores = models.ManyToManyField(
        "inventory.Location", blank=True, related_name="store_managers"
    )  # STORE_MANAGER scope narrowing (X-06, filled in now that apps.inventory exists)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"], name="uniq_membership_user_org"
            ),
        ]

    def __str__(self):
        return f"{self.user} @ {self.organization} ({self.role})"
