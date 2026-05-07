"""
src/train.py
============
Training pipeline for the XGBoost fraud/litigation risk scorer.

Pipeline:
  1. Load training data (historical case patterns + fraud labels)
  2. Feature engineering
  3. Train/val/test split (stratified)
  4. XGBoost training with cross-validation
  5. Hyperparameter tuning (Optuna)
  6. Model evaluation
  7. Save trained model + metadata

Run:
  python src/train.py --mode train
  python src/train.py --mode tune     # Optuna hyperparameter search
  python src/train.py --mode evaluate
"""

import argparse
import json
import logging
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import LabelBinarizer

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logging.warning("XGBoost not installed. Training will fail.")

from src.feature_engineering import FEATURE_NAMES, RiskFeatureExtractor, score_to_risk_level

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Data Generation / Loading
# ─────────────────────────────────────────────────────────────────────────────
def generate_synthetic_training_data(n_samples: int = 5000) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Generate synthetic training data for initial model training.

    In production (Phase 2):
    - Replace with real eCourts historical data
    - Use known fraud/dispute outcomes as labels
    - Minimum 10,000 labeled samples recommended

    Label:
        0 = low risk (no significant dispute)
        1 = high risk (active dispute, fraud signals)
    """
    np.random.seed(42)
    rows = []
    labels = []

    for _ in range(n_samples):
        risk_class = np.random.choice([0, 1], p=[0.6, 0.4])  # 40% risky

        if risk_class == 1:
            # High risk pattern
            row = {
                "total_case_count": np.random.randint(1, 8),
                "active_case_count": np.random.randint(1, 5),
                "disposed_case_count": np.random.randint(0, 3),
                "has_civil_suit": np.random.choice([0, 1], p=[0.3, 0.7]),
                "has_partition_suit": np.random.choice([0, 1], p=[0.4, 0.6]),
                "has_boundary_dispute": np.random.choice([0, 1], p=[0.3, 0.7]),
                "has_mortgage_suit": np.random.choice([0, 1], p=[0.5, 0.5]),
                "has_revenue_case": np.random.choice([0, 1], p=[0.4, 0.6]),
                "has_criminal": np.random.choice([0, 1], p=[0.7, 0.3]),
                "max_case_age_days": np.random.randint(365, 3650),
                "avg_case_age_days": np.random.randint(180, 2000),
                "oldest_case_age_days": np.random.randint(365, 3650),
                "avg_days_to_next_hearing": np.random.randint(1, 90),
                "has_imminent_hearing": np.random.choice([0, 1], p=[0.4, 0.6]),
                "ownership_transfer_count": np.random.randint(2, 10),
                "rapid_transfer_flag": np.random.choice([0, 1], p=[0.3, 0.7]),
                "transfer_frequency_per_year": np.random.uniform(0.5, 3.0),
                "area_acres": np.random.uniform(0.5, 10.0),
                "has_high_court_case": np.random.choice([0, 1], p=[0.5, 0.5]),
                "has_district_court_case": np.random.choice([0, 1], p=[0.3, 0.7]),
                "active_case_ratio": np.random.uniform(0.4, 1.0),
                "unique_courts_count": np.random.randint(1, 4),
            }
        else:
            # Low risk pattern
            row = {
                "total_case_count": np.random.randint(0, 2),
                "active_case_count": 0,
                "disposed_case_count": np.random.randint(0, 2),
                "has_civil_suit": np.random.choice([0, 1], p=[0.8, 0.2]),
                "has_partition_suit": np.random.choice([0, 1], p=[0.9, 0.1]),
                "has_boundary_dispute": 0,
                "has_mortgage_suit": np.random.choice([0, 1], p=[0.9, 0.1]),
                "has_revenue_case": np.random.choice([0, 1], p=[0.8, 0.2]),
                "has_criminal": 0,
                "max_case_age_days": np.random.randint(0, 180),
                "avg_case_age_days": np.random.randint(0, 120),
                "oldest_case_age_days": np.random.randint(0, 180),
                "avg_days_to_next_hearing": np.random.randint(90, 365),
                "has_imminent_hearing": 0,
                "ownership_transfer_count": np.random.randint(0, 3),
                "rapid_transfer_flag": 0,
                "transfer_frequency_per_year": np.random.uniform(0, 0.5),
                "area_acres": np.random.uniform(0.5, 10.0),
                "has_high_court_case": 0,
                "has_district_court_case": np.random.choice([0, 1], p=[0.7, 0.3]),
                "active_case_ratio": 0.0,
                "unique_courts_count": np.random.randint(0, 2),
            }

        # Add label noise (real-world data is noisy)
        if np.random.random() < 0.03:
            risk_class = 1 - risk_class  # flip 3% labels

        rows.append(row)
        labels.append(risk_class)

    X = pd.DataFrame(rows, columns=FEATURE_NAMES)
    y = pd.Series(labels, name="risk_label")
    logger.info("Generated %d synthetic training samples (%.1f%% high risk)", n_samples, y.mean() * 100)
    return X, y


def load_training_data(data_path: Optional[str] = None) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Load training data from CSV or generate synthetic data.
    """
    from typing import Optional

    if data_path and Path(data_path).exists():
        logger.info("Loading training data from %s", data_path)
        df = pd.read_csv(data_path)
        X = df[FEATURE_NAMES]
        y = df["risk_label"]
        return X, y
    else:
        logger.info("No training data found — generating synthetic data")
        return generate_synthetic_training_data()


# ─────────────────────────────────────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────────────────────────────────────
def train_model(
    X: pd.DataFrame,
    y: pd.Series,
    params: Optional[Dict] = None,
) -> "xgb.XGBClassifier":
    """
    Train XGBoost classifier with cross-validation.

    Returns trained model.
    """
    if not XGBOOST_AVAILABLE:
        raise RuntimeError("XGBoost not installed. Run: pip install xgboost")

    default_params = {
        "n_estimators": 300,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "gamma": 0.1,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "scale_pos_weight": (y == 0).sum() / (y == 1).sum(),  # handle class imbalance
        "eval_metric": "auc",
        "random_state": 42,
        "n_jobs": -1,
        "tree_method": "hist",
    }

    if params:
        default_params.update(params)

    # Stratified train/val split
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    logger.info("Training XGBoost: %d train, %d val samples", len(X_train), len(X_val))

    model = xgb.XGBClassifier(**default_params)

    # Fit with early stopping
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )

    # Cross-validation AUC
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc", n_jobs=-1)
    logger.info("5-fold CV AUC: %.4f ± %.4f", cv_scores.mean(), cv_scores.std())

    return model


def tune_hyperparameters(X: pd.DataFrame, y: pd.Series, n_trials: int = 50) -> Dict:
    """
    Optuna-based hyperparameter search for XGBoost.
    Returns best parameters found.
    """
    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
    except ImportError:
        logger.warning("Optuna not installed. Skipping HPO.")
        return {}

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma": trial.suggest_float("gamma", 0, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 0, 2.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 0, 2.0),
        }
        model = xgb.XGBClassifier(**params, eval_metric="auc", random_state=42, n_jobs=-1)
        cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc", n_jobs=-1)
        return scores.mean()

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    logger.info("Best HPO params: %s | AUC=%.4f", study.best_params, study.best_value)
    return study.best_params


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────────────────────
def evaluate_model(model: "xgb.XGBClassifier", X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
    """Compute evaluation metrics on test set."""
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred), 4),
        "recall": round(recall_score(y_test, y_pred), 4),
        "f1_score": round(f1_score(y_test, y_pred), 4),
        "roc_auc": round(roc_auc_score(y_test, y_prob), 4),
        "classification_report": classification_report(y_test, y_pred),
        "feature_importance": dict(zip(
            FEATURE_NAMES,
            [round(float(v), 4) for v in model.feature_importances_]
        )),
    }

    logger.info("=== Model Evaluation ===")
    logger.info("Accuracy:  %.4f", metrics["accuracy"])
    logger.info("Precision: %.4f", metrics["precision"])
    logger.info("Recall:    %.4f", metrics["recall"])
    logger.info("F1 Score:  %.4f", metrics["f1_score"])
    logger.info("ROC-AUC:   %.4f", metrics["roc_auc"])
    logger.info("\n%s", metrics["classification_report"])

    return metrics


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Zamin X Risk Scorer Training Pipeline")
    parser.add_argument("--mode", choices=["train", "tune", "evaluate"], default="train")
    parser.add_argument("--data-path", default=None, help="Path to training CSV")
    parser.add_argument("--n-trials", type=int, default=50, help="Optuna trials for tuning")
    parser.add_argument("--model-out", default="models/xgboost_risk_scorer.pkl")
    args = parser.parse_args()

    # Load data
    X, y = load_training_data(args.data_path)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, stratify=y, random_state=42)

    if args.mode == "tune":
        best_params = tune_hyperparameters(X_train, y_train, n_trials=args.n_trials)
        model = train_model(X_train, y_train, params=best_params)
    else:
        model = train_model(X_train, y_train)

    # Evaluate
    metrics = evaluate_model(model, X_test, y_test)

    # Save model
    model_path = Path(args.model_out)
    model_path.parent.mkdir(exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    logger.info("Model saved to %s", model_path)

    # Save metrics
    metrics_path = MODELS_DIR / "training_metrics.json"
    metrics_copy = {k: v for k, v in metrics.items() if k != "classification_report"}
    with open(metrics_path, "w") as f:
        json.dump({**metrics_copy, "trained_at": datetime.utcnow().isoformat()}, f, indent=2)
    logger.info("Metrics saved to %s", metrics_path)


if __name__ == "__main__":
    main()
