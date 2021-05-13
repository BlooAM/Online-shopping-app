from typing import Callable
import email
import inspect

from adapters import redis_eventpublisher, orm, notifications
from service_layer import messagebus, unit_of_work, handlers


def inject_dependenccies(handler, dependencies):
    params = inspect.signature(handlers).parameters
    deps = {
        name: dependency
        for name, dependency in dependencies.items() if name in params
    }
    return lambda message: handler(message, **deps)


def bootstrap(
        start_orm: bool = True,
        uwo: unit_of_work.AbstractUnitOfWork = unit_of_work.SqlAlchemyUnitOfWork(),
        notifications: notifications.AbstractNotifications = notifications.EmailNotification(),
        publish: Callable = redis_eventpublisher.publish,
) -> messagebus.MessageBus:
    if start_orm:
        orm.start_mappers()

    dependencies = {'uow': uow, 'send_mail': send_mail, 'publish': publish}
    injected_event_handlers = {
        event_type: [
            inject_dependencies(handler, dependencies) for handler in event_handlers
        ]
        for event_type, event_handlers in handlers.EVENT_HANDLERS.items()
    }
    injected_command_hanlers = {
        command_type: inject_dependencies(handler, dependencies)
        for command_type, handler in handlers.COMMAND_HANLDERS.items()
    }

    return messagebus.MessageBus(
        uow=uow,
        event_handlers=injected_event_handlers,
        command_handlers=injected_command_hanlers,
    )