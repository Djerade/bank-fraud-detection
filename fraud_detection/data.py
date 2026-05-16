"""Chargement du jeu FraudShield (CSV brut ou features)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from fraud_scoring.features import enrich_features

TARGET = "Fraud_Label"
RAW_NAME = "FraudShield_Banking_Data.csv"
FEATURES_NAME = "FraudShield_Banking_Data_features.csv"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_data_file(name: str) -> Path | None:
    root = repo_root()
    for base in (root / "data", root / "docs", root):
        candidate = base / name
        if candidate.is_file():
            return candidate
    return None


def load_training_frame(
    *,
    data_path: Path | None = None,
    use_features_csv: bool = True,
) -> pd.DataFrame:
    """Charge le CSV ; enrichit les features si nécessaire."""
    if data_path is not None:
        path = Path(data_path)
        if not path.is_file():
            raise FileNotFoundError(path)
    elif use_features_csv:
        path = resolve_data_file(FEATURES_NAME)
        if path is None:
            path = resolve_data_file(RAW_NAME)
            if path is None:
                raise FileNotFoundError(
                    f"Aucun CSV trouvé ({FEATURES_NAME} ou {RAW_NAME} dans data/ ou docs/)."
                )
    else:
        path = resolve_data_file(RAW_NAME)
        if path is None:
            raise FileNotFoundError(f"{RAW_NAME} introuvable dans data/ ou docs/.")

    df = pd.read_csv(path)
    if TARGET not in df.columns:
        raise ValueError(f"Colonne cible « {TARGET} » absente de {path}")

    if path.name == RAW_NAME or "hour_sin" not in df.columns:
        df = enrich_features(df)
    return df
