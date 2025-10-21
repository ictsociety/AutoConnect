#!/usr/bin/env python3
"""
UNESWA WiFi AutoConnect - UI Package
ICT Society Initiative - University of Eswatini

User interface package for the WiFi AutoConnect application.
Provides dark mode CustomTkinter interface components.
"""

from src.ui.main_window import (
    UNESWAWiFiApp,
    StatusBar,
    CredentialsFrame,
    ActionButtonsFrame,
    LogFrame,
    main,
)

__version__ = "1.2.5"
__author__ = "ICT Society - University of Eswatini"
__description__ = "Dark mode user interface for UNESWA WiFi AutoConnect"

# Expose main UI classes and functions
__all__ = [
    # Main application
    "UNESWAWiFiApp",
    "main",
    # UI Components
    "StatusBar",
    "CredentialsFrame",
    "ActionButtonsFrame",
    "LogFrame",
    # Exceptions
]


# UI Configuration constants
UI_THEMES = {
    "dark": "Dark mode",
}

SUPPORTED_THEMES = ["dark"]


def create_app() -> UNESWAWiFiApp:
    """
    Create and return the main application instance

    Returns:
        UNESWAWiFiApp: Main application window
    """
    return UNESWAWiFiApp()


def run_app():
    """
    Create and run the main application

    Convenience function to start the application directly.
    """
    main()


# Theme validation
def validate_theme(theme: str) -> bool:
    """
    Validate if theme is acceptable

    Args:
        theme: Theme name to validate

    Returns:
        bool: True if theme is supported (dark), False otherwise
    """
    return theme.lower() in SUPPORTED_THEMES


def get_app_info() -> dict:
    """
    Get application UI information

    Returns:
        dict: UI package information
    """
    return {
        "name": "UNESWA WiFi AutoConnect UI",
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "supported_themes": SUPPORTED_THEMES,
    }


__all__.extend(
    [
        "create_app",
        "run_app",
        "validate_theme",
        "get_app_info",
        "UI_THEMES",
        "SUPPORTED_THEMES",
    ]
)
