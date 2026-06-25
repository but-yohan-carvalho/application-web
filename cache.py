import json
import os

import redis

# Connexion Redis via une seule variable d'environnement (REDIS_URL).

_client = redis.from_url(
    os.environ.get('REDIS_URL', 'redis://localhost:6379'),
    decode_responses=True,
)


def _key(order_id):
    return 'order:{}'.format(order_id)


def cache_order(order_id, order_dict):
    """Stocke une commande payée dans Redis

    Tolérant aux pannes : si Redis est indisponible, on n'interrompt
    """
    try:
        _client.set(_key(order_id), json.dumps(order_dict))
        return True
    except redis.RedisError:
        return False


def get_cached_order(order_id):
    """Récupère une commande depuis le cache Redis.

    Retourne le dict de la commande si présente, sinon None.
    En cas de panne Redis, retourne None pour basculer sur Postgres.
    """
    try:
        raw = _client.get(_key(order_id))
    except redis.RedisError:
        return None

    if raw is None:
        return None
    return json.loads(raw)
