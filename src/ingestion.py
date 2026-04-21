import time
import random
import requests
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
from src import config

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

def fetch_historical(zone_name, latitude, longitude, start_date, end_date, variables=None):
    if variables is None:
        variables = config.FEATURES
        
    logger.info(f"Fetching historical weather for {zone_name} ({start_date} to {end_date})")
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(variables),
        "timezone": "auto"
    }
    
    data = _make_request(config.HISTORICAL_URL, params)
    
    if "daily" not in data:
        raise ValueError(f"Malformed response from Archive API for {zone_name}: {data}")
        
    df = pd.DataFrame(data["daily"])
    df["time"] = pd.to_datetime(df["time"])
    df["zone"] = zone_name
    return df

def fetch_forecast(zone_name, latitude, longitude, variables=None):
    if variables is None:
        variables = config.FEATURES
        
    logger.info(f"Fetching weather forecast for {zone_name}")
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join(variables),
        "timezone": "auto"
    }
    
    data = _make_request(config.FORECAST_URL, params)
    
    if "daily" not in data:
        raise ValueError(f"Malformed response from Forecast API for {zone_name}: {data}")
        
    df = pd.DataFrame(data["daily"])
    df["time"] = pd.to_datetime(df["time"])
    df["zone"] = zone_name
    return df

def fetch_flood_historical(zone_name, latitude, longitude, start_date, end_date):
    logger.info(f"Fetching historical flood data for {zone_name} ({start_date} to {end_date})")
    
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
        logger.warning(f"No flood data returned for {zone_name} at ({latitude}, {longitude})")
        return pd.DataFrame()
        
    df = pd.DataFrame(data["daily"])
    df["time"] = pd.to_datetime(df["time"])
    df["zone"] = zone_name
    return df

def fetch_all_zones(start_date, end_date, mode="historical"):
    results = {}
    
    for zone in config.BAKU_ZONES:
        name = zone["zone"]
        lat = zone["latitude"]
        lon = zone["longitude"]
        
        try:
            if mode == "historical":
                results[name] = fetch_historical(name, lat, lon, start_date, end_date)
            elif mode == "forecast":
                results[name] = fetch_forecast(name, lat, lon)
            elif mode == "flood":
                results[name] = fetch_flood_historical(name, lat, lon, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to fetch {mode} data for {name}: {e}")
            
    return results
