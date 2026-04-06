#!/usr/bin/env python3
"""
Ingestion vers le topic Kafka brut (défaut : config.TOPIC_RAW).

Deux entrées possibles :
  - CSV FraudShield (par défaut) : une ligne CSV → un message JSON (mapping config.CSV_TO_JSON_FIELD).
  - JSONL : une ligne = un objet JSON (même schéma que le simulateur / messages déjà prêts).

Prérequis : broker Kafka joignable (ex. docker compose up -d).

Usage:
  python -m bank_fraud_detection.streaming.csv_to_kafka \\
    --bootstrap localhost:9092 --max-rows 1000 --sleep-ms 5

  # Sortie du CLI simulateur (stdout) → Kafka (après pip install -e ., ou PYTHONPATH=src:.)
  python -m simulateur.transaction_simulator --count 5 | \\
    python -m bank_fraud_detection.streaming.csv_to_kafka --jsonl -

  # Fichier produit par le simulateur (--out-file)
  python -m bank_fraud_detection.streaming.csv_to_kafka --jsonl transactions.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

import pandas as pd
from kafka import KafkaProducer
from kafka.errors import KafkaError

from bank_fraud_detection.config import (
    CSV_DEFAULT_PATH,
    CSV_TO_JSON_FIELD,
    KAFKA_BOOTSTRAP_SERVERS,
    TOPIC_RAW,
)

# Clés JSON attendues (pour une validation légère des lignes JSONL)
_JSON_KEYS_EXPECTED = frozenset(CSV_TO_JSON_FIELD.values())


def _row_to_payload(row: pd.Series) -> dict:
    """
    Convertit une ligne pandas (colonnes = en-têtes CSV) en dict prêt pour JSON/Kafka.
    Types : NaN → None ; nombres → int ou float ; le reste → chaîne trimée.
    (Les bool pandas ne sont pas traités comme des nombres.)
    """
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


def _producer(bootstrap: str) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=bootstrap.split(","),
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        key_serializer=lambda k: str(k).encode("utf-8") if k is not None else None,
        acks="all",
        retries=3,
    )


def _send_one(producer: KafkaProducer, topic: str, payload: dict) -> None:
    key = payload.get("transaction_id")
    future = producer.send(topic, value=payload, key=key)
    try:
        future.get(timeout=10)
    except KafkaError as e:
        print(f"Erreur Kafka: {e}", file=sys.stderr)
        raise


def _parse_jsonl_line(line: str, line_no: int) -> dict:
    line = line.strip()
    if not line:
        raise ValueError("ligne vide")
    try:
        obj = json.loads(line)
    except json.JSONDecodeError as e:
        raise ValueError(f"ligne {line_no}: JSON invalide ({e})") from e
    if not isinstance(obj, dict):
        raise ValueError(f"ligne {line_no}: un objet JSON est attendu par ligne")
    keys = frozenset(obj.keys())
    if keys != _JSON_KEYS_EXPECTED:
        missing = _JSON_KEYS_EXPECTED - keys
        extra = keys - _JSON_KEYS_EXPECTED
        parts = []
        if missing:
            parts.append(f"clés manquantes: {sorted(missing)}")
        if extra:
            parts.append(f"clés inconnues: {sorted(extra)}")
        raise ValueError(f"ligne {line_no}: schéma incompatible ({'; '.join(parts)})")
    return obj


def _iter_jsonl_lines(stream: TextIO) -> Iterator[tuple[int, str]]:
    for i, line in enumerate(stream, start=1):
        if line.strip():
            yield i, line


def run_csv(
    csv_path: Path,
    bootstrap: str,
    topic: str,
    max_rows: int | None,
    sleep_ms: int,
    chunk_size: int,
) -> None:
    """
    Parcourt le CSV par chunks pour limiter la mémoire, envoie chaque ligne avec accusé « all ».
    """
    producer = _producer(bootstrap)
    sent = 0
    try:
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
            chunk = chunk.rename(columns=lambda c: c.strip())
            for _, row in chunk.iterrows():
                payload = _row_to_payload(row)
                _send_one(producer, topic, payload)
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


def run_jsonl(
    stream: TextIO,
    bootstrap: str,
    topic: str,
    max_rows: int | None,
    sleep_ms: int,
) -> None:
    """
    Lit un flux JSONL (une ligne = un objet JSON, même clés que le simulateur / le CSV mappé).
    """
    producer = _producer(bootstrap)
    sent = 0
    try:
        for line_no, line in _iter_jsonl_lines(stream):
            try:
                payload = _parse_jsonl_line(line, line_no)
            except ValueError as e:
                print(f"Erreur: {e}", file=sys.stderr)
                sys.exit(1)
            _send_one(producer, topic, payload)
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
    p = argparse.ArgumentParser(
        description="CSV ou JSONL -> Kafka (topic brut). "
        "Utilisez --jsonl - pour lire la sortie du simulateur (pipe)."
    )
    p.add_argument(
        "--csv",
        type=Path,
        default=None,
        help=f"Chemin du CSV FraudShield (défaut si pas de --jsonl: {CSV_DEFAULT_PATH})",
    )
    p.add_argument(
        "--jsonl",
        type=str,
        default=None,
        metavar="CHEMIN_OU_-",
        help="Fichier JSONL (une transaction JSON par ligne) ou « - » pour stdin (ex. pipe depuis le simulateur)",
    )
    p.add_argument(
        "--bootstrap",
        default=KAFKA_BOOTSTRAP_SERVERS,
        help="Serveurs Kafka (séparés par des virgules)",
    )
    p.add_argument("--topic", default=TOPIC_RAW, help="Topic de sortie")
    p.add_argument("--max-rows", type=int, default=None, help="Limite de messages (défaut: tout)")
    p.add_argument("--sleep-ms", type=int, default=0, help="Pause entre chaque message")
    p.add_argument("--chunk-size", type=int, default=5000, help="Taille des chunks pandas (mode CSV uniquement)")
    args = p.parse_args()

    csv_path = args.csv if args.csv is not None else CSV_DEFAULT_PATH

    if args.jsonl is not None:
        if args.jsonl == "-":
            run_jsonl(
                stream=sys.stdin,
                bootstrap=args.bootstrap,
                topic=args.topic,
                max_rows=args.max_rows,
                sleep_ms=args.sleep_ms,
            )
        else:
            path = Path(args.jsonl)
            if not path.is_file():
                print(f"Fichier introuvable: {path}", file=sys.stderr)
                sys.exit(1)
            with path.open(encoding="utf-8") as f:
                run_jsonl(
                    stream=f,
                    bootstrap=args.bootstrap,
                    topic=args.topic,
                    max_rows=args.max_rows,
                    sleep_ms=args.sleep_ms,
                )
        return

    if not csv_path.is_file():
        print(f"Fichier introuvable: {csv_path}", file=sys.stderr)
        sys.exit(1)
    run_csv(
        csv_path=csv_path,
        bootstrap=args.bootstrap,
        topic=args.topic,
        max_rows=args.max_rows,
        sleep_ms=args.sleep_ms,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
