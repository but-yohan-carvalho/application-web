import os
from peewee import PostgresqlDatabase, Model, IntegerField, FloatField, CharField, BooleanField, ForeignKeyField

db = PostgresqlDatabase(
    os.environ.get('DB_NAME', 'api8inf349'),
    host=os.environ.get('DB_HOST', 'localhost'),
    port=int(os.environ.get('DB_PORT', 5432)),
    user=os.environ.get('DB_USER', 'user'),
    password=os.environ.get('DB_PASSWORD', 'pass'),
)


class BaseModel(Model):
    class Meta:
        database = db

class Product(BaseModel):
    id=IntegerField(primary_key=True)
    name=CharField()
    type = CharField()
    description = CharField()
    image = CharField()
    height = IntegerField()
    weight = IntegerField()
    price = IntegerField()
    in_stock = BooleanField()


class Order(BaseModel):
    id=IntegerField(primary_key=True)
    total_price = FloatField(default=0)
    total_price_tax = FloatField(default=0)
    shipping_price = IntegerField(default=0)
    email = CharField(null=True)
    paid = BooleanField(default=False)
    status = CharField(default='pending')

    #Shipping
    shipping_country = CharField(null=True)
    shipping_province = CharField(null=True)
    shipping_address = CharField(null=True)
    shipping_city = CharField(null=True)
    shipping_postal_code = CharField(null=True)

    #Credit Card
    cc_name = CharField(null=True)
    cc_first_digits = CharField(null=True)
    cc_last_digits = CharField(null=True)
    cc_expiration_year = CharField(null=True)
    cc_expiration_month = CharField(null=True)

    #Transaction
    transaction_id = CharField(null=True)
    transaction_success = BooleanField(null=True)
    transaction_amount_charged = IntegerField(null=True)
    transaction_error = CharField(null=True)


class OrderItem(BaseModel):
    order = ForeignKeyField(Order, backref='items', on_delete='CASCADE')
    product = ForeignKeyField(Product)
    quantity = IntegerField()





