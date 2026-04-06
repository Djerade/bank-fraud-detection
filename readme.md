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
| `data/FraudShield_Banking_Data.csv` | Données de transactions et étiquette fraude. |
| `notebooks/exploration.ipynb` | Chargement, EDA, nettoyage, imputation, features temporelles. |
| `src/bank_fraud_detection/` | Package Python : `config`, `streaming/` (producteurs CSV/JSONL, consommateur) — **sans** code de simulation. |
| `simulateur/` | **CLI** + **API FastAPI** (génération JSON, Kafka) + `Dockerfile` pour Compose. |
| `docs/streaming.md` | Détail du streaming Kafka, variables d’environnement, commandes. |
| `docker-compose.yml` | **ZooKeeper + Kafka** (3 brokers) + **Kafka UI** + **`simulateur-api`** (fichier unique à la racine). |
| `scripts/streaming/ingest_csv.sh` | Raccourci pour publier un extrait du CSV vers Kafka. |
| `pyproject.toml` | Métadonnée du projet et liste des dépendances (pins). |
| `requirements.txt` | Installe le package en éditable + dépendances cœur. |
| `requirements-notebooks.txt` | Même chose + extra `[notebooks]` (JupyterLab, visualisation). |

---

## Architecture cible (vue d’ensemble)

1. **Producteur** — envoi des transactions vers Kafka (`bank_fraud_detection.streaming.csv_to_kafka`).
2. **Kafka** — transport des événements (cluster local 3 brokers + ZooKeeper via Docker Compose).
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

- Python 3.10+ recommandé  
- Docker et Docker Compose  
- Git

---

## Installation

```bash
git clone <URL_DU_DEPOT>
cd bank-fraud-detection
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
# ou : .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Cela installe en mode éditable **`bank_fraud_detection`** (`src/`) et le package **`simulateur/`** (CLI + API). Pour **Jupyter** et la visualisation :

```bash
pip install -r requirements-notebooks.txt
```

Les modules `python -m bank_fraud_detection...` et `python -m simulateur...` sont disponibles après installation (`pip install -e .` équivaut à `requirements.txt` seul). Sans installation : préfixer avec `PYTHONPATH=src:.` depuis la racine du dépôt.

---

## Démarrage rapide : Kafka + ingestion

1. **Lancer Kafka (et optionnellement l’API simulateur)**

   ```bash
   docker compose up -d --build
   ```

   - Kafka (hôte) : `localhost:9092`, `9093`, `9094` ; ZooKeeper : `localhost:2181` ; **Kafka UI** : [http://127.0.0.1:8080](http://127.0.0.1:8080)
   - Swagger de l’API : [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
   Le premier build de l’image API peut être long (dépendances du `pyproject.toml`).

   Kafka + ZooKeeper + UI sans reconstruire l’API :  
   `docker compose up -d zookeeper kafka-1 kafka-2 kafka-3 kafka-ui`

   Le `docker-compose.yml` monte `simulateur/` et `src/bank_fraud_detection/` dans le conteneur avec **`uvicorn --reload`** : en enregistrant un `.py` dans ces dossiers, l’API redémarre (voir les logs). Sur Docker Desktop, si le reload ne part pas, décommente `WATCHFILES_FORCE_POLLING` sous `simulateur-api` dans le même fichier.

2. **Publier des transactions** (exemple : 2 000 lignes du CSV)

   ```bash
   export KAFKA_BOOTSTRAP_SERVERS=localhost:9092,localhost:9093,localhost:9094
   python -m bank_fraud_detection.streaming.csv_to_kafka --max-rows 2000 --sleep-ms 1
   ```

3. **Vérifier des messages** sur le topic brut

   ```bash
   python -m bank_fraud_detection.streaming.kafka_consume_sample --max 5
   ```

   **Temps réel** (affichage au fil de l’eau, Ctrl+C pour arrêter) :  
   `python -m bank_fraud_detection.streaming.kafka_consume_sample --follow`

4. **(Optionnel)** Simuler des transactions synthétiques

   ```bash
   python -m simulateur.transaction_simulator --kafka --forever
   # (par défaut : 1 transaction / 5 s ; --interval-seconds 0 pour enchaîner sans pause)
   ```

Détails, variables d’environnement et format JSON : **[docs/streaming.md](docs/streaming.md)**.

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
├── src/
│   └── bank_fraud_detection/   # Package installable
│       ├── config.py           # Kafka, chemins, mapping CSV → JSON
│       └── streaming/          # Producteurs CSV/JSONL, consommateur Kafka
├── simulateur/                 # CLI + API FastAPI + Dockerfile (image Compose)
├── docs/
│   └── streaming.md            # Guide Kafka détaillé
├── data/                       # Jeu FraudShield (CSV)
├── notebooks/                  # Analyses (Jupyter)
├── kafka-cluster/              # Scripts démo : connecteur API, producteur / consommateur Kafka
├── scripts/streaming/          # Raccourcis shell (ex. ingest_csv.sh)
├── docker-compose.yml          # ZooKeeper, Kafka x3, Kafka UI, simulateur-api
├── pyproject.toml
├── requirements.txt
├── requirements-notebooks.txt
└── readme.md
```

---

## Ressources

- Plan de travail (Notion) : [PLAN COMPLET — étape par étape](https://yielding-attempt-7c9.notion.site/PLAN-COMPLET-tape-par-tape-322843a50877800dabc7c13d37ab6f4e?source=copy_link)
