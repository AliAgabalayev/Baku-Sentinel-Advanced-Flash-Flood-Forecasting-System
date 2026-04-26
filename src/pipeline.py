"""
pipeline.py — Baku Sentinel
============================
Medallion ETL pipeline:  Bronze → Silver → Gold

Bronze  : raw hourly weather + daily flood (written by ingestion.py)
Silver  : 6-hourly resampled weather joined with flood discharge
Gold    : full feature-engineered table ready for model training/inference

Key design decisions
--------------------
- All feature engineering lives in a single SQL CTE chain (get_sentinel_feature_sql).
  This guarantees train/serve feature parity — the exact same SQL runs on
  historical Gold and on live forecast stream Gold.
- Bronze is dropped after Silver creation to save disk space.
- Forecast stream writes into silver.weather_stream_6h (separate from historical
  silver.weather_flood_6h) to avoid polluting the training table.
"""

import logging

import duckdb
import pandas as pd

from src import config

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Core SQL: Sentinel feature engineering
# ══════════════════════════════════════════════════════════════════════════════

def get_sentinel_feature_sql(input_table: str,
                              output_table: str,
                              is_forecast: bool = False) -> str:
    """
    Return the DuckDB SQL that transforms a 6-hourly silver table into
    a fully-featured gold table (or temp table for forecast stream).

    Parameters
    ----------
    input_table  : Fully-qualified silver table name, e.g. 'silver.weather_flood_6h'
    output_table : Target table or temp-table name, e.g. 'gold.flood_features'
    is_forecast  : When True, discharge columns are zeroed out (no ground truth).
    """

    # ── Discharge expressions (stubbed to 0 for forecast) ─────────────────────
    if is_forecast:
        discharge_lag_6h   = "0.0"
        discharge_lag_24h  = "0.0"
        discharge_roll_max = "0.0"
        discharge_trend    = "0.0"
        highland_discharge = "0.0"
        target_col         = "0 AS is_flood"
    else:
        discharge_lag_6h   = "LAG(river_discharge, 1) OVER (PARTITION BY zone ORDER BY time_6h)"
        discharge_lag_24h  = "LAG(river_discharge, 4) OVER (PARTITION BY zone ORDER BY time_6h)"
        discharge_roll_max = "MAX(river_discharge) OVER (PARTITION BY zone ORDER BY time_6h ROWS BETWEEN 3 PRECEDING AND CURRENT ROW)"
        discharge_trend    = "river_discharge - LAG(river_discharge, 1) OVER (PARTITION BY zone ORDER BY time_6h)"
        highland_discharge = "river_discharge"
        # Label: discharge threshold AND atmospheric confirmation
        target_col = (
            "CASE WHEN river_discharge > 1.0 "
            "  AND (precipitation > 1.0 OR relative_humidity_2m > 85) "
            "THEN 1 ELSE 0 END AS is_flood"
        )

    return f"""
    CREATE OR REPLACE TABLE {output_table} AS
    WITH

    -- ── Step 1: lag & rolling features ──────────────────────────────────────
    lagged AS (
        SELECT *,
            LAG(precipitation, 1) OVER (PARTITION BY zone ORDER BY time_6h) AS precip_lag_6h,
            LAG(precipitation, 2) OVER (PARTITION BY zone ORDER BY time_6h) AS precip_lag_12h,
            LAG(precipitation, 4) OVER (PARTITION BY zone ORDER BY time_6h) AS precip_lag_24h,
            LAG(precipitation, 8) OVER (PARTITION BY zone ORDER BY time_6h) AS precip_lag_48h,
            {discharge_lag_6h}  AS discharge_lag_6h,
            {discharge_lag_24h} AS discharge_lag_24h,
            LAG(temperature_2m, 4) OVER (PARTITION BY zone ORDER BY time_6h) AS temp_lag_24h,

            SUM(precipitation) OVER (PARTITION BY zone ORDER BY time_6h
                ROWS BETWEEN 3  PRECEDING AND CURRENT ROW) AS precip_roll_sum_24h,
            SUM(precipitation) OVER (PARTITION BY zone ORDER BY time_6h
                ROWS BETWEEN 7  PRECEDING AND CURRENT ROW) AS precip_roll_sum_48h,
            SUM(precipitation) OVER (PARTITION BY zone ORDER BY time_6h
                ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS precip_roll_sum_72h,
            MAX(precipitation) OVER (PARTITION BY zone ORDER BY time_6h
                ROWS BETWEEN 3  PRECEDING AND CURRENT ROW) AS precip_roll_max_24h,
            {discharge_roll_max} AS discharge_roll_max_24h,
            MAX(relative_humidity_2m) OVER (PARTITION BY zone ORDER BY time_6h
                ROWS BETWEEN 3  PRECEDING AND CURRENT ROW) AS humidity_roll_max_24h,
            SUM(et0_fao_evapotranspiration) OVER (PARTITION BY zone ORDER BY time_6h
                ROWS BETWEEN 3  PRECEDING AND CURRENT ROW) AS et0_roll_sum_24h
        FROM {input_table}
    ),

    -- ── Step 2: antecedent precipitation index + soil saturation ────────────
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

    -- ── Step 3: derived indices ───────────────────────────────────────────────
    additional_derived AS (
        SELECT *,
            soil_moisture_0_to_7cm
                - LAG(soil_moisture_0_to_7cm, 1)
                    OVER (PARTITION BY zone ORDER BY time_6h)     AS soil_moisture_change_6h,
            0.45 - soil_saturation_index                          AS soil_moisture_deficit,
            CASE WHEN soil_temperature_0_to_7cm < 0 THEN 1
                 ELSE 0 END                                       AS frozen_ground_flag,
            {discharge_trend}                                     AS discharge_trend_6h,
            temperature_2m - temp_lag_24h                        AS temp_trend_24h,
            precipitation  - et0_fao_evapotranspiration          AS et_deficit_6h,
            precip_roll_sum_24h - et0_roll_sum_24h               AS et_deficit_24h,
            relative_humidity_2m * precipitation                 AS humidity_precip_product
        FROM api_calc
    ),

    -- ── Step 4: highland context for cascade signal ──────────────────────────
    highland_context AS (
        SELECT
            time_6h,
            precip_roll_sum_24h                                  AS highland_precip_24h,
            {highland_discharge}                                 AS highland_discharge_6h
        FROM additional_derived
        WHERE zone = 'High Relief'
    )

    -- ── Step 5: assemble final table ─────────────────────────────────────────
    SELECT
        d.*,
        COALESCE(h.highland_precip_24h,    0.0)                 AS highland_precip_24h,
        COALESCE(h.highland_discharge_6h,  0.0)                 AS highland_discharge_6h,

        -- Cascade risk: fraction of highland load routed to each zone
        CASE
            WHEN d.zone = 'High Relief'     THEN d.precip_roll_sum_24h * (1.0/3.0)
            WHEN d.zone = 'Moderate Relief' THEN COALESCE(h.highland_precip_24h, 0) * (1.0/1.5)
            ELSE                                 COALESCE(h.highland_precip_24h, 0) * (1.0/1.0)
        END                                                      AS zone_cascade_risk,

        -- Cyclic time encodings
        SIN(2 * PI() * EXTRACT(HOUR FROM d.time_6h) / 24)      AS hour_sin,
        COS(2 * PI() * EXTRACT(HOUR FROM d.time_6h) / 24)      AS hour_cos,
        SIN(2 * PI() * EXTRACT(DOY  FROM d.time_6h) / 365)     AS doy_sin,
        COS(2 * PI() * EXTRACT(DOY  FROM d.time_6h) / 365)     AS doy_cos,
        CASE WHEN EXTRACT(MONTH FROM d.time_6h) IN (11, 12, 1, 2)
             THEN 1 ELSE 0 END                                   AS is_winter,

        {target_col}

    FROM additional_derived d
    LEFT JOIN highland_context h ON d.time_6h = h.time_6h;
    """


# ══════════════════════════════════════════════════════════════════════════════
# Silver layer — resample hourly → 6h, join flood
# ══════════════════════════════════════════════════════════════════════════════

def create_silver_layer() -> None:
    """
    Bronze hourly weather + Bronze daily flood → Silver 6-hourly joined table.
    Drops the Bronze schema afterward to reclaim disk space.
    """
    conn = duckdb.connect(str(config.DB_PATH))
    try:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {config.SCHEMA_SILVER}")
        logger.info("Creating Silver layer from Bronze...")

        # Build UNION ALL fragments for every zone
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

        -- Resample hourly → 6-hourly buckets
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

        -- Daily max discharge (flood API is daily-granularity)
        resampled_flood AS (
            SELECT
                zone,
                CAST(time AS DATE)        AS date_key,
                MAX(river_discharge)       AS river_discharge
            FROM combined_flood
            GROUP BY 1, 2
        )

        SELECT
            w.*,
            COALESCE(f.river_discharge, 0.0) AS river_discharge
        FROM resampled_weather w
        LEFT JOIN resampled_flood f
            ON w.zone = f.zone
            AND CAST(w.time_6h AS DATE) = f.date_key
        ORDER BY zone, time_6h;
        """
        conn.execute(resample_sql)
        n = conn.execute(f"SELECT count(*) FROM {config.SCHEMA_SILVER}.weather_flood_6h").fetchone()[0]
        logger.info(f"Silver table created: {n:,} rows at 6h granularity.")

        logger.info("Dropping Bronze schema to reclaim disk space...")
        conn.execute(f"DROP SCHEMA IF EXISTS {config.SCHEMA_BRONZE} CASCADE")

    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Gold layer — feature engineering on historical data
# ══════════════════════════════════════════════════════════════════════════════

def create_gold_layer() -> None:
    """
    Apply Sentinel feature SQL to Silver → Gold.
    Output: gold.flood_features — the training dataset.
    """
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
    """Load the Gold feature table into a Pandas DataFrame for model training."""
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

def run_forecast_pipeline(df_forecast: pd.DataFrame) -> pd.DataFrame:
    """
    Process live hourly forecast DataFrame through the Sentinel pipeline.

    Steps
    -----
    1. Resample hourly → 6-hourly (Silver stream table)
    2. Seed the stream with recent historical Silver if stream is sparse
    3. Apply Sentinel feature SQL (is_forecast=True — discharge zeroed)
    4. Return only future rows (time_6h >= now)

    Parameters
    ----------
    df_forecast : Combined hourly forecast DataFrame from ingestion.fetch_all_forecast()

    Returns
    -------
    DataFrame of engineered features for the forecast window.
    """
    conn = duckdb.connect(str(config.DB_PATH))
    try:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {config.SCHEMA_SILVER}")

        # Register forecast as a temp table
        conn.execute("CREATE OR REPLACE TEMP TABLE forecast_raw_temp AS SELECT * FROM df_forecast")

        # Resample forecast hourly → 6h
        conn.execute(f"""
        CREATE OR REPLACE TEMP TABLE forecast_silver_new AS
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
        """)

        # Ensure stream table exists (schema from Silver historical)
        conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {config.SCHEMA_SILVER}.weather_stream_6h AS
        SELECT * FROM forecast_silver_new WHERE 1=0
        """)

        # Upsert new forecast rows
        conn.execute(f"""
        INSERT INTO {config.SCHEMA_SILVER}.weather_stream_6h
        SELECT src.* FROM forecast_silver_new src
        WHERE NOT EXISTS (
            SELECT 1 FROM {config.SCHEMA_SILVER}.weather_stream_6h dst
            WHERE dst.time_6h = src.time_6h AND dst.zone = src.zone
        )
        """)

        # Seed with recent historical data so lag features compute correctly
        past_count = conn.execute(f"""
            SELECT count(*) FROM {config.SCHEMA_SILVER}.weather_stream_6h
            WHERE time_6h < CURRENT_TIMESTAMP
        """).fetchone()[0]

        if past_count < 12:   # < 12 rows = less than 3 days of context
            logger.info("Stream sparse — seeding from historical Silver...")
            try:
                conn.execute(f"""
                INSERT INTO {config.SCHEMA_SILVER}.weather_stream_6h
                SELECT * FROM {config.SCHEMA_SILVER}.weather_flood_6h
                WHERE time_6h > CURRENT_DATE - INTERVAL '14 days'
                  AND NOT EXISTS (
                      SELECT 1 FROM {config.SCHEMA_SILVER}.weather_stream_6h dst
                      WHERE dst.time_6h = {config.SCHEMA_SILVER}.weather_flood_6h.time_6h
                        AND dst.zone    = {config.SCHEMA_SILVER}.weather_flood_6h.zone
                  )
                """)
            except Exception as e:
                logger.warning(f"Could not seed from historical Silver: {e}")

        # Apply Gold feature SQL in forecast mode (discharge zeroed)
        gold_sql = get_sentinel_feature_sql(
            input_table  = f"{config.SCHEMA_SILVER}.weather_stream_6h",
            output_table = "stream_gold",
            is_forecast  = True,
        )
        conn.execute(gold_sql)

        df_out = conn.execute(
            "SELECT * FROM stream_gold WHERE time_6h >= CURRENT_TIMESTAMP"
        ).df()
        logger.info(f"Forecast pipeline complete: {len(df_out)} rows in prediction window.")
        return df_out

    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Full historical pipeline orchestrator
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline() -> None:
    """Run full historical ETL: Silver → Gold.  (Bronze must exist already.)"""
    logger.info("=== Baku Sentinel: ETL Pipeline ===")
    create_silver_layer()
    create_gold_layer()
    logger.info("=== Pipeline complete ===")
