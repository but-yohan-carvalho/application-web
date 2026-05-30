import json
import urllib.error
from unittest.mock import patch


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

def test_get_products_empty(client):
    # Act
    resp = client.get('/')

    # Assert
    assert resp.status_code == 200
    assert resp.get_json() == {'products': []}


def test_get_products(client, sample_product):
    # Act
    resp = client.get('/')

    # Assert
    assert resp.status_code == 200
    products = resp.get_json()['products']
    assert len(products) == 1
    assert products[0]['id'] == 1
    assert products[0]['name'] == 'Test Product'
    assert products[0]['in_stock'] is True


# ---------------------------------------------------------------------------
# POST /order
# ---------------------------------------------------------------------------

def test_post_order_success(client, sample_product):
    # Act
    resp = client.post('/order', json={'product': {'id': 1, 'quantity': 2}})

    # Assert
    assert resp.status_code == 302


def test_post_order_missing_product_field(client):
    # Act
    resp = client.post('/order', json={})

    # Assert
    assert resp.status_code == 422
    assert resp.get_json()['errors']['product']['code'] == 'missing-fields'


def test_post_order_missing_quantity(client, sample_product):
    # Act
    resp = client.post('/order', json={'product': {'id': 1}})

    # Assert
    assert resp.status_code == 422
    assert resp.get_json()['errors']['product']['code'] == 'missing-fields'


def test_post_order_quantity_zero(client, sample_product):
    # Act
    resp = client.post('/order', json={'product': {'id': 1, 'quantity': 0}})

    # Assert
    assert resp.status_code == 422
    assert resp.get_json()['errors']['product']['code'] == 'missing-fields'


def test_post_order_out_of_stock(client, out_of_stock_product):
    # Act
    resp = client.post('/order', json={'product': {'id': 2, 'quantity': 1}})

    # Assert
    assert resp.status_code == 422
    assert resp.get_json()['errors']['product']['code'] == 'out-of-inventory'


# ---------------------------------------------------------------------------
# GET /order/<id>
# ---------------------------------------------------------------------------

def test_get_order_success(client, sample_product):
    # Arrange
    post = client.post('/order', json={'product': {'id': 1, 'quantity': 1}},
                    follow_redirects=True)
    order_id = post.get_json()['order']['id']

    # Act
    resp = client.get(f'/order/{order_id}')

    # Assert
    assert resp.status_code == 200
    data = resp.get_json()['order']
    assert data['id'] == order_id
    assert data['product']['id'] == 1
    assert data['paid'] is False


def test_get_order_not_found(client):
    # Act
    resp = client.get('/order/9999')

    # Assert
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /order/<id> — shipping
# ---------------------------------------------------------------------------

VALID_SHIPPING = {
    'email': 'test@example.com',
    'shipping_information': {
        'country': 'Canada',
        'province': 'QC',
        'address': '123 Rue Test',
        'city': 'Chicoutimi',
        'postal_code': 'G7H 0A1',
    }
}


def test_put_order_shipping_success(client, sample_product):
    # Arrange
    post = client.post('/order', json={'product': {'id': 1, 'quantity': 1}},
                    follow_redirects=True)
    order_id = post.get_json()['order']['id']

    # Act
    resp = client.put(f'/order/{order_id}', json={'order': VALID_SHIPPING})

    # Assert
    assert resp.status_code == 200
    data = resp.get_json()['order']
    assert data['email'] == 'test@example.com'
    assert data['shipping_information']['province'] == 'QC'
    assert data['shipping_price'] == 500
    assert data['total_price'] == 1000
    assert data['total_price_tax'] == 1150.0  # 1000 * 1.15


def test_put_order_shipping_missing_fields(client, sample_product):
    # Arrange
    post = client.post('/order', json={'product': {'id': 1, 'quantity': 1}},
                        follow_redirects=True)
    order_id = post.get_json()['order']['id']

    # Act
    resp = client.put(f'/order/{order_id}', json={'order': {'email': 'test@example.com'}})

    # Assert
    assert resp.status_code == 422
    assert resp.get_json()['errors']['order']['code'] == 'missing-fields'


def test_put_order_shipping_not_found(client):
    # Act
    resp = client.put('/order/9999', json={'order': VALID_SHIPPING})

    # Assert
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /order/<id> — paiement
# ---------------------------------------------------------------------------

VALID_CARD = {
    'name': 'John Doe',
    'number': '4242 4242 4242 4242',
    'expiration_year': 2027,
    'expiration_month': 12,
    'cvv': '123',
}

MOCK_TRANSACTION = {
    'credit_card': {
        'name': 'John Doe',
        'first_digits': '4242',
        'last_digits': '4242',
        'expiration_year': 2027,
        'expiration_month': 12,
    },
    'transaction': {
        'id': 'txn-abc123',
        'success': True,
        'amount_charged': 1650,
    }
}


def test_put_order_payment_success(client, sample_product):
    # Arrange
    post = client.post('/order', json={'product': {'id': 1, 'quantity': 1}},
                        follow_redirects=True)
    order_id = post.get_json()['order']['id']
    client.put(f'/order/{order_id}', json={'order': VALID_SHIPPING})

    # Act
    with patch('services.PaymentService.charge', return_value=MOCK_TRANSACTION):
        resp = client.put(f'/order/{order_id}', json={'credit_card': VALID_CARD})

    # Assert
    assert resp.status_code == 200
    data = resp.get_json()['order']
    assert data['paid'] is True
    assert data['transaction']['success'] is True
    assert data['credit_card']['last_digits'] == '4242'


def test_put_order_already_paid(client, sample_product):
    # Arrange
    post = client.post('/order', json={'product': {'id': 1, 'quantity': 1}},
                        follow_redirects=True)
    order_id = post.get_json()['order']['id']
    client.put(f'/order/{order_id}', json={'order': VALID_SHIPPING})
    with patch('services.PaymentService.charge', return_value=MOCK_TRANSACTION):
        client.put(f'/order/{order_id}', json={'credit_card': VALID_CARD})

    # Act
    with patch('services.PaymentService.charge', return_value=MOCK_TRANSACTION):
        resp = client.put(f'/order/{order_id}', json={'credit_card': VALID_CARD})

    # Assert
    assert resp.status_code == 422
    assert resp.get_json()['errors']['order']['code'] == 'already-paid'


def test_put_order_card_declined(client, sample_product):
    # Arrange
    post = client.post('/order', json={'product': {'id': 1, 'quantity': 1}},
                    follow_redirects=True)
    order_id = post.get_json()['order']['id']
    client.put(f'/order/{order_id}', json={'order': VALID_SHIPPING})

    declined_body = json.dumps({
        'errors': {'payment': {'code': 'card-declined', 'name': 'La carte a été déclinée'}}
    }).encode()
    http_error = urllib.error.HTTPError(url='', code=422, msg='Unprocessable', hdrs={}, fp=None)
    http_error.read = lambda: declined_body

    # Act
    with patch('services.PaymentService.charge', side_effect=http_error):
        resp = client.put(f'/order/{order_id}', json={'credit_card': VALID_CARD})

    # Assert
    assert resp.status_code == 422
    assert resp.get_json()['errors']['payment']['code'] == 'card-declined'


def test_put_order_payment_without_shipping(client, sample_product):
    # Arrange
    post = client.post('/order', json={'product': {'id': 1, 'quantity': 1}},
                       follow_redirects=True)
    order_id = post.get_json()['order']['id']

    # Act — payer sans avoir fourni email/shipping
    resp = client.put(f'/order/{order_id}', json={'credit_card': VALID_CARD})

    # Assert
    assert resp.status_code == 422
    assert resp.get_json()['errors']['order']['code'] == 'missing-fields'


def test_put_order_payment_not_found(client):
    # Act
    resp = client.put('/order/9999', json={'credit_card': VALID_CARD})

    # Assert
    assert resp.status_code == 404