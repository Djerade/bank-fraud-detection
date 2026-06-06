#!/bin/sh
# Ré-entraînement MLflow dans le conteneur ml-train-init (aucun Python sur l’hôte).
set -eu
cd "$(dirname "$0")/.."
exec docker compose run --rm --no-deps \
  ml-train-init \
  "$@"
