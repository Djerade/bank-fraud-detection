#!/usr/bin/env bash
# Vérifie que le broker Kafka (docker compose) tourne et répond.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if ! docker compose exec -T kafka kafka-broker-api-versions \
  --bootstrap-server localhost:9092 >/dev/null 2>&1; then
  echo "Kafka n'est pas joignable. À la racine du dépôt :" >&2
  echo "  docker compose up -d" >&2
  echo "Attendez ~10 s puis relancez ce script." >&2
  exit 1
fi
echo "OK — le broker répond (bootstrap: localhost:9092)."
