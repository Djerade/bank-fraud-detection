"""
Configuration partagée : Kafka, chemins données, mapping CSV → JSON des messages.
Les variables d'environnement priment pour l'exécution en conteneur ou en local.
"""
from __future__ import annotations

import os
from pathlib import Path

# Racine du dépôt (parent de src/)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

KAFKA_BOOTSTRAP_SERVERS: str = os.environ.get(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)
TOPIC_RAW: str = os.environ.get("KAFKA_TOPIC_RAW", "bank.transactions.raw")
TOPIC_PROCESSED: str = os.environ.get(
    "KAFKA_TOPIC_PROCESSED",
    "bank.transactions.processed",
)
CSV_DEFAULT_PATH: Path = Path(
    os.environ.get("FRAUD_CSV_PATH", str(REPO_ROOT / "data" / "FraudShield_Banking_Data.csv"))
)

# Correspondance en-têtes CSV -> clés JSON (messages Kafka)
CSV_TO_JSON_FIELD: dict[str, str] = {
    "Transaction_ID": "transaction_id",
    "Customer_ID": "customer_id",
    "Transaction_Amount (in Million)": "transaction_amount_million",
    "Transaction_Time": "transaction_time",
    "Transaction_Date": "transaction_date",
    "Transaction_Type": "transaction_type",
    "Merchant_ID": "merchant_id",
    "Merchant_Category": "merchant_category",
    "Transaction_Location": "transaction_location",
    "Customer_Home_Location": "customer_home_location",
    "Distance_From_Home": "distance_from_home",
    "Device_ID": "device_id",
    "IP_Address": "ip_address",
    "Card_Type": "card_type",
    "Account_Balance (in Million)": "account_balance_million",
    "Daily_Transaction_Count": "daily_transaction_count",
    "Weekly_Transaction_Count": "weekly_transaction_count",
    "Avg_Transaction_Amount (in Million)": "avg_transaction_amount_million",
    "Max_Transaction_Last_24h (in Million)": "max_transaction_last_24h_million",
    "Is_International_Transaction": "is_international_transaction",
    "Is_New_Merchant": "is_new_merchant",
    "Failed_Transaction_Count": "failed_transaction_count",
    "Unusual_Time_Transaction": "unusual_time_transaction",
    "Previous_Fraud_Count": "previous_fraud_count",
    "Fraud_Label": "fraud_label",
}
