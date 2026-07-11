"""Garde-fous anti training/serving skew.

Ces tests auraient attrapé l'incident où le modèle réclamait des colonnes
(`_num`, dummies one-hot) que ``fraud_scoring.features`` ne produisait pas.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import fraud_scoring.features as F
from fraud_scoring.features import (
    build_model_input,
    enrich_features,
    json_dict_to_training_dataframe,
)

REPO = Path(__file__).resolve().parents[1]
MODEL = REPO / "models" / "fraud_classifier.joblib"
STATS = REPO / "models" / "global_stats.json"


def _build_X(payload: dict):
    return build_model_input(enrich_features(json_dict_to_training_dataframe(payload)))


def test_all_simulateur_keys_are_mapped(raw_payload):
    """Chaque clé JSON du simulateur (hors label) doit être connue du mapping."""
    known = set(F.JSON_TO_TRAINING_COLS)
    unknown = set(raw_payload) - known
    assert not unknown, f"Clés simulateur non mappées : {unknown}"


def test_no_nan_when_stats_loaded(raw_payload, monkeypatch):
    """Avec des stats globales, une transaction unique ne produit aucun NaN."""
    monkeypatch.setattr(
        F, "_GLOBAL_STATS",
        {"amt_mean": 5.0, "amt_std": 2.5, "amt_q25": 3.0, "amt_q75": 7.0},
    )
    X = _build_X(raw_payload)
    n_nan = int(X.isna().sum().sum())
    assert n_nan == 0, f"{n_nan} NaN dans le vecteur de features"


def test_drop_lists_are_consistent():
    """DROP_COLS (entraînement) et DROP_FOR_MODEL (scoring) ne doivent pas diverger."""
    from fraud_detection.ml import DROP_COLS

    assert set(DROP_COLS) == set(F.DROP_FOR_MODEL), (
        "Les colonnes exclues divergent entre entraînement et scoring "
        "→ risque de training/serving skew."
    )


def test_dropped_columns_absent_from_model_input(raw_payload):
    """Les identifiants / colonnes brutes ne doivent jamais atteindre le modèle."""
    X = _build_X(raw_payload)
    leaked = set(X.columns) & set(F.DROP_FOR_MODEL)
    assert not leaked, f"Colonnes qui n'auraient pas dû rester : {leaked}"


@pytest.mark.skipif(not MODEL.is_file(), reason="modèle non présent (models/fraud_classifier.joblib)")
def test_model_scores_sample_transaction(raw_payload):
    """INTÉGRATION : le modèle exporté doit scorer une transaction brute sans erreur.

    Reproduit exactement le bug 'columns are missing' : si le modèle et
    features.py sont désalignés, ce test échoue.
    """
    from fraud_backend.scoring import Scorer

    scorer = Scorer(MODEL)
    result = scorer.score(raw_payload)
    assert result["fraud_predicted"] in (0, 1)
    if result["fraud_score"] is not None:
        assert 0.0 <= result["fraud_score"] <= 1.0
