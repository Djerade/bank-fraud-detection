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
| `pipeline/` | **Ingestion Kafka** : `csv_to_kafka.py`, `kafka_consume_sample.py`, `config.py` — voir [pipeline/README.md](pipeline/README.md). |
| `docker-compose.yml` | Cluster local **ZooKeeper + 3 brokers Kafka** (images Confluent Community). |
| `scripts/streaming/ingest_csv.sh` | Raccourci pour publier un extrait du CSV vers Kafka. |
| `requirements.txt` | `pandas`, ML, Jupyter, **kafka-python**, FastAPI / Uvicorn (API). |

---

## Architecture cible (vue d’ensemble)

1. **Producteur** — envoi des transactions vers Kafka (script `pipeline/csv_to_kafka.py`).
2. **Kafka** — transport des événements (cluster 3 brokers en local via Docker).
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

Les commandes ci-dessous supposent que le répertoire courant est la **racine du dépôt** (pour que `python -m pipeline...` résolve le package `pipeline`).

---

## Démarrage rapide : Kafka + ingestion

1. **Lancer le cluster Kafka**

   ```bash
   docker compose up -d
   ```

2. **Publier des transactions** (exemple : 2 000 lignes du CSV)

   ```bash
   export KAFKA_BOOTSTRAP_SERVERS=localhost:9092,localhost:9093,localhost:9094
   python -m pipeline.csv_to_kafka --max-rows 2000 --sleep-ms 1
   ```

3. **Vérifier des messages** sur le topic brut

   ```bash
   python -m pipeline.kafka_consume_sample --topic bank.transactions.raw --max 5
   ```

Détails, variables d’environnement et format JSON : **[pipeline/README.md](pipeline/README.md)**.

---

## Exploration des données

```bash
jupyter lab
```

Ouvrir `notebooks/exploration.ipynb` (chargement du CSV, EDA, nettoyage, etc.).

---

## Structure du dépôt

```text
bank-fraud-detection/
├── data/                      # Jeu FraudShield (CSV)
├── notebooks/                 # Analyses et préparation (Jupyter)
├── pipeline/                  # Ingestion Kafka + config + README
├── scripts/streaming/         # Scripts shell (ex. ingest_csv.sh)
├── docker-compose.yml         # ZooKeeper + 3 brokers Kafka
├── requirements.txt
└── readme.md                  # Ce fichier
```

---

## Ressources

- Plan de travail (Notion) : [PLAN COMPLET — étape par étape](https://yielding-attempt-7c9.notion.site/PLAN-COMPLET-tape-par-tape-322843a50877800dabc7c13d37ab6f4e?source=copy_link)
