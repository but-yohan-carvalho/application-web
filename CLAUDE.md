# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Contexte du projet

Application Web REST de paiement de commandes Internet — Projet de session INF349, UQAC.
Première remise : 31 mai 2026 | Remise finale : 25 juin 2026

## Commandes essentielles

Le fichier `.flaskenv` à la racine configure automatiquement `FLASK_APP=inf349`, `FLASK_DEBUG=True` et `FLASK_RUN_PORT=5001` (port 5000 réservé par Windows sur cette machine). `python-dotenv` doit être installé.

```bash
# Initialiser la base de données et charger les produits depuis l'API externe
flask init-db

# Lancer l'application (port 5001)
flask run

# Lancer tous les tests
pytest

# Lancer un test précis
pytest tests/test_routes.py::test_post_order_success

# Lancer les tests avec couverture
pytest --cov=. tests/
```

## Stack imposée

- **Python 3.6+** / **Flask**
- **Peewee** (ORM) — pas SQLAlchemy
- **SQLite** — fichier `database.db` à la racine (ignoré par git)
- Paquets autorisés : `flask`, `pytest`, `pytest-flask`, `peewee` uniquement
- HTTP externe : utiliser `urllib.request` (librairie standard) — **`requests` est interdit**

## Architecture en 3 couches

```
inf349.py       → point d'entrée Flask + commande CLI flask init-db
models.py       → modèles Peewee : Product, Order
services.py     → logique métier : ProductService, OrderService, PaymentService
routes.py       → 4 endpoints REST (importé dans inf349.py)
tests/          → pytest + pytest-flask
docs/           → diagrammes PlantUML (.puml)
```

### Modèles (models.py)

**`Product`** — copie locale des produits récupérés depuis `dimensweb.uqac.ca/~jgnault/shops/products/` au `flask init-db`. Jamais re-fetchés à chaque requête.

**`Order`** — contient tout à plat : champs `shipping_*` (livraison), `cc_*` (carte de crédit retournée par le service distant), `transaction_*`. Les sous-objets `ShippingInformation`, `CreditCard`, `Transaction` existent comme classes Python dans `services.py` mais ne sont pas des tables séparées.

### Services (services.py)

- **`ProductService`** : `fetch_and_store()` (init uniquement), `get_all()`, `get_by_id(id)`
- **`OrderService`** : `create()`, `get()`, `update_shipping()`, `apply_credit_card()` + méthodes privées de calcul
- **`PaymentService`** : `charge(credit_card, amount_charged)` → appel `urllib` vers l'API distante

### Calculs métier

```python
# Frais de livraison (en cents)
< 500g   → 500   (5$)
< 2000g  → 1000  (10$)
>= 2000g → 2500  (25$)

# Taxes par province
QC=15%  ON=13%  AB=5%  BC=12%  NS=14%

# amount_charged envoyé au service de paiement = total_price_tax + shipping_price
```

## API REST

| Méthode | Route | Description |
|---|---|---|
| GET | `/` | Liste tous les produits |
| POST | `/order` | Crée une commande → 302 vers `/order/<id>` |
| GET | `/order/<id>` | Récupère une commande |
| PUT | `/order/<id>` | Update shipping info OU paiement carte (deux appels distincts) |

Le `PUT /order/<id>` distingue deux cas selon le body reçu :
- Body contient `order` → update email + shipping_information
- Body contient `credit_card` → appel au service de paiement distant

## Service de paiement distant

```
POST https://dimensweb.uqac.ca/~jgnault/shops/pay/
Body: { "credit_card": {...}, "amount_charged": <int en cents> }
```

Cartes de test : `4242 4242 4242 4242` (valide) | `4000 0000 0000 0002` (déclinée)

## Codes d'erreur attendus

| Situation | HTTP | code |
|---|---|---|
| Champs product/quantity manquants ou quantity < 1 | 422 | `missing-fields` |
| Produit hors stock | 422 | `out-of-inventory` |
| Champs email/shipping manquants au PUT | 422 | `missing-fields` |
| Commande déjà payée | 422 | `already-paid` |
| Carte déclinée | 422 | `card-declined` |
| Commande inexistante | 404 | — |

## État actuel du projet

- [x] Diagrammes PlantUML dans `docs/` (classes + 6 séquences)
- [x] `inf349.py` — point d'entrée + `flask init-db`
- [x] `models.py` — Product, Order
- [x] `services.py` — ProductService, OrderService, PaymentService
- [x] `routes.py` — 4 endpoints
- [ ] `tests/` — pytest (à faire)
