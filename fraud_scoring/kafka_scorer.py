#!/usr/bin/env python3
"""
Consommateur Kafka : topic brut → scoring (joblib) → topic des transactions scorées.

Variables d’environnement :
  KAFKA_BOOTSTRAP_SERVERS — défaut depuis Config
  KAFKA_TOPIC_IN          — topic à lire (défaut : topic brut)
  KAFKA_TOPIC_OUT         — topic de sortie (défaut : bank.transactions.scored)
  FRAUD_MODEL_PATH        — chemin vers fraud_classifier.joblib
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import joblib
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer

from Config.config import BOOTSTRAP_SERVERS, TOPIC, TOPIC_SCORED

from fraud_scoring.features import build_model_input, enrich_features, json_dict_to_training_dataframe


def _env(name: str, default: str) -> str:
    v = os.environ.get(name, "").strip()
    return v if v else default


def main() -> None:
    bootstrap = _env("KAFKA_BOOTSTRAP_SERVERS", BOOTSTRAP_SERVERS)
    topic_in = _env("KAFKA_TOPIC_IN", TOPIC)
    topic_out = _env("KAFKA_TOPIC_OUT", TOPIC_SCORED)

    model_path = Path(_env("FRAUD_MODEL_PATH", "/app/models/fraud_classifier.joblib"))
    if not model_path.is_file():
        alt = Path(__file__).resolve().parents[1] / "models" / "fraud_classifier.joblib"
        if alt.is_file():
            model_path = alt
    if not model_path.is_file():
        print(f"Modèle introuvable : {model_path}", file=sys.stderr)
        sys.exit(1)

    pipeline = joblib.load(model_path)
    print(f"[fraud-scorer] Modèle chargé : {model_path.resolve()}", file=sys.stderr)
    print(
        f"[fraud-scorer] {bootstrap!r} consume {topic_in!r} → produce {topic_out!r}",
        file=sys.stderr,
    )

    consumer = KafkaConsumer(
        topic_in,
        bootstrap_servers=[h.strip() for h in bootstrap.split(",") if h.strip()],
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        key_deserializer=lambda b: b.decode("utf-8") if b is not None else None,
        group_id=_env("KAFKA_GROUP_ID", "fraud-scorer"),
        auto_offset_reset="latest",
        enable_auto_commit=True,
    )

    producer = KafkaProducer(
        bootstrap_servers=[h.strip() for h in bootstrap.split(",") if h.strip()],
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        key_serializer=lambda k: str(k).encode("utf-8") if k is not None else None,
        acks="all",
        retries=3,
    )

    try:
        for msg in consumer:
            row = msg.value
            if not isinstance(row, dict):
                continue
            try:
                df0 = json_dict_to_training_dataframe(row)
                df1 = enrich_features(df0)
                X = build_model_input(df1)
                proba = None
                pred = pipeline.predict(X)[0]
                clf = getattr(pipeline, "named_steps", {}).get("clf")
                if clf is None and hasattr(pipeline, "steps") and pipeline.steps:
                    clf = pipeline.steps[-1][1]
                if clf is not None and hasattr(clf, "predict_proba"):
                    proba = float(pipeline.predict_proba(X)[0, 1])
                out = {
                    **row,
                    "fraud_predicted": int(pred),
                    "fraud_score": proba,
                }
                key = row.get("transaction_id")
                future = producer.send(topic_out, value=out, key=key)
                future.get(timeout=15)
            except Exception as e:
                print(f"[fraud-scorer] erreur message : {e}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\n[fraud-scorer] arrêt.", file=sys.stderr)
    finally:
        consumer.close()
        producer.flush()
        producer.close()


if __name__ == "__main__":
    main()
