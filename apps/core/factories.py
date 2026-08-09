import factory


class TenantModelFactory(factory.django.DjangoModelFactory):
    """Base for factories of `TenantOwnedModel` subclasses.

    Creates via `all_objects`, the unscoped manager — factory creation legitimately has no
    active organization context, and going through `objects` (`TenantManager`) would raise
    `UnscopedQueryError` by design. See MEMORY.md G-06.
    """

    class Meta:
        abstract = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.all_objects.create(*args, **kwargs)


def match_org(instance, *fk_attrs):
    """Force each named FK's `organization` to match `instance.organization`.

    SubFactory-generated related rows get their own fresh `OrganizationFactory()` by
    default, so an `ItemFactory(organization=org_a)` would otherwise end up with a
    `category` and `uom` in a *different*, unrelated org — silently invalid data for a
    model whose whole `Meta.constraints` assume same-org FKs. Call from a
    `@factory.post_generation` hook: `match_org(self, "category", "uom")`.
    """
    for attr in fk_attrs:
        related = getattr(instance, attr, None)
        if related is not None and related.organization_id != instance.organization_id:
            related.organization = instance.organization
            related.save(update_fields=["organization"])
