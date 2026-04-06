"""
API REST de simulation de transactions bancaires (même schéma que le CLI / Kafka).

Lancer (local, après ``pip install -r requirements.txt`` à la racine du dépôt) :
  uvicorn simulateur.app:app --reload --host 127.0.0.1 --port 8000

Docker :
  docker compose up -d --build   → http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import asyncio
import json
import random
from collections.abc import AsyncIterator

from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse

from bank_fraud_detection.config import KAFKA_BOOTSTRAP_SERVERS, TOPIC_RAW

from .schemas import BatchParams
from .transaction_simulator import generate_transaction


def _bootstrap_list() -> list[str]:
    return [h.strip() for h in KAFKA_BOOTSTRAP_SERVERS.split(",") if h.strip()]


def _kafka_producer():
    from kafka import KafkaProducer

    return KafkaProducer(
        bootstrap_servers=_bootstrap_list(),
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        key_serializer=lambda k: str(k).encode("utf-8") if k is not None else None,
        acks="all",
        retries=3,
    )


def _kafka_send_sync(producer, topic: str, row: dict[str, object]) -> None:
    key = row.get("transaction_id")
    future = producer.send(topic, value=row, key=key)
    future.get(timeout=15)

app = FastAPI(
    title="Simulateur de transactions",
    description="Génère des payloads JSON alignés sur le jeu FraudShield (ingestion Kafka).",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/transaction")
def one_transaction(
    fraud_rate: float = Query(default=0.02, ge=0.0, le=1.0),
    seed: int | None = Query(default=None),
) -> dict[str, object]:
    """Génère une transaction aléatoire (paramètres en query)."""
    rng = random.Random(seed)
    return generate_transaction(rng, fraud_rate=fraud_rate)


@app.post("/transactions")
def batch_transactions(body: BatchParams) -> list[dict[str, object]]:
    """Génère `count` transactions (corps JSON)."""
    rng = random.Random(body.seed)
    return [generate_transaction(rng, fraud_rate=body.fraud_rate) for _ in range(body.count)]


async def _transaction_continuous_bytes(
    fraud_rate: float,
    *,
    to_kafka: bool,
    topic: str,
) -> AsyncIterator[bytes]:
    """Chaque seconde : entre 5 et 7 transactions ; optionnellement publiées sur Kafka."""
    rng = random.Random()
    producer = _kafka_producer() if to_kafka else None
    try:
        while True:
            n = random.randint(5, 7)
            for _ in range(n):
                row = generate_transaction(rng, fraud_rate=fraud_rate)
                yield (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
                if producer is not None:
                    await asyncio.to_thread(_kafka_send_sync, producer, topic, row)
            await asyncio.sleep(1.0)
    finally:
        if producer is not None:
            await asyncio.to_thread(producer.flush)
            producer.close()


@app.get("/transaction_continuous")
async def transaction_continuous(
    fraud_rate: float = Query(default=0.02, ge=0.0, le=1.0),
    to_kafka: bool = Query(
        default=False,
        description="Si true, chaque transaction est aussi envoyée au cluster Kafka (bootstrap via env).",
    ),
    topic: str | None = Query(
        default=None,
        description="Topic Kafka (défaut : KAFKA_TOPIC_RAW / config).",
    ),
) -> StreamingResponse:
    """
    Flux NDJSON infini : par période d’environ 1 s, envoie 5 à 7 transactions.

    Avec ``to_kafka=true``, chaque ligne est **également** produite sur Kafka (même schéma JSON).
    Configure ``KAFKA_BOOTSTRAP_SERVERS`` (ex. dans docker-compose pour ``simulateur-api`` :
    ``kafka-1:29092,...``). En local hors Docker : ``localhost:9092,9093,9094``.

    Le client HTTP ferme la connexion pour arrêter (ex. Ctrl+C avec curl).
    """
    kafka_topic = topic or TOPIC_RAW
    return StreamingResponse(
        _transaction_continuous_bytes(fraud_rate, to_kafka=to_kafka, topic=kafka_topic),
        media_type="application/x-ndjson",
    )