"""Pipelines sklearn alignés sur notebooks/exploration.ipynb."""
from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder, StandardScaler

from fraud_detection.data import TARGET

DROP_COLS = [
    TARGET,
    "Transaction_ID",
    "Customer_ID",
    "IP_Address",
    "transaction_dt",
    "order_date_dt",
    "Transaction_Date",
    "Transaction_Time",
]

TEST_SIZE = 0.2
RANDOM_STATE = 42


def split_data(
    df: pd.DataFrame,
    *,
    test_size: float = TEST_SIZE,
    random_state: int = RANDOM_STATE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    train_df, test_df = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
        stratify=df[TARGET],
    )
    feat_cols = [c for c in train_df.columns if c not in DROP_COLS]
    return (
        train_df[feat_cols],
        test_df[feat_cols],
        train_df[TARGET],
        test_df[TARGET],
    )


def build_preprocessor(X_train: pd.DataFrame) -> ColumnTransformer:
    num_cols = X_train.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = X_train.select_dtypes(include=["object", "category"]).columns.tolist()
    return ColumnTransformer(
        [
            ("num", StandardScaler(), num_cols),
            (
                "cat",
                OrdinalEncoder(
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,
                    encoded_missing_value=-1,
                ),
                cat_cols,
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def classifiers(random_state: int = RANDOM_STATE) -> dict[str, Any]:
    rs = random_state
    return {
        # Meilleur modèle issu du tuning notebook (C=0.01, GridSearchCV)
        "LogisticRegression": LogisticRegression(
            C=0.01, max_iter=2000, class_weight="balanced", solver="lbfgs", random_state=rs
        ),
        "SGDClassifier (log_loss)": SGDClassifier(
            loss="log_loss",
            class_weight="balanced",
            random_state=rs,
            max_iter=2000,
            tol=1e-3,
        ),
        "RandomForestClassifier": RandomForestClassifier(
            class_weight="balanced",
            random_state=rs,
            n_jobs=-1,
            n_estimators=100,
            max_depth=18,
        ),
        "ExtraTreesClassifier": ExtraTreesClassifier(
            class_weight="balanced",
            random_state=rs,
            n_jobs=-1,
            n_estimators=100,
            max_depth=18,
        ),
        "GradientBoostingClassifier": GradientBoostingClassifier(
            random_state=rs, max_depth=4, n_estimators=100, learning_rate=0.08
        ),
        "HistGradientBoostingClassifier": HistGradientBoostingClassifier(
            class_weight="balanced", random_state=rs, max_depth=10, max_iter=200
        ),
    }


def fit_and_metrics(
    name: str,
    clf: Any,
    preprocessor: ColumnTransformer,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> tuple[dict[str, float | str], Pipeline | None]:
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)

    pipe = ImbPipeline([("prep", preprocessor), ("smote", SMOTE(random_state=42)), ("clf", clf)])
    row: dict[str, float | str] = {
        "model": name,
        "accuracy": float("nan"),
        "precision": float("nan"),
        "recall": float("nan"),
        "f1": float("nan"),
        "roc_auc": float("nan"),
        "error": "",
    }
    try:
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
        est = pipe.named_steps["clf"]
        row["accuracy"] = float(accuracy_score(y_test, y_pred))
        row["precision"] = float(precision_score(y_test, y_pred, zero_division=0))
        row["recall"] = float(recall_score(y_test, y_pred, zero_division=0))
        row["f1"] = float(f1_score(y_test, y_pred, zero_division=0))
        if hasattr(est, "predict_proba"):
            row["roc_auc"] = float(roc_auc_score(y_test, pipe.predict_proba(X_test)[:, 1]))
        elif hasattr(est, "decision_function"):
            row["roc_auc"] = float(roc_auc_score(y_test, pipe.decision_function(X_test)))
        return row, pipe
    except Exception as exc:
        row["error"] = str(exc)[:240]
        return row, None


def pick_best(results: list[dict[str, float | str]]) -> dict[str, float | str]:
    ok = [r for r in results if not r.get("error")]
    if not ok:
        raise RuntimeError("Aucun modèle entraîné avec succès.")
    return sorted(
        ok,
        key=lambda r: (float(r["roc_auc"]), float(r["f1"])),
        reverse=True,
    )[0]
