"""Paramètres depuis l’environnement (alignés sur ``Config/config.py``)."""
from __future__ import annotations

import os

KAFKA_BOOTSTRAP_SERVERS: str = os.environ.get(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)
KAFKA_TOPIC: str = os.environ.get("KAFKA_TOPIC") or os.environ.get(
    "KAFKA_TOPIC_RAW",
    "bank.transactions.raw",
)

SPARK_BRONZE_PATH: str = os.environ.get(
    "SPARK_BRONZE_PATH",
    "/data/lake/bronze/transactions",
)
SPARK_GOLD_PATH: str = os.environ.get(
    "SPARK_GOLD_PATH",
    "/data/lake/gold/batch_summary",
)
SPARK_CHECKPOINT_SPEED: str = os.environ.get(
    "SPARK_CHECKPOINT_SPEED",
    "/checkpoint/speed-layer",
)
