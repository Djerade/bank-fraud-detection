"""
API REST de simulation de transactions bancaires (même schéma que le CLI / Kafka).

Lancer (local, après ``pip install -r requirements.txt`` à la racine du dépôt) :
  uvicorn simulateur.app:app --reload --host 127.0.0.1 --port 8000

Docker :
  docker compose up -d --build   → http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import json
import random
import time

from fastapi import FastAPI, HTTPException, Query

from bank_fraud_detection.config import KAFKA_BOOTSTRAP_SERVERS, TOPIC_RAW

from .schemas import BatchParams, PublishParams, PublishResult
from .transaction_simulator import generate_transaction

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


@app.post("/transaction_continuous")
def transaction_continuous() -> dict[str, object]:
    """Génère une transaction continue (corps JSON)."""
    while True:
        yield generate_transaction(random.Random(), fraud_rate=0.02)