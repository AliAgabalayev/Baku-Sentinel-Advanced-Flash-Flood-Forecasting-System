import duckdb
import logging
import os
import pandas as pd
from src import config, ingestion

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_sentinel_feature_sql(input_table, output_table, is_forecast=False):
    discharge_lag_6h = "0.0" if is_forecast else "LAG(river_discharge, 1) OVER (PARTITION BY zone ORDER BY time_6h)"
    discharge_lag_24h = "0.0" if is_forecast else "LAG(river_discharge, 4) OVER (PARTITION BY zone ORDER BY time_6h)"
    discharge_roll_max = "0.0" if is_forecast else "MAX(river_discharge) OVER (PARTITION BY zone ORDER BY time_6h ROWS BETWEEN 3 PRECEDING AND CURRENT ROW)"
    discharge_trend = "0.0" if is_forecast else "river_discharge - LAG(river_discharge, 1) OVER (PARTITION BY zone ORDER BY time_6h)"
    highland_discharge = "0.0" if is_forecast else "river_discharge"

    target_logic = "CASE WHEN river_discharge > 1.0 AND (precipitation > 1.0 OR relative_humidity_2m > 85) THEN 1 ELSE 0 END AS is_flood"
    if is_forecast:
        target_logic = "0 AS is_flood"

    return f"""
    CREATE OR REPLACE TABLE {output_table} AS
    WITH lagged AS (
        SELECT *,
            LAG(precipitation, 1) OVER (PARTITION BY zone ORDER BY time_6h) AS precip_lag_6h,
            LAG(precipitation, 2) OVER (PARTITION BY zone ORDER BY time_6h) AS precip_lag_12h,
            LAG(precipitation, 4) OVER (PARTITION BY zone ORDER BY time_6h) AS precip_lag_24h,
            LAG(precipitation, 8) OVER (PARTITION BY zone ORDER BY time_6h) AS precip_lag_48h,
            {discharge_lag_6h} AS discharge_lag_6h,
            {discharge_lag_24h} AS discharge_lag_24h,
            LAG(temperature_2m, 4) OVER (PARTITION BY zone ORDER BY time_6h) AS temp_lag_24h,
            SUM(precipitation) OVER (PARTITION BY zone ORDER BY time_6h ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS precip_roll_sum_24h,
            SUM(precipitation) OVER (PARTITION BY zone ORDER BY time_6h ROWS BETWEEN 7 PRECEDING AND CURRENT ROW) AS precip_roll_sum_48h,
            SUM(precipitation) OVER (PARTITION BY zone ORDER BY time_6h ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS precip_roll_sum_72h,
            MAX(precipitation) OVER (PARTITION BY zone ORDER BY time_6h ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS precip_roll_max_24h,
            {discharge_roll_max} AS discharge_roll_max_24h,
            MAX(relative_humidity_2m) OVER (PARTITION BY zone ORDER BY time_6h ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS humidity_roll_max_24h,
            SUM(et0_fao_evapotranspiration) OVER (PARTITION BY zone ORDER BY time_6h ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS et0_roll_sum_24h
        FROM {input_table}
    ),
    api_calc AS (
        SELECT *,
            (precipitation + 0.85 * COALESCE(precip_lag_6h, 0) + 0.85^2 * COALESCE(precip_lag_12h, 0) + 0.85^4 * COALESCE(precip_lag_24h, 0)) AS api_7d,
            (soil_moisture_0_to_7cm + soil_moisture_7_to_28cm) / 2 AS soil_saturation_index
        FROM lagged
    ),
    additional_derived AS (
        SELECT *,
            soil_moisture_0_to_7cm - LAG(soil_moisture_0_to_7cm, 1) OVER (PARTITION BY zone ORDER BY time_6h) AS soil_moisture_change_6h,
            0.45 - soil_saturation_index AS soil_moisture_deficit,
            CASE WHEN soil_temperature_0_to_7cm < 0 THEN 1 ELSE 0 END AS frozen_ground_flag,
            {discharge_trend} AS discharge_trend_6h,
            temperature_2m - temp_lag_24h AS temp_trend_24h,
            precipitation - et0_fao_evapotranspiration AS et_deficit_6h,
            precip_roll_sum_24h - et0_roll_sum_24h AS et_deficit_24h,
            relative_humidity_2m * precipitation AS humidity_precip_product
        FROM api_calc
    ),
    highland_context AS (
        SELECT time_6h, precip_roll_sum_24h AS highland_precip_24h, {highland_discharge} AS highland_discharge_6h
        FROM additional_derived WHERE zone = 'High Relief'
    )
    SELECT d.*, h.highland_precip_24h, h.highland_discharge_6h,
        CASE 
            WHEN d.zone = 'High Relief' THEN d.precip_roll_sum_24h * (1/3.0)
            WHEN d.zone = 'Moderate Relief' THEN h.highland_precip_24h * (1/1.5)
            ELSE h.highland_precip_24h * (1/1.0)
        END AS zone_cascade_risk,
        SIN(2 * PI() * EXTRACT(HOUR FROM d.time_6h) / 24) AS hour_sin,
        COS(2 * PI() * EXTRACT(HOUR FROM d.time_6h) / 24) AS hour_cos,
        SIN(2 * PI() * EXTRACT(DOY FROM d.time_6h) / 365) AS doy_sin,
        COS(2 * PI() * EXTRACT(DOY FROM d.time_6h) / 365) AS doy_cos,
        CASE WHEN EXTRACT(MONTH FROM d.time_6h) IN (11, 12, 1, 2) THEN 1 ELSE 0 END AS is_winter,
        {target_logic}
    FROM additional_derived d
    LEFT JOIN highland_context h ON d.time_6h = h.time_6h;
    """


def run_forecast_pipeline(df_forecast):
    conn = duckdb.connect(str(config.DB_PATH))
    try:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {config.SCHEMA_SILVER}")

        conn.execute("CREATE OR REPLACE TEMP TABLE forecast_raw_temp AS SELECT * FROM df_forecast")

        conn.execute(f"""
        CREATE OR REPLACE TEMP TABLE forecast_silver_new AS
        SELECT zone, time_bucket(INTERVAL '6 hours', time) AS time_6h,
            AVG(temperature_2m) AS temperature_2m, AVG(relative_humidity_2m) AS relative_humidity_2m,
            SUM(precipitation) AS precipitation, AVG(wind_speed_10m) AS wind_speed_10m,
            AVG(soil_moisture_0_to_7cm) AS soil_moisture_0_to_7cm, AVG(soil_moisture_7_to_28cm) AS soil_moisture_7_to_28cm,
            AVG(soil_temperature_0_to_7cm) AS soil_temperature_0_to_7cm, SUM(et0_fao_evapotranspiration) AS et0_fao_evapotranspiration,
            0.0 AS river_discharge
        FROM forecast_raw_temp GROUP BY 1, 2
        """)

        conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {config.SCHEMA_SILVER}.weather_stream_6h AS 
        SELECT * FROM forecast_silver_new WHERE 1=0
        """)

        conn.execute(f"""
        INSERT INTO {config.SCHEMA_SILVER}.weather_stream_6h 
        SELECT src.* FROM forecast_silver_new src
        WHERE NOT EXISTS (
            SELECT 1 FROM {config.SCHEMA_SILVER}.weather_stream_6h dest 
            WHERE dest.time_6h = src.time_6h AND dest.zone = src.zone
        )
        """)

        count_stream = conn.execute(
            f"SELECT count(*) FROM {config.SCHEMA_SILVER}.weather_stream_6h WHERE time_6h < CURRENT_TIMESTAMP").fetchone()[
            0]
        if count_stream < 5:
            logger.info("Seeding stream from historical silver...")
            conn.execute(
                f"INSERT INTO {config.SCHEMA_SILVER}.weather_stream_6h SELECT * FROM {config.SCHEMA_SILVER}.weather_flood_6h WHERE time_6h > CURRENT_DATE - INTERVAL '10 days'")

        gold_sql = get_sentinel_feature_sql(f"{config.SCHEMA_SILVER}.weather_stream_6h", "stream_gold",
                                            is_forecast=True)
        conn.execute(gold_sql)

        return conn.execute("SELECT * FROM stream_gold WHERE time_6h >= CURRENT_TIMESTAMP").df()
    finally:
        conn.close()


def create_silver_layer():
    conn = duckdb.connect(str(config.DB_PATH))
    try:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {config.SCHEMA_SILVER}")
        logger.info("Creating Silver layer and CLEANING Bronze...")

        resample_sql = f"""
        CREATE OR REPLACE TABLE {config.SCHEMA_SILVER}.weather_flood_6h AS
        WITH combined_bronze AS ({" UNION ALL ".join([f"SELECT * FROM {config.SCHEMA_BRONZE}.weather_raw_{z['zone'].lower().replace(' ', '_')}" for z in config.BAKU_ZONES])}),
        combined_flood AS ({" UNION ALL ".join([f"SELECT * FROM {config.SCHEMA_BRONZE}.flood_raw_{z['zone'].lower().replace(' ', '_')}" for z in config.BAKU_ZONES])}),
        resampled_weather AS (
            SELECT zone, time_bucket(INTERVAL '6 hours', time) AS time_6h,
                AVG(temperature_2m) AS temperature_2m, AVG(relative_humidity_2m) AS relative_humidity_2m,
                SUM(precipitation) AS precipitation, AVG(wind_speed_10m) AS wind_speed_10m,
                AVG(soil_moisture_0_to_7cm) AS soil_moisture_0_to_7cm, AVG(soil_moisture_7_to_28cm) AS soil_moisture_7_to_28cm,
                AVG(soil_temperature_0_to_7cm) AS soil_temperature_0_to_7cm, SUM(et0_fao_evapotranspiration) AS et0_fao_evapotranspiration
            FROM combined_bronze GROUP BY 1, 2
        ),
        resampled_flood AS (
            SELECT zone, CAST(time AS DATE) AS date_key, MAX(river_discharge) AS river_discharge
            FROM combined_flood GROUP BY 1, 2
        )
        SELECT w.*, COALESCE(f.river_discharge, 0.0) AS river_discharge
        FROM resampled_weather w LEFT JOIN resampled_flood f ON w.zone = f.zone AND CAST(w.time_6h AS DATE) = f.date_key
        ORDER BY zone, time_6h;
        """
        conn.execute(resample_sql)

        logger.info("Dropping Bronze schema to save space...")
        conn.execute(f"DROP SCHEMA IF EXISTS {config.SCHEMA_BRONZE} CASCADE")

    finally:
        conn.close()


def create_gold_layer():
    conn = duckdb.connect(str(config.DB_PATH))
    try:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {config.SCHEMA_GOLD}")
        sql = get_sentinel_feature_sql(f"{config.SCHEMA_SILVER}.weather_flood_6h",
                                       f"{config.SCHEMA_GOLD}.flood_features")
        conn.execute(sql)
    finally:
        conn.close()


def run_pipeline():
    create_silver_layer()
    create_gold_layer()