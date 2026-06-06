---
name: project-overview
description: Architecture complète du pipeline Big Data de détection de fraude bancaire en temps réel
metadata:
  type: project
---

Pipeline Big Data pour la détection de fraude financière en temps réel sur transactions bancaires massives.

**Why:** Projet académique/professionnel alliant streaming, ML et visualisation temps réel.

**Stack technique :**
- **Données :** Dataset FraudShield (50 000 transactions, 25 colonnes), CSV clean + features pré-calculées
- **Ingestion :** Apache Kafka (1 broker + ZooKeeper, topic `bank.transactions.raw`)
- **Simulateur :** FastAPI (`simulateur/`) + CLI → génère des transactions synthétiques JSON
- **ML :** scikit-learn (RandomForest, XGBoost-like, Logistic Regression…) entraîné via `fraud_detection/train.py`, tracé avec MLflow
- **Scoring temps réel :** `fraud_scoring/kafka_scorer.py` — consomme le topic brut, score avec le joblib, publie sur `bank.transactions.scored`
- **Architecture Lambda :** Spark speed layer (streaming bronze) + batch layer (agrégats gold) — `spark_lambda/`
- **Dashboard :** Next.js (`fraud_dashboard/next-dashboard/`) → port 3000
- **MLflow UI :** port 5000, artefacts dans volume Docker `mlflow-data`

**Ports exposés :**
- 8000 → API simulateur (FastAPI)
- 8080 → Kafka UI
- 3000 → Dashboard Next.js
- 5000 → MLflow
- 9092 → Kafka broker (hôte)

**Modèle :** `models/fraud_classifier.joblib` (meilleur modèle selon ROC-AUC + F1, auto-entraîné au premier `docker compose up`)

**Feature engineering :** `fraud_scoring/features.py` — aligné sur `notebooks/exploration.ipynb` (features temporelles, ratios, encodage cyclique heure/jour)

**How to apply:** Toute modification du pipeline de scoring doit rester alignée avec le feature engineering du notebook et de `features.py`. L'entraînement se fait exclusivement via Docker (`ml-train-init` ou `./scripts/ml-train.sh`).
