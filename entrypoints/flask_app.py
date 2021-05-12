import datetime

from flask import Flask, jsonify, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config
from domain import model, events, commands
from adapters import orm, repository
from allocation import bootstrap, views
from service_layer import handlers, unit_of_work, messagebus


app = Flask(__name__)
bus = bootstrap.bootstrap()


@app.route("/allocate", methods=['POST'])
def allocate_endpoint():
    cmd = commands.Allocate(
        request.json['orederid'], request.json['sku'], request.json['qty']
    )
    bus.handle(cmd)
    return jsonify({'batchref': batchref}), 201


@app.route("/add_batch", methods=['POST'])
def add_batch():
    eta = request.json['eta']
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    cmd = commands.CreateBatch(
        request.json['ref'], request.json['sku'], request.json['qty'], eta
    )
    bus.handle(cmd)
    return 'OK', 201


@app.route("/allocations/<orderid>", methods=['GET'])
def allocations_view_endpoint(orderid):
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    result = views.allocations(orderid, uow)
    if not result:
        return 'not found', 404
    return jsonify(result), 200
