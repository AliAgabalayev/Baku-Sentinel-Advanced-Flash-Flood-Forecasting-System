
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

# ── Cities ────────────────────────────────────────────────────────────────────
CITIES: list[dict] = [
    {"name": "Baku",      "latitude": 40.41, "longitude": 49.87, "country": "AZ"},
    {"name": "Lenkaran",  "latitude": 38.75, "longitude": 48.85, "country": "AZ"},
    {"name": "Ismayilli", "latitude": 40.79, "longitude": 48.15, "country": "AZ"},
]

# ── Date range ────────────────────────────────────────────────────────────────
HISTORICAL_START = "2019-01-01"
HISTORICAL_END   = "2024-12-31"

# ── Variables ─────────────────────────────────────────────────────────────────
DAILY_VARIABLES: list[str] = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "apparent_temperature_max",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "windspeed_10m_max",
    "relative_humidity_2m_mean",
    "weathercode",
]

# ── Quality gates ─────────────────────────────────────────────────────────────
MAX_MISSING_PCT = 5.0
TEMP_RANGE      = (-50.0, 60.0)
PRECIP_MAX      = 500.0
