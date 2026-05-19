"""
Centralized configuration management for Plane Tracker RGB Pi.

This module loads configuration from environment variables with fallback
to default values. Sensitive credentials should be set via environment
variables or a .env file, never hardcoded.

Usage:
    from config import settings
    
    api_key = settings.TOMORROW_API_KEY
    brightness = settings.BRIGHTNESS
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any
from pathlib import Path


def _get_env(key: str, default: Any = None, cast_type: type = str) -> Any:
    """Get environment variable with type casting."""
    value = os.environ.get(key)
    if value is None:
        return default
    
    if cast_type == bool:
        return value.lower() in ('true', '1', 'yes', 'on')
    
    try:
        return cast_type(value)
    except (ValueError, TypeError):
        return default


@dataclass
class Settings:
    """Application settings loaded from environment variables."""
    
    # Base directory (where config.py lives)
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).parent)
    
    # Location Configuration
    LOCATION_HOME: Tuple[float, float] = field(default_factory=lambda: (
        _get_env('HOME_LATITUDE', 44.797734, float),
        _get_env('HOME_LONGITUDE', -93.186722, float)
    ))
    
    ZONE_HOME: Dict[str, float] = field(default_factory=lambda: {
        'tl_y': _get_env('ZONE_TL_LATITUDE', 44.757601, float),
        'tl_x': _get_env('ZONE_TL_LONGITUDE', -93.226722, float),
        'br_y': _get_env('ZONE_BR_LATITUDE', 44.837734, float),
        'br_x': _get_env('ZONE_BR_LONGITUDE', -93.146722, float),
    })
    
    TEMPERATURE_LOCATION: str = field(default_factory=lambda: _get_env(
        'TEMPERATURE_LOCATION',
        f"{_get_env('HOME_LATITUDE', 44.797734, float)},{_get_env('HOME_LONGITUDE', -93.186722, float)}"
    ))
    
    # API Keys (sensitive - must be set via environment)
    TOMORROW_API_KEY: Optional[str] = field(default_factory=lambda: _get_env('TOMORROW_API_KEY'))
    
    # Email Configuration (sensitive)
    EMAIL: str = field(default_factory=lambda: _get_env('EMAIL', ''))
    EMAIL_SENDER: str = field(default_factory=lambda: _get_env('EMAIL_SENDER', ''))
    EMAIL_PASSWORD: str = field(default_factory=lambda: _get_env('EMAIL_PASSWORD', ''))
    
    # Display Settings
    BRIGHTNESS: int = field(default_factory=lambda: _get_env('BRIGHTNESS', 100, int))
    BRIGHTNESS_NIGHT: int = field(default_factory=lambda: _get_env('BRIGHTNESS_NIGHT', 50, int))
    NIGHT_BRIGHTNESS: bool = field(default_factory=lambda: _get_env('NIGHT_BRIGHTNESS_ENABLED', False, bool))
    NIGHT_START: str = field(default_factory=lambda: _get_env('NIGHT_START', '22:00'))
    NIGHT_END: str = field(default_factory=lambda: _get_env('NIGHT_END', '06:00'))
    
    # Hardware Settings
    GPIO_SLOWDOWN: int = field(default_factory=lambda: _get_env('GPIO_SLOWDOWN', 4, int))
    HAT_PWM_ENABLED: bool = field(default_factory=lambda: _get_env('HAT_PWM_ENABLED', False, bool))
    
    # Flight Tracker Settings
    MIN_ALTITUDE: int = field(default_factory=lambda: _get_env('MIN_ALTITUDE', 2000, int))
    JOURNEY_CODE_SELECTED: str = field(default_factory=lambda: _get_env('JOURNEY_CODE_SELECTED', 'MSP'))
    JOURNEY_BLANK_FILLER: str = field(default_factory=lambda: _get_env('JOURNEY_BLANK_FILLER', ' ? '))
    MAX_CLOSEST: int = field(default_factory=lambda: _get_env('MAX_CLOSEST', 3, int))
    MAX_FARTHEST: int = field(default_factory=lambda: _get_env('MAX_FARTHEST', 3, int))
    
    # ADS-B Data Source
    # Supports local receiver (e.g. "http://192.168.10.120/tar1090/data/aircraft.json")
    # or ADSB.lol (e.g. "https://api.adsb.lol/v2/point/{lat}/{lon}/{range}")
    ADSB_URL: str = field(default_factory=lambda: _get_env('ADSB_URL', 'https://api.adsb.lol/v2/point/{lat}/{lon}/{range}'))
    RANGE: int = field(default_factory=lambda: _get_env('RANGE', 50, int))
    
    # SWIM (System Wide Information Management) API for flight enrichment
    SWIM_API_URL: Optional[str] = field(default_factory=lambda: _get_env('SWIM_API_URL'))
    SWIM_API_KEY: Optional[str] = field(default_factory=lambda: _get_env('SWIM_API_KEY'))
    
    # Units and Formats
    TEMPERATURE_UNITS: str = field(default_factory=lambda: _get_env('TEMPERATURE_UNITS', 'imperial'))
    DISTANCE_UNITS: str = field(default_factory=lambda: _get_env('DISTANCE_UNITS', 'imperial'))
    CLOCK_FORMAT: str = field(default_factory=lambda: _get_env('CLOCK_FORMAT', '12hr'))
    FORECAST_DAYS: int = field(default_factory=lambda: _get_env('FORECAST_DAYS', 3, int))
    
    def __post_init__(self):
        """Validate settings after initialization."""
        # Validate temperature units
        if self.TEMPERATURE_UNITS not in ('metric', 'imperial'):
            self.TEMPERATURE_UNITS = 'metric'
        
        # Validate distance units
        if self.DISTANCE_UNITS not in ('metric', 'imperial'):
            self.DISTANCE_UNITS = 'imperial'
        
        # Validate clock format
        if self.CLOCK_FORMAT not in ('12hr', '24hr'):
            self.CLOCK_FORMAT = '12hr'
        
        # Validate brightness range
        self.BRIGHTNESS = max(0, min(100, self.BRIGHTNESS))
        self.BRIGHTNESS_NIGHT = max(0, min(100, self.BRIGHTNESS_NIGHT))


def _load_dotenv():
    """Load .env file if it exists (simple implementation without external dependency)."""
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if present
                    if value and value[0] in ('"', "'") and value[-1] == value[0]:
                        value = value[1:-1]
                    os.environ.setdefault(key, value)


# Load .env file before creating settings
_load_dotenv()

# Global settings instance
settings = Settings()


# Backward compatibility exports
# These allow existing code to continue using `from config import BRIGHTNESS` etc.
ZONE_HOME = settings.ZONE_HOME
LOCATION_HOME = list(settings.LOCATION_HOME)
TEMPERATURE_LOCATION = settings.TEMPERATURE_LOCATION
TOMORROW_API_KEY = settings.TOMORROW_API_KEY
TEMPERATURE_UNITS = settings.TEMPERATURE_UNITS
DISTANCE_UNITS = settings.DISTANCE_UNITS
CLOCK_FORMAT = settings.CLOCK_FORMAT
MIN_ALTITUDE = settings.MIN_ALTITUDE
BRIGHTNESS = settings.BRIGHTNESS
BRIGHTNESS_NIGHT = settings.BRIGHTNESS_NIGHT
NIGHT_BRIGHTNESS = settings.NIGHT_BRIGHTNESS
NIGHT_START = settings.NIGHT_START
NIGHT_END = settings.NIGHT_END
GPIO_SLOWDOWN = settings.GPIO_SLOWDOWN
JOURNEY_CODE_SELECTED = settings.JOURNEY_CODE_SELECTED
JOURNEY_BLANK_FILLER = settings.JOURNEY_BLANK_FILLER
HAT_PWM_ENABLED = settings.HAT_PWM_ENABLED
FORECAST_DAYS = settings.FORECAST_DAYS
EMAIL = settings.EMAIL
MAX_FARTHEST = settings.MAX_FARTHEST
MAX_CLOSEST = settings.MAX_CLOSEST
ADSB_URL = settings.ADSB_URL
RANGE = settings.RANGE
SWIM_API_URL = settings.SWIM_API_URL
SWIM_API_KEY = settings.SWIM_API_KEY
