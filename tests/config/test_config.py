"""
Simple pytest tests for config.py module.

This demonstrates basic pytest concepts:
- Basic test functions
- Testing class instantiation
- Testing function returns
- Testing default values
- Using environment variables in tests
"""

import pytest
import os
from unittest.mock import patch
from src.core.config import Settings, get_settings

def test_settings_instantiation():
    """Test that Settings class can be instantiated"""
    settings = Settings()
    assert isinstance(settings, Settings)
    
def test_settings_from_environment():
    """Test that settings can be loaded from environment variables."""
    settings = Settings()
    assert settings.MODEL == "xxxxxxxxxxxxxxxxxxxxxxx"
    
def test_default_api_settings():
    """Test that default API settings are correct."""
    settings = Settings()
    assert settings.API_V1_STR == "/api/v1"
    assert settings.PROJECT_NAME == ""

    