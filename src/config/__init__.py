#!/usr/bin/env python3
"""
UNESWA WiFi AutoConnect - Configuration Package
ICT Society Initiative - University of Eswatini

Configuration management for the application.
"""

from src.config.settings import *
from src.config.translations import translator, t, LANG_ENGLISH, LANG_SISWATI

__version__ = "1.0.0"
__author__ = "ICT Society - University of Eswatini"
__description__ = "Configuration management for UNESWA WiFi AutoConnect"

# Expose main configuration items for easy access
__all__ = [
    "APP_NAME",
    "VERSION",
    "WIFI_SSID",
    "PROXY_HOST",
    "PROXY_PORT",
    "PROXY_URL",
    "REGISTRATION_BASE_URL",
    "PASSWORD_PREFIX",
    "UI_THEME",
    "STATUS_MESSAGES",
    "ERROR_MESSAGES",
    "SUCCESS_MESSAGES",
    "WINDOWS_SETTINGS",
    "LINUX_SETTINGS",
]
