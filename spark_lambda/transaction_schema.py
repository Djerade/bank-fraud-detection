"""Schéma Spark pour les transactions JSON (simulateur / pipeline FraudShield)."""
from __future__ import annotations

from pyspark.sql.types import (
    DoubleType,
    StringType,
    StructField,
    StructType,
)

# Champs alignés sur ``simulateur.transaction_simulator.generate_transaction``.
TRANSACTION_SCHEMA: StructType = StructType(
    [
        StructField("transaction_id", DoubleType(), True),
        StructField("customer_id", DoubleType(), True),
        StructField("transaction_amount_million", DoubleType(), True),
        StructField("transaction_time", StringType(), True),
        StructField("transaction_date", StringType(), True),
        StructField("transaction_type", StringType(), True),
        StructField("merchant_id", DoubleType(), True),
        StructField("merchant_category", StringType(), True),
        StructField("transaction_location", StringType(), True),
        StructField("customer_home_location", StringType(), True),
        StructField("distance_from_home", DoubleType(), True),
        StructField("device_id", DoubleType(), True),
        StructField("ip_address", StringType(), True),
        StructField("card_type", StringType(), True),
        StructField("account_balance_million", DoubleType(), True),
        StructField("daily_transaction_count", DoubleType(), True),
        StructField("weekly_transaction_count", DoubleType(), True),
        StructField("avg_transaction_amount_million", DoubleType(), True),
        StructField("max_transaction_last_24h_million", DoubleType(), True),
        StructField("is_international_transaction", StringType(), True),
        StructField("is_new_merchant", StringType(), True),
        StructField("failed_transaction_count", DoubleType(), True),
        StructField("unusual_time_transaction", StringType(), True),
        StructField("previous_fraud_count", DoubleType(), True),
    ]
)
