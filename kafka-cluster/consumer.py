#!/usr/bin/env python3
"""
Consommateur minimal sur le cluster Kafka (kafka-python).

Usage (depuis la racine du dépôt, cluster déjà démarré) :
  python kafka-cluster/consumer.py
  python kafka-cluster/consumer.py --max 10 --from-beginning

Ctrl+C pour arrêter si --follow ou si vous laissez tourner après --max.
"""
from __future__ import annotations

import argparse
import json
import sys

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from config import TOPIC_DEMO, bootstrap_servers_list


def main() -> None:
    p = argparse.ArgumentParser(description="Lit des messages JSON depuis un topic Kafka")
    p.add_argument("--topic", default=TOPIC_DEMO, help="Topic à lire")
    p.add_argument(
        "--from-beginning",
        action="store_true",
        help="Repartir du début du topic (sinon seulement les nouveaux messages)",
    )
    p.add_argument(
        "--max",
        type=int,
        default=None,
        help="Nombre maximum de messages puis arrêt (défaut : illimité)",
    )
    p.add_argument(
        "--follow",
        action="store_true",
        help="Après --max atteint ou sans --max, continuer à poller (temps réel)",
    )
    args = p.parse_args()
    servers = bootstrap_servers_list()

    # Bloquer indéfiniment entre messages si on attend un nombre précis ou du flux continu
    block_forever = args.follow or args.max is not None
    consumer = KafkaConsumer(
        args.topic,
        bootstrap_servers=servers,
        auto_offset_reset="earliest" if args.from_beginning else "latest",
        enable_auto_commit=True,
        group_id="kafka-cluster-demo-consumer",
        value_deserializer=lambda b: json.loads(b.decode("utf-8")) if b else None,
        consumer_timeout_ms=None if block_forever else 10_000,
    )

    received = 0
    try:
        for msg in consumer:
            received += 1
            print(
                f"partition={msg.partition} offset={msg.offset} key={msg.key!r} "
                f"value={msg.value!r}",
                flush=True,
            )
            if args.max is not None and received >= args.max and not args.follow:
                break
    except KafkaError as e:
        print(f"Erreur Kafka: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print(file=sys.stderr)
    finally:
        consumer.close()

    if received == 0:
        print(
            "Aucun message (topic vide, timeout ou pas encore de producteur).",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
