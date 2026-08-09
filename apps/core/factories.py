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
