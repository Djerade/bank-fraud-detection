# MLflow — entièrement dans Docker

Tout le cycle **serveur MLflow → entraînement → export joblib** s’exécute dans des conteneurs Compose. L’hôte ne fait que lancer Compose et ouvrir l’UI.

| Service | Rôle |
|---------|------|
| **`mlflow`** | Serveur de tracking + UI [http://127.0.0.1:5000](http://127.0.0.1:5000) |
| **`ml-train-init`** | Job one-shot au `docker compose up` : entraîne **si** `models/fraud_classifier.joblib` est absent |
| **`fraud-scorer`** | Attend la fin réussie de `ml-train-init` avant de démarrer |

## Démarrage (stack complète)

Prérequis : CSV dans `data/` (`FraudShield_Banking_Data_features.csv` ou `FraudShield_Banking_Data.csv`).

```bash
docker compose up -d --build
```

Ordre typique :

1. `mlflow` devient healthy  
2. `ml-train-init` entraîne (ou saute si le modèle existe déjà)  
3. `fraud-scorer` et le reste de la stack démarrent  

UI MLflow : **http://127.0.0.1:5000** — expérience `bank-fraud-detection`.

## Ré-entraînement manuel (conteneur)

```bash
./scripts/ml-train.sh
```

Équivalent :

```bash
docker compose run --rm --entrypoint python ml-train-init \
  -m fraud_detection.train --register
```

Options supplémentaires (passées au script Python) :

```bash
./scripts/ml-train.sh --run-name rerun-2026-05-16
./scripts/ml-train.sh --data-path /app/data/FraudShield_Banking_Data.csv --raw-only
```

## Variables (définies dans Compose)

| Variable | Valeur conteneur |
|----------|------------------|
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` |
| `MLFLOW_EXPERIMENT_NAME` | `bank-fraud-detection` |
| `FRAUD_MODEL_PATH` | `/app/models/fraud_classifier.joblib` |

## Persistance

- Métadonnées / artefacts MLflow : volume **`mlflow-data`**
- Modèle pour Kafka : répertoire hôte **`models/`** monté en volume (écrit par `ml-train-init`)

Reset complet : `docker compose down -v` (supprime aussi Kafka, lac Spark, etc.).

## Lien avec le scoring

`fraud-scorer` lit `models/fraud_classifier.joblib` (montage `./models:/app/models:ro`). Après un ré-entraînement :

```bash
docker compose restart fraud-scorer
```
