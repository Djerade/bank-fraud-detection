"""
Configuration Kafka, topics et chemins utilisés par le simulateur et les producteurs.

Les variables d'environnement surchargent les valeurs par défaut (voir docker-compose).
"""
from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

KAFKA_BOOTSTRAP_SERVERS: str = os.environ.get(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092,localhost:9093,localhost:9094",
)

TOPIC_RAW: str = os.environ.get("KAFKA_TOPIC_RAW", "bank.transactions.raw")
TOPIC_PROCESSED: str = os.environ.get(
    "KAFKA_TOPIC_PROCESSED",
    "bank.transactions.processed",
)

FRAUD_CSV_PATH: str = os.environ.get(
    "FRAUD_CSV_PATH",
    str(_REPO_ROOT / "data" / "FraudShield_Banking_Data.csv"),
)
