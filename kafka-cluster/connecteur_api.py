#!/usr/bin/env python3
"""
Connecteur HTTP : récupère le flux NDJSON de l’API simulateur (GET /transaction_continuous).

L’API doit tourner (ex. docker compose → http://127.0.0.1:8000).

Usage (depuis la racine du dépôt) :
  python kafka-cluster/connecteur_api.py
  python kafka-cluster/connecteur_api.py --max 20
  python kafka-cluster/connecteur_api.py --base-url http://127.0.0.1:8000 --fraud-rate 0.1

Variables d’environnement : SIMULATEUR_API_BASE (voir config.py).

Aucune dépendance HTTP supplémentaire (urllib stdlib).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from config import SIMULATEUR_API_BASE


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
        description="Lit le flux /transaction_continuous de l’API simulateur (NDJSON)."
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
        "--api-to-kafka",
        action="store_true",
        help="Passe to_kafka=true à l’API (l’API publie aussi sur Kafka en parallèle du flux HTTP)",
    )
    p.add_argument(
        "--max",
        type=int,
        default=None,
        help="Arrêt après ce nombre de transactions (défaut : illimité, Ctrl+C pour anrrêter)",
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

    url = _build_stream_url(
        args.base_url,
        fraud_rate=args.fraud_rate,
        to_kafka=args.api_to_kafka,
    )
    print(f"Connexion : {url}", file=sys.stderr)

    out_f = open(args.out_jsonl, "a", encoding="utf-8") if args.out_jsonl else None
    n = 0
    try:
        for row in iter_transactions_from_api(url):
            n += 1
            if not args.quiet:
                print(json.dumps(row, ensure_ascii=False), flush=True)
            if out_f is not None:
                out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                out_f.flush()
            if args.max is not None and n >= args.max:
                break
    except KeyboardInterrupt:
        print(file=sys.stderr)
    finally:
        if out_f is not None:
            out_f.close()

    print(f"Reçu {n} transaction(s).", file=sys.stderr)


if __name__ == "__main__":
    main()
