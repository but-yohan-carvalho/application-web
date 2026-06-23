# INF349 — Application Web de paiement de commandes

Travail de session — UQAC  
Étudiants : Damien Dema Lima, Yohan D'Alvaringa Carvalho

## Prérequis

- Python 3.9+
- pip

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
```

## Démarrage

```bash
# 1. Initialiser la base de données (à faire une seule fois)
flask init-db

# 2. Lancer l'application (port 5001)
flask run
```

L'API est disponible sur `http://localhost:5001`.

## Tests

```bash
pytest
```

## Structure

```
inf349.py       Point d'entrée Flask + commande init-db
models.py       Modèles Peewee : Product, Order
services.py     Logique métier : ProductService, OrderService, PaymentService
routes.py       4 endpoints REST
templates/      Pages HTML (Jinja2)
tests/          Suite de tests pytest
docs/           Diagrammes PlantUML + PNG
```

## Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Liste des produits |
| POST | `/order` | Créer une commande |
| GET | `/order/<id>` | Détail d'une commande |
| PUT | `/order/<id>` | Mettre à jour livraison ou payer |

Les routes `GET /` et `GET /order/<id>` retournent du HTML si le client envoie `Accept: text/html`, sinon du JSON.

## Cartes de test

| Numéro | Résultat |
|--------|----------|
| `4242 4242 4242 4242` | Paiement accepté |
| `4000 0000 0000 0002` | Carte déclinée |