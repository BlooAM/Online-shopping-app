from collections import abc

from domain import repository


class AbstractUnitOfWork(abc.ABC):
    batches: repository.AbstractRepository

    def __exit__(self, *args):
        self.rollback()

    @abc.abstractmethod
    def commit(self):
        raise NotImplemented

    @abc.abstractmethod
    def rollback(self):
        raise NotImplementedError