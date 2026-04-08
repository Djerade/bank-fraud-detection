"""
Paramètres Kafka pour le dépôt (Docker Compose : 1 broker + ZooKeeper).

Un seul topic Kafka est utilisé dans tout le projet.

Variables d'environnement (optionnelles) :
  KAFKA_BOOTSTRAP_SERVERS — liste séparée par des virgules (défaut : localhost:9092)
  KAFKA_TOPIC             — nom du topic (défaut : bank.transactions.raw) ;
                            si absent, repli sur l’ancienne variable KAFKA_TOPIC_RAW
  SIMULATEUR_API_BASE     — URL de base de l'API FastAPI (défaut : http://127.0.0.1:8000)
"""
from __future__ import annotations

import os

BOOTSTRAP_SERVERS: str = os.environ.get(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)

KAFKA_BOOTSTRAP_SERVERS: str = BOOTSTRAP_SERVERS

TOPIC: str = os.environ.get("KAFKA_TOPIC") or os.environ.get(
    "KAFKA_TOPIC_RAW",
    "bank.transactions.raw",
)

SIMULATEUR_API_BASE: str = os.environ.get(
    "SIMULATEUR_API_BASE",
    "http://127.0.0.1:8000",
)


def bootstrap_servers_list() -> list[str]:
    """Brokers sous forme de liste pour kafka-python."""
    return [h.strip() for h in BOOTSTRAP_SERVERS.split(",") if h.strip()]
