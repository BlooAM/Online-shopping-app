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


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.batches = FakeRepository([])
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self):
        pass


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
