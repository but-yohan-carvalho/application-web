import os
from flask import Blueprint, jsonify, request, redirect, url_for, render_template, current_app
from redis import Redis
from rq import Queue
from services import ProductService, OrderService, order_to_dict
from cache import get_cached_order

api = Blueprint('api', __name__)


# Alias : la sérialisation vit désormais dans services .
_order_to_dict = order_to_dict


def _enqueue_payment(order_id, credit_card):
    """Met le paiement en file RQ (ou l'exécute en synchrone pendant les tests).

    """
    if current_app.testing:
        OrderService.process_payment(order_id, credit_card)
        return
    redis_conn = Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
    Queue(connection=redis_conn).enqueue(OrderService.process_payment, order_id, credit_card)


def _wants_html():
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    return best == 'text/html'


@api.route('/')
def get_products():
    products = ProductService.get_all()

    if _wants_html():
        return render_template('index.html', products=products)

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

    products = data.get('products')
    old_product = data.get('product')

    if not products and old_product:
        p_id = old_product.get('id')
        qty = old_product.get('quantity')
        if p_id and qty:
            products = [{'id': p_id, 'quantity': qty}]

    if not products or not isinstance(products, list):
        return jsonify({'errors': {'product': {'code': 'missing-fields', 'name': 'La création d\'une commande nécessite un produit'}}}), 422

    _product_error_names = {
        'out-of-inventory': "Le produit demandé n'est pas en inventaire",
        'missing-fields': "La création d'une commande nécessite un produit",
    }

    try:
        order = OrderService.create(products)
    except ValueError as e:
        code = str(e)
        name = _product_error_names.get(code, code)
        return jsonify({'errors': {'product': {'code': code, 'name': name}}}), 422

    return redirect(url_for('api.get_order', order_id=order.id), code=302)


@api.route('/order/<int:order_id>', methods=['GET'])
def get_order(order_id):


    cached = get_cached_order(order_id)
    if cached is not None:
        if _wants_html():

            items = []
            try:
                for line in cached['order'].get('products', []):
                    items.append({
                        'product': ProductService.get_by_id(line['id']),
                        'quantity': line['quantity'],
                    })
            except Exception:
                items = []
            return render_template('order.html', order=cached['order'], items=items)
        return jsonify(cached)

    order = OrderService.get(order_id)

    if order is None:
        if _wants_html():
            return render_template('error.html', message="Commande introuvable"), 404
        return jsonify({'errors': {'order': {'code': 'not-found', 'name': 'La commande n\'existe pas'}}}), 404

    if order.status == 'processing':
        if _wants_html():
            return render_template('processing.html', order_id=order_id), 202
        return '', 202

    if _wants_html():
        items_data = [
            {
                'product': ProductService.get_by_id(item.product_id),
                'quantity': item.quantity
            }
            for item in order.items
        ]
        return render_template('order.html', order=_order_to_dict(order)['order'], items=items_data)

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
        order = OrderService.get(order_id)

        if order is None:
            return jsonify({'errors': {'order': {'code': 'not-found', 'name': 'La commande n\'existe pas'}}}), 404

        if order.paid:
            return jsonify({'errors': {'order': {'code': 'already-paid', 'name': 'La commande a déjà été payée.'}}}), 422

        # Paiement déjà en cours → conflit.
        if order.status == 'processing':
            return jsonify({'errors': {'order': {'code': 'conflict', 'name': 'Un paiement est déjà en cours pour cette commande.'}}}), 409

        if not order.email or not order.shipping_country:
            return jsonify({'errors': {'order': {'code': 'missing-fields', 'name': "Les informations du client sont nécessaires avant d'appliquer une carte de crédit"}}}), 422

        # Paiement asynchrone : on marque la commande « en cours », on met la
        # tâche en file RQ, puis on répond 202 sans corps.
        order.status = 'processing'
        order.save()
        _enqueue_payment(order_id, data['credit_card'])
        return '', 202

    return jsonify({'errors': {'order': {'code': 'missing-fields', 'name': 'Il manque un ou plusieurs champs qui sont nécessaires'}}}), 422