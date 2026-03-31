#!/usr/bin/env python3
"""
Ingestion : lecture du CSV FraudShield et publication des lignes sur le topic Kafka brut.

Usage:
  python -m pipeline.csv_to_kafka --bootstrap localhost:9092,localhost:9093,localhost:9094 --max-rows 1000 --sleep-ms 5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
from kafka import KafkaProducer
from kafka.errors import KafkaError

from pipeline.config import CSV_DEFAULT_PATH, CSV_TO_JSON_FIELD, KAFKA_BOOTSTRAP_SERVERS, TOPIC_RAW


def _row_to_payload(row: pd.Series) -> dict:
    out: dict = {}
    for csv_col, json_key in CSV_TO_JSON_FIELD.items():
        val = row.get(csv_col)
        if pd.isna(val):
            out[json_key] = None
        elif isinstance(val, (float, int)) and not isinstance(val, bool):
            out[json_key] = float(val) if isinstance(val, float) else int(val)
        else:
            out[json_key] = str(val).strip()
    return out


def run(
    csv_path: Path,
    bootstrap: str,
    topic: str,
    max_rows: int | None,
    sleep_ms: int,
    chunk_size: int,
) -> None:
    producer = KafkaProducer(
        bootstrap_servers=bootstrap.split(","),
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        key_serializer=lambda k: str(k).encode("utf-8") if k is not None else None,
        acks="all",
        retries=3,
    )
    sent = 0
    try:
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
            chunk = chunk.rename(columns=lambda c: c.strip())
            for _, row in chunk.iterrows():
                payload = _row_to_payload(row)
                key = payload.get("transaction_id")
                future = producer.send(topic, value=payload, key=key)
                try:
                    future.get(timeout=10)
                except KafkaError as e:
                    print(f"Erreur Kafka: {e}", file=sys.stderr)
                    raise
                sent += 1
                if max_rows is not None and sent >= max_rows:
                    producer.flush()
                    print(f"Publie {sent} messages sur {topic}")
                    return
                if sleep_ms > 0:
                    time.sleep(sleep_ms / 1000.0)
        producer.flush()
        print(f"Publie {sent} messages sur {topic}")
    finally:
        producer.close()


def main() -> None:
    p = argparse.ArgumentParser(description="CSV -> Kafka (topic brut)")
    p.add_argument("--csv", type=Path, default=CSV_DEFAULT_PATH, help="Chemin du CSV")
    p.add_argument(
        "--bootstrap",
        default=KAFKA_BOOTSTRAP_SERVERS,
        help="Serveurs Kafka (séparés par des virgules)",
    )
    p.add_argument("--topic", default=TOPIC_RAW, help="Topic de sortie")
    p.add_argument("--max-rows", type=int, default=None, help="Limite de lignes (défaut: tout le fichier)")
    p.add_argument("--sleep-ms", type=int, default=0, help="Pause entre chaque message")
    p.add_argument("--chunk-size", type=int, default=5000, help="Taille des chunks pandas")
    args = p.parse_args()
    if not args.csv.is_file():
        print(f"Fichier introuvable: {args.csv}", file=sys.stderr)
        sys.exit(1)
    run(
        csv_path=args.csv,
        bootstrap=args.bootstrap,
        topic=args.topic,
        max_rows=args.max_rows,
        sleep_ms=args.sleep_ms,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
