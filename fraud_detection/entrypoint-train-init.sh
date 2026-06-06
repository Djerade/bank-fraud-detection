#!/bin/sh
set -eu

MODEL="${FRAUD_MODEL_PATH:-/app/models/fraud_classifier.joblib}"

# Ancien joblib sans passage par MLflow → relancer l'entraînement pour remplir l'UI.
if [ -f "$MODEL" ] && python -m fraud_detection.mlflow_has_runs; then
  echo "Modèle et historique MLflow présents ($MODEL), entraînement ignoré."
  exit 0
fi

if [ -f "$MODEL" ]; then
  echo "Modèle présent mais UI MLflow vide → entraînement pour journaliser les runs."
else
  echo "Modèle absent → entraînement MLflow → $MODEL"
fi

exec python -m fraud_detection.train --register "$@"
