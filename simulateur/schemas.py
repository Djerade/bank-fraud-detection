"""Modèles Pydantic pour l'API simulateur."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TransactionParams(BaseModel):
    """Paramètres communs de génération."""

    fraud_rate: float = Field(default=0.02, ge=0.0, le=1.0)
    seed: int | None = Field(default=None, description="Graine pour reproductibilité")


class BatchParams(TransactionParams):
    count: int = Field(default=1, ge=1, le=500)


class PublishParams(BatchParams):
    topic: str | None = Field(default=None, description="Topic Kafka (défaut: config TOPIC_RAW)")
    interval_seconds: float = Field(
        default=0.0,
        ge=0.0,
        le=60.0,
        description="Pause entre deux envois Kafka (0 = rafale)",
    )


class PublishResult(BaseModel):
    published: int
    topic: str
