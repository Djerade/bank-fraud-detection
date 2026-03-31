#!/usr/bin/env python3
"""Affiche quelques messages d'un topic (démo / debug)."""
from __future__ import annotations

import argparse
import json
import sys

from kafka import KafkaConsumer

from pipeline.config import KAFKA_BOOTSTRAP_SERVERS, TOPIC_PROCESSED


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--bootstrap", default=KAFKA_BOOTSTRAP_SERVERS)
    p.add_argument("--topic", default=TOPIC_PROCESSED)
    p.add_argument("--max", type=int, default=5)
    args = p.parse_args()
    c = KafkaConsumer(
        args.topic,
        bootstrap_servers=args.bootstrap.split(","),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        consumer_timeout_ms=8000,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")) if b else None,
    )
    n = 0
    try:
        for msg in c:
            print(json.dumps(msg.value, indent=2, ensure_ascii=False))
            n += 1
            if n >= args.max:
                break
    except Exception as e:
        if "NoBrokersAvailable" in type(e).__name__ or "NoBrokersAvailable" in str(e):
            print(
                "Kafka injoignable. Démarrez : docker compose -f docker-compose.kafka.yml up -d",
                file=sys.stderr,
            )
        raise
    finally:
        c.close()
    if n == 0:
        print("Aucun message (topic vide ou timeout). Publiez d'abord avec csv_to_kafka.", file=sys.stderr)


if __name__ == "__main__":
    main()
