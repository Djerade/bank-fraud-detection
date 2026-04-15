#!/usr/bin/env python3
"""
Couche **vitesse** (Lambda) : Structured Streaming Kafka → lac bronze (Parquet) + console.

Lance avec ``spark-submit`` et le package ``spark-sql-kafka-0-10`` (voir ``spark/Dockerfile`` / compose).
"""
from __future__ import annotations

import argparse
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col

from spark_lambda.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC,
    SPARK_BRONZE_PATH,
    SPARK_CHECKPOINT_SPEED,
)


def main() -> None:
    p = argparse.ArgumentParser(description="Lambda — couche vitesse (Kafka → bronze Parquet)")
    p.add_argument(
        "--trigger-seconds",
        type=int,
        default=10,
        help="Intervalle micro-batch (processingTime)",
    )
    args = p.parse_args()

    spark = SparkSession.builder.appName("bank-fraud-lambda-speed").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    print(
        f"[speed] bootstrap={KAFKA_BOOTSTRAP_SERVERS!r} topic={KAFKA_TOPIC!r} "
        f"bronze={SPARK_BRONZE_PATH!r} checkpoint={SPARK_CHECKPOINT_SPEED!r}",
        file=sys.stderr,
    )

    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "earliest")
        .load()
    )

    bronze = raw.select(
        col("timestamp").alias("kafka_ts"),
        col("partition").alias("kafka_partition"),
        col("offset").alias("kafka_offset"),
        col("key").cast("string").alias("key"),
        col("value").cast("string").alias("raw_json"),
    )

    q = (
        bronze.writeStream.outputMode("append")
        .format("parquet")
        .option("path", SPARK_BRONZE_PATH)
        .option("checkpointLocation", SPARK_CHECKPOINT_SPEED)
        .trigger(processingTime=f"{args.trigger_seconds} seconds")
        .start()
    )

    try:
        q.awaitTermination()
    except KeyboardInterrupt:
        print("[speed] arrêt demandé.", file=sys.stderr)
        q.stop()
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
