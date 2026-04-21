"""
API REST de simulation de transactions bancaires (même schéma que le CLI).

Pour publier sur Kafka, utiliser le module ``simulateur.transaction_simulator`` (CLI ``--kafka``).

Déploiement prévu : image ``simulateur-api`` (Docker Compose) → http://127.0.0.1:8000/docs

Pour un essai ponctuel hors conteneur : ``uvicorn simulateur.app:app`` avec ``PYTHONPATH=/racine_du_depot``.
"""
from __future__ import annotations

import asyncio
import json
import random
from collections.abc import AsyncIterator

from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse

from .schemas import BatchParams
from .transaction_simulator import generate_transaction

app = FastAPI(
    title="Simulateur de transactions",
    description="Génère des payloads JSON alignés sur le jeu FraudShield. "
    "Pour Kafka, utiliser le CLI `transaction_simulator --kafka`.",
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


async def _transaction_continuous_bytes(fraud_rate: float) -> AsyncIterator[bytes]:
    """Chaque seconde : entre 5 et 7 transactions en NDJSON."""
    rng = random.Random()
    while True:
        n = random.randint(5, 7)
        for _ in range(n):
            row = generate_transaction(rng, fraud_rate=fraud_rate)
            yield (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
        await asyncio.sleep(1.0)


@app.get("/transaction_continuous")
async def transaction_continuous(
    fraud_rate: float = Query(default=0.02, ge=0.0, le=1.0),
) -> StreamingResponse:
    """
    Flux NDJSON infini : par période d’environ 1 s, envoie 5 à 7 transactions.

    Le client HTTP ferme la connexion pour arrêter (ex. Ctrl+C avec curl).
    """
    return StreamingResponse(
        _transaction_continuous_bytes(fraud_rate),
        media_type="application/x-ndjson",
    )
