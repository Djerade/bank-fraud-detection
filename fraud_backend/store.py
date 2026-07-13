"""Tampon mémoire des transactions scorées + agrégation pour le dashboard.

Portage fidèle de ``fraud_dashboard/lib/kafka-buffer.ts`` (normalisation) et
``fraud_dashboard/lib/snapshot.ts`` (agrégation) : le JSON produit ici a la même
forme que celui attendu par le frontend Next.js (``DashboardSnapshot``).
"""
from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone

MAX_STORE: int | None = None
REFRESH_SECONDS = 2
ALERT_THRESHOLD = 0.7

_TX_TYPES = {"ATM", "POS", "Online"}
_CARD_TYPES = {"Visa", "Mastercard", "Amex", "Credit", "Debit"}
_MERCHANT_ALIASES = {"Electronics": "Retail", "Grocery": "Groceries"}
_MERCHANT_ALLOWED = {
    "Retail", "Travel", "Groceries", "Healthcare", "Entertainment",
    "ATM", "Electronics", "Grocery", "Fuel",
}


def _iso(dt: datetime) -> str:
    """ISO 8601 en UTC avec millisecondes et suffixe Z (comme Date.toISOString())."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
        f"{dt.microsecond // 1000:03d}Z"


def _coerce_merchant(raw: str) -> str:
    if raw in _MERCHANT_ALIASES:
        return _MERCHANT_ALIASES[raw]
    return raw if raw in _MERCHANT_ALLOWED else "Retail"


def _as_percent(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator * 100, 2)


def normalize(raw: dict) -> dict | None:
    """Transaction brute + champs de scoring → objet ``Transaction`` du frontend."""
    tid = raw.get("transaction_id")
    if tid is None:
        return None

    tt = str(raw.get("transaction_type") or "Online")
    transaction_type = tt if tt in _TX_TYPES else "Online"

    ct = str(raw.get("card_type") or "Credit")
    card_type = ct if ct in _CARD_TYPES else "Credit"

    try:
        amt = float(raw.get("transaction_amount_million"))
    except (TypeError, ValueError):
        amt = 0.0

    try:
        score = float(raw.get("fraud_score"))
    except (TypeError, ValueError):
        score = 0.0

    fraud_predicted = 1 if int(raw.get("fraud_predicted") or 0) == 1 else 0

    scored_at = raw.get("_scored_at")
    if isinstance(scored_at, (int, float)):
        timestamp = _iso(datetime.fromtimestamp(scored_at, tz=timezone.utc))
    else:
        d, t = raw.get("transaction_date"), raw.get("transaction_time")
        timestamp = None
        if isinstance(d, str) and isinstance(t, str):
            padded = f"{t}:00" if len(t) == 5 else t
            try:
                timestamp = _iso(datetime.fromisoformat(f"{d}T{padded}"))
            except ValueError:
                timestamp = None
        if timestamp is None:
            timestamp = _iso(datetime.now(timezone.utc))

    return {
        "transaction_id": str(tid),
        "customer_id": str(raw.get("customer_id")) if raw.get("customer_id") is not None else "",
        "transaction_type": transaction_type,
        "merchant_category": _coerce_merchant(str(raw.get("merchant_category") or "Retail")),
        "transaction_location": str(raw.get("transaction_location") or ""),
        "card_type": card_type,
        "transaction_amount_million": amt,
        "fraud_score": score,
        "fraud_predicted": fraud_predicted,
        "timestamp": timestamp,
    }


class Store:
    """Tampon thread-safe de l'historique complet des transactions scorées (mémoire du process)."""

    def __init__(self, maxlen: int | None = MAX_STORE) -> None:
        self._rows: deque[dict] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, tx: dict) -> None:
        with self._lock:
            self._rows.append(tx)

    def __len__(self) -> int:
        return len(self._rows)

    def snapshot(self) -> dict:
        with self._lock:
            rows = list(self._rows)
        return build_snapshot(rows)


def _score_histogram(rows: list[dict]) -> list[dict]:
    bins = [
        {"bucket": f"{i / 10:.1f}-{(i + 1) / 10:.1f}", "count": 0}
        for i in range(10)
    ]
    for tx in rows:
        s = tx["fraud_score"]
        s = min(0.9999, max(0.0, s)) if isinstance(s, (int, float)) else 0.0
        bins[min(9, int(s * 10))]["count"] += 1
    return bins


def _group_by(rows: list[dict], key: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for tx in rows:
        k = tx[key]
        cur = out.setdefault(k, {"volume": 0, "alerts": 0})
        cur["volume"] += 1
        cur["alerts"] += tx["fraud_predicted"]
    return out


def build_snapshot(rows: list[dict], *, source: str = "kafka") -> dict:
    total = len(rows)
    alerts = sum(tx["fraud_predicted"] for tx in rows)
    critical = [tx for tx in rows if tx["fraud_score"] >= ALERT_THRESHOLD]
    unique_clients = len({tx["customer_id"] for tx in rows})
    avg_amount = (
        sum(tx["transaction_amount_million"] for tx in rows) / max(1, total)
    )

    # Séries par minute (20 dernières minutes présentes)
    by_minute: dict[str, dict] = {}
    for tx in rows:
        dt = datetime.fromisoformat(tx["timestamp"].replace("Z", "+00:00"))
        key = _iso(dt.replace(second=0, microsecond=0))
        cur = by_minute.setdefault(key, {"volume": 0, "alerts": 0})
        cur["volume"] += 1
        cur["alerts"] += tx["fraud_predicted"]
    series = [
        {
            "minute": minute,
            "volume": item["volume"],
            "alerts": item["alerts"],
            "alertRatePct": _as_percent(item["alerts"], item["volume"]),
        }
        for minute, item in sorted(by_minute.items())[-20:]
    ]

    by_type = sorted(
        (
            {"name": name, "volume": v["volume"], "alerts": v["alerts"]}
            for name, v in _group_by(rows, "transaction_type").items()
        ),
        key=lambda x: x["volume"],
        reverse=True,
    )

    by_merchant = sorted(
        (
            {
                "name": name,
                "volume": v["volume"],
                "alerts": v["alerts"],
                "ratePct": _as_percent(v["alerts"], v["volume"]),
            }
            for name, v in _group_by(rows, "merchant_category").items()
        ),
        key=lambda x: x["alerts"],
        reverse=True,
    )

    by_location = sorted(
        (
            {
                "name": name,
                "alerts": v["alerts"],
                "ratePct": _as_percent(v["alerts"], v["volume"]),
            }
            for name, v in _group_by(rows, "transaction_location").items()
        ),
        key=lambda x: x["alerts"],
        reverse=True,
    )[:8]

    return {
        "meta": {
            "source": source,
            "updatedAt": _iso(datetime.now(timezone.utc)),
            "refreshSeconds": REFRESH_SECONDS,
        },
        "metrics": {
            "total": total,
            "alerts": alerts,
            "alertRatePct": _as_percent(alerts, total),
            "criticalAlerts": len(critical),
            "avgAmountM": round(avg_amount, 3),
            "uniqueClients": unique_clients,
        },
        "series": series,
        "byType": by_type,
        "byMerchant": by_merchant,
        "byLocation": by_location,
        "scoreDistribution": _score_histogram(rows),
        "criticalTransactions": sorted(
            critical, key=lambda t: t["fraud_score"], reverse=True
        )[:100],
        "recentTransactions": sorted(
            rows, key=lambda t: t["timestamp"], reverse=True
        )[:250],
    }
