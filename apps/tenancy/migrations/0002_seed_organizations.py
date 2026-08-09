import json
from pathlib import Path

from django.db import migrations

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "organizations.json"


def load_organizations():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def seed_organizations(apps, schema_editor):
    Organization = apps.get_model("tenancy", "Organization")
    for org in load_organizations():
        Organization.objects.get_or_create(
            slug=org["slug"],
            defaults={
                "name": org["name"],
                "short_name": org["short_name"],
                "org_type": org["org_type"],
            },
        )


def unseed_organizations(apps, schema_editor):
    Organization = apps.get_model("tenancy", "Organization")
    slugs = [org["slug"] for org in load_organizations()]
    Organization.objects.filter(slug__in=slugs).delete()


def flag_superusers_as_trust_admins(apps, schema_editor):
    User = apps.get_model("tenancy", "User")
    User.objects.filter(is_superuser=True).update(is_trust_admin=True)


def unflag_trust_admins(apps, schema_editor):
    User = apps.get_model("tenancy", "User")
    User.objects.filter(is_superuser=True).update(is_trust_admin=False)


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_organizations, unseed_organizations),
        migrations.RunPython(flag_superusers_as_trust_admins, unflag_trust_admins),
    ]
