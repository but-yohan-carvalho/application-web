# GEMINI.md

Ce fichier sert de guide pour Gemini (et autres assistants IA) lors de l'implémentation et de la maintenance du projet de session de paiement de commandes.

## Contexte du Projet

Application Web REST de paiement de commandes Internet — Projet de session INF349, UQAC.
* **Remise finale :** 25 juin 2026
* **Nom de l'application :** `api8inf349`

---

## Commandes Essentielles

Pour exécuter l'application et les composants requis :

```bash
# Activation de l'environnement virtuel (Windows)
.venv\Scripts\activate

# Configuration des variables d'environnement (Développement local)
# Note : Port 5001 utilisé car le port 5000 est souvent réservé sur Windows
SET FLASK_APP=api8inf349
SET FLASK_DEBUG=True
SET REDIS_URL=redis://localhost:6379
SET DB_HOST=localhost
SET DB_USER=user
SET DB_PASSWORD=pass
SET DB_PORT=5432
SET DB_NAME=api8inf349

# Initialisation de la base de données et chargement des produits
flask init-db

# Lancement du serveur de développement Flask (sur le port 5001 défini dans .flaskenv)
flask run

# Lancement du worker RQ pour traiter les paiements en arrière-plan
flask worker

# Exécution des tests unitaires et de couverture
pytest
pytest tests/test_routes.py::test_post_order_success
pytest --cov=. tests/

# Docker et Docker Compose
docker-compose up -d       # Lance Postgres 12 et Redis 5 en arrière-plan
docker build -t api8inf349 .
```

---

## Stack Technique & Règles Strictes

1. **Langage & Framework :** Python 3.6+ et Flask 1.11+.
2. **Base de Données & ORM :** PostgreSQL (v12) avec l'ORM **Peewee**.
3. **Tâches Asynchrones :** **RQ** (Redis Queue) pour le worker de paiement en arrière-plan.
4. **Cache :** **Redis** (v5) via la variable `REDIS_URL` pour la mise en cache des commandes payées.
5. **Appels HTTP Externes :** Utiliser **uniquement** `urllib.request` de la bibliothèque standard Python. **L'usage de la bibliothèque `requests` est strictement interdit.**
6. **Dépendances :** Toutes les dépendances doivent figurer dans `requirements.txt`.
7. **Négociation de contenu :** Les routes `GET /` et `GET /order/<id>` doivent renvoyer du HTML si le client demande `Accept: text/html`, ou du JSON par défaut.

---

## État d'Avancement & Prochaines Étapes (TODO)

Voici la suite détaillée des tâches à réaliser pour la remise finale :

### 1. Intégration de Redis & Configuration du Cache [ ]
- [ ] Installer le paquet `redis` et l'ajouter à `requirements.txt`.
- [ ] Créer un module ou une classe de connexion Redis (par exemple `cache.py`) lisant la variable d'environnement `REDIS_URL`.
- [ ] S'assurer que la connexion se fait proprement et gère les cas d'indisponibilité.

### 2. Refactorisation en Multi-produits [ ]
- [ ] **Modèle de données :** Modifier le modèle d'une commande (`Order`) dans `models.py`. Le champ unique `product` + `quantity` doit être remplacé par un système gérant plusieurs lignes de produits (par exemple, une table de jointure `OrderItem` reliée à `Order` et `Product` ou un stockage JSON en base). Tout doit être stocké en base Postgres.
- [ ] **Création de commande (`POST /order`) :**
  - Gérer le format multi-produits : `{"products": [{"id": X, "quantity": Y}, ...]}`.
  - Assurer la rétrocompatibilité avec l'ancien format : `{"product": {"id": X, "quantity": Y}}`.
- [ ] **Logique métier :**
  - Ajuster les calculs des prix dans `OrderService`.
  - **Frais de livraison :** Calculer le poids total cumulé de tous les produits commandés.
    - `< 500g` $\rightarrow$ 500 cents (5$)
    - `< 2000g` $\rightarrow$ 1000 cents (10$)
    - `>= 2000g` $\rightarrow$ 2500 cents (25$)
  - **Taxes :** Calculer les taxes sur le prix total cumulé selon la province de destination (QC: 15%, ON: 13%, AB: 5%, BC: 12%, NS: 14%).
- [ ] **Affichage / API :** Ajuster le format de retour du `GET` pour exposer la liste des produits commandés.

### 3. Traitement Asynchrone des Paiements avec RQ [ ]
- [ ] Installer le paquet `rq` et l'ajouter à `requirements.txt`.
- [ ] Configurer un worker RQ. La commande `flask worker` doit démarrer le worker écoutant sur la file par défaut.
- [ ] **Comportement des routes et du service :**
  - Lors d'un `PUT /order/<id>` contenant un objet `credit_card`, la tâche de paiement doit être mise dans la file RQ en arrière-plan.
  - La route `PUT` doit immédiatement renvoyer un statut **202 Accepted** (sans corps).
  - Pendant le traitement du paiement, un `GET /order/<id>` doit retourner un statut **202 Accepted** (sans corps).
  - Pendant le traitement, si un autre `PUT /order/<id>` est reçu sur cette commande, retourner un **409 Conflict**.
  - Une fois le paiement complété avec succès par le worker :
    - Enregistrer les informations de transaction et de carte (masquée) en base.
    - Mettre à jour le statut `paid: true`.
    - La route `GET /order/<id>` doit alors renvoyer **200 OK** avec le JSON complet de la commande.
  - Si le paiement échoue (ex: carte déclinée par le service distant avec une erreur HTTP/422) :
    - Persister l'erreur dans le champ `transaction.error` de la commande et mettre `paid: false`.
    - Le statut de la commande passe de "en cours de traitement" à "terminé en échec", et le `GET` subséquent retourne **200 OK** avec le JSON contenant l'erreur persistée.

### 4. Cache de Résilience Redis [ ]
- [ ] Lors de la finalisation d'un paiement (succès), enregistrer la commande finalisée en format JSON dans Redis.
- [ ] Modifier `GET /order/<id>` pour interroger Redis en premier.
- [ ] **Résilience :** Si la commande est trouvée dans le cache Redis, la route doit retourner la commande avec un succès 200 **sans faire aucune requête à PostgreSQL**. L'application doit continuer à servir les commandes payées même si la base Postgres est arrêtée ou inaccessible.

### 5. Conteneurisation (Dockerfile & Docker Compose) [ ]
- [ ] Créer un `Dockerfile` optimisé pour l'application Flask et son worker.
- [ ] Ajuster le fichier `docker-compose.yml` pour inclure :
  - Un conteneur PostgreSQL 12 avec un volume persistant.
  - Un conteneur Redis 5.
  - Un conteneur pour l'application Flask `api8inf349` fonctionnant sur le port 5001.
  - Un conteneur pour le worker RQ.
- [ ] Valider que tout démarre avec un simple `docker-compose up`.

### 6. Templates HTML Jinja2 (Front-end) [ ]
- [ ] Développer/améliorer les templates dans `templates/` pour permettre une navigation graphique :
  - **Accueil (`/`) :** Formulaire/Boutons pour ajouter un produit à une commande, liste des produits.
  - **Détail Commande (`/order/<id>`) :** Interface affichant le statut de la commande (en cours, payée, en attente d'infos), formulaire pour renseigner les informations de livraison, et formulaire pour saisir la carte de crédit et soumettre le paiement.
- [ ] Assurer la bonne intégration de la négociation de contenu pour servir ces pages quand demandées.

### 7. Finalisation & Livrables administratifs [ ]
- [ ] Créer le fichier `CODES-PERMANENTS` à la racine contenant les codes permanents des membres de l'équipe (un par ligne).
- [ ] Mettre à jour le fichier `requirements.txt` avec toutes les dépendances finales installées.
- [ ] Mettre à jour la suite de tests unitaires dans `tests/` pour couvrir les nouveaux comportements :
  - Multi-produits
  - Statuts 202, 409 et persistence des erreurs
  - Cache Redis et résilience
- [ ] Ajouter l'enseignant (`jgnault@uqac.ca`) comme collaborateur du dépôt Git privé.
