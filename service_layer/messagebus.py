import email
from typing import List
from tenacity import Retrying, RetryError, stop_after_attempt, wait_expotential

from domain import events, commands
from service_layer import unit_of_work, handlers


def handle(message: Message, uow: unit_of_work.AbstractUnitOfWork):
    results = []
    queue = [message]
    while queue:
        event = queue.pop(0)
        if isinstance(message, events.Event):
            handle_event(message, queue, uow)
        elif isinstance(message, commands.Command):
            cmd_result = handle_command(message, queue, uow)
            results.append(cmd_result)
        else:
            raise Exception(f'{message} was not an Event or Command')
    return results


def handle_event(
        event: events.Event,
        queue: List[Message],
        uow: unit_of_work.AbstractUnitOfWork
):
    for handler in EVENT_HANDLERS[type(event)]:
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(3),
                wait=wait_expotential()
            ):
                with attempt:
                    logger.debug('handling event %s with handler %s', event, handler)
                    handler(event, uow=uow)
                    queue.extend(uow.collect_new_events())
        except RetryError as retry_failure:
            logger.exception('Exception handling event %s', event)
            continue


def handle_command(
        command: commands.Command,
        queue: List[Message],
        uow: unit_of_work.AbstractUnitOfWork
):
    logger.debug('Handling command %s', command)
    try:
        handler = COMMAND_HANDLERS[type(command)]
        result = handler(command, uow=uow)
        queue.extend(uow.collect_new_events())
        return result
    except Exception:
        logger.Exception(f'Exception handling command %s', command)
        raise Exception


EVENT_HANDLERS = {
    events.OUT: [handlers.send_out_of_stock_notification],
}

COMMAND_HANDLERS = {
    commands.Allocate: handlers.allocate,
    commands.CreateBatch: handlers.add_batch,
    commands.ChangeBatchQuantity: handlers.change_batch_quantity,
}
