import duckdb
import logging
import os
from src import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_silver_layer():
    """Refine Bronze data into 6-hourly Silver grain and export to file."""
    os.makedirs(config.DATA_PROCESSED_DIR, exist_ok=True)
    conn = duckdb.connect(str(config.DB_PATH))
    try:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {config.SCHEMA_SILVER}")
        
        logger.info("Resampling Bronze data to 6-hourly Silver layer...")
        
        # Combine all zones into a single Silver table
        resample_sql = f"""
        CREATE OR REPLACE TABLE {config.SCHEMA_SILVER}.weather_flood_6h AS
        WITH combined_bronze AS (
            {" UNION ALL ".join([f"SELECT * FROM {config.SCHEMA_BRONZE}.weather_raw_{z['zone'].lower()}" for z in config.BAKU_ZONES])}
        ),
        combined_flood AS (
            {" UNION ALL ".join([f"SELECT * FROM {config.SCHEMA_BRONZE}.flood_raw_{z['zone'].lower()}" for z in config.BAKU_ZONES])}
        ),
        resampled_weather AS (
            SELECT 
                zone,
                time_bucket(INTERVAL '6 hours', time) AS time_6h,
                AVG(temperature_2m) AS temperature_2m,
                AVG(relative_humidity_2m) AS relative_humidity_2m,
                SUM(precipitation) AS precipitation,
                AVG(wind_speed_10m) AS wind_speed_10m,
                AVG(soil_moisture_0_to_7cm) AS soil_moisture_0_to_7cm,
                AVG(soil_moisture_7_to_28cm) AS soil_moisture_7_to_28cm,
                AVG(soil_temperature_0_to_7cm) AS soil_temperature_0_to_7cm,
                AVG(et0_fao_evapotranspiration) AS et0_fao_evapotranspiration
            FROM combined_bronze
            GROUP BY 1, 2
        ),
        resampled_flood AS (
            SELECT 
                zone,
                CAST(time AS DATE) AS date_key,
                MAX(river_discharge) AS river_discharge
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
        
        # Export Silver to Parquet
        silver_path = config.DATA_PROCESSED_DIR / "silver_weather_flood_6h.parquet"
        conn.execute(f"COPY {config.SCHEMA_SILVER}.weather_flood_6h TO '{silver_path}' (FORMAT PARQUET)")
        
        count = conn.execute(f"SELECT COUNT(*) FROM {config.SCHEMA_SILVER}.weather_flood_6h").fetchone()[0]
        logger.info(f"Silver layer saved to {silver_path} with {count} records.")
        
    finally:
        conn.close()

def run_pipeline():
    """Run full medallion pipeline."""
    create_silver_layer()
