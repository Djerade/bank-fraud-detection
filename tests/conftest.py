"""Fixtures partagées : une transaction brute au format simulateur (snake_case)."""
from __future__ import annotations

import pytest


@pytest.fixture
def raw_payload() -> dict:
    """Transaction telle que produite par le simulateur / connecteur sur Kafka."""
    return {
        "transaction_id": 865478.0,
        "customer_id": 29968.0,
        "transaction_amount_million": 9.0,
        "transaction_time": "21:13",
        "transaction_date": "2025-06-14",
        "transaction_type": "POS",
        "merchant_id": 64885.0,
        "merchant_category": "ATM",
        "transaction_location": "Karachi",
        "customer_home_location": "London",
        "distance_from_home": 552.0,
        "device_id": 911686.0,
        "ip_address": "195.167.146.58",
        "card_type": "Debit",
        "account_balance_million": 11.0,
        "daily_transaction_count": 2.0,
        "weekly_transaction_count": 16.0,
        "avg_transaction_amount_million": 2.0,
        "max_transaction_last_24h_million": 10.0,
        "is_international_transaction": "Yes",
        "is_new_merchant": "Yes",
        "failed_transaction_count": 2.0,
        "unusual_time_transaction": "Yes",
        "previous_fraud_count": 2.0,
    }
