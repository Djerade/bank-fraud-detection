"""
Paramètres Kafka pour les scripts de ce dossier (cluster Docker Compose : 3 brokers + ZooKeeper).

Variables d'environnement (optionnelles) :
  KAFKA_BOOTSTRAP_SERVERS — liste séparée par des virgules (défaut : les trois ports hôte)
  KAFKA_TOPIC_DEMO       — topic utilisé par produceur.py / consumer.py
"""
from __future__ import annotations

import os

# Depuis l'hôte, avec le compose du dépôt : trois brokers sur 127.0.0.1
BOOTSTRAP_SERVERS: str = os.environ.get(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092,localhost:9093,localhost:9094",
)

TOPIC_DEMO: str = os.environ.get("KAFKA_TOPIC_DEMO", "kafka.cluster.demo")


def bootstrap_servers_list() -> list[str]:
    """Brokers sous forme de liste pour kafka-python."""
    return [h.strip() for h in BOOTSTRAP_SERVERS.split(",") if h.strip()]
