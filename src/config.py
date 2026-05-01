"""
config.py — Baku Sentinel
Central configuration for all pipeline stages.
"""
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT_DIR      = Path(__file__).resolve().parents[1]
DATA_DIR      = ROOT_DIR / "data"
DATA_RAW_DIR  = DATA_DIR / "raw"
DB_PATH       = DATA_DIR / "weather.duckdb"
MODELS_DIR    = ROOT_DIR / "models"
LOGS_DIR      = ROOT_DIR / "logs"
REPORTS_DIR   = ROOT_DIR / "reports"
NOTEBOOKS_DIR = ROOT_DIR / "notebooks"

for _d in [DATA_RAW_DIR, MODELS_DIR, LOGS_DIR, REPORTS_DIR, NOTEBOOKS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ── Medallion schema names ─────────────────────────────────────────────────────
SCHEMA_BRONZE = "bronze"
SCHEMA_SILVER = "silver"
SCHEMA_GOLD   = "gold"

# ── API endpoints ─────────────────────────────────────────────────────────────
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL   = "https://api.open-meteo.com/v1/forecast"
FLOOD_URL      = "https://flood-api.open-meteo.com/v1/flood"

# ── Baku Zones ────────────────────────────────────────────────────────────────
BAKU_ZONES = [
    {"zone": "High Relief",     "latitude": 40.34376, "longitude": 49.55835},
    {"zone": "Low Relief",      "latitude": 40.29215, "longitude": 49.83208},
    {"zone": "Moderate Relief", "latitude": 40.35038, "longitude": 49.65975},
]

ZONE_METADATA = {
    "High Relief":     {"zone_id": "C", "elevation_mean": 150.0, "slope_mean": 12.0,
                        "impervious_ratio": 0.15, "watershed_area": 45.0},
    "Moderate Relief": {"zone_id": "B", "elevation_mean": 40.0,  "slope_mean": 6.0,
                        "impervious_ratio": 0.40, "watershed_area": 120.0},
    "Low Relief":      {"zone_id": "A", "elevation_mean": 3.0,   "slope_mean": 1.5,
                        "impervious_ratio": 0.70, "watershed_area": 280.0},
}
ZONE_CASCADE_ORDER = ["High Relief", "Moderate Relief", "Low Relief"]

# ── Date range ────────────────────────────────────────────────────────────────
HISTORICAL_START = "2020-01-01"
HISTORICAL_END   = "2026-04-20"

# ── Open-Meteo hourly variable list ───────────────────────────────────────────
HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "soil_moisture_0_to_7cm",
    "soil_moisture_7_to_28cm",
    "soil_temperature_0_to_7cm",
    "et0_fao_evapotranspiration",
]
FLOOD_VARIABLE = "river_discharge"

# ── Gold feature columns (exact model input) ───────────────────────────────────
GOLD_FEATURE_COLS = [
    "temperature_2m", "relative_humidity_2m", "precipitation",
    "wind_speed_10m", "soil_moisture_0_to_7cm", "soil_moisture_7_to_28cm",
    "soil_temperature_0_to_7cm", "et0_fao_evapotranspiration",
    "precip_lag_6h", "precip_lag_12h", "precip_lag_24h", "precip_lag_48h",
    "temp_lag_24h",
    "precip_roll_sum_24h", "precip_roll_sum_48h", "precip_roll_sum_72h",
    "precip_roll_max_24h", "humidity_roll_max_24h",
    "et0_roll_sum_24h",
    "api_7d", "soil_saturation_index",
    "soil_moisture_change_6h", "soil_moisture_deficit", "frozen_ground_flag",
    "temp_trend_24h",
    "et_deficit_6h", "et_deficit_24h", "humidity_precip_product",
    "highland_precip_24h", "zone_cascade_risk",
    "hour_sin", "hour_cos", "doy_sin", "doy_cos", "is_winter",
    "zone_Low Relief", "zone_Moderate Relief",
]

# ── Model settings ─────────────────────────────────────────────────────────────
TARGET_COL = "is_flood"

# ── Sensor Boundaries (for DQ Score) ──────────────────────────────────────────
SENSOR_BOUNDS = {
    "temperature_2m": (-50.0, 60.0),
    "relative_humidity_2m": (0.0, 100.0),
    "precipitation": (0.0, 500.0),
    "wind_speed_10m": (0.0, 250.0),
    "soil_moisture_0_to_7cm": (0.0, 1.0),
    "soil_moisture_7_to_28cm": (0.0, 1.0),
}

# ── Risk thresholds ────────────────────────────────────────────────────────────
RISK_HIGH   = 0.60
RISK_MEDIUM = 0.30

# ── Ingestion ──────────────────────────────────────────────────────────────────
MAX_RETRIES    = 3
BACKOFF_FACTOR = 2
FORECAST_DAYS  = 15
MAX_MISSING_PCT = 5.0
