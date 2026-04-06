#!/usr/bin/env python3
"""
Simulateur de transactions bancaires aligné sur les colonnes du jeu FraudShield.

Génère des payloads JSON avec les mêmes clés que `CSV_TO_JSON_FIELD` dans
`bank_fraud_detection.config`, pour tests locaux ou publication sur le topic Kafka brut
(même format que `csv_to_kafka`).

Vers Kafka, par défaut **une transaction toutes les 5 secondes** (débit type flux).
Sortie stdout seule : génération en rafale sans pause (sauf si --interval-seconds).

Usage (après ``pip install -e .`` ou ``pip install -r requirements.txt`` depuis la racine du dépôt) :

  python -m simulateur.transaction_simulator --count 20
  python -m simulateur.transaction_simulator --kafka --count 12
  python -m simulateur.transaction_simulator --kafka --forever
  python -m simulateur.transaction_simulator --kafka --interval-seconds 2 --count 50

Sans installation : ``PYTHONPATH=src:. python -m simulateur.transaction_simulator …`` (racine du dépôt).
Dans l’image Docker Compose, ``PYTHONPATH`` inclut la racine du projet.
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

# Entre deux envois Kafka si aucun --sleep-ms ni --interval-seconds n'est fourni
DEFAULT_KAFKA_INTERVAL_SECONDS = 5.0


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


def _resolve_interval_seconds(
    sleep_ms: int,
    interval_seconds: float | None,
    use_kafka: bool,
) -> float:
    """Pause entre deux transactions : --sleep-ms prioritaire, sinon --interval-seconds, sinon 5 s si Kafka."""
    if sleep_ms != 0:
        return max(0.0, sleep_ms / 1000.0)
    if interval_seconds is not None:
        return max(0.0, interval_seconds)
    if use_kafka:
        return DEFAULT_KAFKA_INTERVAL_SECONDS
    return 0.0


def main() -> None:
    p = argparse.ArgumentParser(
        description="Simule des transactions (schéma FraudShield / JSON pipeline)"
    )
    p.add_argument(
        "--count",
        type=int,
        default=10,
        help="Nombre de transactions (ignoré si --forever)",
    )
    p.add_argument(
        "--forever",
        action="store_true",
        help="Envoie en boucle jusqu'à Ctrl+C (utile avec --kafka)",
    )
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
    p.add_argument(
        "--sleep-ms",
        type=int,
        default=0,
        help="Pause entre chaque envoi (ms), prioritaire sur --interval-seconds",
    )
    p.add_argument(
        "--interval-seconds",
        type=float,
        default=None,
        help=(
            f"Secondes entre chaque transaction. "
            f"Vers Kafka seul, défaut {DEFAULT_KAFKA_INTERVAL_SECONDS:g} s si non précisé. "
            "Utiliser 0 pour enchaîner sans pause."
        ),
    )
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
        help="Optionnel : une ligne JSON par transaction (écriture au fil de l'eau)",
    )
    args = p.parse_args()

    if not args.forever and args.count < 1:
        print("--count doit être >= 1 (ou utilisez --forever)", file=sys.stderr)
        sys.exit(1)

    use_stdout = args.output in ("stdout", "both")
    use_kafka = args.kafka or args.output in ("kafka", "both")
    interval = _resolve_interval_seconds(args.sleep_ms, args.interval_seconds, use_kafka)

    rng = random.Random(args.seed)

    producer = None
    if use_kafka:
        from kafka import KafkaProducer
        from kafka.errors import KafkaError as _KafkaError

        producer = KafkaProducer(
            bootstrap_servers=args.bootstrap.split(","),
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: str(k).encode("utf-8") if k is not None else None,
            acks="all",
            retries=3,
        )

    out_f = None
    if args.out_file is not None:
        args.out_file.parent.mkdir(parents=True, exist_ok=True)
        out_f = args.out_file.open("w", encoding="utf-8")

    sent = 0
    first = True

    if use_kafka and args.forever:
        print(
            f"Flux Kafka : 1 message toutes les {interval:g} s sur {args.topic} (Ctrl+C pour arrêter)",
            file=sys.stderr,
        )

    try:
        while True:
            if not args.forever and sent >= args.count:
                break
            if not first and interval > 0:
                time.sleep(interval)
            first = False

            row = generate_transaction(rng, fraud_rate=args.fraud_rate)

            if use_stdout:
                print(json.dumps(row, ensure_ascii=False))

            if out_f is not None:
                out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                out_f.flush()

            if producer is not None:
                key = row.get("transaction_id")
                future = producer.send(args.topic, value=row, key=key)
                try:
                    future.get(timeout=10)
                except _KafkaError as e:
                    print(f"Erreur Kafka: {e}", file=sys.stderr)
                    raise

            sent += 1
    except KeyboardInterrupt:
        print(file=sys.stderr)
        print(f"Arrêt après {sent} transaction(s).", file=sys.stderr)
    finally:
        if producer is not None:
            producer.flush()
            producer.close()
        if out_f is not None:
            out_f.close()

    if use_kafka and sent > 0 and not args.forever:
        print(f"Publie {sent} message(s) sur {args.topic}", file=sys.stderr)


if __name__ == "__main__":
    main()
