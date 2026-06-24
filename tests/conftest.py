import pytest
from peewee import SqliteDatabase
from models import Product, Order, OrderItem

TEST_DB = SqliteDatabase(':memory:')


@pytest.fixture(autouse=True)
def use_test_db():
    TEST_DB.bind([Product, Order, OrderItem], bind_refs=False, bind_backrefs=False)
    TEST_DB.connect()
    TEST_DB.create_tables([Product, Order, OrderItem])
    yield
    TEST_DB.drop_tables([Product, Order, OrderItem])
    TEST_DB.close()


@pytest.fixture()
def sample_product():
    return Product.create(
        id=1,
        name='Test Product',
        type='test',
        description='A test product',
        image='http://example.com/img.png',
        height=10,
        weight=400,
        price=1000,
        in_stock=True,
    )


@pytest.fixture()
def out_of_stock_product():
    return Product.create(
        id=2,
        name='Out of Stock',
        type='test',
        description='No stock',
        image='http://example.com/img2.png',
        height=10,
        weight=400,
        price=1000,
        in_stock=False,
    )


@pytest.fixture()
def app():
    import api8inf349
    api8inf349.app.config['TESTING'] = True
    return api8inf349.app


@pytest.fixture()
def client(app):
    return app.test_client()