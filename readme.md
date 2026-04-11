# Conception d’un Pipeline Big Data pour la Détection en Temps Réel de Fraudes Financières via l’IA et l’Analyse Prédictive sur Transactions Bancaires Massives

Ce dépôt illustre la mise en œuvre d’une chaîne **Big Data** orientée **flux** : ingestion de **transactions bancaires** à grande échelle (Kafka), **exploration** et **préparation** des données, et socle **IA / analyse prédictive** (machine learning, API) pour la **détection de fraude en temps réel**.

---

## Objectifs

- Ingérer des transactions (jeu **FraudShield** ou futur flux temps réel) vers **Kafka**.
- Analyser et préparer les données (notebooks, `pandas`, `scikit-learn`, `XGBoost`, etc.).
- Entraîner et servir un modèle de scoring (pickle / API REST prévue dans les dépendances).
- Architecture évolutive : producteur → Kafka → consommateur / service de détection (à étendre).

---

## Contenu actuel du dépôt

| Élément | Description |
|---------|-------------|
| `docs/FraudShield_Banking_Data.csv` | Données de transactions et étiquette fraude (référence FraudShield). |
| `notebooks/exploration.ipynb` | Chargement, EDA, nettoyage, imputation, features temporelles. |
| `Config/` | Paramètres Kafka partagés (brokers, **un seul topic** `KAFKA_TOPIC`) pour l’API et les scripts. |
| `kafka-cluster/` | Scripts CLI : producteur / consommateur Kafka, connecteur vers l’API (montés dans l’image API pour `docker compose exec`). |
| `simulateur/` | **CLI** + **API FastAPI** (génération JSON, Kafka) + `Dockerfile` pour Compose. |
| `docs/streaming.md` | Détail du streaming Kafka, variables d’environnement, commandes. |
| `docker-compose.yml` | **ZooKeeper + Kafka** (1 broker) + **Kafka UI** + **`simulateur-api`** (fichier unique à la racine). |
| `pyproject.toml` | Métadonnée du projet et liste des dépendances (pins). |
| `requirements.txt` | Installe le package en éditable + dépendances cœur. |
| `requirements-notebooks.txt` | Même chose + extra `[notebooks]` (JupyterLab, visualisation). |

---

## Architecture cible (vue d’ensemble)

1. **Producteur** — envoi des transactions vers Kafka (API simulateur, CLI `simulateur`, ou scripts `kafka-cluster/`).
2. **Kafka** — transport des événements (broker local + ZooKeeper via Docker Compose).
3. **Traitement / scoring** — consommateur Python, microservice, ou autre moteur (Flink, Kafka Streams…) qui lit le topic, enrichit et score.
4. **Modèle IA** — entraîné hors ligne ; chargé dans le service de scoring ou l’API REST.
5. **Sorties** — alertes, stockage, dashboard (à brancher selon le besoin).

---

## Technologies

- **Python** : `pandas`, `numpy`, `scikit-learn`, `imbalanced-learn`, `xgboost`
- **Notebooks** : JupyterLab
- **Streaming** : Apache Kafka (`kafka-python`), cluster Docker Compose
- **API** (optionnelle) : FastAPI, Uvicorn, Pydantic

---

## Prérequis

- **Docker** et **Docker Compose** (flux de travail principal)
- **Git**
- Python 3.10+ **facultatif** — uniquement si vous utilisez les notebooks Jupyter sur l’hôte

---

## Installation (facultatif, notebooks / outils hors Docker)

```bash
git clone <URL_DU_DEPOT>
cd bank-fraud-detection
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
pip install -r requirements.txt
```

Pour **Jupyter** et la visualisation :

```bash
pip install -r requirements-notebooks.txt
```

Le dépôt est conçu pour être utilisé **via Docker** ; un venv local reste utile surtout pour `notebooks/exploration.ipynb`.

---

## Démarrage rapide : tout dans Docker

1. **Lancer la stack**

   ```bash
   docker compose up -d --build
   ```

   - Depuis l’hôte : Kafka `localhost:9092`, ZooKeeper `localhost:2181`, **Kafka UI** [http://127.0.0.1:8080](http://127.0.0.1:8080), **API** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
   - Le premier build de l’image API peut être long.

   Sans reconstruire l’API :  
   `docker compose up -d zookeeper kafka kafka-ui simulateur-api`

   Les dossiers `simulateur/`, `Config/` et `kafka-cluster/` sont montés dans `simulateur-api` avec **`uvicorn --reload`**. Sur Docker Desktop, si le reload ne part pas, décommente `WATCHFILES_FORCE_POLLING` sous `simulateur-api` dans `docker-compose.yml`.

2. **Publier des transactions synthétiques** (dans le réseau Docker, brokers déjà configurés)

   ```bash
   docker compose exec simulateur-api python -m simulateur.transaction_simulator --kafka --count 50
   ```

   Flux continu (par défaut ~1 transaction / 5 s) :  
   `docker compose exec simulateur-api python -m simulateur.transaction_simulator --kafka --forever`

3. **Lire des messages** sur le topic (conteneur API, scripts sous `/app/kafka-cluster`)

   ```bash
   docker compose exec simulateur-api bash -lc "cd /app/kafka-cluster && python consumer.py --max 5"
   ```

   Suivi temps réel (Ctrl+C pour arrêter) :  
   `docker compose exec simulateur-api bash -lc "cd /app/kafka-cluster && python consumer.py --follow"`

4. **Producteur JSON d’exemple** (même conteneur)

   ```bash
   docker compose exec simulateur-api bash -lc "cd /app/kafka-cluster && python produceur.py --count 3"
   ```

Détails, variables d’environnement et format JSON : **[docs/streaming.md](docs/streaming.md)**. Un seul topic Kafka est défini par `KAFKA_TOPIC` (défaut `bank.transactions.raw`).

---

## Exploration des données

```bash
pip install -r requirements-notebooks.txt   # une fois, si ce n’est pas déjà fait
jupyter lab
```

Ouvrir `notebooks/exploration.ipynb` (chargement du CSV, EDA, nettoyage, etc.).

---

## Structure du dépôt

```text
bank-fraud-detection/
├── Config/                     # Config Kafka partagée (API simulateur)
├── simulateur/                 # CLI + API FastAPI + Dockerfile (image Compose)
├── kafka-cluster/              # Scripts : connecteur API, producteur / consommateur Kafka
├── docs/
│   ├── streaming.md            # Guide Kafka détaillé
│   └── FraudShield_Banking_Data.csv  # Données de référence (exemple)
├── notebooks/                  # Analyses (Jupyter)
├── docker-compose.yml          # ZooKeeper, Kafka (1 broker), Kafka UI, simulateur-api
├── pyproject.toml
├── requirements.txt
├── requirements-notebooks.txt
└── readme.md
```

---

## Ressources

- Plan de travail (Notion) : [PLAN COMPLET — étape par étape](https://yielding-attempt-7c9.notion.site/PLAN-COMPLET-tape-par-tape-322843a50877800dabc7c13d37ab6f4e?source=copy_link)
