import pytest
import requests

from adapters import notifications
from allocation import bootstrap
from service_layer import unit_of_work
from domain import commands


@pytest.fixture
def bus(sqlite_session_factory):
    bus = bootstrap.bootstrap(
        start_orm=True,
        uow=unit_of_work.SqlAlchemyUnitOfWork(sqlite_session_factory),
        notifications=notifications.EmailNotifications(),
        publish=lambda *args: None,
    )
    yield bus
    clear_mappers()

def get_email_from_mailhog(sku):
    host, port = map(config.get_email_host_and_port().get, ['host', 'http_port'])
    all_emails = requests.get(f'https://{host}:{port}/api/v2/messages').json()
    return next(m for m in all_emails['items'] if sku in str(m))

def test_out_of_stock_email(bus):
    sku = random_sku()
    bus.handle(commands.CreateBatch('batch1', sku, 9, None))
    bus.handle(commands.Allocate('order1', sku, 10))
    email = get_email_from_mailhog(sku)
    assert email['Raw']['From'] == 'allocaations@example.com'
    assert email['Raw']['To'] == ['stock@made.com']
    assert f'No {sku} unit' in email['Raw']['Data']

