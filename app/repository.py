import collections as abc

from app import model


class AbstractRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, batch: model.Batch):
        raise NotImplementedError

    @abs.abstractmethod
    def get(self, reference) -> model.Batch:
        raise NotImplementedError
