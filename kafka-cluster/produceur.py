#!/usr/bin/env python3
"""
Producteur minimal vers le cluster Kafka (kafka-python).

Usage (depuis la racine du dépôt, cluster déjà démarré) :
  python kafka-cluster/produceur.py
  python kafka-cluster/produceur.py --count 5 --topic mon.topic

Dépendance : kafka-python (déjà dans le pyproject du dépôt).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone

from kafka import KafkaProducer
from kafka.errors import KafkaError

from config import TOPIC_RAW, bootstrap_servers_list


def main() -> None:
    p = argparse.ArgumentParser(description="Envoie des messages JSON sur un topic Kafka")
    p.add_argument(
        "--topic",
        default=TOPIC_RAW,
        help=f"Topic de sortie (défaut : {TOPIC_RAW} / KAFKA_TOPIC_RAW)",
    )
    p.add_argument("--count", type=int, default=3, help="Nombre de messages")
    p.add_argument(
        "--sleep",
        type=float,
        default=0.5,
        help="Pause en secondes entre deux envois (0 = rafale)",
    )
    args = p.parse_args()
    servers = bootstrap_servers_list()

    producer = KafkaProducer(
        bootstrap_servers=servers,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        key_serializer=lambda k: str(k).encode("utf-8") if k is not None else None,
        acks="all",
        retries=3,
    )

    try:
        for i in range(args.count):
            payload = {
                "seq": i + 1,
                "source": "kafka-cluster/produceur.py",
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            future = producer.send(args.topic, value=payload, key=str(i))
            try:
                record = future.get(timeout=15)
                print(
                    f"OK partition={record.partition} offset={record.offset} {payload}",
                    file=sys.stderr,
                )
            except KafkaError as e:
                print(f"Erreur Kafka: {e}", file=sys.stderr)
                sys.exit(1)
            if args.sleep > 0 and i < args.count - 1:
                time.sleep(args.sleep)
    finally:
        producer.flush()
        producer.close()

    print(f"Publie {args.count} message(s) sur le topic « {args.topic} » (brokers: {servers}).")


if __name__ == "__main__":
    main()
