"""
predict.py
==========
Baku Sentinel — 30-Day Two-Phase Forecast Runner

Phase 1 (Days 1–15):  Open-Meteo Forecast API → direct real forecast data
Phase 2 (Days 16–30): ML weather prediction → flood risk layer

Output: per-zone daily risk scores + zone-level alert summary
"""

import logging
from datetime import timedelta
from typing import Optional

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from src.feature_engineering import build_features
from src.model import load_model, predict

logger = logging.getLogger(__name__)

# ── Phase configuration ────────────────────────────────────────────────────────
PHASE1_DAYS = 15
PHASE2_DAYS = 15
TOTAL_DAYS  = PHASE1_DAYS + PHASE2_DAYS

# Weather variables to predict in Phase 2
WEATHER_TARGETS = [
    "precipitation_sum",
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "relative_humidity_2m_mean",
    "et0_fao_evapotranspiration",
    "soil_moisture_0_to_7cm_mean",
    "soil_moisture_7_to_28cm_mean",
    "soil_temperature_0_to_7cm_mean",
    "wind_speed_10m_max",
    "snowfall_sum",
]

RISK_THRESHOLDS = {
    "HIGH":   0.60,
    "MEDIUM": 0.30,
    "LOW":    0.00,
}


# ══════════════════════════════════════════════════════════════════════════════
# Phase 1: Direct forecast (Days 1–15)
# ══════════════════════════════════════════════════════════════════════════════

def prepare_phase1(forecast_df: pd.DataFrame,
                   historical_tail: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare Phase 1 features by appending the real API forecast to the
    historical tail (needed for lag/rolling features).

    Parameters
    ----------
    forecast_df     : 15-day raw forecast from Open-Meteo Forecast API.
    historical_tail : Last 30 days of historical data (provides context for lags).

    Returns
    -------
    Engineered Phase 1 DataFrame (only forecast dates).
    """
    # Combine tail + forecast so rolling/lag features are computed correctly
    combined = pd.concat([historical_tail, forecast_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=["time", "zone"]).sort_values(["zone", "time"])

    engineered = build_features(combined, mode="predict")

    # Return only the forecast window
    min_forecast_date = pd.to_datetime(forecast_df["time"]).min()
    phase1 = engineered[engineered["time"] >= min_forecast_date].copy()
    phase1["forecast_phase"] = 1
    logger.info(f"Phase 1 prepared: {len(phase1)} rows across {phase1['zone'].nunique()} zones.")
    return phase1


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2: ML weather extension (Days 16–30)
# ══════════════════════════════════════════════════════════════════════════════

class WeatherExtensionModel:
    """
    Lightweight auto-regressive weather extender for Days 16–30.
    Trains a separate XGBoost regressor per weather variable per zone,
    using the preceding 15-day window as predictors.
    """

    def __init__(self, window: int = 15):
        self.window = window
        self._models: dict = {}
        self._fitted = False

    def fit(self, historical_df: pd.DataFrame):
        """Fit one regressor per (zone, variable) on the full historical dataset."""
        logger.info("Fitting weather extension models...")
        for zone, grp in historical_df.groupby("zone"):
            grp = grp.sort_values("time").copy()
            self._models[zone] = {}
            for var in WEATHER_TARGETS:
                if var not in grp.columns:
                    continue
                series = grp[var].fillna(method="ffill").fillna(0).values
                X, y = self._make_sequences(series)
                if len(X) < 20:
                    continue
                xgb = XGBClassifier(
                    n_estimators=100, learning_rate=0.1, max_depth=3,
                    objective="reg:squarederror", n_jobs=1, random_state=42
                )
                # Use a plain XGBRegressor via duck-typing
                from xgboost import XGBRegressor
                reg = XGBRegressor(
                    n_estimators=100, learning_rate=0.1, max_depth=3,
                    n_jobs=1, random_state=42
                )
                reg.fit(X, y, verbose=False)
                self._models[zone][var] = reg
        self._fitted = True
        logger.info("Weather extension models fitted.")

    def _make_sequences(self, series: np.ndarray):
        X, y = [], []
        for i in range(self.window, len(series)):
            X.append(series[i - self.window: i])
            y.append(series[i])
        return np.array(X), np.array(y)

    def predict_next_n(self, seed_df: pd.DataFrame, n_days: int = 15) -> pd.DataFrame:
        """
        Roll forward n_days using the last `window` days as seed.

        Parameters
        ----------
        seed_df : DataFrame containing the last ≥ window days of Phase 1 output.
        n_days  : Number of days to extend.
        """
        if not self._fitted:
            raise RuntimeError("WeatherExtensionModel must be fitted before predicting.")

        all_rows = []
        for zone, grp in seed_df.groupby("zone"):
            grp = grp.sort_values("time").copy()
            last_date = grp["time"].max()
            zone_models = self._models.get(zone, {})

            # Seed buffers
            buffers = {
                var: grp[var].fillna(0).values[-self.window:].tolist()
                for var in WEATHER_TARGETS if var in grp.columns
            }

            for day in range(1, n_days + 1):
                row = {"time": last_date + timedelta(days=day), "zone": zone}
                for var in WEATHER_TARGETS:
                    if var not in zone_models or var not in buffers:
                        row[var] = 0.0
                        continue
                    seed_arr = np.array(buffers[var][-self.window:]).reshape(1, -1)
                    pred_val = float(zone_models[var].predict(seed_arr)[0])
                    # Apply physical constraints
                    if "precipitation" in var or "snowfall" in var or "moisture" in var:
                        pred_val = max(0.0, pred_val)
                    row[var] = pred_val
                    buffers[var].append(pred_val)
                all_rows.append(row)

        phase2_raw = pd.DataFrame(all_rows)
        logger.info(f"Phase 2 weather extension: {len(phase2_raw)} rows generated.")
        return phase2_raw


def prepare_phase2(weather_extension: pd.DataFrame,
                   phase1_tail: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer features for Phase 2 weather predictions.

    Parameters
    ----------
    weather_extension : Raw predicted weather from WeatherExtensionModel.
    phase1_tail       : Last window of Phase 1 (for continuity of lag features).
    """
    combined = pd.concat([phase1_tail, weather_extension], ignore_index=True)
    combined = combined.drop_duplicates(subset=["time", "zone"]).sort_values(["zone", "time"])

    engineered = build_features(combined, mode="predict")

    min_p2_date = pd.to_datetime(weather_extension["time"]).min()
    phase2 = engineered[engineered["time"] >= min_p2_date].copy()
    phase2["forecast_phase"] = 2
    logger.info(f"Phase 2 prepared: {len(phase2)} rows.")
    return phase2


# ══════════════════════════════════════════════════════════════════════════════
# Master 30-day runner
# ══════════════════════════════════════════════════════════════════════════════

def run_30day_forecast(
    forecast_df: pd.DataFrame,
    historical_df: pd.DataFrame,
    weather_ext_model: Optional[WeatherExtensionModel] = None,
    flood_model_name: str = "baku_sentinel",
) -> dict:
    """
    Execute the full 30-day two-phase flood risk forecast.

    Parameters
    ----------
    forecast_df       : 15-day raw Open-Meteo forecast (all zones combined).
    historical_df     : Full historical dataset (engineered or raw).
    weather_ext_model : Pre-fitted WeatherExtensionModel.  If None, a new one
                        is fitted on the historical data on-the-fly.
    flood_model_name  : Name of the saved flood risk model to load.

    Returns
    -------
    results : dict with keys:
        'phase1'    : Phase 1 predictions DataFrame
        'phase2'    : Phase 2 predictions DataFrame
        'combined'  : Full 30-day predictions
        'alerts'    : Zone-level alert summary
        'metadata'  : Run metadata
    """
    logger.info("=" * 65)
    logger.info("Baku Sentinel: Starting 30-Day Two-Phase Forecast")
    logger.info("=" * 65)

    # ── Load flood model ───────────────────────────────────────────────────────
    bundle = load_model(flood_model_name)
    logger.info(f"Loaded flood model: {flood_model_name}")

    # ── Historical tail for lag context ───────────────────────────────────────
    tail_window = 30
    historical_tail = (
        historical_df.sort_values("time")
        .groupby("zone", group_keys=False)
        .tail(tail_window)
    )

    # ── Phase 1 ───────────────────────────────────────────────────────────────
    logger.info(f"--- Phase 1: Days 1–{PHASE1_DAYS} (Direct API Forecast) ---")
    phase1_features = prepare_phase1(forecast_df, historical_tail)
    phase1_preds    = predict(phase1_features, bundle)

    # ── Phase 2 ───────────────────────────────────────────────────────────────
    logger.info(f"--- Phase 2: Days {PHASE1_DAYS+1}–{TOTAL_DAYS} (ML Weather Extension) ---")

    if weather_ext_model is None:
        logger.info("Fitting weather extension model on historical data...")
        weather_ext_model = WeatherExtensionModel(window=15)
        weather_ext_model.fit(historical_df)

    # Seed Phase 2 from Phase 1 output
    phase1_tail = phase1_preds.sort_values("time").groupby("zone", group_keys=False).tail(15)
    weather_ext = weather_ext_model.predict_next_n(phase1_tail, n_days=PHASE2_DAYS)
    phase2_features = prepare_phase2(weather_ext, phase1_tail)
    phase2_preds    = predict(phase2_features, bundle)

    # ── Combine ───────────────────────────────────────────────────────────────
    combined = pd.concat([phase1_preds, phase2_preds], ignore_index=True)
    combined = combined.sort_values(["zone", "time"]).reset_index(drop=True)

    # ── Generate alert summary ─────────────────────────────────────────────────
    alerts = _generate_alerts(combined)

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata = {
        "forecast_start":   str(combined["time"].min().date()),
        "forecast_end":     str(combined["time"].max().date()),
        "n_days":           TOTAL_DAYS,
        "zones":            combined["zone"].unique().tolist(),
        "model_used":       flood_model_name,
        "phase1_days":      PHASE1_DAYS,
        "phase2_days":      PHASE2_DAYS,
        "high_risk_days":   int((combined["risk_level"] == "HIGH").sum()),
    }

    logger.info(f"Forecast complete. High-risk zone-days: {metadata['high_risk_days']}")

    return {
        "phase1":    phase1_preds,
        "phase2":    phase2_preds,
        "combined":  combined,
        "alerts":    alerts,
        "metadata":  metadata,
    }


def _generate_alerts(combined: pd.DataFrame) -> pd.DataFrame:
    """
    Produce a per-zone alert summary table.

    Columns: zone, max_risk_level, max_flood_prob, high_risk_days,
             first_high_risk_date, alert_message
    """
    rows = []
    for zone, grp in combined.groupby("zone"):
        max_prob       = grp["flood_prob"].max()
        high_risk_days = int((grp["risk_level"] == "HIGH").sum())
        med_risk_days  = int((grp["risk_level"] == "MEDIUM").sum())

        if max_prob >= RISK_THRESHOLDS["HIGH"]:
            level = "HIGH"
        elif max_prob >= RISK_THRESHOLDS["MEDIUM"]:
            level = "MEDIUM"
        else:
            level = "LOW"

        first_high = None
        high_rows  = grp[grp["risk_level"] == "HIGH"]
        if not high_rows.empty:
            first_high = str(high_rows["time"].min().date())

        alert_msg = _compose_alert(zone, level, max_prob, high_risk_days, first_high)

        rows.append({
            "zone":              zone,
            "max_risk_level":    level,
            "max_flood_prob":    round(max_prob, 3),
            "high_risk_days":    high_risk_days,
            "medium_risk_days":  med_risk_days,
            "first_high_risk_date": first_high,
            "alert_message":     alert_msg,
        })

    alerts_df = pd.DataFrame(rows).sort_values("max_flood_prob", ascending=False)
    logger.info(f"Alerts generated:\n{alerts_df[['zone', 'max_risk_level', 'max_flood_prob']].to_string(index=False)}")
    return alerts_df


def _compose_alert(zone, level, prob, high_days, first_high_date) -> str:
    zone_short = zone.replace(" Relief", "")
    prob_pct   = round(prob * 100, 1)

    if level == "HIGH":
        return (
            f"⚠️  CRITICAL FLOOD RISK — {zone_short} Zone: "
            f"{prob_pct}% peak probability, {high_days} high-risk day(s). "
            f"First high-risk day: {first_high_date}. "
            "Activate emergency drainage protocols."
        )
    elif level == "MEDIUM":
        return (
            f"🟡 ELEVATED FLOOD RISK — {zone_short} Zone: "
            f"{prob_pct}% peak probability. Monitor saturation indices closely."
        )
    else:
        return (
            f"🟢 LOW RISK — {zone_short} Zone: "
            f"{prob_pct}% peak probability. Normal conditions forecast."
        )
