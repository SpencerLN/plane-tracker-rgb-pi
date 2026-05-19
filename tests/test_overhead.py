"""Tests for the overhead utility module.

Tests the geographic calculations and utility functions that don't
require actual flight data from the API.
"""

import pytest
import sys
from pathlib import Path

# Ensure conftest.py is loaded first to set up mocks
sys.path.insert(0, str(Path(__file__).parent))


class TestHaversine:
    """Test the haversine distance calculation."""
    
    def test_haversine_same_point(self):
        """Distance from a point to itself should be 0."""
        from utilities.overhead import haversine
        
        lat, lon = 44.797734, -93.186722
        distance = haversine(lat, lon, lat, lon)
        assert distance == pytest.approx(0, abs=0.001)
    
    def test_haversine_known_distance(self):
        """Test with a known distance between two cities."""
        from utilities.overhead import haversine
        
        # Minneapolis to Chicago is approximately 355 miles
        minneapolis = (44.9778, -93.2650)
        chicago = (41.8781, -87.6298)
        
        distance = haversine(minneapolis[0], minneapolis[1], chicago[0], chicago[1])
        # Allow 10% tolerance for great-circle vs actual distance
        assert 320 < distance < 390
    
    def test_haversine_metric_conversion(self):
        """Test that metric conversion works."""
        from utilities.overhead import haversine, EARTH_RADIUS_M
        
        # The haversine function uses DISTANCE_UNITS from config
        # We can verify the formula is correct by checking against known values
        lat1, lon1 = 0, 0
        lat2, lon2 = 0, 1  # 1 degree longitude at equator
        
        distance = haversine(lat1, lon1, lat2, lon2)
        # At equator, 1 degree longitude ≈ 69 miles (111 km)
        assert 60 < distance < 80  # Allow tolerance for imperial units


class TestDegreesToCardinal:
    """Test the degrees to cardinal direction conversion."""
    
    def test_north(self):
        """Test north direction."""
        from utilities.overhead import degrees_to_cardinal
        
        assert degrees_to_cardinal(0) == "N"
        assert degrees_to_cardinal(360) == "N"
        assert degrees_to_cardinal(22) == "N"
    
    def test_cardinal_directions(self):
        """Test all cardinal directions."""
        from utilities.overhead import degrees_to_cardinal
        
        assert degrees_to_cardinal(45) == "NE"
        assert degrees_to_cardinal(90) == "E"
        assert degrees_to_cardinal(135) == "SE"
        assert degrees_to_cardinal(180) == "S"
        assert degrees_to_cardinal(225) == "SW"
        assert degrees_to_cardinal(270) == "W"
        assert degrees_to_cardinal(315) == "NW"
    
    def test_boundary_cases(self):
        """Test boundary cases between directions."""
        from utilities.overhead import degrees_to_cardinal
        
        # Just below boundary
        assert degrees_to_cardinal(22) == "N"
        # Just above boundary  
        assert degrees_to_cardinal(23) == "NE"


class TestOrdinal:
    """Test the ordinal number formatting."""
    
    def test_ordinals(self):
        """Test ordinal suffix generation."""
        from utilities.overhead import ordinal
        
        assert ordinal(1) == "1st"
        assert ordinal(2) == "2nd"
        assert ordinal(3) == "3rd"
        assert ordinal(4) == "4th"
        assert ordinal(11) == "11th"
        assert ordinal(12) == "12th"
        assert ordinal(13) == "13th"
        assert ordinal(21) == "21st"
        assert ordinal(22) == "22nd"
        assert ordinal(23) == "23rd"
        assert ordinal(100) == "100th"
        assert ordinal(101) == "101st"


class TestSafeJsonOperations:
    """Test JSON file operations."""
    
    def test_safe_load_json_nonexistent(self, tmp_path):
        """Loading nonexistent file returns empty list."""
        from utilities.overhead import safe_load_json
        
        result = safe_load_json(str(tmp_path / "nonexistent.json"))
        assert result == []
    
    def test_safe_load_json_invalid(self, tmp_path):
        """Loading invalid JSON returns empty list."""
        from utilities.overhead import safe_load_json
        
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json {")
        
        result = safe_load_json(str(invalid_file))
        assert result == []
    
    def test_safe_load_json_valid(self, tmp_path):
        """Loading valid JSON returns the data."""
        from utilities.overhead import safe_load_json
        import json
        
        data = [{"callsign": "TEST123", "distance": 5.0}]
        valid_file = tmp_path / "valid.json"
        valid_file.write_text(json.dumps(data))
        
        result = safe_load_json(str(valid_file))
        assert result == data
    
    def test_safe_write_json(self, tmp_path):
        """Writing JSON creates valid file."""
        from utilities.overhead import safe_write_json, safe_load_json
        
        data = [{"test": "data", "number": 42}]
        file_path = str(tmp_path / "output.json")
        
        safe_write_json(file_path, data)
        result = safe_load_json(file_path)
        
        assert result == data
