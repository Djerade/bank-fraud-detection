#!/usr/bin/env python3
"""
Benchmark de latence end-to-end : Kafka raw → topic scoré (OS 5.2).

Injecte des transactions avec un timestamp ``_sent_at`` dans le topic brut,
lit le topic scoré et calcule la latence (P50 / P95 / P99) pour quatre
niveaux de charge : 1 000, 5 000, 15 000 et 30 000 transactions/s.

Usage (Kafka en cours, depuis la racine du dépôt) :
  PYTHONPATH=. python scripts/benchmark_latency.py
  PYTHONPATH=. python scripts/benchmark_latency.py --tps 1000 5000 --messages 2000

Depuis Docker :
  docker compose exec simulateur-api bash -lc \
    "cd /app && PYTHONPATH=. python scripts/benchmark_latency.py --messages 2000"
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

from Config.config import BOOTSTRAP_SERVERS, TOPIC, TOPIC_SCORED
from simulateur.transaction_simulator import generate_transaction
import random

TPS_LEVELS = [1_000, 5_000, 15_000, 30_000]
DEFAULT_MESSAGES = 5_000
CONSUMER_TIMEOUT_S = 90


def _make_producer(bootstrap: list[str]) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=bootstrap,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        key_serializer=lambda k: str(k).encode("utf-8") if k is not None else None,
        acks=1,
        batch_size=65_536,
        linger_ms=5,
        compression_type="gzip",
    )


def _make_consumer(bootstrap: list[str], topic: str) -> KafkaConsumer:
    return KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        group_id=f"bench-{int(time.time())}",
        auto_offset_reset="latest",
        enable_auto_commit=True,
        consumer_timeout_ms=500,
        fetch_max_bytes=52_428_800,
    )


def _produce_burst(
    producer: KafkaProducer,
    topic: str,
    tps: int,
    n: int,
    batch_id: str,
) -> dict[str, float]:
    """Envoie n messages à target TPS ; retourne {bench_id: sent_at}."""
    rng = random.Random()
    interval = 1.0 / tps
    sent: dict[str, float] = {}
    next_send = time.perf_counter()

    for i in range(n):
        tx = generate_transaction(rng)
        bench_id = f"{batch_id}-{i}"
        tx["_bench_id"] = bench_id
        tx["_sent_at"] = time.time()
        try:
            producer.send(topic, value=tx, key=bench_id)
            sent[bench_id] = tx["_sent_at"]
        except KafkaError as exc:
            print(f"[producer] erreur : {exc}", file=sys.stderr)

        next_send += interval
        sleep = next_send - time.perf_counter()
        if sleep > 0:
            time.sleep(sleep)

    producer.flush()
    return sent


def _collect_scored(
    consumer: KafkaConsumer,
    expected: set[str],
    timeout_s: float,
) -> dict[str, float]:
    """Lit le topic scoré jusqu'à avoir tous les bench_ids ou timeout."""
    arrived: dict[str, float] = {}
    deadline = time.time() + timeout_s

    while len(arrived) < len(expected) and time.time() < deadline:
        records = consumer.poll(timeout_ms=600)
        for _, msgs in records.items():
            for msg in msgs:
                v = msg.value
                if not isinstance(v, dict):
                    continue
                bid = v.get("_bench_id")
                if bid and bid in expected and bid not in arrived:
                    arrived[bid] = float(v.get("_scored_at", time.time()))
    return arrived


def _percentiles(values: list[float]) -> tuple[float, float, float]:
    a = np.array(values)
    return float(np.percentile(a, 50)), float(np.percentile(a, 95)), float(np.percentile(a, 99))


def run_benchmark(
    bootstrap_str: str,
    topic_raw: str,
    topic_scored: str,
    tps_levels: list[int],
    n_messages: int,
    timeout_s: float,
) -> list[dict]:
    servers = [h.strip() for h in bootstrap_str.split(",") if h.strip()]
    producer = _make_producer(servers)
    consumer = _make_consumer(servers, topic_scored)

    # Avancer le consumer à la fin du topic pour ne lire que les nouveaux messages
    consumer.poll(timeout_ms=1_000)
    consumer.seek_to_end()

    results = []

    for tps in tps_levels:
        print(f"\n{'='*60}", flush=True)
        print(f"Niveau de charge  : {tps:>8,} TPS | Messages envoyés : {n_messages:,}", flush=True)

        batch_id = str(uuid.uuid4())[:12]

        t0 = time.perf_counter()
        sent = _produce_burst(producer, topic_raw, tps, n_messages, batch_id)
        t1 = time.perf_counter()

        actual_tps = len(sent) / (t1 - t0) if (t1 - t0) > 0 else 0.0
        print(f"Envoyés           : {len(sent):,} | TPS réel : {actual_tps:,.0f}", flush=True)
        print(f"Attente scoring (timeout {timeout_s}s)...", flush=True)

        arrived = _collect_scored(consumer, set(sent.keys()), timeout_s)
        received_pct = len(arrived) / len(sent) * 100 if sent else 0.0
        print(f"Scorés reçus      : {len(arrived):,} / {len(sent):,}  ({received_pct:.1f} %)", flush=True)

        latencies_ms = [
            (arrived[bid] - sent[bid]) * 1_000
            for bid in arrived
            if bid in sent and (arrived[bid] - sent[bid]) > 0
        ]

        if latencies_ms:
            p50, p95, p99 = _percentiles(latencies_ms)
            print(f"Latence E2E       →  P50: {p50:7.1f} ms | P95: {p95:7.1f} ms | P99: {p99:7.1f} ms", flush=True)
            results.append({
                "tps_target": tps,
                "tps_actual": round(actual_tps),
                "sent": len(sent),
                "received": len(arrived),
                "received_pct": round(received_pct, 1),
                "p50_ms": round(p50, 1),
                "p95_ms": round(p95, 1),
                "p99_ms": round(p99, 1),
            })
        else:
            print("Aucune mesure (scorer pas assez rapide ou timeout dépassé).", flush=True)
            results.append({
                "tps_target": tps,
                "tps_actual": round(actual_tps),
                "sent": len(sent),
                "received": 0,
                "received_pct": 0.0,
                "p50_ms": None,
                "p95_ms": None,
                "p99_ms": None,
            })

        # Pause entre niveaux pour laisser le scorer se vider
        time.sleep(10)

    producer.close()
    consumer.close()

    # ── Tableau récapitulatif ─────────────────────────────────────────────────
    print(f"\n{'='*72}", flush=True)
    print("RÉSUMÉ BENCHMARK — LATENCE END-TO-END (Kafka raw → topic scoré)", flush=True)
    print(f"{'='*72}", flush=True)
    header = f"{'TPS cible':>10} {'TPS réel':>9} {'Envoyés':>8} {'Reçus':>7} {'%':>5}  {'P50 ms':>8} {'P95 ms':>8} {'P99 ms':>8}"
    print(header, flush=True)
    print("-" * 72, flush=True)
    for r in results:
        p50 = f"{r['p50_ms']:8.1f}" if r["p50_ms"] is not None else "     N/A"
        p95 = f"{r['p95_ms']:8.1f}" if r["p95_ms"] is not None else "     N/A"
        p99 = f"{r['p99_ms']:8.1f}" if r["p99_ms"] is not None else "     N/A"
        print(
            f"{r['tps_target']:>10,} {r['tps_actual']:>9,} {r['sent']:>8,} "
            f"{r['received']:>7,} {r['received_pct']:>4.0f}%  {p50} {p95} {p99}",
            flush=True,
        )

    return results


def main() -> None:
    p = argparse.ArgumentParser(
        description="Benchmark latence E2E Kafka raw → scored (OS 5.2)"
    )
    p.add_argument(
        "--bootstrap",
        default=BOOTSTRAP_SERVERS,
        help=f"Brokers Kafka (défaut : {BOOTSTRAP_SERVERS})",
    )
    p.add_argument("--topic-raw", default=TOPIC, help="Topic brut (source)")
    p.add_argument("--topic-scored", default=TOPIC_SCORED, help="Topic scoré (destination)")
    p.add_argument(
        "--messages",
        type=int,
        default=DEFAULT_MESSAGES,
        help=f"Messages envoyés par niveau de charge (défaut : {DEFAULT_MESSAGES})",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=CONSUMER_TIMEOUT_S,
        help=f"Timeout (s) pour la collecte des scores (défaut : {CONSUMER_TIMEOUT_S})",
    )
    p.add_argument(
        "--tps",
        nargs="+",
        type=int,
        default=TPS_LEVELS,
        help="Niveaux de charge TPS à tester (défaut : 1000 5000 15000 30000)",
    )
    args = p.parse_args()

    run_benchmark(
        bootstrap_str=args.bootstrap,
        topic_raw=args.topic_raw,
        topic_scored=args.topic_scored,
        tps_levels=args.tps,
        n_messages=args.messages,
        timeout_s=args.timeout,
    )


if __name__ == "__main__":
    main()
