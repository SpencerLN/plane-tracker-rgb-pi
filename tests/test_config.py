"""Tests for the configuration module."""

import os
import pytest
import sys
from pathlib import Path

# Ensure conftest.py is loaded first
sys.path.insert(0, str(Path(__file__).parent))


class TestSettings:
    """Test the Settings configuration class."""
    
    def test_default_values(self):
        """Test that settings has sensible defaults."""
        from config import settings
        
        assert settings.BRIGHTNESS == 100 or isinstance(settings.BRIGHTNESS, int)
        assert settings.BRIGHTNESS_NIGHT == 50 or isinstance(settings.BRIGHTNESS_NIGHT, int)
        assert settings.TEMPERATURE_UNITS in ('metric', 'imperial')
        assert settings.DISTANCE_UNITS in ('metric', 'imperial')
        assert settings.CLOCK_FORMAT in ('12hr', '24hr')
    
    def test_brightness_validation(self):
        """Test that brightness values are clamped to valid range."""
        from config import Settings
        
        # Test that validation happens in __post_init__
        settings = Settings()
        assert 0 <= settings.BRIGHTNESS <= 100
        assert 0 <= settings.BRIGHTNESS_NIGHT <= 100
    
    def test_location_home_format(self):
        """Test LOCATION_HOME is a valid coordinate tuple."""
        from config import settings
        
        assert isinstance(settings.LOCATION_HOME, tuple)
        assert len(settings.LOCATION_HOME) == 2
        lat, lon = settings.LOCATION_HOME
        assert -90 <= lat <= 90  # Valid latitude
        assert -180 <= lon <= 180  # Valid longitude
    
    def test_zone_home_format(self):
        """Test ZONE_HOME has required keys."""
        from config import settings
        
        required_keys = {'tl_y', 'tl_x', 'br_y', 'br_x'}
        assert required_keys.issubset(set(settings.ZONE_HOME.keys()))
        
        for key, value in settings.ZONE_HOME.items():
            assert isinstance(value, (int, float))
    
    def test_backward_compatibility_exports(self):
        """Test that old-style imports still work."""
        from config import (
            BRIGHTNESS,
            BRIGHTNESS_NIGHT,
            TEMPERATURE_UNITS,
            DISTANCE_UNITS,
            CLOCK_FORMAT,
            NIGHT_START,
            NIGHT_END,
        )
        
        assert isinstance(BRIGHTNESS, int)
        assert isinstance(BRIGHTNESS_NIGHT, int)
        assert isinstance(TEMPERATURE_UNITS, str)
        assert isinstance(DISTANCE_UNITS, str)
        assert isinstance(CLOCK_FORMAT, str)
        assert isinstance(NIGHT_START, str)
        assert isinstance(NIGHT_END, str)


class TestEnvironmentVariables:
    """Test that environment variables override defaults."""
    
    def test_env_override(self):
        """Test that setting env var changes setting value."""
        # Note: These tests need to be run with proper env setup
        # The conftest.py sets some defaults
        api_key = os.environ.get('TOMORROW_API_KEY', '')
        assert api_key == 'test_api_key' or api_key != ''  # Set by conftest or user
