"""
pipeline.py — Baku Sentinel
============================
Medallion ETL pipeline:  Bronze → Silver → Gold

Key standards:
- Idempotency: All stages are re-runnable without side effects.
- Schema Contracts: Explicit column definitions, no SELECT *.
- Null Handling: Deliberate COALESCE to ensure analytical integrity.
- Data Quality: Row-level DQ scores attached to the Gold layer.
"""

import logging
import duckdb
import pandas as pd
from src import config, weather_model

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Core SQL: Sentinel feature engineering
# ══════════════════════════════════════════════════════════════════════════════

def get_sentinel_feature_sql(input_table: str,
                              output_table: str,
                              is_forecast: bool = False) -> str:
    """
    Return the DuckDB SQL that transforms a 6-hourly silver table into
    a fully-featured gold table with zero leakage and DQ scoring.
    """

    # ── Target Logic ──────────────────────────────────────────────────────────
    # Computed in `base` so river_discharge is consumed at the source and never
    # propagated into the CTE chain where lag/rolling features are built.
    if is_forecast:
        target_expr = "0 AS is_flood"
    else:
        # COALESCE against the raw input columns (aliases not yet in scope here)
        target_expr = (
            "CASE WHEN COALESCE(river_discharge, 0.0) > 1.0 "
            "  AND (COALESCE(precipitation, 0.0) > 1.0 OR COALESCE(relative_humidity_2m, 0.0) > 85) "
            "THEN 1 ELSE 0 END AS is_flood"
        )

    # ── DQ Score Calculation (Row level) ──────────────────────────────────────
    dq_checks = []
    for var, (low, high) in config.SENSOR_BOUNDS.items():
        dq_checks.append(f"CASE WHEN {var} BETWEEN {low} AND {high} THEN 0 ELSE 1 END")
    
    # dq_score = 1.0 - (count of violations / total checks)
    dq_score_expr = f"1.0 - (({' + '.join(dq_checks)}) / {len(dq_checks)}.0)"

    return f"""
    CREATE OR REPLACE TABLE {output_table} AS
    WITH
    
    -- ── Step 1: Base Cleanup & DQ ──────────────────────────────────────────
    -- river_discharge is consumed here for the label and NOT forwarded, so it
    -- cannot be referenced by any lag/rolling CTE in later steps.
    base AS (
        SELECT
            zone,
            time_6h,
            COALESCE(temperature_2m, 0.0) AS temperature_2m,
            COALESCE(relative_humidity_2m, 0.0) AS relative_humidity_2m,
            COALESCE(precipitation, 0.0) AS precipitation,
            COALESCE(wind_speed_10m, 0.0) AS wind_speed_10m,
            COALESCE(soil_moisture_0_to_7cm, 0.0) AS soil_moisture_0_to_7cm,
            COALESCE(soil_moisture_7_to_28cm, 0.0) AS soil_moisture_7_to_28cm,
            COALESCE(soil_temperature_0_to_7cm, 0.0) AS soil_temperature_0_to_7cm,
            COALESCE(et0_fao_evapotranspiration, 0.0) AS et0_fao_evapotranspiration,
            {target_expr},
            {dq_score_expr} AS dq_score
        FROM {input_table}
    ),

    -- ── Step 2: lag & rolling features (NO DISCHARGE FEATURES) ──────────────
    lagged AS (
        SELECT *,
            LAG(precipitation, 1) OVER (PARTITION BY zone ORDER BY time_6h) AS precip_lag_6h,
            LAG(precipitation, 2) OVER (PARTITION BY zone ORDER BY time_6h) AS precip_lag_12h,
            LAG(precipitation, 4) OVER (PARTITION BY zone ORDER BY time_6h) AS precip_lag_24h,
            LAG(precipitation, 8) OVER (PARTITION BY zone ORDER BY time_6h) AS precip_lag_48h,
            LAG(temperature_2m, 4) OVER (PARTITION BY zone ORDER BY time_6h) AS temp_lag_24h,

            SUM(precipitation) OVER (PARTITION BY zone ORDER BY time_6h
                ROWS BETWEEN 3  PRECEDING AND CURRENT ROW) AS precip_roll_sum_24h,
            SUM(precipitation) OVER (PARTITION BY zone ORDER BY time_6h
                ROWS BETWEEN 7  PRECEDING AND CURRENT ROW) AS precip_roll_sum_48h,
            SUM(precipitation) OVER (PARTITION BY zone ORDER BY time_6h
                ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS precip_roll_sum_72h,
            MAX(precipitation) OVER (PARTITION BY zone ORDER BY time_6h
                ROWS BETWEEN 3  PRECEDING AND CURRENT ROW) AS precip_roll_max_24h,
            MAX(relative_humidity_2m) OVER (PARTITION BY zone ORDER BY time_6h
                ROWS BETWEEN 3  PRECEDING AND CURRENT ROW) AS humidity_roll_max_24h,
            SUM(et0_fao_evapotranspiration) OVER (PARTITION BY zone ORDER BY time_6h
                ROWS BETWEEN 3  PRECEDING AND CURRENT ROW) AS et0_roll_sum_24h
        FROM base
    ),

    -- ── Step 3: antecedent precipitation index + soil saturation ────────────
    api_calc AS (
        SELECT *,
            (  precipitation
             + 0.85   * COALESCE(precip_lag_6h,  0)
             + 0.85*0.85 * COALESCE(precip_lag_12h, 0)
             + 0.85*0.85*0.85*0.85 * COALESCE(precip_lag_24h, 0)
            ) AS api_7d,
            (soil_moisture_0_to_7cm + soil_moisture_7_to_28cm) / 2.0 AS soil_saturation_index
        FROM lagged
    ),

    -- ── Step 4: derived indices ───────────────────────────────────────────────
    additional_derived AS (
        SELECT *,
            soil_moisture_0_to_7cm
                - LAG(soil_moisture_0_to_7cm, 1)
                    OVER (PARTITION BY zone ORDER BY time_6h)     AS soil_moisture_change_6h,
            0.45 - soil_saturation_index                          AS soil_moisture_deficit,
            CASE WHEN soil_temperature_0_to_7cm < 0 THEN 1
                 ELSE 0 END                                       AS frozen_ground_flag,
            temperature_2m - temp_lag_24h                        AS temp_trend_24h,
            precipitation  - et0_fao_evapotranspiration          AS et_deficit_6h,
            precip_roll_sum_24h - et0_roll_sum_24h               AS et_deficit_24h,
            relative_humidity_2m * precipitation                 AS humidity_precip_product
        FROM api_calc
    ),

    -- ── Step 5: highland context for cascade signal ──────────────────────────
    highland_context AS (
        SELECT
            time_6h,
            precip_roll_sum_24h                                  AS highland_precip_24h
        FROM additional_derived
        WHERE zone = 'High Relief'
    )

    -- ── Step 6: assemble final table with strict schema ──────────────────────
    SELECT
        d.zone,
        d.time_6h,
        COALESCE(d.temperature_2m, 0.0) AS temperature_2m,
        COALESCE(d.relative_humidity_2m, 0.0) AS relative_humidity_2m,
        COALESCE(d.precipitation, 0.0) AS precipitation,
        COALESCE(d.wind_speed_10m, 0.0) AS wind_speed_10m,
        COALESCE(d.soil_moisture_0_to_7cm, 0.0) AS soil_moisture_0_to_7cm,
        COALESCE(d.soil_moisture_7_to_28cm, 0.0) AS soil_moisture_7_to_28cm,
        COALESCE(d.soil_temperature_0_to_7cm, 0.0) AS soil_temperature_0_to_7cm,
        COALESCE(d.et0_fao_evapotranspiration, 0.0) AS et0_fao_evapotranspiration,
        COALESCE(d.precip_lag_6h, 0.0) AS precip_lag_6h,
        COALESCE(d.precip_lag_12h, 0.0) AS precip_lag_12h,
        COALESCE(d.precip_lag_24h, 0.0) AS precip_lag_24h,
        COALESCE(d.precip_lag_48h, 0.0) AS precip_lag_48h,
        COALESCE(d.temp_lag_24h, 0.0) AS temp_lag_24h,
        COALESCE(d.precip_roll_sum_24h, 0.0) AS precip_roll_sum_24h,
        COALESCE(d.precip_roll_sum_48h, 0.0) AS precip_roll_sum_48h,
        COALESCE(d.precip_roll_sum_72h, 0.0) AS precip_roll_sum_72h,
        COALESCE(d.precip_roll_max_24h, 0.0) AS precip_roll_max_24h,
        COALESCE(d.humidity_roll_max_24h, 0.0) AS humidity_roll_max_24h,
        COALESCE(d.et0_roll_sum_24h, 0.0) AS et0_roll_sum_24h,
        COALESCE(d.api_7d, 0.0) AS api_7d,
        COALESCE(d.soil_saturation_index, 0.0) AS soil_saturation_index,
        COALESCE(d.soil_moisture_change_6h, 0.0) AS soil_moisture_change_6h,
        COALESCE(d.soil_moisture_deficit, 0.0) AS soil_moisture_deficit,
        COALESCE(d.frozen_ground_flag, 0) AS frozen_ground_flag,
        COALESCE(d.temp_trend_24h, 0.0) AS temp_trend_24h,
        COALESCE(d.et_deficit_6h, 0.0) AS et_deficit_6h,
        COALESCE(d.et_deficit_24h, 0.0) AS et_deficit_24h,
        COALESCE(d.humidity_precip_product, 0.0) AS humidity_precip_product,
        COALESCE(h.highland_precip_24h, 0.0) AS highland_precip_24h,
        
        -- Cascade risk: fraction of highland load routed to each zone
        CASE
            WHEN d.zone = 'High Relief'     THEN d.precip_roll_sum_24h * (1.0/3.0)
            WHEN d.zone = 'Moderate Relief' THEN COALESCE(h.highland_precip_24h, 0) * (1.0/1.5)
            ELSE                                 COALESCE(h.highland_precip_24h, 0) * (1.0/1.0)
        END AS zone_cascade_risk,

        -- Cyclic time encodings
        SIN(2 * PI() * EXTRACT(HOUR FROM d.time_6h) / 24)      AS hour_sin,
        COS(2 * PI() * EXTRACT(HOUR FROM d.time_6h) / 24)      AS hour_cos,
        SIN(2 * PI() * EXTRACT(DOY  FROM d.time_6h) / 365)     AS doy_sin,
        COS(2 * PI() * EXTRACT(DOY  FROM d.time_6h) / 365)     AS doy_cos,
        CASE WHEN EXTRACT(MONTH FROM d.time_6h) IN (11, 12, 1, 2)
             THEN 1 ELSE 0 END                                   AS is_winter,

        d.dq_score,
        d.is_flood

    FROM additional_derived d
    LEFT JOIN highland_context h ON d.time_6h = h.time_6h;
    """


# ══════════════════════════════════════════════════════════════════════════════
# Silver layer — resample hourly → 6h, join flood
# ══════════════════════════════════════════════════════════════════════════════

def create_silver_layer() -> None:
    """
    Bronze hourly weather + Bronze daily flood → Silver 6-hourly joined table.
    """
    conn = duckdb.connect(str(config.DB_PATH))
    try:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {config.SCHEMA_SILVER}")
        logger.info("Creating Silver layer from Bronze...")

        weather_unions = " UNION ALL ".join([
            f"SELECT * FROM {config.SCHEMA_BRONZE}.weather_raw_{z['zone'].lower().replace(' ', '_')}"
            for z in config.BAKU_ZONES
        ])
        flood_unions = " UNION ALL ".join([
            f"SELECT * FROM {config.SCHEMA_BRONZE}.flood_raw_{z['zone'].lower().replace(' ', '_')}"
            for z in config.BAKU_ZONES
        ])

        resample_sql = f"""
        CREATE OR REPLACE TABLE {config.SCHEMA_SILVER}.weather_flood_6h AS
        WITH
        combined_weather AS ({weather_unions}),
        combined_flood   AS ({flood_unions}),

        resampled_weather AS (
            SELECT
                zone,
                time_bucket(INTERVAL '6 hours', time) AS time_6h,
                AVG(temperature_2m)            AS temperature_2m,
                AVG(relative_humidity_2m)      AS relative_humidity_2m,
                SUM(precipitation)             AS precipitation,
                AVG(wind_speed_10m)            AS wind_speed_10m,
                AVG(soil_moisture_0_to_7cm)    AS soil_moisture_0_to_7cm,
                AVG(soil_moisture_7_to_28cm)   AS soil_moisture_7_to_28cm,
                AVG(soil_temperature_0_to_7cm) AS soil_temperature_0_to_7cm,
                SUM(et0_fao_evapotranspiration) AS et0_fao_evapotranspiration
            FROM combined_weather
            GROUP BY 1, 2
        ),

        resampled_flood AS (
            SELECT
                zone,
                CAST(time AS DATE)        AS date_key,
                MAX(river_discharge)       AS river_discharge
            FROM combined_flood
            GROUP BY 1, 2
        )

        SELECT
            w.zone,
            w.time_6h,
            COALESCE(w.temperature_2m, 0.0) AS temperature_2m,
            COALESCE(w.relative_humidity_2m, 0.0) AS relative_humidity_2m,
            COALESCE(w.precipitation, 0.0) AS precipitation,
            COALESCE(w.wind_speed_10m, 0.0) AS wind_speed_10m,
            COALESCE(w.soil_moisture_0_to_7cm, 0.0) AS soil_moisture_0_to_7cm,
            COALESCE(w.soil_moisture_7_to_28cm, 0.0) AS soil_moisture_7_to_28cm,
            COALESCE(w.soil_temperature_0_to_7cm, 0.0) AS soil_temperature_0_to_7cm,
            COALESCE(w.et0_fao_evapotranspiration, 0.0) AS et0_fao_evapotranspiration,
            COALESCE(f.river_discharge, 0.0) AS river_discharge
        FROM resampled_weather w
        LEFT JOIN resampled_flood f
            ON w.zone = f.zone
            AND CAST(w.time_6h AS DATE) = f.date_key + INTERVAL '1 day'
        ORDER BY zone, time_6h;
        """
        conn.execute(resample_sql)
        n = conn.execute(f"SELECT count(*) FROM {config.SCHEMA_SILVER}.weather_flood_6h").fetchone()[0]
        logger.info(f"Silver table created: {n:,} rows at 6h granularity.")

        # Optional: Purge Bronze
        # conn.execute(f"DROP SCHEMA IF EXISTS {config.SCHEMA_BRONZE} CASCADE")

    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Gold layer — feature engineering on historical data
# ══════════════════════════════════════════════════════════════════════════════

def create_gold_layer() -> None:
    conn = duckdb.connect(str(config.DB_PATH))
    try:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {config.SCHEMA_GOLD}")
        sql = get_sentinel_feature_sql(
            input_table  = f"{config.SCHEMA_SILVER}.weather_flood_6h",
            output_table = f"{config.SCHEMA_GOLD}.flood_features",
            is_forecast  = False,
        )
        conn.execute(sql)
        n = conn.execute(f"SELECT count(*) FROM {config.SCHEMA_GOLD}.flood_features").fetchone()[0]
        pos = conn.execute(f"SELECT avg(is_flood) FROM {config.SCHEMA_GOLD}.flood_features").fetchone()[0]
        logger.info(f"Gold table created: {n:,} rows  |  flood rate = {pos*100:.2f}%")
    finally:
        conn.close()


def load_gold() -> pd.DataFrame:
    conn = duckdb.connect(str(config.DB_PATH), read_only=True)
    try:
        df = conn.execute(f"SELECT * FROM {config.SCHEMA_GOLD}.flood_features").df()
        logger.info(f"Gold layer loaded: {df.shape}")
        return df
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Forecast stream pipeline
# ══════════════════════════════════════════════════════════════════════════════

def run_forecast_pipeline(df_forecast: pd.DataFrame, extend_to_days: int = 30) -> pd.DataFrame:
    conn = duckdb.connect(str(config.DB_PATH))
    try:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {config.SCHEMA_SILVER}")
        conn.execute("CREATE OR REPLACE TEMP TABLE forecast_raw_temp AS SELECT * FROM df_forecast")

        df_live_6h = conn.execute("""
        SELECT
            zone,
            time_bucket(INTERVAL '6 hours', time) AS time_6h,
            AVG(temperature_2m)             AS temperature_2m,
            AVG(relative_humidity_2m)       AS relative_humidity_2m,
            SUM(precipitation)              AS precipitation,
            AVG(wind_speed_10m)             AS wind_speed_10m,
            AVG(soil_moisture_0_to_7cm)     AS soil_moisture_0_to_7cm,
            AVG(soil_moisture_7_to_28cm)    AS soil_moisture_7_to_28cm,
            AVG(soil_temperature_0_to_7cm)  AS soil_temperature_0_to_7cm,
            SUM(et0_fao_evapotranspiration) AS et0_fao_evapotranspiration,
            0.0                             AS river_discharge
        FROM forecast_raw_temp
        GROUP BY 1, 2
        ORDER BY 1, 2
        """).df()

        if extend_to_days > 15:
            df_silver_6h = weather_model.get_extended_forecast(df_live_6h, target_days=extend_to_days)  # noqa: F841
        else:
            df_silver_6h = df_live_6h  # noqa: F841

        conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {config.SCHEMA_SILVER}.weather_stream_6h AS
        SELECT * FROM df_silver_6h WHERE 1=0
        """)

        conn.execute(f"""
        INSERT INTO {config.SCHEMA_SILVER}.weather_stream_6h
        SELECT src.* FROM df_silver_6h src
        WHERE NOT EXISTS (
            SELECT 1 FROM {config.SCHEMA_SILVER}.weather_stream_6h dst
            WHERE dst.time_6h = src.time_6h AND dst.zone = src.zone
        )
        """)

        gold_sql = get_sentinel_feature_sql(
            input_table  = f"{config.SCHEMA_SILVER}.weather_stream_6h",
            output_table = "stream_gold",
            is_forecast  = True,
        )
        conn.execute(gold_sql)

        df_out = conn.execute(
            "SELECT * FROM stream_gold WHERE time_6h >= CURRENT_TIMESTAMP"
        ).df()
        return df_out

    finally:
        conn.close()

def run_pipeline() -> None:
    logger.info("=== Baku Sentinel: ETL Pipeline ===")
    create_silver_layer()
    create_gold_layer()
    logger.info("=== Pipeline complete ===")
