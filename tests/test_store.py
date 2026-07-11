"""Tests de l'agrégation du backend (normalisation + snapshot)."""
from __future__ import annotations

from fraud_backend.store import ALERT_THRESHOLD, build_snapshot, normalize


def _scored(**over) -> dict:
    base = {
        "transaction_id": 1,
        "customer_id": 10,
        "transaction_type": "POS",
        "merchant_category": "Grocery",
        "transaction_location": "Karachi",
        "card_type": "Debit",
        "transaction_amount_million": 4.0,
        "fraud_predicted": 0,
        "fraud_score": 0.2,
        "_scored_at": 1_752_000_000.0,
    }
    base.update(over)
    return normalize(base)


def test_normalize_coerces_unknown_categories():
    tx = _scored(transaction_type="WEIRD", card_type="Bitcoin", merchant_category="Restaurant")
    assert tx["transaction_type"] == "Online"   # inconnu → défaut
    assert tx["card_type"] == "Credit"          # inconnu → défaut
    assert tx["merchant_category"] == "Retail"  # inconnu → défaut


def test_normalize_maps_merchant_aliases():
    assert _scored(merchant_category="Grocery")["merchant_category"] == "Groceries"
    assert _scored(merchant_category="Electronics")["merchant_category"] == "Retail"


def test_normalize_requires_transaction_id():
    assert normalize({"customer_id": 1}) is None


def test_build_snapshot_metrics():
    rows = [
        _scored(customer_id=1, fraud_predicted=1, fraud_score=0.85),
        _scored(customer_id=2, fraud_predicted=0, fraud_score=0.10),
        _scored(customer_id=2, fraud_predicted=1, fraud_score=0.50),
    ]
    snap = build_snapshot(rows)
    m = snap["metrics"]
    assert m["total"] == 3
    assert m["alerts"] == 2                       # deux fraud_predicted == 1
    assert m["uniqueClients"] == 2                # clients 1 et 2
    assert m["criticalAlerts"] == 1               # un seul score >= 0.7
    assert m["alertRatePct"] == round(2 / 3 * 100, 2)


def test_build_snapshot_shape():
    snap = build_snapshot([_scored()])
    for key in (
        "meta", "metrics", "series", "byType", "byMerchant",
        "byLocation", "scoreDistribution", "criticalTransactions", "recentTransactions",
    ):
        assert key in snap
    assert len(snap["scoreDistribution"]) == 10   # 10 bacs d'histogramme
    assert snap["meta"]["source"] == "kafka"


def test_alert_threshold_constant():
    assert 0.0 < ALERT_THRESHOLD <= 1.0
