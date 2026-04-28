"""
weather_model.py — Baku Sentinel
================================
Provides climatological weather predictions for extended horizons (e.g., days 16-30).
Calculates historical averages for each zone, day of year, and hour.
"""

import logging
import duckdb
import pandas as pd
import numpy as np
from src import config

logger = logging.getLogger(__name__)

class WeatherClimatologyModel:
    """
    Predicts weather variables based on historical averages (climatology).
    Used to bridge the gap between live 15-day forecasts and 30-day targets.
    """

    def __init__(self):
        self.stats = None

    def train(self) -> None:
        """
        Computes 6-hourly historical averages for every zone and day-of-year.
        Reads from silver.weather_flood_6h.
        """
        conn = duckdb.connect(str(config.DB_PATH))
        try:
            logger.info("Training Weather Climatology model from Silver historical data...")
            
            # We group by zone, day-of-year, and hour to get a robust seasonal/daily profile
            sql = f"""
            SELECT 
                zone,
                EXTRACT(DOY FROM time_6h) AS doy,
                EXTRACT(HOUR FROM time_6h) AS hour,
                AVG(temperature_2m) AS temperature_2m,
                AVG(relative_humidity_2m) AS relative_humidity_2m,
                AVG(precipitation) AS precipitation,
                AVG(wind_speed_10m) AS wind_speed_10m,
                AVG(soil_moisture_0_to_7cm) AS soil_moisture_0_to_7cm,
                AVG(soil_moisture_7_to_28cm) AS soil_moisture_7_to_28cm,
                AVG(soil_temperature_0_to_7cm) AS soil_temperature_0_to_7cm,
                AVG(et0_fao_evapotranspiration) AS et0_fao_evapotranspiration
            FROM {config.SCHEMA_SILVER}.weather_flood_6h
            GROUP BY 1, 2, 3
            """
            self.stats = conn.execute(sql).df()
            logger.info(f"Climatology trained: {len(self.stats)} profile points.")
        finally:
            conn.close()

    def predict(self, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
        """
        Generates a synthetic 6-hourly forecast for all zones between start and end.
        """
        if self.stats is None:
            self.train()

        # Create time grid
        time_grid = pd.date_range(
            start=start_date.floor('6h'),
            end=end_date.floor('6h'),
            freq='6h'
        )
        
        frames = []
        for zone_cfg in config.BAKU_ZONES:
            zone = zone_cfg['zone']
            df_z = pd.DataFrame({'time_6h': time_grid})
            df_z['zone'] = zone
            df_z['doy'] = df_z['time_6h'].dt.dayofyear
            df_z['hour'] = df_z['time_6h'].dt.hour
            
            # Join with historical stats
            # Note: We use merge as it's cleaner for multi-column keys
            df_z = df_z.merge(self.stats, on=['zone', 'doy', 'hour'], how='left')
            
            # Fill any missing DOYs (e.g. leap years or gaps) with global zone averages
            # as a fallback
            if df_z.isnull().any().any():
                zone_means = self.stats[self.stats['zone'] == zone].mean(numeric_only=True).drop(['doy', 'hour'])
                df_z = df_z.fillna(zone_means)
            
            frames.append(df_z)
            
        combined = pd.concat(frames, ignore_index=True)
        # Drop helper columns
        combined = combined.drop(columns=['doy', 'hour'])
        # Ensure 0 river discharge for forecast
        combined['river_discharge'] = 0.0
        
        logger.info(f"Generated {len(combined)} climatological 6h rows.")
        return combined

def get_extended_forecast(df_live_6h: pd.DataFrame, target_days: int = 30) -> pd.DataFrame:
    """
    Extension utility: Merges live 15-day forecast with climatology up to target_days.
    """
    if target_days <= 15:
        return df_live_6h

    # Identify the gap
    last_live = df_live_6h['time_6h'].max()
    # We need to reach today + target_days
    # But for simplicity, we just add 15 days after the last live forecast row
    start_ext = last_live + pd.Timedelta(hours=6)
    end_ext = df_live_6h['time_6h'].min() + pd.Timedelta(days=target_days)
    
    if end_ext <= start_ext:
        return df_live_6h

    model = WeatherClimatologyModel()
    df_ext = model.predict(start_ext, end_ext)
    
    # Concatenate
    combined = pd.concat([df_live_6h, df_ext], ignore_index=True).sort_values(['zone', 'time_6h'])
    return combined
