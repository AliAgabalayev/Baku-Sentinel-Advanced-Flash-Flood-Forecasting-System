from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR     = Path(__file__).resolve().parents[1]
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
DB_PATH      = ROOT_DIR / "data" / "weather.duckdb"
LOGS_DIR     = ROOT_DIR / "logs"
REPORTS_DIR  = ROOT_DIR / "reports"

# ── API endpoints ─────────────────────────────────────────────────────────────
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL   = "https://api.open-meteo.com/v1/forecast"
FLOOD_URL      = "https://flood-api.open-meteo.com/v1/flood"

# ── Baku Zones ────────────────────────────────────────────────────────────────
BAKU_ZONES: list[dict] = [
    {"zone": "High Relief",     "latitude": 40.34376, "longitude": 49.55835},
    {"zone": "Low Relief",      "latitude": 40.29215, "longitude": 49.83208},
    {"zone": "Moderate Relief", "latitude": 40.35038, "longitude": 49.65975},
]

# ── Date range ────────────────────────────────────────────────────────────────
HISTORICAL_START = "2020-01-01"
HISTORICAL_END   = "2026-04-20"

# ── Features (Hourly Grain) ───────────────────────────────────────────────────
# Validated hourly variables for Open-Meteo Archive API
HOURLY_FEATURES: list[str] = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "soil_moisture_0_to_7cm",
    "soil_moisture_7_to_28cm",
    "soil_temperature_0_to_7cm",
    "et0_fao_evapotranspiration"
]

# ── Ingestion Logic ───────────────────────────────────────────────────────────
MAX_RETRIES     = 3
BACKOFF_FACTOR  = 2

# ── Medallion Layers ─────────────────────────────────────────────────────────
SCHEMA_BRONZE = "bronze"
SCHEMA_SILVER = "silver"
SCHEMA_GOLD   = "gold"

# ── Quality gates ─────────────────────────────────────────────────────────────
FLOOD_THRESHOLD = 1.0  # m3/s
MAX_MISSING_PCT = 5.0
TEMP_RANGE      = (-50.0, 60.0)
PRECIP_MAX      = 500.0
