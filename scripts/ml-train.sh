#!/bin/sh
# Ré-entraînement MLflow dans le conteneur ml-train-init (aucun Python sur l’hôte).
set -eu
cd "$(dirname "$0")/.."
exec docker compose run --rm \
  --entrypoint python \
  ml-train-init \
  -m fraud_detection.train \
  --register \
  "$@"
