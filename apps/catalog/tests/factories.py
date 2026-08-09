import factory

from apps.core.factories import TenantModelFactory, match_org
from apps.tenancy.tests.factories import OrganizationFactory

from ..models import Category, Item, ItemSupplier, Supplier, UnitOfMeasure


class UnitOfMeasureFactory(TenantModelFactory):
    class Meta:
        model = UnitOfMeasure

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Unit {n}")
    symbol = factory.Sequence(lambda n: f"U{n}")


class CategoryFactory(TenantModelFactory):
    class Meta:
        model = Category

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Category {n}")
    code = factory.Sequence(lambda n: f"CAT{n}")


class ItemFactory(TenantModelFactory):
    class Meta:
        model = Item
        skip_postgeneration_save = True

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Item {n}")
    sku = factory.Sequence(lambda n: f"SKU{n}")
    category = factory.SubFactory(CategoryFactory)
    uom = factory.SubFactory(UnitOfMeasureFactory)

    @factory.post_generation
    def _match_org(self, create, extracted, **kwargs):
        if create:
            match_org(self, "category", "uom")


class SupplierFactory(TenantModelFactory):
    class Meta:
        model = Supplier

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Supplier {n}")
    code = factory.Sequence(lambda n: f"SUP{n}")


class ItemSupplierFactory(TenantModelFactory):
    class Meta:
        model = ItemSupplier

    organization = factory.SubFactory(OrganizationFactory)
    item = factory.SubFactory(ItemFactory)
    supplier = factory.SubFactory(SupplierFactory)
    unit_price = "10.00"
