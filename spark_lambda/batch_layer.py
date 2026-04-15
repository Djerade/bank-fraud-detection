#!/usr/bin/env python3
"""
Couche **batch** (Lambda) : lecture du lac **bronze** (alimenté par la couche vitesse),
parsing JSON transactions, agrégations, écriture **gold** (Parquet).

Si le bronze est vide, option ``--from-kafka`` : une passe batch sur Kafka (earliest → latest).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.functions import col, from_json, get_json_object, when
from pyspark.sql.types import LongType

from spark_lambda.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC,
    SPARK_BRONZE_PATH,
    SPARK_GOLD_PATH,
)
from spark_lambda.transaction_schema import TRANSACTION_SCHEMA


def _read_bronze(spark: SparkSession, path: str):
    p = Path(path)
    if not p.is_dir():
        return None
    try:
        if not any(p.iterdir()):
            return None
    except OSError:
        return None
    return spark.read.parquet(path)


def _read_kafka_batch(spark: SparkSession):
    return (
        spark.read.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "earliest")
        .option("endingOffsets", "latest")
        .load()
        .select(
            col("timestamp").alias("kafka_ts"),
            col("partition").alias("kafka_partition"),
            col("offset").alias("kafka_offset"),
            col("key").cast("string").alias("key"),
            col("value").cast("string").alias("raw_json"),
        )
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Lambda — couche batch (bronze → agrégats gold)")
    p.add_argument(
        "--from-kafka",
        action="store_true",
        help="Forcer la lecture Kafka (earliest → latest) même si le bronze existe",
    )
    p.add_argument(
        "--bronze-path",
        default=SPARK_BRONZE_PATH,
        help="Répertoire Parquet bronze",
    )
    p.add_argument(
        "--gold-path",
        default=SPARK_GOLD_PATH,
        help="Répertoire Parquet gold (écrasé à chaque run)",
    )
    args = p.parse_args()

    spark = SparkSession.builder.appName("bank-fraud-lambda-batch").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    if args.from_kafka:
        base = _read_kafka_batch(spark)
        print("[batch] source=Kafka (forcé par --from-kafka)", file=sys.stderr)
    else:
        loaded = _read_bronze(spark, args.bronze_path)
        if loaded is None:
            base = _read_kafka_batch(spark)
            print(
                "[batch] bronze vide ou absent → repli Kafka (batch unique earliest→latest). "
                "Lancez ``spark-speed`` pour alimenter le lac en continu.",
                file=sys.stderr,
            )
        else:
            base = loaded
            print(f"[batch] source=bronze {args.bronze_path!r}", file=sys.stderr)

    # Ne garder que les lignes qui ressemblent aux transactions simulateur (évite messages produceur.py).
    with_tx = base.filter(get_json_object(col("raw_json"), "$.transaction_id").isNotNull())

    tmp = with_tx.select(
        col("raw_json"),
        from_json(col("raw_json"), TRANSACTION_SCHEMA, {"mode": "PERMISSIVE"}).alias("t"),
    ).select(col("raw_json"), "t.*")

    fraud_col = (
        when(get_json_object(col("raw_json"), "$.fraud_label") == "Fraud", 1)
        .otherwise(0)
        .cast(LongType())
    )

    stats = tmp.select(
        F.count("*").alias("transaction_count"),
        F.sum(fraud_col).alias("fraud_count"),
        F.avg("transaction_amount_million").alias("avg_amount_million"),
    )

    stats.write.mode("overwrite").parquet(args.gold_path)

    stats.show(truncate=False)
    print(f"[batch] gold écrit : {args.gold_path!r}", file=sys.stderr)
    spark.stop()


if __name__ == "__main__":
    main()
