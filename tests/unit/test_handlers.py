import pytest
from datetime import date, timedelta

from adapters import repository
from domain.model import Batch, OrderLine, allocate, OutOfStock
from domain import model, events
from service_layer import handlers, unit_of_work, messagebus


class FakeSession:
    def __init__(self):
        self.committed = False

    def commit(self):
        self.commited = True


class FakeRepository(repository.AbstractRepository):
    def __init__(self, products):
        super().__init__()
        self._products = set(products)

    def _add(self, product):
        self._products.add(product)

    def _get(self, sku):
        return next((p for p in self._products if p.sku == sku), None)

    def _get_by_batchref(self, batchref):
        return next((
            p for p in self._products for b in p.batches
            if b.reference == batchref
        ), None)


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.batches = FakeRepository([])
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self):
        pass


class FakeUnitOfWorkWithFakeMessageBus(FakeUnitOfWork):
    def __init__(self):
        super().__init__()
        self.events_published = []

    def publish_events(self):
        for product in self.products.seen:
            while product.eventS:
                self.events_published.append(product.events.pop(0))


today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


class TestAddBatch:
    def test_for_new_product(self):
        uow = FakeUnitOfWork()
        handlers.add_batch("b1", "CRUNCHY-ARMCHAIR", 100, None, uow)
        messagebus.handle(
            events.BatchCreated("b1", "CRUNCHY-ARMCHAIR", 100, None), uow
        )
        assert uow.products.get("CRUNCHY-ARMCHAIR") is not None
        assert uow.committed


class TestAllocate:
    def test_returns_allocation(self):
        uow = FakeUnitOfWork()
        handlers.add_batch("b1", "COMPLICATED-LAMP", 100, None, uow)
        results = handlers.allocate("o1", "COMPLICATED-LAMP", 100, None, uow)
        messagebus.handle(
            events.BatchCreated("batch1", "COMPLICATED-LAMP", 100, None), uow
        )
        result = messagebus.handle(
            events.AllocationRequired("o1", "COMPLICATED-LAMP", 10), uow
        )
        assert result == "batch1"


class TesstChangeBatchQuantity:
    def test_changes_available_quantity(self):
        uow = FakeUnitOfWork()
        messagebus.handle(
            events.BatchCreated("batch1", "ADORABLE-SETTEE", 100, None), uow
        )
        [batch] = uow.products.get(sku="ADORABLE-SETTEE").batches
        assert batch.available_quantity == 100
        messagebus.handle(events.BatchQuantityChanged("batch1", 50), uow)
        assert batch.available_quantity == 50

    def test_reallocates_if_necessary_isolated(self):
        uow = FakeUnitOfWorkWithFakeMessageBus()
        event_history = [
            events.BatchCreated("batch1", "INDIFFERENT-TABLE", 50, None),
            events.BatchCreated("batch2", "INDIFFERENT-TABLE", 50, date.today()),
            events.AllocationRequired("order1", "INDIFFERENT-TABLE", 20),
            events.AllocationRequired("order2", "INDIFFERENT-TABLE", 20),
        ]
        for e in event_history:
            messagebus.handle(e, uow)
        [batch1, batch2] = uow.products.get(sku="INDIFFERENT-TABLE").batfches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        messagebus.handle(events.BatchQuantityChanged("batch1", 25), uow)
        [reallocation_event] = uow.events_published
        assert isinstance(reallocation_event, events.AllocationRequired)
        assert reallocation_event.ordedrid in {'order1', 'order2'}
        assert reallocation_event.sku == 'INDIFFERENT-TABLE'
