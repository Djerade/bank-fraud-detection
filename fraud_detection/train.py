#!/usr/bin/env python3
"""
Entraîne la shortlist de classificateurs et journalise dans MLflow (Docker uniquement).

  docker compose up -d --build          # ml-train-init si modèle absent
  docker compose run --rm ml-train      # ré-entraînement manuel
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.models import infer_signature

from fraud_detection.data import TARGET, load_training_frame, repo_root
from fraud_detection.ml import (
    RANDOM_STATE,
    TEST_SIZE,
    build_preprocessor,
    classifiers,
    fit_and_metrics,
    pick_best,
    split_data,
)


def _tracking_uri(args: argparse.Namespace) -> str:
    return (
        args.tracking_uri
        or os.environ.get("MLFLOW_TRACKING_URI")
        or "http://mlflow:5000"
    )


def _experiment_name(args: argparse.Namespace) -> str:
    return (
        args.experiment_name
        or os.environ.get("MLFLOW_EXPERIMENT_NAME")
        or "bank-fraud-detection"
    )


def run_training(args: argparse.Namespace) -> None:
    df = load_training_frame(
        data_path=Path(args.data_path) if args.data_path else None,
        use_features_csv=not args.raw_only,
    )

    X_train, X_test, y_train, y_test = split_data(
        df,
        test_size=args.test_size,
        random_state=args.random_state,
    )
    preprocessor = build_preprocessor(X_train)

    mlflow.set_tracking_uri(_tracking_uri(args))
    mlflow.set_experiment(_experiment_name(args))

    fitted: dict[str, object] = {}
    results: list[dict] = []

    with mlflow.start_run(run_name=args.run_name or "fraud-shortlist") as parent:
        mlflow.log_param("dataset_rows", len(df))
        mlflow.log_param("train_rows", len(y_train))
        mlflow.log_param("test_rows", len(y_test))
        mlflow.log_param("test_size", args.test_size)
        mlflow.log_param("random_state", args.random_state)
        mlflow.log_param("fraud_rate_train", float(y_train.mean()))
        mlflow.log_param("fraud_rate_test", float(y_test.mean()))

        for name, clf in classifiers(random_state=args.random_state).items():
            with mlflow.start_run(run_name=name, nested=True):
                row, pipe = fit_and_metrics(
                    name, clf, preprocessor, X_train, y_train, X_test, y_test
                )
                results.append(row)
                for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
                    if key in row and row[key] == row[key]:  # not NaN
                        mlflow.log_metric(key, float(row[key]))
                if row.get("error"):
                    mlflow.log_param("error", row["error"])
                    continue
                if pipe is not None:
                    fitted[name] = pipe
                    mlflow.sklearn.log_model(
                        pipe,
                        artifact_path="model",
                        registered_model_name=None,
                    )

        best_row = pick_best(results)
        best_name = str(best_row["model"])
        best_pipe = fitted[best_name]

        mlflow.log_param("best_model", best_name)
        for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
            mlflow.log_metric(f"best_{key}", float(best_row[key]))

        signature = infer_signature(X_train, best_pipe.predict(X_train))
        model_info = mlflow.sklearn.log_model(
            best_pipe,
            artifact_path="best_model",
            signature=signature,
            registered_model_name="fraud-classifier" if args.register else None,
        )
        mlflow.set_tag("best_model", best_name)

        out_dir = Path(args.output_dir or repo_root() / "models")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / args.output_name
        joblib.dump(best_pipe, out_path)
        mlflow.log_artifact(str(out_path), artifact_path="joblib_export")

        # Stats globales pour les features comportementales (amt_z_score, amt_is_outlier)
        amt_col = "Transaction_Amount (in Million)"
        if amt_col in X_train.columns:
            stats = {
                "amt_mean": float(X_train[amt_col].mean()),
                "amt_std":  float(X_train[amt_col].std()),
                "amt_q25":  float(X_train[amt_col].quantile(0.25)),
                "amt_q75":  float(X_train[amt_col].quantile(0.75)),
            }
            stats_path = out_dir / "global_stats.json"
            stats_path.write_text(json.dumps(stats, indent=2))
            mlflow.log_artifact(str(stats_path), artifact_path="joblib_export")
            print(f"  global_stats → {stats_path.resolve()}")

        print(f"Meilleur modèle : {best_name}")
        print(f"  ROC-AUC={best_row['roc_auc']:.4f}  F1={best_row['f1']:.4f}")
        print(f"  joblib → {out_path.resolve()}")
        print(f"  MLflow run_id={parent.info.run_id}")
        if model_info.model_uri:
            print(f"  artifact={model_info.model_uri}")


def main() -> None:
    p = argparse.ArgumentParser(description="Entraînement fraude + MLflow")
    p.add_argument("--data-path", default=None, help="CSV explicite (sinon data/ ou docs/)")
    p.add_argument("--raw-only", action="store_true", help="Ignorer le CSV features pré-calculé")
    p.add_argument("--tracking-uri", default=None)
    p.add_argument("--experiment-name", default=None)
    p.add_argument("--run-name", default=None)
    p.add_argument("--test-size", type=float, default=TEST_SIZE)
    p.add_argument("--random-state", type=int, default=RANDOM_STATE)
    p.add_argument("--output-dir", default=None)
    p.add_argument("--output-name", default="fraud_classifier.joblib")
    p.add_argument(
        "--register",
        action="store_true",
        help="Enregistre le meilleur modèle dans le Model Registry MLflow",
    )
    run_training(p.parse_args())


if __name__ == "__main__":
    main()
