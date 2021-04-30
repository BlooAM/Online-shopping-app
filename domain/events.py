from datetime import date
from dataclasses import dataclass
from typing import Optional


class Event:
    pass


@dataclass
class Allocated(Event):
    orderid: str
    sku: str
    qty: int
    batchref: str


@dataclass
class BatchCreated(Event):
    ref: str
    sku: str
    qty: int
    eta: Optional[date] = None


@dataclass
class AllocationRequired(Event):
    orderid: str
    sku: str
    qty: int


@dataclass
class BatchQuantityChanged(Event):
    ref: str
    qty: int


@dataclass
class OutOfStock(Event):
    sku: str
