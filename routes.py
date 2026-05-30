import json
import urllib.error
from flask import Blueprint, jsonify, request, redirect, url_for
from services import ProductService, OrderService

api = Blueprint('api', __name__)


@api.route('/')
def get_products():
    products = ProductService.get_all()
    return jsonify({
        'products': [
            {
                'id': p.id,
                'name': p.name,
                'type': p.type,
                'description': p.description,
                'image': p.image,
                'height': p.height,
                'weight': p.weight,
                'price': p.price,
                'in_stock': p.in_stock,
            }
            for p in products
        ]
    })


@api.route('/order', methods=['POST'])
def post_order():
    data = request.get_json(silent=True) or {}

    product_id = data.get('product', {}).get('id')
    quantity = data.get('product', {}).get('quantity')

    if not product_id or not quantity or quantity < 1:
        return jsonify({'errors': {'product': {'code': 'missing-fields', 'name': 'La création d\'une commande nécessite un produit'}}}), 422

    try:
        order = OrderService.create(product_id, quantity)
    except ValueError as e:
        code = str(e)
        return jsonify({'errors': {'product': {'code': code, 'name': code}}}), 422

    return redirect(url_for('api.get_order', order_id=order.id), code=302)


@api.route('/order/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = OrderService.get(order_id)

    if order is None:
        return jsonify({'errors': {'order': {'code': 'not-found', 'name': 'La commande n\'existe pas'}}}), 404

    return jsonify(_order_to_dict(order))


@api.route('/order/<int:order_id>', methods=['PUT'])
def put_order(order_id):
    data = request.get_json(silent=True) or {}

    if 'order' in data:
        order_data = data['order']
        email = order_data.get('email')
        shipping = order_data.get('shipping_information', {})

        if not email or not all([
            shipping.get('country'),
            shipping.get('province'),
            shipping.get('address'),
            shipping.get('city'),
            shipping.get('postal_code'),
        ]):
            return jsonify({'errors': {'order': {'code': 'missing-fields', 'name': 'Il manque un ou plusieurs champs qui sont nécessaires'}}}), 422

        order = OrderService.update_shipping(order_id, email, shipping)

        if order is None:
            return jsonify({'errors': {'order': {'code': 'not-found', 'name': 'La commande n\'existe pas'}}}), 404

        return jsonify(_order_to_dict(order))

    elif 'credit_card' in data:
        try:
            order = OrderService.apply_credit_card(order_id, data['credit_card'])
        except ValueError as e:
            code = str(e)
            return jsonify({'errors': {'order': {'code': code, 'name': code}}}), 422
        except urllib.error.HTTPError as e:
            error_body = json.loads(e.read().decode())
            return jsonify(error_body), 422

        if order is None:
            return jsonify({'errors': {'order': {'code': 'not-found', 'name': 'La commande n\'existe pas'}}}), 404

        return jsonify(_order_to_dict(order))

    return jsonify({'errors': {'order': {'code': 'missing-fields', 'name': 'Il manque un ou plusieurs champs qui sont nécessaires'}}}), 422


def _order_to_dict(order):
    return {
        'order': {
            'id': order.id,
            'product': {
                'id': order.product,
                'quantity': order.quantity,
            },
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
            } if order.transaction_id else {},
        }
    }