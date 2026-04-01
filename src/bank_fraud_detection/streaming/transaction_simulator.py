#!/usr/bin/env python3
"""
Simulateur de transactions bancaires aligné sur les colonnes du jeu FraudShield.

Génère des payloads JSON avec les mêmes clés que `CSV_TO_JSON_FIELD` dans
`bank_fraud_detection.config`, pour tests locaux ou publication sur le topic Kafka brut
(même format que `csv_to_kafka`).

Usage:
  python -m bank_fraud_detection.streaming.transaction_simulator --count 20
  python -m bank_fraud_detection.streaming.transaction_simulator --count 100 --kafka --sleep-ms 2
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from bank_fraud_detection.config import KAFKA_BOOTSTRAP_SERVERS, TOPIC_RAW

# Valeurs typiques observées dans FraudShield_Banking_Data.csv
TRANSACTION_TYPES = ("POS", "ATM", "Online")
MERCHANT_CATEGORIES = ("ATM", "Electronics", "Grocery", "Fuel")
LOCATIONS = (
    "Singapore",
    "Lahore",
    "Faisalabad",
    "London",
    "Karachi",
    "Islamabad",
    "Multan",
    "Bangkok",
)
CARD_TYPES = ("Credit", "Debit")
YES_NO = ("Yes", "No")


def _random_ip(rng: random.Random) -> str:
    return ".".join(str(rng.randint(1, 223)) for _ in range(4))


def _random_time(rng: random.Random) -> str:
    return f"{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}"


def _random_date_str(rng: random.Random, start: date, end: date) -> str:
    delta = (end - start).days
    d = start + timedelta(days=rng.randint(0, max(delta, 0)))
    return d.isoformat()


def generate_transaction(
    rng: random.Random,
    *,
    fraud_rate: float = 0.02,
    id_lo: int = 100_000,
    id_hi: int = 999_999,
) -> dict[str, object]:
    """
    Produit un dict avec les clés JSON du pipeline (snake_case), types compatibles
    avec la sérialisation utilisée par csv_to_kafka (nombres vs chaînes).
    """
    is_fraud = rng.random() < max(0.0, min(1.0, fraud_rate))
    fraud_label: str = "Fraud" if is_fraud else "Normal"

    home = rng.choice(LOCATIONS)
    tx_loc = rng.choice(LOCATIONS)
    distance = float(rng.randint(10, 600))

    if is_fraud:
        unusual = rng.choice(("Yes", "Yes", "No"))
        failed = float(rng.randint(1, 5))
        prev_fraud = float(rng.randint(1, 4))
        international = rng.choice(("Yes", "Yes", "No"))
    else:
        unusual = rng.choice(YES_NO)
        failed = float(rng.randint(0, 2))
        prev_fraud = float(rng.randint(0, 2))
        international = rng.choice(YES_NO)

    daily = float(rng.randint(1, 8))
    weekly = max(daily, float(rng.randint(int(daily), 20)))
    amount = float(rng.randint(1, 10))
    avg_amt = float(rng.randint(1, 6))
    max_24 = float(max(amount, rng.randint(1, 10)))

    period_start = date(2025, 1, 1)
    period_end = date(2025, 6, 30)

    return {
        "transaction_id": float(rng.randint(id_lo, id_hi)),
        "customer_id": float(rng.randint(10_000, 99_999)),
        "transaction_amount_million": amount,
        "transaction_time": _random_time(rng),
        "transaction_date": _random_date_str(rng, period_start, period_end),
        "transaction_type": rng.choice(TRANSACTION_TYPES),
        "merchant_id": float(rng.randint(10_000, 99_999)),
        "merchant_category": rng.choice(MERCHANT_CATEGORIES),
        "transaction_location": tx_loc,
        "customer_home_location": home,
        "distance_from_home": distance,
        "device_id": float(rng.randint(200_000, 999_999)),
        "ip_address": _random_ip(rng),
        "card_type": rng.choice(CARD_TYPES),
        "account_balance_million": float(rng.randint(1, 40)),
        "daily_transaction_count": daily,
        "weekly_transaction_count": weekly,
        "avg_transaction_amount_million": avg_amt,
        "max_transaction_last_24h_million": max_24,
        "is_international_transaction": international,
        "is_new_merchant": rng.choice(YES_NO),
        "failed_transaction_count": failed,
        "unusual_time_transaction": unusual,
        "previous_fraud_count": prev_fraud,
        "fraud_label": fraud_label,
    }


def _send_kafka(
    payloads: list[dict[str, object]],
    bootstrap: str,
    topic: str,
    sleep_ms: int,
) -> None:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError

    producer = KafkaProducer(
        bootstrap_servers=bootstrap.split(","),
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        key_serializer=lambda k: str(k).encode("utf-8") if k is not None else None,
        acks="all",
        retries=3,
    )
    try:
        for i, payload in enumerate(payloads):
            key = payload.get("transaction_id")
            future = producer.send(topic, value=payload, key=key)
            try:
                future.get(timeout=10)
            except KafkaError as e:
                print(f"Erreur Kafka: {e}", file=sys.stderr)
                raise
            if sleep_ms > 0 and i < len(payloads) - 1:
                time.sleep(sleep_ms / 1000.0)
        producer.flush()
    finally:
        producer.close()


def main() -> None:
    p = argparse.ArgumentParser(
        description="Simule des transactions (schéma FraudShield / JSON pipeline)"
    )
    p.add_argument("--count", type=int, default=10, help="Nombre de transactions à générer")
    p.add_argument("--seed", type=int, default=None, help="Graine aléatoire (reproductibilité)")
    p.add_argument(
        "--fraud-rate",
        type=float,
        default=0.02,
        help="Proportion approximative de Fraud_Label=Fraud (0..1)",
    )
    p.add_argument(
        "--kafka",
        action="store_true",
        help="Publier sur Kafka (topic brut par défaut)",
    )
    p.add_argument(
        "--bootstrap",
        default=KAFKA_BOOTSTRAP_SERVERS,
        help="Brokers Kafka (virgules)",
    )
    p.add_argument("--topic", default=TOPIC_RAW, help="Topic Kafka de sortie")
    p.add_argument("--sleep-ms", type=int, default=0, help="Pause entre envois Kafka")
    p.add_argument(
        "--output",
        choices=("stdout", "kafka", "both"),
        default="stdout",
        help="Sortie : lignes JSON, Kafka, ou les deux",
    )
    p.add_argument(
        "--out-file",
        type=Path,
        default=None,
        help="Optionnel : écrire une ligne JSON par transaction dans ce fichier",
    )
    args = p.parse_args()

    if args.count < 1:
        print("--count doit être >= 1", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(args.seed)
    payloads = [generate_transaction(rng, fraud_rate=args.fraud_rate) for _ in range(args.count)]

    use_stdout = args.output in ("stdout", "both")
    use_kafka = args.kafka or args.output in ("kafka", "both")

    if use_stdout:
        for row in payloads:
            print(json.dumps(row, ensure_ascii=False))

    if args.out_file is not None:
        args.out_file.parent.mkdir(parents=True, exist_ok=True)
        with args.out_file.open("w", encoding="utf-8") as f:
            for row in payloads:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    if use_kafka:
        _send_kafka(payloads, args.bootstrap, args.topic, args.sleep_ms)
        print(f"Publie {len(payloads)} messages sur {args.topic}", file=sys.stderr)


if __name__ == "__main__":
    main()
