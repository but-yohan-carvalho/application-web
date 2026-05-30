import json, urllib.request
from models import Product, Order

class ProductService:
    PRODUCT_URL="https://dimensweb.uqac.ca/~jgnault/shops/products/"

    @staticmethod
    def fetch_and_store():
        with urllib.request.urlopen(ProductService.PRODUCT_URL) as response:
            data = json.loads(response.read().decode())

        for p in data['products']:
            Product.get_or_create(
                id=p['id'],
                defaults={
                    'name': p['name'],
                    'type': p['type'],
                    'description': p['description'],
                    'image': p['image'],
                    'height': p['height'],
                    'weight': p['weight'],
                    'price': p['price'],
                    'in_stock': p['in_stock'],
                    }
                )


    @staticmethod
    def get_all():
        return  list(Product.select())


    @staticmethod
    def get_by_id(product_id):
        return Product.get_or_none(Product.id == product_id)



class OrderService:
    @staticmethod
    def create(product_id, quantity):
        product = ProductService.get_by_id(product_id)

        if product is None:
            raise ValueError('missing-fields')

        if not product.in_stock:
            raise ValueError('out-of-inventory')

        order = Order.create(
            product=product.id,
            quantity=quantity, )
        return order

    @staticmethod
    def get(order_id):
        return Order.get_or_none(Order.id == order_id)

    @staticmethod
    def _calc_shipping(weight):
        if weight<500:
            return 500
        elif weight<2000:
            return 1000
        else:
            return 2500
    @staticmethod
    def _calc_total(price, quantity):
        return price * quantity
    @staticmethod
    def _calc_total_tax(total, province):
        taxes = {
            'QC': 0.15,
            'ON': 0.13,
            'AB': 0.05,
            'BC': 0.12,
            'NS': 0.14,
        }
        rate = taxes.get(province, 0)
        return round(total * (1 + rate), 2)

    @staticmethod
    def update_shipping(order_id, email, info):
        order = OrderService.get(order_id)

        if order is None:
            return None

        product = ProductService.get_by_id(order.product)

        order.email = email
        order.shipping_country = info['country']
        order.shipping_province = info['province']
        order.shipping_address = info['address']
        order.shipping_city = info['city']
        order.shipping_postal_code = info['postal_code']

        order.shipping_price = OrderService._calc_shipping(product.weight)
        order.total_price = OrderService._calc_total(product.price, order.quantity)
        order.total_price_tax = OrderService._calc_total_tax(order.total_price, info['province'])

        order.save()
        return order

    @staticmethod
    def apply_credit_card(order_id, credit_card):
        order = OrderService.get(order_id)

        if order is None:
            return None

        if order.paid:
            raise ValueError('already-paid')

        if not order.email or not order.shipping_country:
            raise ValueError('missing-fields')

        amount_charged = order.total_price_tax + order.shipping_price
        transaction = PaymentService.charge(credit_card, amount_charged)

        order.cc_name = transaction['credit_card']['name']
        order.cc_first_digits = transaction['credit_card']['first_digits']
        order.cc_last_digits = transaction['credit_card']['last_digits']
        order.cc_expiration_year = transaction['credit_card']['expiration_year']
        order.cc_expiration_month = transaction['credit_card']['expiration_month']

        order.transaction_id = transaction['transaction']['id']
        order.transaction_success = transaction['transaction']['success']
        order.transaction_amount_charged = transaction['transaction']['amount_charged']

        order.paid = True
        order.save()
        return order

class PaymentService:

    PAY_URL = 'https://dimensweb.uqac.ca/~jgnault/shops/pay/'

    @staticmethod
    def charge(credit_card, amount_charged):
        payload = json.dumps({
            'credit_card': credit_card,
            'amount_charged': amount_charged
        }).encode('utf-8')

        req = urllib.request.Request(
            PaymentService.PAY_URL,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())







