from flask import Flask
from models import db, Product, Order, OrderItem


app = Flask(__name__)

@app.before_request
def connect_db():
    # Résilience : si Postgres est indisponible, on ne fait pas planter la
    # requête ici.
    try:
        db.connect(reuse_if_open=True)
    except Exception:
        pass

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
    from rq import Queue, Worker

    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    redis_conn = Redis.from_url(redis_url)

    queue = Queue('default', connection=redis_conn)
    worker = Worker([queue], connection=redis_conn)
    worker.work()

from routes import api
app.register_blueprint(api)

app.jinja_env.globals['IMAGE_BASE'] = 'https://dimensweb.uqac.ca/~jgnault/shops/products/'

