import email

from domain import events
from service_layer import unit_of_work


def handle(event: events.Event, uow: unit_of_work.AbstractUnitOfWork):
    queue = [event]
    while queue:
        event = queue.pop(0)
        for handler in HANDLERS[type(event)]:
            handler(event, uow=uow)
            queue.extend(uow.collent_new_events())
    return results

def sent_out_of_stock_notification(event: events.OutOfStock):
    email.send_mail(
        'stock@made.com',
        f'No available {event.sku}'
    )

HANDLERS = {
    events.OutOfStock: [sent_out_of_stock_notification],
}
