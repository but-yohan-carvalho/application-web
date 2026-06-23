from flask import Flask
from models import db, Product, Order


app = Flask(__name__)

@app.before_request
def connect_db():
    db.connect(reuse_if_open=True)

@app.teardown_request
def close_db(exc):
    if not db.is_closed():
        db.close()

@app.cli.command('init-db')
def init_db():
    db.connect(reuse_if_open=True)
    db.create_tables([Product, Order])
    from services import ProductService
    ProductService.fetch_and_store()
    print("Base de données initialisée.")

from routes import api
app.register_blueprint(api)

app.jinja_env.globals['IMAGE_BASE'] = 'https://dimensweb.uqac.ca/~jgnault/shops/products/'

