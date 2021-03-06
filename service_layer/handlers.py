import email
from datetime import date

from domain import model, events
from domain.model import OrderLine
from adapters.repository import AbstractRepository
from service_layer import unit_of_work


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def add_batch(
        event: events.BatchCreated, uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        product = uow.products.get(sku=event.sku)
        if product is None:
            product = model.Product(event.sku, batches=[])
            uow.products.add(product)
        uow.batches.append(model.Batch(event.ref, event.sku, event.qty, event.eta))
        uow.commit()


def allocate(
        event: events.AllocationRequired, uow: unit_of_work.AbstractUnitOfWork
) -> str:
    line = OrderLine(event.orderid, event.sku, event.qty)
    with uow:
        product = uow.products.get(sku=event.sku)
        if product is None:
            raise InvalidSku(f'Invalid SKU {line.sku}')
        batchref = product.allocate(line)
        uow.commit()
        return batchref


def send_out_of_stock_notification(
        event: events.OutOfStock, uwo: unit_of_work.AbstractUnitOfWork
):
    email.send(
        'stock@made.com',
        f'No available {event.sku}',
    )


def change_batch_quantity(
        event: events.BatchQuantityChanged, uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        product = uow.products.get_by_batchref(batchref=event.ref)
        product.change_batch_quantity(ref=event.ref, qty=event.qty)
        uow.commit()


def add_allocation_to_read_model(
        event: events.Allocated, uow: unit_of_work.SqlAlchemyUnitOfWork,
):
    with uow:
        uow.session.execute(
            'INSERT INTO allocations_view (orderid, sku, batchref)'
            ' VALUES (:orderid, :sku, :batchref)',
            dict(orderid=event.orderid, sku=event.sku, batchref=event.batchref)
        )
        uow.commit()


def remove_allocation_from_read_model(
        event: events.Deallocated, uwo: unit_of_work.SqlAlchemyUnitOfWork,
):
    with uow:
        uow.session.execute(
            'DELETE FROM allocations_view'
            ' WHERE orderid = :orderid AND sku = :sku'
        )