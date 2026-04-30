"""
predict.py — Baku Sentinel
=========================
Main entry point for generating the 30-day flood risk forecast.
Phases:
1. Fetch live 15-day forecast (Open-Meteo).
2. Extend to 30 days using climatological averages (WeatherClimatologyModel).
3. Process through Sentinel Feature Engineering (pipeline.py).
4. Run inference using calibrated XGBoost model (model.py).
"""

import logging
import pandas as pd
from src import config, ingestion, pipeline, model

logger = logging.getLogger(__name__)

def run_30day_forecast(model_name: str = "baku_sentinel_xgb") -> dict:
    """
    Executes the end-to-end 30-day forecast.
    
    Returns
    -------
    results : dict containing 'combined_forecast', 'alerts', and 'metadata'
    """
    logger.info("=" * 60)
    logger.info("Baku Sentinel: Starting 30-Day Forecast Runner")
    logger.info("=" * 60)

    # 1. Fetch live forecast (15 days)
    logger.info(f"Phase 1: Fetching {config.FORECAST_DAYS}-day live forecast...")
    df_live_raw = ingestion.fetch_all_forecast(forecast_days=config.FORECAST_DAYS)

    # 2. Run through forecast pipeline (includes 30-day climatological extension)
    logger.info("Phase 2: Extending horizon to 30 days & Engineering features...")
    df_features = pipeline.run_forecast_pipeline(df_live_raw, extend_to_days=30)

    # 3. Load model and predict
    logger.info(f"Phase 3: Running inference with model: {model_name}")
    df_preds = model.predict(df_features, model_name=model_name)

    # 4. Generate alert summary
    alerts = _generate_alerts(df_preds)
    
    # 5. Build metadata
    metadata = {
        "forecast_start": str(df_preds["time_6h"].min()),
        "forecast_end":   str(df_preds["time_6h"].max()),
        "horizon_days":   30,
        "high_risk_count": int((df_preds["risk_level"] == "HIGH").sum()),
        "model_used":     model_name
    }

    logger.info(f"Forecast complete. High-risk instances found: {metadata['high_risk_count']}")
    
    return {
        "forecast": df_preds,
        "alerts":   alerts,
        "metadata": metadata
    }

def _generate_alerts(df: pd.DataFrame) -> pd.DataFrame:
    """Produces a per-zone summary of risks and alerts."""
    rows = []
    for zone, grp in df.groupby("zone"):
        max_score = grp["risk_score"].max()
        high_risk_hours = len(grp[grp["risk_level"] == "HIGH"]) * 6
        
        risk_level = "LOW"
        if max_score >= config.RISK_HIGH:
            risk_level = "HIGH"
        elif max_score >= config.RISK_MEDIUM:
            risk_level = "MEDIUM"
            
        alert_msg = _compose_alert(zone, risk_level, max_score, high_risk_hours)
        
        rows.append({
            "zone": zone,
            "max_risk_score": round(max_score, 3),
            "risk_level": risk_level,
            "high_risk_exposure_hours": high_risk_hours,
            "alert_message": alert_msg
        })
        
    return pd.DataFrame(rows).sort_values("max_risk_score", ascending=False)

def _compose_alert(zone: str, level: str, score: float, hours: int) -> str:
    """Helper to generate a human-readable alert string."""
    pct = round(score * 100, 1)
    if level == "HIGH":
        return f"🚨 CRITICAL: {zone} shows {pct}% flood probability. {hours}h total exposure predicted."
    elif level == "MEDIUM":
        return f"⚠️ WARNING: {zone} shows {pct}% flood probability. Monitor levels."
    return f"✅ Normal: {zone} risk is low ({pct}%)."

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = run_30day_forecast()
    print("\n--- ZONE ALERT SUMMARY ---")
    print(results["alerts"][["zone", "risk_level", "max_risk_score", "alert_message"]].to_string(index=False))
