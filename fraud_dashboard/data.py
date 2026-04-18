"""Lecture Kafka (topic scoré) et données de démonstration."""
from __future__ import annotations

import json
import random
import time
from typing import Any

from kafka import KafkaConsumer


def make_consumer(
    bootstrap: str,
    topic: str,
    group_id: str,
) -> KafkaConsumer:
    servers = [h.strip() for h in bootstrap.split(",") if h.strip()]
    return KafkaConsumer(
        topic,
        bootstrap_servers=servers,
        group_id=group_id,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        key_deserializer=lambda b: b.decode("utf-8") if b is not None else None,
        auto_offset_reset="latest",
        enable_auto_commit=True,
        consumer_timeout_ms=200,
    )


def poll_records(consumer: KafkaConsumer, max_messages: int = 256) -> list[dict[str, Any]]:
    """Récupère jusqu’à ``max_messages`` enregistrements (poll non bloquant)."""
    out: list[dict[str, Any]] = []
    # kafka-python : poll retourne un dict TopicPartition -> [ConsumerRecord]
    raw = consumer.poll(timeout_ms=600)
    if not raw:
        return out
    for _tp, records in raw.items():
        for r in records:
            v = r.value
            if isinstance(v, dict):
                v = dict(v)
                v["_ingested_at"] = time.time()
                out.append(v)
            if len(out) >= max_messages:
                return out
    return out


def demo_batch(n: int, rng: random.Random | None = None) -> list[dict[str, Any]]:
    """Quelques lignes factices alignées sur le simulateur + champs ML."""
    r = rng or random.Random()
    types = ("POS", "ATM", "Online")
    merchants = ("ATM", "Electronics", "Grocery", "Fuel")
    now = time.time()
    rows: list[dict[str, Any]] = []
    for i in range(n):
        fraud = r.random() < 0.08
        score = r.uniform(0.65, 0.99) if fraud else r.uniform(0.01, 0.45)
        rows.append(
            {
                "transaction_id": float(r.randint(100_000, 999_999)),
                "customer_id": float(r.randint(10_000, 99_999)),
                "transaction_amount_million": round(r.uniform(0.5, 12.0), 2),
                "transaction_type": r.choice(types),
                "merchant_category": r.choice(merchants),
                "fraud_predicted": 1 if fraud else 0,
                "fraud_score": round(score, 4),
                "_ingested_at": now - r.uniform(0, 120),
                "_demo": True,
            }
        )
    return rows
