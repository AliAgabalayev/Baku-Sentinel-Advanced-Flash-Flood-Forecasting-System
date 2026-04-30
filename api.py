"""
api.py — Baku Sentinel
FastAPI server bridging the React frontend to the Python ML backend.

Endpoints:
  GET /api/forecast               — 30-day 6-hourly flood risk forecast
  GET /api/historical?start=&end= — historical predictions from gold.predictions
  GET /api/metrics                — model evaluation metrics
"""

import json
import os
from datetime import datetime

import duckdb
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src import config, predict

app = FastAPI(title="Baku Sentinel API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

LIVE_MODE = os.getenv("LIVE_MODE", "false").lower() == "true"
_forecast_cache: dict = {}

_FORECAST_COLS = [
    "zone", "time", "temperature_2m", "relative_humidity_2m", "precipitation",
    "wind_speed_10m", "soil_moisture_0_to_7cm", "soil_moisture_7_to_28cm",
    "et0_fao_evapotranspiration", "river_discharge", "risk_score", "flood_pred", "risk_level",
]


def _open_db():
    return duckdb.connect(str(config.DB_PATH), read_only=True)


def _risk_level_str(score: float) -> str:
    if score >= config.RISK_HIGH:
        return "HIGH"
    if score >= config.RISK_MEDIUM:
        return "MEDIUM"
    return "LOW"


def _check_predictions_table(conn) -> None:
    rows = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'gold' AND table_name = 'predictions'"
    ).fetchall()
    if not rows:
        raise HTTPException(status_code=503, detail="Run setup_db.py first")


def _serialize_forecast(df: pd.DataFrame) -> list:
    df = df.copy()
    df["time"] = pd.to_datetime(df["time_6h"]).dt.strftime("%Y-%m-%dT%H:%M:%S")
    df["risk_level"] = df["risk_level"].astype(str)
    df["flood_pred"] = df["flood_pred"].astype(int)
    if "river_discharge" not in df.columns:
        df["river_discharge"] = 0.0
    return df[_FORECAST_COLS].fillna(0).to_dict(orient="records")


def _forecast_from_gold(conn) -> pd.DataFrame:
    """Demo mode: take the 120 most-recent rows per zone, shift timestamps to start from now."""
    df = conn.execute("""
        WITH ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY zone ORDER BY time_6h DESC) AS rn
            FROM gold.predictions
        )
        SELECT zone, time_6h, temperature_2m, relative_humidity_2m, precipitation,
               wind_speed_10m, soil_moisture_0_to_7cm, soil_moisture_7_to_28cm,
               et0_fao_evapotranspiration, risk_score, flood_pred, risk_level
        FROM ranked
        WHERE rn <= 120
        ORDER BY zone, time_6h
    """).df()

    base = pd.Timestamp.now().floor("6h")
    shifted = []
    for _, grp in df.groupby("zone"):
        grp = grp.sort_values("time_6h").copy()
        delta = base - grp["time_6h"].iloc[0]
        grp["time_6h"] = grp["time_6h"] + delta
        shifted.append(grp)

    df = pd.concat(shifted).sort_values(["time_6h", "zone"]).reset_index(drop=True)
    df["river_discharge"] = 0.0
    return df


@app.get("/api/forecast")
def get_forecast():
    now = datetime.now()
    cache_key = f"{now.date().isoformat()}-{now.hour // 6}"
    if cache_key in _forecast_cache:
        return _forecast_cache[cache_key]

    try:
        if LIVE_MODE:
            results = predict.run_30day_forecast()
            df = results["forecast"]
        else:
            conn = _open_db()
            try:
                _check_predictions_table(conn)
                df = _forecast_from_gold(conn)
            finally:
                conn.close()

        data = _serialize_forecast(df)
        _forecast_cache.clear()
        _forecast_cache[cache_key] = data
        return data

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/api/historical")
def get_historical(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
):
    conn = _open_db()
    try:
        _check_predictions_table(conn)
        df = conn.execute(
            """
            SELECT zone, time_6h, precipitation, is_flood, risk_score, flood_pred, risk_level
            FROM gold.predictions
            WHERE time_6h >= ? AND time_6h < ?
            ORDER BY zone, time_6h
            """,
            [start, end],
        ).df()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        conn.close()

    return [
        {
            "zone": row.zone,
            "time": pd.Timestamp(row.time_6h).strftime("%Y-%m-%dT%H:%M:%S"),
            "precipitation": float(row.precipitation),
            "predicted_score": float(row.risk_score),
            "actual_score": float(row.is_flood),
            "flood_pred": int(row.flood_pred),
            "is_flood": int(row.is_flood),
            "predicted_level": _risk_level_str(float(row.risk_score)),
            "actual_level": _risk_level_str(float(row.is_flood)),
            "event_label": None,
        }
        for row in df.itertuples(index=False)
    ]


@app.get("/api/metrics")
def get_metrics():
    path = config.MODELS_DIR / "baku_sentinel_xgb_metrics.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Metrics file not found")
    with open(path) as f:
        return json.load(f)
