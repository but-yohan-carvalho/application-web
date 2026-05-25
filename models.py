from peewee import SqliteDatabase, Model, IntegerField, CharField, BooleanField, FloatField
db = SqliteDatabase('database.db')

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

