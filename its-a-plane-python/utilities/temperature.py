from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
import requests as r
import time
import json 
import logging
import os

logger = logging.getLogger(__name__)

# Attempt to load config data
try:
    from config import TOMORROW_API_KEY
    from config import TEMPERATURE_UNITS
    from config import FORECAST_DAYS

except (ModuleNotFoundError, NameError, ImportError):
    # If there's no config data
    TOMORROW_API_KEY = None
    TEMPERATURE_UNITS = "metric"
    FORECAST_DAYS = 3

if TEMPERATURE_UNITS != "metric" and TEMPERATURE_UNITS != "imperial":
    TEMPERATURE_UNITS = "metric"

from config import TEMPERATURE_LOCATION

# Weather API
TOMORROW_API_URL = "https://api.tomorrow.io/v4/"

# Cache settings
CACHE_FILE = os.path.join(os.path.dirname(__file__), "temperature_cache.json")
FORECAST_CACHE_FILE = os.path.join(os.path.dirname(__file__), "forecast_cache.json")
CACHE_DURATION = 1200  # 20 minutes in seconds

# Retry settings
MAX_RETRIES = 5


def grab_temperature_and_humidity(delay: int = 2, max_retries: Optional[int] = None) -> Tuple[Optional[float], Optional[float]]:
    """
    Fetch current temperature and humidity from the Tomorrow.io API.
    
    Uses caching to avoid excessive API calls. If cached data is less than
    CACHE_DURATION seconds old, returns cached values.
    
    Args:
        delay: Number of seconds to wait between retry attempts.
        max_retries: Maximum number of retry attempts. If None, uses default behavior.
    
    Returns:
        A tuple of (temperature, humidity). Values may be None if fetching fails
        and max_retries is reached, or 0 if data is missing from the API response.
    """
    # Check cache first
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.utcnow() - cached_time < timedelta(seconds=CACHE_DURATION):
                return cache_data['temperature'], cache_data['humidity']
        except (json.JSONDecodeError, KeyError, ValueError):
            pass  # Ignore invalid cache

    current_temp, humidity = None, None
    retries = 0

    while True:
        try:
            request = r.get(
                f"{TOMORROW_API_URL}/weather/realtime",
                params={
                    "location": TEMPERATURE_LOCATION,
                    "units": TEMPERATURE_UNITS,
                    "apikey": TOMORROW_API_KEY
                },
                timeout=10  # Add timeout for the request
            )
            request.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
            
            # Safely extract data
            data = request.json().get("data", {}).get("values", {})
            current_temp = data.get("temperature")
            humidity = data.get("humidity")

            # If temperature or humidity is missing, assign a default value of 0
            if current_temp is None:
                logger.warning("Temperature data missing, defaulting to 0.")
                current_temp = 0

            if humidity is None:
                logger.warning("Humidity data missing, defaulting to 0.")
                humidity = 0

            # If the data is valid (including defaults), exit the loop
            break

        except (r.exceptions.RequestException, ValueError) as e:
            logger.error(f"Request failed. Error: {e}")
            
            retries += 1
            if max_retries and retries >= max_retries:
                logger.error("Max retries reached. Exiting.")
                break
            
            logger.info(f"Retrying in {delay} seconds...")
            time.sleep(delay)

    # Save to cache if data was successfully fetched
    if current_temp is not None and humidity is not None:
        cache_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'temperature': current_temp,
            'humidity': humidity
        }
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache_data, f)
        except Exception:
            pass  # Ignore if can't write

    return current_temp, humidity


def grab_forecast(delay: int = 2) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch weather forecast data from the Tomorrow.io API.
    
    Retrieves daily forecast data including min/max temperatures, weather codes,
    sunrise/sunset times, and moon phase for the configured number of days.
    Uses caching to avoid excessive API calls.
    
    Args:
        delay: Number of seconds to wait between retry attempts.
    
    Returns:
        A list of forecast intervals, each containing weather data for a day.
        Returns None if fetching fails after MAX_RETRIES attempts.
    """
    # Check cache first
    if os.path.exists(FORECAST_CACHE_FILE):
        try:
            with open(FORECAST_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.utcnow() - cached_time < timedelta(seconds=CACHE_DURATION):
                return cache_data['forecast']
        except (json.JSONDecodeError, KeyError, ValueError):
            pass  # Ignore invalid cache

    retries = 0
    while retries < MAX_RETRIES:
        try:
            current_time = datetime.utcnow()
            dt = current_time + timedelta(hours=6)
            
            resp = r.post(
                f"{TOMORROW_API_URL}/timelines",
                headers={
                    "Accept-Encoding": "gzip",
                    "accept": "application/json",
                    "content-type": "application/json"
                },
                params={"apikey": TOMORROW_API_KEY}, 
                json={
                    "location": TEMPERATURE_LOCATION,
                    "units": TEMPERATURE_UNITS,
                    "fields": [
                        "temperatureMin",
                        "temperatureMax",
                        "weatherCodeFullDay",
                        "sunriseTime",
                        "sunsetTime",
                        "moonPhase"
                    ],
                    "timesteps": [
                        "1d"
                    ],
                    "startTime": dt.isoformat(),
                    "endTime": (dt + timedelta(days=int(FORECAST_DAYS))).isoformat()
                }
            )    
            resp.raise_for_status()  # Raise an exception for 4xx or 5xx status codes

            # Safely access the JSON response to avoid KeyError
            data = resp.json().get("data", {})
            timelines = data.get("timelines", [])

            if not timelines:
                raise KeyError("Timelines not found in response.")

            forecast = timelines[0].get("intervals", [])

            if not forecast:
                raise KeyError("Forecast intervals not found in timelines.")

            # Save to cache
            cache_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'forecast': forecast
            }
            try:
                with open(FORECAST_CACHE_FILE, 'w') as f:
                    json.dump(cache_data, f)
            except Exception:
                pass  # Ignore if can't write

            return forecast

        except (r.exceptions.RequestException, KeyError) as e:
            logger.error(f"Request failed. Error: {e}")
            retries += 1
            if retries >= MAX_RETRIES:
                logger.error("Max retries reached for forecast. Exiting.")
                break
            logger.info(f"Retrying in {delay} seconds...")
            time.sleep(delay)
    
    return None
