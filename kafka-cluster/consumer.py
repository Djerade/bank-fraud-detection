#!/usr/bin/env python3
"""
Consommateur minimal sur le cluster Kafka (kafka-python).

Usage (depuis la racine du dépôt, cluster déjà démarré) :
  python kafka-cluster/consumer.py
  python kafka-cluster/consumer.py --max 10
  python kafka-cluster/consumer.py --only-new --follow
  python kafka-cluster/consumer.py --max 100 --out-jsonl recu.jsonl --quiet

Ctrl+C pour arrêter si --follow ou si vous laissez tourner après --max.
"""
from __future__ import annotations

import argparse
import json
import sys

import _repo_root  # noqa: F401 — racine du dépôt pour Config
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from Config.config import TOPIC, bootstrap_servers_list


def main() -> None:
    p = argparse.ArgumentParser(description="Lit des messages JSON depuis un topic Kafka")
    p.add_argument(
        "--topic",
        default=TOPIC,
        help=f"Topic à lire (défaut : {TOPIC} / KAFKA_TOPIC)",
    )
    p.add_argument(
        "--from-beginning",
        action="store_true",
        help="Lire depuis le début du topic (comportement par défaut ; gardé pour compatibilité)",
    )
    p.add_argument(
        "--only-new",
        action="store_true",
        help="Ne lire que les messages produits après le démarrage (offset latest ; sans cela, tout l’historique)",
    )
    p.add_argument(
        "--max",
        type=int,
        default=None,
        help="Nombre maximum de messages puis arrêt (défaut : illimité)",
    )
    p.add_argument(
        "--follow",
        action="store_true",
        help="Après --max atteint ou sans --max, continuer à poller (temps réel)",
    )
    p.add_argument(
        "--group-id",
        default="kafka-cluster-cli-consumer",
        metavar="ID",
        help="Groupe consumer Kafka (changer de nom pour relire depuis le début si le groupe "
        "existant a déjà consommé tout le topic)",
    )
    p.add_argument(
        "--out-jsonl",
        metavar="FICHIER",
        default=None,
        help="Enregistre chaque valeur de message en une ligne JSON (NDJSON), prêt pour pandas ou scripts",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="N’affiche pas les lignes partition/offset/value sur stdout (utile avec --out-jsonl)",
    )
    args = p.parse_args()
    servers = bootstrap_servers_list()

    # Par défaut : earliest (sinon tout message déjà produit avant le consumer semble « invisible »).
    offset_mode = "latest" if args.only_new else "earliest"

    # Ne pas passer consumer_timeout_ms=None : kafka-python 2.x compare avec >= 0 et lève TypeError.
    # Défaut du client : attente illimitée entre polls dans l’itérateur.
    consumer = KafkaConsumer(
        args.topic,
        bootstrap_servers=servers,
        auto_offset_reset=offset_mode,
        enable_auto_commit=True,
        group_id=args.group_id,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")) if b else None,
    )

    print(
        f"Lecture topic={args.topic!r} group={args.group_id!r} brokers={servers} "
        f"auto_offset_reset={offset_mode!r}. Ctrl+C pour arrêter.",
        file=sys.stderr,
    )
    print(
        "Astuce : sans message, soit personne n’écrit sur le topic (lancez un producteur dans un "
        "autre terminal), soit ce groupe a déjà lu jusqu’à la fin — essayez "
        "--group-id lecteur-demo-1 pour repartir comme un nouveau lecteur (avec earliest).",
        file=sys.stderr,
    )

    out_f = open(args.out_jsonl, "a", encoding="utf-8") if args.out_jsonl else None
    received = 0
    try:
        for msg in consumer:
            received += 1
            if not args.quiet:
                print(
                    f"partition={msg.partition} offset={msg.offset} key={msg.key!r} "
                    f"value={msg.value!r}",
                    flush=True,
                )
            if out_f is not None and msg.value is not None:
                out_f.write(json.dumps(msg.value, ensure_ascii=False) + "\n")
                out_f.flush()
            if args.max is not None and received >= args.max and not args.follow:
                break
    except KafkaError as e:
        print(f"Erreur Kafka: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print(file=sys.stderr)
    finally:
        consumer.close()
        if out_f is not None:
            out_f.close()

    if received == 0:
        print(
            "Aucun message reçu : lancez un producteur (produceur.py, connecteur_api.py "
            "--to-kafka, ou simulateur --kafka), ou utilisez --group-id <nouveau> pour "
            "repartir de earliest si l’ancien groupe était déjà à jour du topic.",
            file=sys.stderr,
        )
    elif args.out_jsonl:
        print(f"Enregistré {received} message(s) dans {args.out_jsonl!r}.", file=sys.stderr)


if __name__ == "__main__":
    main()
