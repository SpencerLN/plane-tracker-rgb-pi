"""
Test configuration and fixtures for plane-tracker-rgb-pi tests.

This conftest.py automatically mocks the rgbmatrix module before any
test imports it, allowing tests to run on non-Raspberry Pi hardware.
"""

import sys
import os
from pathlib import Path

# Add the its-a-plane-python directory to the path
PROJECT_ROOT = Path(__file__).parent.parent
ITS_A_PLANE_DIR = PROJECT_ROOT / "its-a-plane-python"
sys.path.insert(0, str(ITS_A_PLANE_DIR))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))

# Import and install the mock rgbmatrix before any other imports
import mock_rgbmatrix

# Install the mock module into sys.modules so imports find it
sys.modules['rgbmatrix'] = mock_rgbmatrix

# Set environment variables for testing
os.environ.setdefault('TOMORROW_API_KEY', 'test_api_key')
os.environ.setdefault('EMAIL', '')
os.environ.setdefault('EMAIL_SENDER', '')
os.environ.setdefault('EMAIL_PASSWORD', '')
os.environ.setdefault('FLASK_DEBUG', 'false')
