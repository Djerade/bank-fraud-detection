"""Exit 0 si l'expérience MLflow contient au moins un run, sinon exit 1."""
from __future__ import annotations

import os
import sys

import mlflow
from mlflow.tracking import MlflowClient


def experiment_has_runs() -> bool:
    uri = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    name = os.environ.get("MLFLOW_EXPERIMENT_NAME", "bank-fraud-detection")
    mlflow.set_tracking_uri(uri)
    exp = MlflowClient().get_experiment_by_name(name)
    if exp is None:
        return False
    return bool(
        MlflowClient().search_runs(experiment_ids=[exp.experiment_id], max_results=1)
    )


if __name__ == "__main__":
    sys.exit(0 if experiment_has_runs() else 1)
