#!/usr/bin/env python3
"""
Affiche des messages d'un topic Kafka (démo / debug).

Sans --follow : lit jusqu'à --max messages puis s'arrête (offset « earliest » par défaut).

Avec --follow : reste branché et affiche chaque nouveau message au fil de l'eau (Ctrl+C pour
arrêter). Par défaut seuls les messages publiés **après** le lancement du consumer sont vus
(auto_offset_reset=latest). Utilisez --from-beginning pour commencer au début du topic puis
continuer à suivre.
"""
from __future__ import annotations

import argparse
import json
import sys

from kafka import KafkaConsumer

from bank_fraud_detection.config import KAFKA_BOOTSTRAP_SERVERS, TOPIC_RAW


def main() -> None:
    p = argparse.ArgumentParser(
        description="Lit des messages JSON sur un topic Kafka (échantillon ou suivi temps réel)"
    )
    p.add_argument("--bootstrap", default=KAFKA_BOOTSTRAP_SERVERS)
    p.add_argument(
        "--topic",
        default=TOPIC_RAW,
        help="Topic à lire (souvent bank.transactions.raw pour l'ingestion)",
    )
    p.add_argument(
        "--max",
        type=int,
        default=5,
        help="Nombre max de messages (ignoré si --follow sans limite ; défaut: 5)",
    )
    p.add_argument(
        "--follow",
        "-f",
        action="store_true",
        help="Suivi continu (temps réel) jusqu'à Ctrl+C",
    )
    p.add_argument(
        "--from-beginning",
        action="store_true",
        help="Avec --follow : lire d'abord tout l'historique du topic puis les nouveaux messages",
    )
    args = p.parse_args()

    if args.follow:
        reset = "earliest" if args.from_beginning else "latest"
    else:
        reset = "earliest"

    consumer_kwargs: dict = dict(
        bootstrap_servers=args.bootstrap.split(","),
        auto_offset_reset=reset,
        enable_auto_commit=True,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")) if b else None,
    )
    # En mode échantillon, timeout pour ne pas bloquer indéfiniment sur topic vide
    if not args.follow:
        consumer_kwargs["consumer_timeout_ms"] = 10_000

    consumer = KafkaConsumer(args.topic, **consumer_kwargs)

    n = 0
    try:
        if args.follow:
            print(
                f"Suivi du topic « {args.topic} » (reset={reset}). Ctrl+C pour arrêter.\n",
                file=sys.stderr,
            )
            while True:
                records = consumer.poll(timeout_ms=1000)
                for _tp, messages in records.items():
                    for msg in messages:
                        print(json.dumps(msg.value, indent=2, ensure_ascii=False))
                        sys.stdout.flush()
                        n += 1
        else:
            for msg in consumer:
                print(json.dumps(msg.value, indent=2, ensure_ascii=False))
                n += 1
                if n >= args.max:
                    break
    except KeyboardInterrupt:
        print(file=sys.stderr)
        print(f"Arrêt après {n} message(s).", file=sys.stderr)
    except Exception as e:
        if "NoBrokersAvailable" in type(e).__name__ or "NoBrokersAvailable" in str(e):
            print(
                "Kafka injoignable. À la racine du dépôt : docker compose up -d",
                file=sys.stderr,
            )
        raise
    finally:
        consumer.close()

    if n == 0 and not args.follow:
        print(
            "Aucun message (topic vide ou timeout). Publiez d'abord (csv_to_kafka, simulateur…).",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
