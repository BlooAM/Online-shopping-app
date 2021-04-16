import email

from domain import events


def handle(event: events.Event):
    for handler in HANDLERS[type(event)]:
        handler(event)

def sent_out_of_stock_notification(event: events.OutOfStock):
    email.send_mail(
        'stock@made.com',
        f'No available {event.sku}'
    )

HANDLERS = {
    events.OutOfStock: [sent_out_of_stock_notification],
}