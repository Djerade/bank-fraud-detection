#!/usr/bin/env bash
# Publie le CSV vers le topic brut Kafka (producteur Python).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
elif [[ -x "$ROOT/env/bin/python" ]]; then
  PY="$ROOT/env/bin/python"
else
  PY="${PYTHON:-python3}"
fi

exec "$PY" -m bank_fraud_detection.streaming.csv_to_kafka --max-rows "${1:-500}" --sleep-ms "${2:-2}"
