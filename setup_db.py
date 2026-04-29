"""
setup_db.py — Baku Sentinel
Pre-bakes model predictions into gold.predictions for instant API responses.
Run once before the demo: python setup_db.py
"""

import logging
import sys

import duckdb

from src import config, model, pipeline

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_COLS = [
    "zone", "time_6h", "temperature_2m", "relative_humidity_2m", "precipitation",
    "wind_speed_10m", "soil_moisture_0_to_7cm", "soil_moisture_7_to_28cm",
    "et0_fao_evapotranspiration", "is_flood", "risk_score", "flood_pred", "risk_level",
]


def main() -> None:
    logger.info("Loading gold.flood_features...")
    try:
        df = pipeline.load_gold()
    except Exception as exc:
        logger.error(f"gold.flood_features not found: {exc}")
        logger.error("Run ETL first: python -c \"from src.pipeline import run_pipeline; run_pipeline()\"")
        sys.exit(1)

    logger.info(f"Loaded {len(df):,} rows. Running model inference...")
    df_pred = model.predict(df)
    df_pred["risk_level"] = df_pred["risk_level"].astype(str)
    df_pred["risk_score"] = df_pred["risk_score"].astype("float64")
    df_out = df_pred[_COLS].copy()

    logger.info(f"Writing {len(df_out):,} rows to gold.predictions...")
    conn = duckdb.connect(str(config.DB_PATH))
    try:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {config.SCHEMA_GOLD}")
        conn.execute("CREATE OR REPLACE TABLE gold.predictions AS SELECT * FROM df_out")
        n = conn.execute("SELECT count(*) FROM gold.predictions").fetchone()[0]
        pos = conn.execute("SELECT avg(is_flood) FROM gold.predictions").fetchone()[0]
        logger.info(f"Done: {n:,} rows | flood rate: {pos * 100:.2f}%")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
