import os
import time
import random
import requests
import pandas as pd
import logging
import duckdb
from datetime import datetime
from src import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _make_request(url, params):
    for attempt in range(config.MAX_RETRIES):
        response = None
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if response is not None and response.status_code == 400:
                logger.error(f"Bad Request: {response.text}")
            if attempt == config.MAX_RETRIES - 1:
                logger.error(f"Request failed after {config.MAX_RETRIES} attempts: {e}")
                raise e

            wait_time = (config.BACKOFF_FACTOR ** attempt) + random.uniform(0, 1)
            logger.warning(f"Attempt {attempt + 1} failed. Retrying in {wait_time:.2f}s...")
            time.sleep(wait_time)
    return None


def fetch_weather_hourly(zone_name, latitude, longitude, start_date, end_date):
    logger.info(f"Fetching hourly weather for {zone_name} ({start_date} to {end_date})")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(config.HOURLY_FEATURES),
        "timezone": "auto"
    }

    data = _make_request(config.HISTORICAL_URL, params)

    if "hourly" not in data:
        raise ValueError(f"Malformed response from Archive API for {zone_name}")

    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    df["zone"] = zone_name
    return df


def fetch_flood_hourly(zone_name, latitude, longitude, start_date, end_date):
    logger.info(f"Fetching flood data for {zone_name} ({start_date} to {end_date})")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "river_discharge",
        "timezone": "auto"
    }

    data = _make_request(config.FLOOD_URL, params)

    if "daily" not in data:
        logger.warning(f"No flood data returned for {zone_name}")
        return pd.DataFrame()

    df = pd.DataFrame(data["daily"])
    df["time"] = pd.to_datetime(df["time"])
    df["zone"] = zone_name
    return df


def fetch_weather_forecast(zone_name, latitude, longitude, forecast_days=15):
    logger.info(f"Fetching {forecast_days}-day forecast for {zone_name}")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(config.HOURLY_FEATURES),
        "forecast_days": forecast_days,
        "timezone": "auto"
    }

    data = _make_request(config.FORECAST_URL, params)

    if "hourly" not in data:
        raise ValueError(f"Malformed response from Forecast API for {zone_name}")

    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    df["zone"] = zone_name
    return df


def ingest_to_bronze(df, table_name, mode='overwrite'):
    if df.empty:
        return

    conn = duckdb.connect(str(config.DB_PATH))
    try:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {config.SCHEMA_BRONZE}")

        df["_ingested_at"] = datetime.now()
        df["_source_system"] = "open-meteo"

        normalized_table = table_name.lower().replace(' ', '_')
        target_full_path = f"{config.SCHEMA_BRONZE}.{normalized_table}"

        if mode == 'overwrite':
            conn.execute(f"CREATE OR REPLACE TABLE {target_full_path} AS SELECT * FROM df")
        else:
            conn.execute(f"CREATE TABLE IF NOT EXISTS {target_full_path} AS SELECT * FROM df WHERE 1=0")
            conn.execute(f"""
                INSERT INTO {target_full_path}
                SELECT * FROM df src
                WHERE NOT EXISTS (
                    SELECT 1 FROM {target_full_path} dest
                    WHERE dest.time = src.time AND dest.zone = src.zone
                )
            """)

        count = conn.execute(f"SELECT COUNT(*) FROM {target_full_path}").fetchone()[0]
        logger.info(f"Table {target_full_path} now has {count} total rows.")
    finally:
        conn.close()


def run_full_ingestion():
    for zone in config.BAKU_ZONES:
        name = zone["zone"]
        lat = zone["latitude"]
        lon = zone["longitude"]

        weather_df = fetch_weather_hourly(name, lat, lon, config.HISTORICAL_START, config.HISTORICAL_END)
        ingest_to_bronze(weather_df, f"weather_raw_{name}")

        flood_df = fetch_flood_hourly(name, lat, lon, config.HISTORICAL_START, config.HISTORICAL_END)
        ingest_to_bronze(flood_df, f"flood_raw_{name}")