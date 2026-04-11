#!/usr/bin/env python3
"""
Connecteur HTTP : récupère le flux NDJSON de l’API simulateur (GET /transaction_continuous).

Publication **Kafka** côté connecteur (pont API → topic) :

  python kafka-cluster/connecteur_api.py --to-kafka --max 100
  # Docker (API et Kafka joignables depuis simulateur-api) :
  docker compose exec simulateur-api bash -lc \\
    "cd /app/kafka-cluster && python connecteur_api.py --to-kafka --max 50 --base-url http://127.0.0.1:8000"

Par défaut l’URL utilise ``to_kafka=false`` : seul ce script envoie sur Kafka si vous passez
``--to-kafka``. Utilisez ``--api-to-kafka`` seulement si vous voulez **aussi** que l’API
publie en parallèle (doublons sur le topic).

Variables d’environnement : ``SIMULATEUR_API_BASE``, ``KAFKA_BOOTSTRAP_SERVERS``, ``KAFKA_TOPIC``
(voir ``Config/config.py``).

HTTP : urllib (stdlib). Kafka : kafka-python.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

import _repo_root  # noqa: F401 — racine du dépôt pour Config
from Config.config import SIMULATEUR_API_BASE, TOPIC, bootstrap_servers_list


def _build_stream_url(
    base: str,
    *,
    fraud_rate: float,
    to_kafka: bool,
) -> str:
    base = base.rstrip("/")
    q = urllib.parse.urlencode(
        {
            "fraud_rate": fraud_rate,
            "to_kafka": str(to_kafka).lower(),
        }
    )
    return f"{base}/transaction_continuous?{q}"


def iter_transactions_from_api(url: str):
    """Itère sur les objets JSON (une ligne NDJSON = une transaction)."""
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/x-ndjson, application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=None) as resp:
            while True:
                raw = resp.readline()
                if not raw:
                    break
                line = raw.decode("utf-8").strip()
                if not line:
                    continue
                yield json.loads(line)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.reason}", file=sys.stderr)
        if e.fp:
            body = e.fp.read().decode("utf-8", errors="replace")
            if body:
                print(body[:2000], file=sys.stderr)
        raise SystemExit(1) from e
    except urllib.error.URLError as e:
        print(f"Connexion impossible : {e.reason}", file=sys.stderr)
        print("L’API est-elle démarrée ? (uvicorn ou docker compose)", file=sys.stderr)
        raise SystemExit(1) from e


def main() -> None:
    p = argparse.ArgumentParser(
        description="Lit le flux /transaction_continuous (NDJSON) ; option --to-kafka pour publier sur Kafka."
    )
    p.add_argument(
        "--base-url",
        default=SIMULATEUR_API_BASE,
        help="URL de base de l’API (défaut : env SIMULATEUR_API_BASE ou http://127.0.0.1:8000)",
    )
    p.add_argument(
        "--fraud-rate",
        type=float,
        default=0.02,
        help="Transmis à l’API (query fraud_rate)",
    )
    p.add_argument(
        "--to-kafka",
        action="store_true",
        help="Publie chaque transaction reçue sur le topic Kafka (Config / --topic)",
    )
    p.add_argument(
        "--topic",
        default=None,
        help=f"Topic Kafka si --to-kafka (défaut : {TOPIC} / KAFKA_TOPIC)",
    )
    p.add_argument(
        "--api-to-kafka",
        action="store_true",
        help="Passe to_kafka=true à l’API (doublons si combiné avec --to-kafka)",
    )
    p.add_argument(
        "--max",
        type=int,
        default=None,
        help="Arrêt après ce nombre de transactions (défaut : illimité, Ctrl+C pour arrêter)",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="N’affiche pas chaque ligne JSON sur stdout (compte seulement)",
    )
    p.add_argument(
        "--out-jsonl",
        type=str,
        default=None,
        help="Écrit aussi chaque transaction en une ligne dans ce fichier",
    )
    args = p.parse_args()

    if args.to_kafka and args.api_to_kafka:
        print(
            "Attention : --to-kafka et --api-to-kafka → chaque message peut être publié **deux fois**.",
            file=sys.stderr,
        )

    url = _build_stream_url(
        args.base_url,
        fraud_rate=args.fraud_rate,
        to_kafka=args.api_to_kafka,
    )
    print(f"Connexion : {url}", file=sys.stderr)

    kafka_topic = args.topic or TOPIC
    producer = None
    if args.to_kafka:
        from kafka import KafkaProducer

        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers_list(),
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: str(k).encode("utf-8") if k is not None else None,
            acks="all",
            retries=3,
        )
        print(
            f"Publication Kafka activée → topic={kafka_topic!r} brokers={bootstrap_servers_list()}",
            file=sys.stderr,
        )

    out_f = open(args.out_jsonl, "a", encoding="utf-8") if args.out_jsonl else None
    n = 0
    kafka_sent = 0
    try:
        for row in iter_transactions_from_api(url):
            n += 1
            if not args.quiet:
                print(json.dumps(row, ensure_ascii=False), flush=True)
            if out_f is not None:
                out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                out_f.flush()
            if producer is not None:
                key = row.get("transaction_id")
                try:
                    future = producer.send(kafka_topic, value=row, key=key)
                    future.get(timeout=15)
                    kafka_sent += 1
                except Exception as e:
                    print(f"Erreur envoi Kafka : {e}", file=sys.stderr)
                    raise SystemExit(1) from e
            if args.max is not None and n >= args.max:
                break
    except KeyboardInterrupt:
        print(file=sys.stderr)
    finally:
        if producer is not None:
            producer.flush()
            producer.close()
        if out_f is not None:
            out_f.close()

    print(f"Reçu {n} transaction(s).", file=sys.stderr)
    if producer is not None:
        print(f"Publié sur Kafka : {kafka_sent} message(s).", file=sys.stderr)


if __name__ == "__main__":
    main()
