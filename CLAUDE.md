# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Contexte du projet

Application Web REST de paiement de commandes Internet — Projet de session INF349, UQAC.
Première remise : 31 mai 2026 | Remise finale : 25 juin 2026

## Commandes essentielles

> **Remise finale : nom d'app `api8inf349`** (les commandes de correction utilisent `FLASK_APP=api8inf349`). Le fichier `.flaskenv` configure le dev local (`FLASK_DEBUG=True`, `FLASK_RUN_PORT=5001` — port 5000 réservé par Windows). `python-dotenv` doit être installé. Connexion DB/Redis via variables d'environnement (voir ci-dessous).

```bash
# Variables d'env (Postgres + Redis) — exemple correction
SET FLASK_APP=api8inf349& SET FLASK_DEBUG=True& SET REDIS_URL=redis://localhost& \
SET DB_HOST=localhost& SET DB_USER=user& SET DB_PASSWORD=pass& SET DB_PORT=5432& SET DB_NAME=api8inf349

# Créer les tables (ne crée PAS la base) + charger les produits depuis l'API externe
flask init-db

# Lancer l'application
flask run

# Lancer le worker RQ (exécution des paiements en arrière-plan)
flask worker          # ou : python -m flask worker

# Tests
pytest
pytest tests/test_routes.py::test_post_order_success
pytest --cov=. tests/

# Docker
docker build -t api8inf349 .
docker run -e REDIS_URL=redis://host.docker.internal -e DB_HOST=host.docker.internal \
  -e DB_USER=user -e DB_PASSWORD=pass -e DB_PORT=5432 -e DB_NAME=api8inf349 api8inf349
docker-compose up      # lance Postgres 12 + Redis 5
```

## Stack imposée

- **Python 3.6+** / **Flask 1.11+**
- **Peewee** (ORM) + **RQ** (gestionnaire de tâches, https://python-rq.org/)
- **PostgreSQL** (v12 en compose) — connexion via `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `DB_NAME`
- **Redis** (v5 en compose) — connexion via `REDIS_URL` (une seule variable)
- HTTP externe : utiliser `urllib.request` (librairie standard) — **`requests` est interdit**
- Hors Flask/peewee/RQ : aucune restriction de paquets, mais **tout doit être dans `requirements.txt`** (ajouter `psycopg2-binary`, `redis`, `rq`). Correction via `pip install -r requirements.txt`.
- Toutes les données doivent être stockées en base.

## Architecture en 3 couches

```
api8inf349.py     → point d'entrée Flask + CLI flask init-db + flask worker (RQ)
models.py         → modèles Peewee : Product, Order (+ ligne de commande multi-produits)
services.py       → logique métier : ProductService, OrderService, PaymentService
routes.py         → 4 endpoints REST + négociation HTML/JSON
tasks.py          → tâche RQ de paiement exécutée en arrière-plan par le worker
cache.py          → accès Redis (cache des commandes payées)
templates/        → templates Jinja2 (front-end HTML)
tests/            → pytest + pytest-flask
docs/             → diagrammes PlantUML (.puml) + PNG générés
Dockerfile        → image de l'app (sans Postgres/Redis)
docker-compose.yml→ Postgres 12 (volume, port 5432) + Redis 5 (port 6379)
CODES-PERMANENTS  → codes permanents, un par ligne
```

> Les noms `tasks.py`/`cache.py` sont indicatifs ; l'app doit être renommée/exposée sous `api8inf349`.

### Modèles (models.py)

**`Product`** — copie locale des produits récupérés depuis `dimensweb.uqac.ca/~jgnault/shops/products/` au `flask init-db`. Jamais re-fetchés à chaque requête.

**`Order`** — contient tout à plat : champs `shipping_*` (livraison), `cc_*` (carte de crédit retournée par le service distant), `transaction_*`. Les sous-objets `ShippingInformation`, `CreditCard`, `Transaction` existent comme classes Python dans `services.py` mais ne sont pas des tables séparées.

**Multi-produits (remise 2)** — une commande peut contenir plusieurs produits. Le champ unique `product` + `quantity` actuel doit devenir une **liste de lignes** `{id, quantity}` (table de jointure `OrderItem` ou stockage JSON en base — tout doit être stocké en base). `total_price`, `total_price_tax` et `shipping_price` se calculent sur l'ensemble des lignes (le poids total détermine le palier de livraison).

**Statut de paiement asynchrone** — prévoir un état « en cours de paiement » (ex. champ booléen `processing` ou présence d'un job RQ) pour distinguer 202 (en cours) de 200 (payée).

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
| GET | `/` | Liste tous les produits (JSON ou HTML selon `Accept`) |
| POST | `/order` | Crée une commande (mono- ou multi-produits) → 302 vers `/order/<id>` |
| GET | `/order/<id>` | Récupère une commande — **200** (payée/non), **202** (paiement en cours) |
| PUT | `/order/<id>` | Update shipping info OU paiement carte (deux appels distincts) |

**`POST /order`** accepte deux formats (rétrocompatibilité obligatoire) :
- `{"product": {"id": .., "quantity": ..}}` — ancien format mono-produit
- `{"products": [{"id": .., "quantity": ..}, ...]}` — nouveau format multi-produits

**`PUT /order/<id>`** distingue deux cas selon le body :
- `order` → update email + shipping_information (200)
- `credit_card` → **met le paiement en file RQ et retourne 202 sans corps**. Le worker (`flask worker`) exécute le paiement distant en arrière-plan.

**Codes de paiement asynchrone :**
- `PUT` avec `credit_card` accepté → **202 Accepted** (sans corps)
- `GET` pendant que le paiement tourne → **202 Accepted** (sans corps)
- `PUT` sur une commande en cours de paiement → **409 Conflict**
- Commande payée → **200 OK** avec le JSON complet (`paid: true`, `transaction`, `credit_card` avec `first_digits`/`last_digits`)
- Erreur du service distant → persistée dans `transaction.error`, `paid: false`, mais `GET` retourne quand même **200**

**Cache Redis (résilience) :** une commande payée est persistée dans Postgres **et** mise en cache dans Redis. `GET /order/<id>` lit Redis en premier ; si la commande est en cache, la route doit fonctionner **sans Postgres**.

La négociation de contenu (`_wants_html()`) permet à `GET /` et `GET /order/<id>` de retourner du HTML (templates Jinja2) quand le client envoie `Accept: text/html`, ou du JSON sinon.

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
| Carte déclinée (erreur service distant) | 200 GET | persistée dans `transaction.error` (`card-declined`), `paid: false` |
| Modifier une commande en cours de paiement | 409 | — |
| Commande inexistante | 404 | — |

> Note remise 2 : seules les **erreurs du service distant** (ex. carte déclinée) sont persistées et renvoyées avec un GET 200. Les erreurs de **validation client** (déjà payée, champs manquants) gardent leur comportement de la remise 1 (422).

## État actuel du projet

### Première remise (31 mai 2026) — complète
- [x] Diagrammes PlantUML dans `docs/` (classes + 6 séquences) + PNG générés
- [x] `inf349.py` — point d'entrée + `flask init-db`
- [x] `models.py` — Product, Order
- [x] `services.py` — ProductService, OrderService, PaymentService
- [x] `routes.py` — 4 endpoints REST + négociation HTML/JSON
- [x] `tests/` — 17 tests pytest (conftest.py + test_routes.py)
- [x] `requirements.txt`

### Remise finale (25 juin 2026) — en cours

Critères d'évaluation : Exigences techniques 25% · Docker 10% · Multi-produits 5% · Résilience 10% · Extraction paiement (RQ) 20% · Front-end HTML 10% · Qualité du code 10% · Présentation 10%.

- [x] **Postgres** — `models.py` : `PostgresqlDatabase` configuré via `DB_*` env vars (+ nettoyage NUL dans `ProductService._clean`)
- [ ] **Redis** — module de connexion via `REDIS_URL`
- [x] **Renommer l'app en `api8inf349`** (`api8inf349.py` + `.flaskenv` + `conftest.py`)
- [ ] **Multi-produits** — `POST /order` (liste `products` + rétrocompat mono-produit) + recalcul total/livraison + format `GET` adapté
- [ ] **Extraction paiement → RQ** — `flask worker`, `PUT credit_card` → 202, GET 202/200, PUT 409, erreur distante persistée (GET 200)
- [ ] **Cache Redis** — commande payée mise en cache ; `GET` lit Redis d'abord et fonctionne sans Postgres
- [ ] **Dockerfile** (`docker build -t api8inf349 .`)
- [x] **docker-compose.yml** — Postgres 12 (volume, 5432) + Redis 5 (6379)
- [ ] **`templates/`** — pages HTML pour chaque route (formulaires GET/POST)
- [ ] **`CODES-PERMANENTS`** à la racine (un code par ligne)
- [ ] **`requirements.txt`** — ajouter `psycopg2-binary`, `redis`, `rq`
- [ ] Ajouter `jgnault@uqac.ca` comme collaborateur du repo privé + remettre le lien sur Moodle
