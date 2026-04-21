from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR     = Path(__file__).resolve().parents[1]
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DB_PATH      = ROOT_DIR / "data" / "weather.duckdb"
LOGS_DIR     = ROOT_DIR / "logs"
REPORTS_DIR  = ROOT_DIR / "reports"

# ── API endpoints ─────────────────────────────────────────────────────────────
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL   = "https://api.open-meteo.com/v1/forecast"
FLOOD_URL      = "https://flood-api.open-meteo.com/v1/flood"

# ── Baku Zones ────────────────────────────────────────────────────────────────
BAKU_ZONES: list[dict] = [
    {"zone": "Coastal",    "latitude": 40.37, "longitude": 49.85},
    {"zone": "Urban",      "latitude": 40.40, "longitude": 49.88},
    {"zone": "Highland",   "latitude": 40.45, "longitude": 49.75},
]

# ── Date range ────────────────────────────────────────────────────────────────
HISTORICAL_START = "2020-01-01"
HISTORICAL_END   = "2026-04-20"  # Today is April 21, so 20th is the last full day

# ── Features ──────────────────────────────────────────────────────────────────
# Validated daily variables for Open-Meteo Archive API
FEATURES: list[str] = [
    "temperature_2m_max", 
    "temperature_2m_min", 
    "temperature_2m_mean",
    "precipitation_sum", 
    "relative_humidity_2m_mean",
    "wind_speed_10m_max", 
    "et0_fao_evapotranspiration",
    "snowfall_sum",
    "soil_moisture_0_to_7cm_mean",
    "soil_moisture_7_to_28cm_mean",
    "soil_temperature_0_to_7cm_mean"
]

# ── Ingestion Logic ───────────────────────────────────────────────────────────
MAX_RETRIES     = 3
BACKOFF_FACTOR  = 2

# ── Quality gates ─────────────────────────────────────────────────────────────
MAX_MISSING_PCT = 5.0
TEMP_RANGE      = (-50.0, 60.0)
PRECIP_MAX      = 500.0
