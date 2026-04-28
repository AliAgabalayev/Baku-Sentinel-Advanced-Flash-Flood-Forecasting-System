"""
model.py — Baku Sentinel
=========================
Trains XGBoost on the Gold feature table produced by pipeline.py.

Key design decisions
--------------------
- Zone is one-hot encoded with drop_first=True, matching the notebook's
  pd.get_dummies call (produces zone_Low Relief, zone_Moderate Relief).
- Chronological train/test split — zero data leakage.
- scale_pos_weight auto-computed from class imbalance.
- F1-maximising threshold tuned on the training set.
- Isotonic calibration for reliable probabilities.
- SHAP TreeExplainer for global feature importance.
- Saved artifact: models/baku_sentinel_rf.joblib
  (name kept for backward-compat with existing notebook load code)
"""

import json
import logging
from pathlib import Path
from typing import Optional, Tuple

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    f1_score,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score
from xgboost import XGBClassifier

from src import config

logger = logging.getLogger(__name__)

# ── Non-feature columns ────────────────────────────────────────────────────────
_DROP_COLS = {
    # 1. Standard Metadata/Target
    "time_6h", "zone", config.TARGET_COL,

    # 2. Redundant "Twins" (>0.90 correlation)
    "river_discharge",           # Use discharge_lag_6h instead
    "humidity_precip_product",   # Use precipitation instead
    "precip_roll_max_24h",       # Use precip_roll_sum_24h instead
    "zone_cascade_risk",         # Use highland_precip instead
    "soil_temperature_0_to_7cm", # Use temperature_2m instead
    "soil_saturation_index",     # Use soil_moisture_0_to_7cm instead
    "discharge_roll_max_24h",    # Use discharge_lag_6h instead
    "temp_lag_24h",              # Use temperature_2m instead
    "discharge_lag_24h",         # Redundant with 6h lag
    "precip_roll_sum_24h",       # Redundant with highland_precip

    # 3. Insignificant "Noise" (p >= 0.05 in Mann-Whitney U)
    "frozen_ground_flag",
    "discharge_trend_6h",
    "soil_moisture_change_6h",
    "temp_trend_24h"
}

# ── XGBoost hyperparameters ───────────────────────────────────────────────────
_XGB_PARAMS = {
    "n_estimators":     500,
    "learning_rate":    0.05,
    "max_depth":        5,
    "min_child_weight": 3,
    "subsample":        0.8,
    "colsample_bytree": 0.8,
    "reg_alpha":        0.1,
    "reg_lambda":       1.0,
    "eval_metric":      "aucpr",
    "random_state":     42,
    "n_jobs":           -1,
}


# ══════════════════════════════════════════════════════════════════════════════
# Data preparation
# ══════════════════════════════════════════════════════════════════════════════

def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
    """
    Encodes 'zone' into dummy variables first, then removes non-feature
    columns defined in _DROP_COLS.
    """
    # 1. One-hot encode 'zone' (this consumes the 'zone' column and creates dummies)
    # We do this first so 'zone' is guaranteed to be present for the encoder.
    X = pd.get_dummies(df, columns=["zone"], drop_first=True)

    # 2. Identify which columns from _DROP_COLS are present in the new DataFrame X.
    # Note: 'zone' will no longer be in X.columns anyway because get_dummies
    # replaced it with dummy columns.
    drop = [c for c in _DROP_COLS if c in X.columns]

    # 3. Drop the non-feature/target columns
    X = X.drop(columns=drop)

    # 4. Capture the final list of columns for model training/alignment
    feature_cols = X.columns.tolist()

    return X, feature_cols


def _time_split(df: pd.DataFrame,
                test_frac: float = 0.20) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Chronological split — most recent `test_frac` goes to test."""
    df = df.sort_values("time_6h").reset_index(drop=True)
    cut = int(len(df) * (1 - test_frac))
    cut_date = df.iloc[cut]["time_6h"]
    train = df[df["time_6h"] <  cut_date]
    test  = df[df["time_6h"] >= cut_date]
    logger.info(f"Train: {len(train):,}  |  Test: {len(test):,}  |  cutoff: {cut_date}")
    return train, test


def _pos_weight(y: pd.Series) -> float:
    neg, pos = (y == 0).sum(), (y == 1).sum()
    ratio = neg / max(pos, 1)
    logger.info(f"Class ratio (neg/pos): {ratio:.1f}")
    return float(ratio)


def _best_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    f1 = 2 * precision * recall / (precision + recall + 1e-9)
    best = float(thresholds[np.argmax(f1[:-1])])
    logger.info(f"Optimal threshold: {best:.3f}  F1={f1.max():.4f}")
    return best


# ══════════════════════════════════════════════════════════════════════════════
# Training
# ══════════════════════════════════════════════════════════════════════════════

def train(df: pd.DataFrame,
          calibrate: bool = True,
          model_name: str = "baku_sentinel_rf") -> dict:
    """
    Train XGBoost on the Gold feature DataFrame.

    Parameters
    ----------
    df          : Output of pipeline.load_gold() or equivalent.
    calibrate   : Wrap with isotonic calibration for better probabilities.
    model_name  : Stem for saved .joblib and _metrics.json files.

    Returns
    -------
    bundle : dict — model, features, threshold, metrics, shap_importance, test_df
    """
    target = config.TARGET_COL
    if target not in df.columns:
        raise ValueError(f"Target '{target}' not in DataFrame.")

    df = df.dropna(subset=[target]).copy()
    train_df, test_df = _time_split(df)

    X_train_raw, feature_cols = prepare_features(train_df)
    X_test_raw,  _            = prepare_features(test_df)
    # Align test columns to training columns
    for c in feature_cols:
        if c not in X_test_raw.columns:
            X_test_raw[c] = 0
    X_test_raw = X_test_raw[feature_cols]

    y_train = train_df[target].values
    y_test  = test_df[target].values

    X_train = X_train_raw.fillna(0).values
    X_test  = X_test_raw.fillna(0).values

    logger.info(f"Training: {X_train.shape}  |  Features: {len(feature_cols)}")

    # ── XGBoost ───────────────────────────────────────────────────────────────
    params = {**_XGB_PARAMS, "scale_pos_weight": _pos_weight(train_df[target])}
    val_cut = int(len(X_train) * 0.85)
    base = XGBClassifier(**params)
    base.fit(
        X_train[:val_cut], y_train[:val_cut],
        eval_set=[(X_train[val_cut:], y_train[val_cut:])],
        verbose=False,
    )

    # ── Calibration ───────────────────────────────────────────────────────────
    if calibrate:
        # We use cv=5 or a ShuffleSplit. This ensures the model is calibrated
        # on data it didn't see during the base XGBoost training.
        model = CalibratedClassifierCV(base, method="isotonic", cv=5)
        model.fit(X_train, y_train)
        logger.info("Isotonic calibration applied via 5-fold CV.")
    else:
        model = base

    # ── Threshold optimisation ────────────────────────────────────────────────
    train_prob = model.predict_proba(X_train)[:, 1]
    # threshold  = _best_threshold(y_train, train_prob)

    # We are overriding the F1-max threshold (0.80) with a manual safety threshold (0.40)
    # based on our reliability diagram and the need for higher Recall.
    threshold = 0.30
    logger.info(f"Using manual safety threshold: {threshold}")


    # ── Evaluation ────────────────────────────────────────────────────────────
    test_prob = model.predict_proba(X_test)[:, 1]
    test_pred = (test_prob >= threshold).astype(int)

    metrics = {
        "auc_roc":   round(roc_auc_score(y_test, test_prob), 4),
        "auc_pr":    round(average_precision_score(y_test, test_prob), 4),
        "f1_score":  round(f1_score(y_test, test_pred, zero_division=0), 4),
        "threshold": round(threshold, 4),
        "n_train":   int(len(y_train)),
        "n_test":    int(len(y_test)),
        "pos_rate_train": float(y_train.mean()),
        "pos_rate_test":  float(y_test.mean()),
        "report": classification_report(y_test, test_pred, output_dict=True, zero_division=0),
    }
    logger.info(
        f"AUC-ROC={metrics['auc_roc']}  AUC-PR={metrics['auc_pr']}  "
        f"F1={metrics['f1_score']}  threshold={threshold:.3f}"
    )

    # ── Cross-validation ──────────────────────────────────────────────────────
    X_all, _ = prepare_features(df)
    X_all = X_all.fillna(0)
    for c in feature_cols:
        if c not in X_all.columns:
            X_all[c] = 0
    X_all = X_all[feature_cols]
    cv_scores = cross_val_score(
        XGBClassifier(**params), X_all, df[target],
        cv=StratifiedKFold(n_splits=5, shuffle=False),
        scoring="average_precision", n_jobs=-1,
    )
    metrics["cv_auc_pr_mean"] = round(float(cv_scores.mean()), 4)
    metrics["cv_auc_pr_std"]  = round(float(cv_scores.std()), 4)
    logger.info(f"CV AUC-PR: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # ── SHAP ──────────────────────────────────────────────────────────────────
    shap_importance = _compute_shap(base, X_train, feature_cols)

    # ── Annotate test set ─────────────────────────────────────────────────────
    test_out = test_df.copy()
    test_out["risk_score"] = test_prob
    test_out["flood_pred"] = test_pred
    test_out["risk_level"] = pd.cut(
        test_prob,
        bins=[-0.001, config.RISK_MEDIUM, config.RISK_HIGH, 1.001],
        labels=["LOW", "MEDIUM", "HIGH"],
    )

    bundle = {
        "model":            model,
        "features":         feature_cols,      # ← key name matches notebook checkpoint
        "threshold":        threshold,
        "metrics":          metrics,
        "shap_importance":  shap_importance,
        "test_df":          test_out,
    }

    _save(bundle, model_name)
    return bundle


def _compute_shap(base_model, X_train: np.ndarray,
                  feature_cols: list) -> dict:
    try:
        explainer = shap.TreeExplainer(base_model)
        n = min(2000, len(X_train))
        idx = np.random.choice(len(X_train), n, replace=False)
        sv = explainer.shap_values(X_train[idx])
        if isinstance(sv, list):
            sv = sv[1]
        mean_abs = np.abs(sv).mean(axis=0)
        return dict(sorted(zip(feature_cols, mean_abs.tolist()),
                            key=lambda x: x[1], reverse=True))
    except Exception as e:
        logger.warning(f"SHAP failed: {e}")
        return {}


def _save(bundle: dict, model_name: str) -> None:
    path = config.MODELS_DIR / f"{model_name}.joblib"
    joblib.dump({
        "model":     bundle["model"],
        "features":  bundle["features"],
        "threshold": bundle["threshold"],
    }, path)
    meta_path = config.MODELS_DIR / f"{model_name}_metrics.json"
    save_meta = {k: v for k, v in bundle["metrics"].items() if k != "report"}
    save_meta["shap_top10"] = list(bundle["shap_importance"].keys())[:10]
    with open(meta_path, "w") as f:
        json.dump(save_meta, f, indent=2)
    logger.info(f"Model saved → {path}")


# ══════════════════════════════════════════════════════════════════════════════
# Inference
# ══════════════════════════════════════════════════════════════════════════════

def load_model(model_name: str = "baku_sentinel_rf") -> dict:
    path = config.MODELS_DIR / f"{model_name}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {path}  — run train() first.")
    return joblib.load(path)


def predict(df_features: pd.DataFrame,
            checkpoint: Optional[dict] = None,
            model_name: str = "baku_sentinel_rf") -> pd.DataFrame:
    """
    Score a feature DataFrame. Corrected to prevent KeyError on 'zone'.
    """
    if checkpoint is None:
        checkpoint = load_model(model_name)

    model = checkpoint["model"]
    feature_cols = checkpoint["features"]
    threshold = checkpoint["threshold"]

    # 1. Encode 'zone' first while it still exists in the DataFrame
    X = pd.get_dummies(df_features, columns=["zone"], drop_first=True)

    # 2. Now identify which columns to drop from the ENCODED dataframe
    # This prevents dropping 'zone' before get_dummies can see it
    drop_for_predict = [c for c in _DROP_COLS if c in X.columns]
    X = X.drop(columns=drop_for_predict)
    # --- THE FIX ENDS HERE ---

    # 3. Align columns with the features the model was trained on
    for col in feature_cols:
        if col not in X.columns:
            X[col] = 0

    # Ensure column order matches training
    X = X[feature_cols].fillna(0)

    # 4. Generate Probabilities and Predictions
    probs = model.predict_proba(X)[:, 1]
    preds = (probs >= threshold).astype(int)

    # 5. Build Output DataFrame
    out = df_features.copy()
    out["risk_score"] = probs
    out["flood_pred"] = preds
    out["risk_level"] = pd.cut(
        probs,
        bins=[-0.001, config.RISK_MEDIUM, config.RISK_HIGH, 1.001],
        labels=["LOW", "MEDIUM", "HIGH"],
    )
    return out
