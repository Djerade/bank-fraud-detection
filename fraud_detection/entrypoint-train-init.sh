#!/bin/sh
set -eu

MODEL="${FRAUD_MODEL_PATH:-/app/models/fraud_classifier.joblib}"

if [ -f "$MODEL" ]; then
  echo "Modèle déjà présent ($MODEL), entraînement ignoré."
  exit 0
fi

echo "Modèle absent, entraînement MLflow → $MODEL"
exec python -m fraud_detection.train --register "$@"
