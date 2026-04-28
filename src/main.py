"""
main.py
=======
Baku Sentinel — End-to-End Pipeline Orchestrator

Usage:
  python main.py --mode ingest    # Fetch & store historical data (Bronze)
  python main.py --mode etl       # Bronze → Silver → Gold ETL
  python main.py --mode train     # Train model on Gold layer
  python main.py --mode forecast  # Run 30-day live forecast (Live 15d + Clim 15d)
  python main.py --mode full      # ingest + etl + train + forecast
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from src import config, predict
import ingestion
import pipeline
import model as mdl

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOGS_DIR / "baku_sentinel.log", mode="a"),
    ],
)
logger = logging.getLogger("main")


# ══════════════════════════════════════════════════════════════════════════════
# Steps
# ══════════════════════════════════════════════════════════════════════════════

def step_ingest():
    logger.info("━━━ STEP: INGEST (Bronze) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    ingestion.run_historical_ingest(
        start=config.HISTORICAL_START,
        end=config.HISTORICAL_END,
    )


def step_etl():
    logger.info("━━━ STEP: ETL (Silver → Gold) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    pipeline.run_pipeline()


def step_train():
    logger.info("━━━ STEP: TRAIN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    df_gold = pipeline.load_gold()
    bundle  = mdl.train(df_gold)

    logger.info("\nMetrics:")
    for k, v in bundle["metrics"].items():
        if k != "report":
            logger.info(f"  {k:25s}: {v}")

    logger.info("\nTop 10 SHAP features:")
    for feat, val in list(bundle["shap_importance"].items())[:10]:
        logger.info(f"  {feat:35s}: {val:.4f}")

    return bundle


def step_forecast():
    logger.info("━━━ STEP: FORECAST (30-day horizon) ━━━━━━━━━━━━━━━━━━━━━━━━━━")

    results = predict.run_30day_forecast()
    df_predicted = results["forecast"]
    alerts_df = results["alerts"]

    # Save
    config.REPORTS_DIR.mkdir(exist_ok=True)
    out = config.REPORTS_DIR / "forecast_30day.csv"
    df_predicted.to_csv(out, index=False)
    logger.info(f"Forecast saved → {out}")

    logger.info("\n── Alert Summary ───────────────────────────────────────────")
    icons = {"HIGH": "🚨", "MEDIUM": "⚠️ ", "LOW": "✅"}
    for _, row in alerts_df.iterrows():
        level = row["risk_level"]
        logger.info(f"{icons[level]}  {row['zone']:20s}  peak={row['max_risk_score']*100:.1f}%  "
                    f"exposure={row['high_risk_exposure_hours']}h  [{level}]")
        logger.info(f"    {row['alert_message']}")

    return df_predicted


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Baku Sentinel Flood Forecasting")
    parser.add_argument(
        "--mode",
        choices=["ingest", "etl", "train", "forecast", "full"],
        default="full",
    )
    args = parser.parse_args()

    if args.mode == "ingest":
        step_ingest()
    elif args.mode == "etl":
        step_etl()
    elif args.mode == "train":
        step_train()
    elif args.mode == "forecast":
        step_forecast()
    elif args.mode == "full":
        step_ingest()
        step_etl()
        step_train()
        step_forecast()


if __name__ == "__main__":
    main()
