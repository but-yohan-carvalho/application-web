from flask import Flask
from models import db, Product, Order, OrderItem


app = Flask(__name__)

@app.before_request
def connect_db():
    if app.testing:
        return
    db.connect(reuse_if_open=True)

@app.teardown_request
def close_db(exc):
    if app.testing:
        return
    if not db.is_closed():
        db.close()

@app.cli.command('init-db')
def init_db():
    db.connect(reuse_if_open=True)
    db.create_tables([Product, Order, OrderItem])
    from services import ProductService
    ProductService.fetch_and_store()
    print("Base de données initialisée.")

@app.cli.command('worker')
def run_worker():
    import os
    from redis import Redis
    from rq import Connection, Worker

    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    redis_conn = Redis.from_url(redis_url)

    with Connection(redis_conn):
        worker = Worker(['default'])
        worker.work()

from routes import api
app.register_blueprint(api)

app.jinja_env.globals['IMAGE_BASE'] = 'https://dimensweb.uqac.ca/~jgnault/shops/products/'

