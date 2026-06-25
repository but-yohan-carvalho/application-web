import json, urllib.request
from models import Product, Order, OrderItem


def _clean(value):
    """Postgres refuse les caractères NUL , on les retire."""
    if isinstance(value, str):
        return value.replace('\x00', '')
    return value


def order_to_dict(order):
    """Sérialise une commande au format JSON de l'API.
    """
    return {
        'order': {
            'id': order.id,
            'products': [
                {
                    'id': item.product_id,
                    'quantity': item.quantity,
                }
                for item in order.items
            ],
            'email': order.email,
            'paid': order.paid,
            'shipping_information': {
                'country': order.shipping_country,
                'province': order.shipping_province,
                'address': order.shipping_address,
                'city': order.shipping_city,
                'postal_code': order.shipping_postal_code,
            } if order.shipping_country else {},
            'shipping_price': order.shipping_price,
            'total_price': order.total_price,
            'total_price_tax': order.total_price_tax,
            'credit_card': {
                'name': order.cc_name,
                'first_digits': order.cc_first_digits,
                'last_digits': order.cc_last_digits,
                'expiration_year': order.cc_expiration_year,
                'expiration_month': order.cc_expiration_month,
            } if order.cc_name else {},
            'transaction': {
                'id': order.transaction_id,
                'success': order.transaction_success,
                'amount_charged': order.transaction_amount_charged,
                'error': order.transaction_error,
            } if (order.transaction_id or order.transaction_error) else {},
        }
    }


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
                    'name': _clean(p['name']),
                    'type': _clean(p['type']),
                    'description': _clean(p['description']),
                    'image': _clean(p['image']),
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
    def create(products_list):
        if not products_list:
            raise ValueError('missing-fields')

        total_price = 0
        total_weight = 0
        validated_items = []

        for item in products_list:
            p_id = item.get('id')
            qty = item.get('quantity')
            if not p_id or qty is None or qty < 1:
                raise ValueError('missing-fields')

            product = ProductService.get_by_id(p_id)
            if product is None:
                raise ValueError('missing-fields')
            if not product.in_stock:
                raise ValueError('out-of-inventory')

            validated_items.append((product, qty))
            total_price += product.price * qty
            total_weight += product.weight * qty

        shipping_price = OrderService._calc_shipping(total_weight)

        order = Order.create(
            total_price=total_price,
            shipping_price=shipping_price,
            status='pending',
        )

        for product, qty in validated_items:
            OrderItem.create(
                order=order,
                product=product,
                quantity=qty,
            )

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

        order.email = email
        order.shipping_country = info['country']
        order.shipping_province = info['province']
        order.shipping_address = info['address']
        order.shipping_city = info['city']
        order.shipping_postal_code = info['postal_code']

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

    @staticmethod
    def process_payment(order_id, credit_card):
        db = Order._meta.database
        is_sqlite = db.__class__.__name__ == 'SqliteDatabase'

        def _execute():
            order = OrderService.get(order_id)
            if order is None:
                return

            if order.paid:
                return

            try:
                amount_charged = int(order.total_price_tax) + order.shipping_price
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
                order.status = 'paid'
                order.transaction_error = None
                order.save()

                try:
                    from cache import cache_order
                    cache_order(order.id, order_to_dict(order))
                except Exception as ce:
                    print(f"Redis cache error: {ce}")

            except urllib.error.HTTPError as e:
                try:
                    error_body = json.loads(e.read().decode())
                    err_msg = error_body.get('errors', {}).get('payment', {}).get('name', 'La carte a été déclinée')
                except Exception:
                    err_msg = "La carte a été déclinée"

                order.transaction_error = err_msg
                order.paid = False
                order.status = 'failed'
                order.save()
            except Exception as e:
                order.transaction_error = str(e)
                order.paid = False
                order.status = 'failed'
                order.save()

        if is_sqlite:
            _execute()
        else:
            with db.connection_context():
                _execute()

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







