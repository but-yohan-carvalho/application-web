# INF349 — Application Web de paiement de commandes

Travail de session — UQAC
Étudiants : Damien Dema Lima, Yohan D'Alvaringa Carvalho

API REST de paiement de commandes Internet : catalogue de produits, commandes
multi-produits, paiement par carte traité **en arrière-plan** (RQ), et cache de
**résilience** (Redis) permettant de consulter une commande payée même si la base
est indisponible.

## Stack

- Python 3.8+ / Flask
- **Peewee** (ORM) + **PostgreSQL 12**
- **RQ** + **Redis 5** (file de tâches + cache)
- HTTP externe via `urllib` (librairie standard)

## Démarrage avec Docker (recommandé)

```bash
# Lance Postgres, Redis, l'app (web) et le worker RQ
docker compose up -d --build

# Crée les tables + charge les produits depuis l'API externe (une seule fois)
docker compose run --rm web flask init-db
```

L'application est disponible sur `http://localhost:5001`.

## Démarrage local (sans Docker)

Nécessite un Postgres et un Redis accessibles. Connexion via variables
d'environnement :

```bash
SET FLASK_APP=api8inf349& SET REDIS_URL=redis://localhost& ^
SET DB_HOST=localhost& SET DB_USER=user& SET DB_PASSWORD=pass& ^
SET DB_PORT=5432& SET DB_NAME=api8inf349

pip install -r requirements.txt

flask init-db     # crée les tables + charge les produits
flask run         # lance l'API (port 5001)
flask worker      # dans un autre terminal : worker RQ (paiements asynchrones)
```

## Tests

```bash
pytest
pytest --cov=. tests/
```

## Structure

```
api8inf349.py   Point d'entrée Flask + commandes flask init-db / flask worker
models.py       Modèles Peewee : Product, Order, OrderItem
services.py     Logique métier : ProductService, OrderService, PaymentService
                + order_to_dict() (sérialisation) + process_payment() (tâche RQ)
cache.py        Accès Redis (cache des commandes payées)
routes.py       Endpoints REST + négociation HTML/JSON + mise en file RQ
templates/      Pages HTML (Jinja2) : catalogue, panier, commande, paiement
static/         CSS + JS (panier client, formulaires)
tests/          Suite de tests pytest
docs/           Diagrammes PlantUML (.puml) + PNG
Dockerfile          Image de l'application
docker-compose.yml  Postgres 12 + Redis 5 + web + worker
```

## Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Liste des produits (JSON ou HTML) |
| POST | `/order` | Créer une commande (mono- ou multi-produits) → 302 |
| GET | `/order/<id>` | Détail — **200** (payée/non), **202** (paiement en cours) |
| PUT | `/order/<id>` | Mettre à jour la livraison **ou** payer (carte) |

`POST /order` accepte les deux formats :

```json
{"products": [{"id": 1, "quantity": 2}, {"id": 3, "quantity": 1}]}
{"product": {"id": 1, "quantity": 1}}
```

**Paiement asynchrone** : `PUT /order/<id>` avec `credit_card` met le paiement en
file RQ et répond **202** (sans corps). Le worker effectue le paiement distant ;
`GET` renvoie **202** tant qu'il est en cours, puis **200** une fois payée. Un
`PUT` pendant le traitement renvoie **409**.

**Résilience** : une commande payée est persistée dans Postgres **et** mise en
cache Redis. `GET /order/<id>` lit Redis en premier et fonctionne même si
Postgres est éteint.

## Cartes de test

| Numéro | Résultat |
|--------|----------|
| `4242 4242 4242 4242` | Paiement accepté |
| `4000 0000 0000 0002` | Carte déclinée |
