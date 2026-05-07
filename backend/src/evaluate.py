"""
src/evaluate.py
===============
Comprehensive model evaluation:
- Confusion matrix
- ROC curve
- Precision-Recall curve
- Feature importance plot
- Risk score distribution
- Calibration plot

Run:
    python src/evaluate.py --model-path models/xgboost_risk_scorer.pkl
"""

import argparse
import json
import logging
import pickle
from pathlib import Path
from typing import Dict, Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for server environments
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    PrecisionRecallDisplay,
    auc,
    confusion_matrix,
    precision_recall_curve,
    roc_curve,
)
from sklearn.model_selection import train_test_split

from src.feature_engineering import FEATURE_NAMES
from src.train import generate_synthetic_training_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Plot Helpers
# ─────────────────────────────────────────────────────────────────────────────
ZAMIN_COLOR = "#4A7C59"   # Brand green
ACCENT = "#F4A261"


def plot_confusion_matrix(y_true, y_pred, save_path: str):
    """Confusion matrix with class labels."""
    fig, ax = plt.subplots(figsize=(6, 5))
    cm = confusion_matrix(y_true, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Low Risk", "High Risk"])
    disp.plot(ax=ax, colorbar=False, cmap="Greens")
    ax.set_title("Confusion Matrix — Zamin X Risk Scorer", fontsize=13, color=ZAMIN_COLOR)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    logger.info("Saved confusion matrix: %s", save_path)


def plot_roc_curve(y_true, y_prob, save_path: str):
    """ROC curve with AUC annotation."""
    fig, ax = plt.subplots(figsize=(7, 5))
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    roc_auc = auc(fpr, tpr)

    ax.plot(fpr, tpr, color=ZAMIN_COLOR, lw=2, label=f"AUC = {roc_auc:.3f}")
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="Random baseline")
    ax.fill_between(fpr, tpr, alpha=0.1, color=ZAMIN_COLOR)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve — Litigation Risk Scorer", fontsize=13, color=ZAMIN_COLOR)
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    logger.info("Saved ROC curve: %s", save_path)


def plot_precision_recall(y_true, y_prob, save_path: str):
    """Precision-Recall curve."""
    fig, ax = plt.subplots(figsize=(7, 5))
    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    pr_auc = auc(recall, precision)

    ax.plot(recall, precision, color=ACCENT, lw=2, label=f"AP = {pr_auc:.3f}")
    ax.axhline(y=y_true.mean(), color="k", linestyle="--", lw=1, label=f"Baseline = {y_true.mean():.2f}")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curve — Litigation Risk Scorer", fontsize=13, color=ZAMIN_COLOR)
    ax.legend()
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    logger.info("Saved PR curve: %s", save_path)


def plot_feature_importance(model, save_path: str, top_n: int = 15):
    """Horizontal bar chart of top feature importances."""
    importances = model.feature_importances_
    indices = np.argsort(importances)[-top_n:]
    features_sorted = [FEATURE_NAMES[i] for i in indices]
    imp_sorted = importances[indices]

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = [ZAMIN_COLOR if i < top_n // 2 else ACCENT for i in range(len(features_sorted))]
    ax.barh(features_sorted, imp_sorted, color=colors[::-1])
    ax.set_xlabel("Feature Importance (Gain)")
    ax.set_title(f"Top {top_n} Features — Zamin X Risk Scorer", fontsize=13, color=ZAMIN_COLOR)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    logger.info("Saved feature importance: %s", save_path)


def plot_risk_score_distribution(y_prob, y_true, save_path: str):
    """Distribution of predicted risk scores by class."""
    fig, ax = plt.subplots(figsize=(8, 5))
    risk_scores = y_prob * 100  # scale to 0-100

    low_risk = risk_scores[y_true == 0]
    high_risk = risk_scores[y_true == 1]

    ax.hist(low_risk, bins=30, alpha=0.6, color="steelblue", label="Low Risk (Ground Truth)")
    ax.hist(high_risk, bins=30, alpha=0.6, color="firebrick", label="High Risk (Ground Truth)")
    ax.axvline(x=50, color="gray", linestyle="--", lw=1.5, label="Decision threshold (50)")
    ax.set_xlabel("Risk Score (0-100)")
    ax.set_ylabel("Count")
    ax.set_title("Risk Score Distribution by True Class", fontsize=13, color=ZAMIN_COLOR)
    ax.legend()
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    logger.info("Saved risk distribution: %s", save_path)


def plot_calibration(y_true, y_prob, save_path: str):
    """Reliability diagram — calibration of probability scores."""
    fig, ax = plt.subplots(figsize=(7, 5))
    frac_pos, mean_pred = calibration_curve(y_true, y_prob, n_bins=10)

    ax.plot(mean_pred, frac_pos, "s-", color=ZAMIN_COLOR, label="XGBoost")
    ax.plot([0, 1], [0, 1], "k--", label="Perfectly calibrated")
    ax.set_xlabel("Mean Predicted Probability")
    ax.set_ylabel("Fraction of Positives")
    ax.set_title("Calibration Plot (Reliability Diagram)", fontsize=13, color=ZAMIN_COLOR)
    ax.legend()
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    logger.info("Saved calibration plot: %s", save_path)


# ─────────────────────────────────────────────────────────────────────────────
# Main Evaluation Runner
# ─────────────────────────────────────────────────────────────────────────────
def run_evaluation(model_path: str, data_path: Optional[str] = None) -> Dict:
    """Load model and generate all evaluation plots + metrics."""
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    with open(model_path, "rb") as f:
        model = pickle.load(f)
    logger.info("Loaded model: %s", model_path)

    # Load data
    if data_path and Path(data_path).exists():
        df = pd.read_csv(data_path)
        X = df[FEATURE_NAMES]
        y = df["risk_label"]
    else:
        X, y = generate_synthetic_training_data(n_samples=2000)

    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    # Generate all plots
    plot_confusion_matrix(y_test, y_pred, str(REPORTS_DIR / "confusion_matrix.png"))
    plot_roc_curve(y_test, y_prob, str(REPORTS_DIR / "roc_curve.png"))
    plot_precision_recall(y_test, y_prob, str(REPORTS_DIR / "precision_recall.png"))
    plot_feature_importance(model, str(REPORTS_DIR / "feature_importance.png"))
    plot_risk_score_distribution(y_prob, y_test.values, str(REPORTS_DIR / "risk_distribution.png"))
    plot_calibration(y_test.values, y_prob, str(REPORTS_DIR / "calibration.png"))

    logger.info("All evaluation plots saved to %s/", REPORTS_DIR)
    return {"status": "evaluation_complete", "reports_dir": str(REPORTS_DIR)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Zamin X Risk Scorer")
    parser.add_argument("--model-path", default="models/xgboost_risk_scorer.pkl")
    parser.add_argument("--data-path", default=None)
    args = parser.parse_args()
    run_evaluation(args.model_path, args.data_path)
