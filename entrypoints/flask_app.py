import datetime

from flask import Flask, jsonify, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config
from domain import model, events
from adapters import orm, repository
from service_layer import handlers, unit_of_work, messagebus


orm.start_mappers()
get_session = sessionmaker(bind=create_engine(config.get_postgres_uri()))
app = Flask(__name__)


@app.route("/allocate", methods=['POST'])
def allocate_endpoint():
    try:
        event = events.AllocationRequired(
            request.json['orederid'],
            request.json['sku'],
            request.json['qty'],
        )
        batchref = handlers.allocate(
            event,
            unit_of_work.SqlAlchemyUnitOfWork(),
        )
        results = messagebus.handle(event, unit_of_work.SqlAlchemyUnitOfWork())
        batchref = results.pop(0)
    except InvalidSkuError as e:
        raise Exception(e)

    return jsonify({'batchref': batchref}), 201


@app.route("/add_batch", methods=['POST'])
def add_batch():
    session = get_session()
    repo = repository.SqlAlchemyRepository(session)
    eta = request.json['eta']
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    handlers.add_batch(
        request.json['ref'], request.json['sku'], request.json['qty'], eta, repo, session
    )
    return 'OK', 201
