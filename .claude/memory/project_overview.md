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
- **Backend / scoring temps réel :** `fraud_backend/` (FastAPI, port **8001**) — consomme le topic brut via un thread Kafka de fond, score avec le joblib (réutilise `fraud_scoring.features`), garde les transactions scorées dans un tampon mémoire (6000 max) et les sert au dashboard. Endpoints : `GET /api/dashboard` (agrégé), `POST /predict` (à la demande), `GET /health`. Réutilise l'image `bank-fraud-detection-simulateur:latest` (pas de build dédié).
- **Architecture Lambda :** Spark speed layer (streaming bronze) + batch layer (agrégats gold) — `spark_lambda/`
- **Dashboard :** Next.js (`fraud_dashboard/`) → port 3000. La route `/api/dashboard` est un simple **proxy** vers `http://fraud-backend:8001` (var `FRAUD_API_BASE`). Le frontend ne parle plus à Kafka.

**Architecture actuelle (depuis juillet 2026) :** `producteur → Kafka raw → fraud-backend (modèle) → dashboard (polling)`. L'ancien service `fraud-scorer` (`fraud_scoring/kafka_scorer.py` → topic `bank.transactions.scored`) et la consommation Kafka côté Next.js ont été **retirés**. `fraud_scoring/kafka_scorer.py` subsiste comme variante Kafka→Kafka mais n'est plus dans le compose (encore référencé par `scripts/generate_rapport_docx.py`).
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
