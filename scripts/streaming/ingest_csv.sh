#!/usr/bin/env bash
# Publie le CSV vers le topic brut Kafka (producteur Python).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092,localhost:9093,localhost:9094}"
./env/bin/python -m pipeline.csv_to_kafka --max-rows "${1:-500}" --sleep-ms "${2:-2}"
