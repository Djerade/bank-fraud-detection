"""Chargement du modèle et scoring d'une transaction brute.

Source du modèle (par ordre de priorité) :
  1. Registry MLflow via ``FRAUD_MODEL_URI`` (ex. ``models:/fraud-classifier@champion``)
     si ``MLFLOW_TRACKING_URI`` est défini et le client MLflow disponible.
  2. Repli : joblib local ``FRAUD_MODEL_PATH`` (jamais de coupure de service).

Le feature engineering reste ``fraud_scoring.features`` (identique à l'entraînement).
Le modèle est rechargeable à chaud (``reload()``) sans redémarrer le service.
"""
from __future__ import annotations

import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import joblib

from fraud_scoring.features import (
    build_model_input,
    enrich_features,
    json_dict_to_training_dataframe,
    load_global_stats,
)


class Scorer:
    """Encapsule le pipeline sklearn ; Registry MLflow + repli joblib, thread-safe."""

    def __init__(self, model_path: str | Path) -> None:
        model_path = Path(model_path)
        if not model_path.is_file():
            alt = Path(__file__).resolve().parents[1] / "models" / "fraud_classifier.joblib"
            if alt.is_file():
                model_path = alt
        # Le joblib sert de repli : sa présence est requise même en mode Registry.
        if not model_path.is_file():
            raise FileNotFoundError(f"Modèle (repli) introuvable : {model_path}")

        self.model_path = model_path
        self.model_uri = os.environ.get("FRAUD_MODEL_URI", "").strip()
        self.tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "").strip()
        self._lock = threading.Lock()
        self.source: str = ""
        self.loaded_at: str = ""
        self.stats_loaded: bool = False
        self._load()

    def _load_pipeline(self) -> tuple[object, str]:
        """Charge depuis le Registry si possible, sinon depuis le joblib."""
        if self.model_uri and self.tracking_uri:
            try:
                import mlflow
                import mlflow.sklearn

                mlflow.set_tracking_uri(self.tracking_uri)
                pipeline = mlflow.sklearn.load_model(self.model_uri)
                return pipeline, self.model_uri
            except Exception as e:  # noqa: BLE001
                print(
                    f"[fraud-backend] Registry indisponible ({e}) → repli joblib.",
                    file=sys.stderr,
                )
        return joblib.load(self.model_path), str(self.model_path)

    def _load(self) -> None:
        pipeline, source = self._load_pipeline()
        stats_path = self.model_path.parent / "global_stats.json"
        load_global_stats(stats_path)  # stats globales figées à l'entraînement
        with self._lock:
            self.pipeline = pipeline
            self._has_proba = hasattr(pipeline, "predict_proba")
            self.source = source
            self.stats_loaded = stats_path.is_file()
            self.loaded_at = datetime.now(timezone.utc).isoformat()
        print(
            f"[fraud-backend] Modèle chargé depuis {source} "
            f"(stats={'oui' if self.stats_loaded else 'NON'})",
            file=sys.stderr,
        )

    def reload(self) -> dict:
        """Recharge le modèle (Registry ou joblib) + global_stats sans redémarrage."""
        self._load()
        return {
            "reloaded": True,
            "source": self.source,
            "loaded_at": self.loaded_at,
            "stats_loaded": self.stats_loaded,
        }

    def score(self, payload: dict) -> dict:
        """Retourne ``{fraud_predicted, fraud_score}`` pour une transaction brute JSON."""
        df0 = json_dict_to_training_dataframe(payload)
        df1 = enrich_features(df0)
        X = build_model_input(df1)

        with self._lock:
            pipeline = self.pipeline
            has_proba = self._has_proba

        pred = int(pipeline.predict(X)[0])
        proba: float | None = None
        if has_proba:
            proba = float(pipeline.predict_proba(X)[0, 1])
        return {"fraud_predicted": pred, "fraud_score": proba}
