import factory

from apps.catalog.tests.factories import ItemFactory
from apps.core.factories import TenantModelFactory, match_org
from apps.tenancy.tests.factories import OrganizationFactory

from ..models import Batch, Location, SerialUnit, StockLevel, StockMovement


class LocationFactory(TenantModelFactory):
    class Meta:
        model = Location

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Location {n}")
    code = factory.Sequence(lambda n: f"LOC{n}")
    location_type = Location.LocationType.MAIN_STORE


class BatchFactory(TenantModelFactory):
    class Meta:
        model = Batch
        skip_postgeneration_save = True

    organization = factory.SubFactory(OrganizationFactory)
    item = factory.SubFactory(ItemFactory)
    batch_number = factory.Sequence(lambda n: f"BATCH{n}")

    @factory.post_generation
    def _match_org(self, create, extracted, **kwargs):
        if create:
            match_org(self, "item")


class StockLevelFactory(TenantModelFactory):
    class Meta:
        model = StockLevel
        skip_postgeneration_save = True

    organization = factory.SubFactory(OrganizationFactory)
    item = factory.SubFactory(ItemFactory)
    location = factory.SubFactory(LocationFactory)
    quantity = "0"

    @factory.post_generation
    def _match_org(self, create, extracted, **kwargs):
        if create:
            match_org(self, "item", "location")


class SerialUnitFactory(TenantModelFactory):
    class Meta:
        model = SerialUnit
        skip_postgeneration_save = True

    organization = factory.SubFactory(OrganizationFactory)
    item = factory.SubFactory(ItemFactory)
    serial_number = factory.Sequence(lambda n: f"SN{n}")

    @factory.post_generation
    def _match_org(self, create, extracted, **kwargs):
        if create:
            match_org(self, "item")


class StockMovementFactory(TenantModelFactory):
    class Meta:
        model = StockMovement
        skip_postgeneration_save = True

    organization = factory.SubFactory(OrganizationFactory)
    item = factory.SubFactory(ItemFactory)
    location = factory.SubFactory(LocationFactory)
    movement_type = StockMovement.MovementType.OPENING
    quantity = "1"
    balance_after = "1"

    @factory.post_generation
    def _match_org(self, create, extracted, **kwargs):
        if create:
            match_org(self, "item", "location")
