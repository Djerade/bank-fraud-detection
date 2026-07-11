"""API FastAPI : point d'entrée du scoring temps réel et du dashboard.

Flux : Kafka ``bank.transactions.raw`` → modèle exporté → tampon mémoire → HTTP.

Endpoints :
  GET  /health          état du service (modèle chargé, transactions en tampon)
  GET  /api/dashboard   instantané agrégé consommé par le dashboard Next.js
  POST /predict         scoring à la demande d'une transaction brute (JSON simulateur)

Variables d'environnement :
  KAFKA_BOOTSTRAP_SERVERS  brokers (défaut : Config)
  KAFKA_TOPIC_IN           topic brut à consommer (défaut : bank.transactions.raw)
  FRAUD_MODEL_PATH         chemin du joblib (défaut : /app/models/fraud_classifier.joblib)
  FRAUD_BACKEND_GROUP      group_id Kafka (défaut : fraud-backend)
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import Body, FastAPI

from Config.config import BOOTSTRAP_SERVERS, TOPIC

from .consumer import ScoringConsumer
from .metrics import Metrics
from .scoring import Scorer
from .store import Store


def _env(name: str, default: str) -> str:
    v = os.environ.get(name, "").strip()
    return v if v else default


class State:
    scorer: Scorer
    store: Store
    metrics: Metrics
    consumer: ScoringConsumer


state = State()


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_path = _env("FRAUD_MODEL_PATH", "/app/models/fraud_classifier.joblib")
    state.scorer = Scorer(model_path)
    state.store = Store()
    state.metrics = Metrics()
    state.consumer = ScoringConsumer(
        state.scorer,
        state.store,
        state.metrics,
        bootstrap=_env("KAFKA_BOOTSTRAP_SERVERS", BOOTSTRAP_SERVERS),
        topic_in=_env("KAFKA_TOPIC_IN", TOPIC),
        group_id=_env("FRAUD_BACKEND_GROUP", "fraud-backend"),
    )
    state.consumer.start()
    yield
    state.consumer.stop()


app = FastAPI(title="Fraud Detection Backend", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model_source": state.scorer.source,
        "model_fallback": str(state.scorer.model_path),
        "model_loaded_at": state.scorer.loaded_at,
        "stats_loaded": state.scorer.stats_loaded,
        "buffered": len(state.store),
    }


@app.get("/metrics")
def metrics() -> dict:
    """Compteurs cumulatifs de supervision (débit, taux d'alerte, latence, drift)."""
    return {"model_source": state.scorer.source, **state.metrics.snapshot()}


@app.post("/reload")
def reload_model() -> dict:
    """Recharge le modèle + global_stats depuis le disque, sans redémarrer le service."""
    return state.scorer.reload()


@app.get("/api/dashboard")
def dashboard() -> dict:
    return state.store.snapshot()


@app.post("/predict")
def predict(payload: dict = Body(...)) -> dict:
    """Score une transaction brute (format JSON du simulateur) à la demande."""
    result = state.scorer.score(payload)
    print("Result",result)
    return {**result, "is_fraud": bool(result["fraud_predicted"])}
