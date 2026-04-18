"""
Alignement des messages Kafka (JSON simulateur, snake_case) sur le format d’entraînement
(CSV / noms pandas du notebook) puis **feature engineering** identique à ``exploration.ipynb``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# snake_case (simulateur / Kafka) → noms colonnes du CSV / notebook
JSON_TO_TRAINING_COLS: dict[str, str] = {
    "transaction_id": "Transaction_ID",
    "customer_id": "Customer_ID",
    "transaction_amount_million": "Transaction_Amount (in Million)",
    "transaction_time": "Transaction_Time",
    "transaction_date": "Transaction_Date",
    "transaction_type": "Transaction_Type",
    "merchant_id": "Merchant_ID",
    "merchant_category": "Merchant_Category",
    "transaction_location": "Transaction_Location",
    "customer_home_location": "Customer_Home_Location",
    "distance_from_home": "Distance_From_Home",
    "device_id": "Device_ID",
    "ip_address": "IP_Address",
    "card_type": "Card_Type",
    "account_balance_million": "Account_Balance (in Million)",
    "daily_transaction_count": "Daily_Transaction_Count",
    "weekly_transaction_count": "Weekly_Transaction_Count",
    "avg_transaction_amount_million": "Avg_Transaction_Amount (in Million)",
    "max_transaction_last_24h_million": "Max_Transaction_Last_24h (in Million)",
    "is_international_transaction": "Is_International_Transaction",
    "is_new_merchant": "Is_New_Merchant",
    "failed_transaction_count": "Failed_Transaction_Count",
    "unusual_time_transaction": "Unusual_Time_Transaction",
    "previous_fraud_count": "Previous_Fraud_Count",
    "fraud_label": "Fraud_Label",
}

EPS = 1e-6
AMT = "Transaction_Amount (in Million)"
AVG_AMT = "Avg_Transaction_Amount (in Million)"
MAX24 = "Max_Transaction_Last_24h (in Million)"

# Colonnes exclues du vecteur X (identique au notebook)
DROP_FOR_MODEL = {
    "Fraud_Label",
    "Transaction_ID",
    "Customer_ID",
    "IP_Address",
    "transaction_dt",
    "order_date_dt",
    "Transaction_Date",
    "Transaction_Time",
}


def _yes_no_int(x) -> float:
    if pd.isna(x):
        return np.nan
    s = str(x).strip().casefold()
    if s in ("yes", "y", "true", "1"):
        return 1.0
    if s in ("no", "n", "false", "0"):
        return 0.0
    return np.nan


def json_dict_to_training_dataframe(payload: dict) -> pd.DataFrame:
    """Une ligne DataFrame avec les noms de colonnes du jeu d’entraînement."""
    row: dict = {}
    for k, v in payload.items():
        lk = k.strip() if isinstance(k, str) else k
        if lk in JSON_TO_TRAINING_COLS:
            row[JSON_TO_TRAINING_COLS[lk]] = v
        elif k in JSON_TO_TRAINING_COLS.values():
            row[k] = v
    if not row:
        raise ValueError("Aucun champ reconnu dans le JSON (clés simulateur snake_case attendues).")
    return pd.DataFrame([row])


def enrich_features(df: pd.DataFrame) -> pd.DataFrame:
    """Même logique que le notebook (après nettoyage type trim sur les objets)."""
    df = df.copy()
    for _c in df.select_dtypes(include=["object"]).columns:
        df[_c] = df[_c].apply(lambda x: x.strip() if isinstance(x, str) else x)

    _t = pd.to_datetime(df["Transaction_Time"], format="%H:%M", errors="coerce")
    df["order_date_dt"] = pd.to_datetime(df["Transaction_Date"], errors="coerce")
    df["hour"] = _t.dt.hour
    df["minute"] = _t.dt.minute
    if df["hour"].isna().any():
        df["hour"] = df["hour"].fillna(df["hour"].median())
    if df["minute"].isna().any():
        df["minute"] = df["minute"].fillna(0)

    base = df["order_date_dt"].dt.normalize()
    df["transaction_dt"] = base + pd.to_timedelta(df["hour"], unit="h") + pd.to_timedelta(
        df["minute"], unit="min"
    )

    df["day_of_week"] = df["order_date_dt"].dt.dayofweek
    df["day_of_month"] = df["order_date_dt"].dt.day
    df["month"] = df["order_date_dt"].dt.month
    df["quarter"] = df["order_date_dt"].dt.quarter
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    h = df["hour"]
    df["is_night"] = ((h < 6) | (h >= 22)).astype(int)

    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24.0)
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7.0)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7.0)

    for col in ["Is_International_Transaction", "Is_New_Merchant", "Unusual_Time_Transaction"]:
        df[f"{col}_num"] = df[col].map(_yes_no_int).astype(float)

    df["log_transaction_amount"] = np.log1p(df[AMT].clip(lower=0))
    df["amount_vs_avg_ratio"] = df[AMT] / (df[AVG_AMT].abs() + EPS)
    df["amount_vs_max24_ratio"] = df[AMT] / (df[MAX24].abs() + EPS)

    return df


def build_model_input(df: pd.DataFrame) -> pd.DataFrame:
    """Retire les colonnes non utilisées par le pipeline sklearn (comme le notebook)."""
    cols = [c for c in df.columns if c not in DROP_FOR_MODEL]
    return df[cols]
