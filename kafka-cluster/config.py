"""
Paramètres Kafka pour les scripts de ce dossier (Docker Compose : 1 broker + ZooKeeper).

Variables d'environnement (optionnelles) :
  KAFKA_BOOTSTRAP_SERVERS — liste séparée par des virgules (défaut : localhost:9092)
  KAFKA_TOPIC_RAW         — topic par défaut pour produceur.py / consumer.py (défaut : bank.transactions.raw)
  KAFKA_TOPIC_PROCESSED   — topic traité (aligné sur bank_fraud_detection.config)
  SIMULATEUR_API_BASE     — URL de base de l'API FastAPI (défaut : http://127.0.0.1:8000)
"""
from __future__ import annotations

import os

# Depuis l'hôte, avec le compose du dépôt : un broker sur 127.0.0.1:9092
BOOTSTRAP_SERVERS: str = os.environ.get(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)

TOPIC_RAW: str = os.environ.get("KAFKA_TOPIC_RAW", "bank.transactions.raw")
TOPIC_PROCESSED: str = os.environ.get(
    "KAFKA_TOPIC_PROCESSED",
    "bank.transactions.processed",
)

SIMULATEUR_API_BASE: str = os.environ.get(
    "SIMULATEUR_API_BASE",
    "http://127.0.0.1:8000",
)


def bootstrap_servers_list() -> list[str]:
    """Brokers sous forme de liste pour kafka-python."""
    return [h.strip() for h in BOOTSTRAP_SERVERS.split(",") if h.strip()]
