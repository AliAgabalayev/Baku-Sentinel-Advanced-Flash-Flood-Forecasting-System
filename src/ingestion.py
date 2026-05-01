"""
ingestion.py — Baku Sentinel
============================
Fetches hourly weather + daily flood data from Open-Meteo APIs.
Writes raw data into the Bronze DuckDB schema.

Bronze tables:
  bronze.weather_raw_{zone_slug}   — hourly weather
  bronze.flood_raw_{zone_slug}     — daily river discharge
"""

import logging
import random
import time

import duckdb
import pandas as pd
import requests

from src import config

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# HTTP helper
# ══════════════════════════════════════════════════════════════════════════════

def _make_request(url: str, params: dict) -> dict:
    for attempt in range(config.MAX_RETRIES):
        resp = None
        try:
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as exc:
            if resp is not None and resp.status_code == 400:
                logger.error(f"Bad request (400): {resp.text}")
                raise
            if attempt == config.MAX_RETRIES - 1:
                logger.error(f"Failed after {config.MAX_RETRIES} attempts: {exc}")
                raise
            wait = (config.BACKOFF_FACTOR ** attempt) + random.uniform(0, 1)
            logger.warning(f"Attempt {attempt + 1} failed — retrying in {wait:.1f}s")
            time.sleep(wait)


# ══════════════════════════════════════════════════════════════════════════════
# Fetch helpers — return DataFrames
# ══════════════════════════════════════════════════════════════════════════════

def fetch_weather_historical(zone: str, lat: float, lon: float,
                             start: str, end: str) -> pd.DataFrame:
    """Fetch hourly historical weather from Open-Meteo Archive API."""
    logger.info(f"[Historical] {zone}  {start} → {end}")
    params = {
        "latitude":  lat,
        "longitude": lon,
        "start_date": start,
        "end_date":   end,
        "hourly":    ",".join(config.HOURLY_VARIABLES),
        "timezone":  "auto",
    }
    data = _make_request(config.HISTORICAL_URL, params)
    if "hourly" not in data:
        raise ValueError(f"Malformed archive response for {zone}: {data}")
    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    df["zone"] = zone
    return df


def fetch_weather_forecast(zone: str, lat: float, lon: float,
                           forecast_days: int = 15) -> pd.DataFrame:
    """Fetch hourly forecast from Open-Meteo Forecast API (up to 15 days)."""
    logger.info(f"[Forecast] {zone}  {forecast_days}d")
    params = {
        "latitude":      lat,
        "longitude":     lon,
        "hourly":        ",".join(config.HOURLY_VARIABLES),
        "timezone":      "auto",
        "forecast_days": forecast_days,
    }
    data = _make_request(config.FORECAST_URL, params)
    if "hourly" not in data:
        raise ValueError(f"Malformed forecast response for {zone}: {data}")
    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    df["zone"] = zone
    return df


def fetch_flood_historical(zone: str, lat: float, lon: float,
                           start: str, end: str) -> pd.DataFrame:
    """Fetch daily river discharge from Open-Meteo Flood API."""
    logger.info(f"[Flood] {zone}  {start} → {end}")
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "start_date": start,
        "end_date":   end,
        "daily":      config.FLOOD_VARIABLE,
        "timezone":   "auto",
    }
    data = _make_request(config.FLOOD_URL, params)
    if "daily" not in data:
        logger.warning(f"No flood data for {zone} at ({lat}, {lon})")
        return pd.DataFrame()
    df = pd.DataFrame(data["daily"])
    df["time"] = pd.to_datetime(df["time"])
    df["zone"] = zone
    return df


# ══════════════════════════════════════════════════════════════════════════════
# Bronze layer writers
# ══════════════════════════════════════════════════════════════════════════════

def _zone_slug(zone_name: str) -> str:
    return zone_name.lower().replace(" ", "_")


def write_bronze(conn: duckdb.DuckDBPyConnection,
                 df: pd.DataFrame,
                 table_name: str) -> None:
    """Upsert a DataFrame into a Bronze DuckDB table."""
    tmp = f"_tmp_{table_name}"
    conn.execute(f"CREATE OR REPLACE TEMP TABLE {tmp} AS SELECT * FROM df")
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {config.SCHEMA_BRONZE}.{table_name}
        AS SELECT * FROM {tmp} WHERE 1=0
    """)
    conn.execute(f"""
        INSERT INTO {config.SCHEMA_BRONZE}.{table_name}
        SELECT src.* FROM {tmp} src
        WHERE NOT EXISTS (
            SELECT 1 FROM {config.SCHEMA_BRONZE}.{table_name} dst
            WHERE dst.time = src.time AND dst.zone = src.zone
        )
    """)
    n = conn.execute(f"SELECT count(*) FROM {config.SCHEMA_BRONZE}.{table_name}").fetchone()[0]
    logger.info(f"Bronze {config.SCHEMA_BRONZE}.{table_name}: {n} total rows")


# ══════════════════════════════════════════════════════════════════════════════
# Full historical ingest (run once / periodically)
# ══════════════════════════════════════════════════════════════════════════════

def run_historical_ingest(
    start: str = config.HISTORICAL_START,
    end:   str = config.HISTORICAL_END,
) -> None:
    """
    Fetch all historical weather + flood data for every zone,
    write to Bronze schema in DuckDB.
    """
    conn = duckdb.connect(str(config.DB_PATH))
    try:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {config.SCHEMA_BRONZE}")
        for zone_cfg in config.BAKU_ZONES:
            zone = zone_cfg["zone"]
            lat  = zone_cfg["latitude"]
            lon  = zone_cfg["longitude"]
            slug = _zone_slug(zone)

            # Weather
            try:
                df_w = fetch_weather_historical(zone, lat, lon, start, end)
                write_bronze(conn, df_w, f"weather_raw_{slug}")
            except Exception as e:
                logger.error(f"Weather ingest failed for {zone}: {e}")

            # Flood
            try:
                df_f = fetch_flood_historical(zone, lat, lon, start, end)
                if not df_f.empty:
                    write_bronze(conn, df_f, f"flood_raw_{slug}")
            except Exception as e:
                logger.error(f"Flood ingest failed for {zone}: {e}")

    finally:
        conn.close()
    logger.info("Historical ingest complete.")


# ══════════════════════════════════════════════════════════════════════════════
# Live forecast fetch (used by forecast pipeline)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_all_forecast(forecast_days: int = config.FORECAST_DAYS) -> pd.DataFrame:
    """
    Fetch live forecast for all zones, return a combined DataFrame.
    Does NOT write to Bronze (forecast data flows directly into Silver stream).
    """
    frames = []
    for zone_cfg in config.BAKU_ZONES:
        try:
            df = fetch_weather_forecast(
                zone_cfg["zone"],
                zone_cfg["latitude"],
                zone_cfg["longitude"],
                forecast_days=forecast_days,
            )
            frames.append(df)
        except Exception as e:
            logger.error(f"Forecast fetch failed for {zone_cfg['zone']}: {e}")
    if not frames:
        raise RuntimeError("All forecast fetches failed.")
    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"Forecast fetch complete: {len(combined)} hourly rows across {combined['zone'].nunique()} zones.")
    return combined
