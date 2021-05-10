import email
from typing import Callable, Dict, List, Type
from tenacity import Retrying, RetryError, stop_after_attempt, wait_expotential

from adapters import redis_eventpublisher
from domain import events, commands
from service_layer import unit_of_work, handlers


def publish_allocated_event(
        event: events.Allocated, uow: unit_of_work.AbstractUnitOfWork
):
    redis_eventpublisher.publish('line_allocated', event)


class MessageBus:
    def __init__(
            self,
            uow: unit_of_work.AbstractUnitOfWork,
            event_handlers: Dict[Type[events.Event], List[Callable]],
            command_handlers: Dict[Type[commands.Command], Callable],
    ):
        self.uow = uow
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers

    def handle(self, message: Message):
        self.queue = [message]
        while self.queue:
            message = self.queue.pop(0)
            if isinstance(message, events.Event):
                self.handle_event(message)
            elif isinstance(message, commands.Command):
                self.handle_command(message)
            else:
                raise Exception(f'{message} is neither event nor command.')

    def handle_event(self, event: events.Event):
        for handler in self.event_handlers[type(event)]:
            try:
                logger.debug('Handling event %s using %s', event, handler)
                handler(event)
                self.queue.extend(self.uow.collect_new_events())
            except Exception:
                logger.exception('Exception while handling event %s', event)
                continue

    def handle_command(self, command: commands.Command):
        logger.debug('Handling command %s', command)
        try:
            handler = self.command_handlers[type(command)]
            result = handler(command)
            self.queue.extend(self.uow.collect_new_events())
            return result
        except Exception:
            logger.Exception(f'Exception handling command %s', command)
            raise Exception


EVENT_HANDLERS = {
    events.Allocated: [
        handlers.publish_allocated_event,
        handlers.add_allocation_to_read_model,
    ],
    events.Deallocated: [
        handlers.remove_allocation_from_read_model,
        handlers.reallocate,
    ],
    events.OutOfStock: [handlers.send_out_of_stock_notification],
}

COMMAND_HANDLERS = {
    commands.Allocate: handlers.allocate,
    commands.CreateBatch: handlers.add_batch,
    commands.ChangeBatchQuantity: handlers.change_batch_quantity,
}
