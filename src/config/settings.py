#!/usr/bin/env python3
"""
UNESWA WiFi AutoConnect - Configuration Settings
ICT Society Initiative - University of Eswatini

All the configuration constants and settings for the app.
Network settings, timeouts, file paths, and platform-specific configs.
"""

import os
from pathlib import Path

# Application Information
APP_NAME = "UNESWA WiFi AutoConnect"
VERSION = "1.2.5"
DEVELOPER = "ICT Society - University of Eswatini"

# Network Configuration
WIFI_SSID = "uniswawifi-students"
WIFI_SECURITY = "WPA2-Enterprise"
WIFI_EAP_METHOD = "PEAP"
WIFI_PHASE2_AUTH = "MSCHAPv2"

# Proxy Configuration (Manual Proxy - NOT PAC)
PROXY_HOST = "proxy02.uniswa.sz"
PROXY_PORT = 3128
PROXY_URL = f"http://{PROXY_HOST}:{PROXY_PORT}"
# Official university PAC script URL (Windows PAC mode)
PROXY_PAC_URL = "http://www.uniswa.sz/uniswa/uniswaproxy.pac"

# Device Registration
REGISTRATION_BASE_URL = "https://netreg.uniswa.sz"
REGISTRATION_ENDPOINTS = {
    "netreg": "https://netreg.uniswa.sz",
}

# Connection Test URLs
TEST_URLS = [
    "http://httpbin.org/ip",
    "http://www.google.com",
    "http://www.uniswa.sz",
    "http://connectivitycheck.gstatic.com/generate_204",
]

# Password Configuration
# Password format: Uneswa + birthday in ddmmyyyy format
# Example: Uneswa12052001 (Uneswa + 12/05/2001)
PASSWORD_PREFIX = "Uneswa"
PASSWORD_FORMAT_HINT = "Birthday in ddmmyyyy format (e.g., 12052001 for 12 May 2001)"
EXPECTED_PASSWORD_LENGTH = 14  # 6 (Uneswa) + 8 (ddmmyyyy) = 14

# UI Configuration
UI_THEME = "dark"
UI_COLOR_THEME = "blue"
UI_WINDOW_SIZE = "520x700"
UI_RESIZABLE = True

# Language Configuration
DEFAULT_LANGUAGE = "en"  # "en" for English, "ss" for siSwati
AVAILABLE_LANGUAGES = ["en", "ss"]

# Scrollable UI Configuration
SCROLLABLE_FRAME_CORNER_RADIUS = 0
SCROLLBAR_BUTTON_COLOR = "#2B2B2B"
SCROLLBAR_BUTTON_HOVER_COLOR = "#3B3B3B"
MIN_WINDOW_WIDTH = 520
MIN_WINDOW_HEIGHT = 700

# File Paths
APP_DIR = Path(__file__).parent.parent.parent
ASSETS_DIR = APP_DIR / "assets"
LOGS_DIR = APP_DIR / "logs"
CONFIG_DIR = APP_DIR / "config"
TEMP_DIR = APP_DIR / "temp"

# Logging Configuration
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"
MAX_LOG_SIZE_MB = 5
LOG_BACKUP_COUNT = 3

# Network Timeouts
CONNECTION_TIMEOUT = 10
REGISTRATION_TIMEOUT = 15
WIFI_CONNECT_TIMEOUT = 30
PROXY_TEST_TIMEOUT = 5

# Background Service Configuration
MONITOR_INTERVAL = 30  # seconds
RECONNECT_ATTEMPTS = 3
RECONNECT_DELAY = 5  # seconds

# Platform-Specific Settings
WINDOWS_SETTINGS = {
    "registry_path": r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
    "temp_profile_name": "uneswa_wifi_temp.xml",
    "netsh_timeout": 15,
    # Configure WinHTTP (system service) proxy alongside WinINet
    "configure_winhttp": True,
    # Windows 11: Try native connection first, wait this many seconds before falling back
    "win11_native_wait_seconds": 15,
}

LINUX_SETTINGS = {
    "networkmanager_timeout": 20,
    "shell_files": ["~/.bashrc", "~/.zshrc", "~/.profile", "/etc/environment"],
    "proxy_exports": [
        f"export http_proxy='{PROXY_URL}'",
        f"export https_proxy='{PROXY_URL}'",
        f"export HTTP_PROXY='{PROXY_URL}'",
        f"export HTTPS_PROXY='{PROXY_URL}'",
        f"export ftp_proxy='{PROXY_URL}'",
        f"export FTP_PROXY='{PROXY_URL}'",
    ],
    "distro_configs": {
        "ubuntu": {
            "proxy_setup": "environment_vars",
            "commands": ["pkexec systemctl restart NetworkManager"],
        },
        "debian": {
            "proxy_setup": "environment_vars",
            "commands": ["pkexec systemctl restart NetworkManager"],
        },
        "arch": {
            "proxy_setup": "environment_vars",
            "additional_files": ["/etc/environment"],
            "commands": ["pkexec systemctl restart NetworkManager"],
        },
        "manjaro": {
            "proxy_setup": "environment_vars",
            "additional_files": ["/etc/environment"],
            "commands": ["pkexec systemctl restart NetworkManager"],
        },
        "fedora": {
            "proxy_setup": "dnf_config",
            "dnf_config_file": "/etc/dnf/dnf.conf",
            "dnf_proxy_line": f"proxy={PROXY_URL}",
            "commands": ["pkexec systemctl restart NetworkManager"],
        },
        "centos": {
            "proxy_setup": "dnf_config",
            "dnf_config_file": "/etc/dnf/dnf.conf",
            "dnf_proxy_line": f"proxy={PROXY_URL}",
            "commands": ["pkexec systemctl restart NetworkManager"],
        },
        "rhel": {
            "proxy_setup": "dnf_config",
            "dnf_config_file": "/etc/dnf/dnf.conf",
            "dnf_proxy_line": f"proxy={PROXY_URL}",
            "commands": ["pkexec systemctl restart NetworkManager"],
        },
    },
}

# Status Messages
STATUS_MESSAGES = {
    "disconnected": "Not connected",
    "connecting": "Connecting...",
    "connected_wifi": "WiFi connected",
    "connected_proxy": "Proxy configured",
    "connected_registered": "Device registered",
    "connected_full": "Fully connected",
    "error": "Connection error",
    "testing": "Testing connection...",
}

# Error Messages
ERROR_MESSAGES = {
    "no_admin": "Administrator privileges required for network configuration",
    "wifi_failed": "Failed to connect to WiFi. Check credentials and try again.",
    "proxy_failed": "Failed to configure proxy settings",
    "registration_failed": "Device registration failed. Check network connection.",
    "invalid_credentials": "Invalid student ID or password format",
    "network_unavailable": "University network not available",
    "connection_test_failed": "Connection test failed",
}

# Success Messages
SUCCESS_MESSAGES = {
    "wifi_connected": "WiFi connection established successfully",
    "proxy_configured": "Proxy settings configured successfully",
    "device_registered": "Device registered successfully on university network",
    "full_setup": "Complete network setup finished successfully",
}

# Development/Debug Settings
DEBUG_MODE = os.getenv("UNESWA_DEBUG", "false").lower() == "true"
VERBOSE_LOGGING = DEBUG_MODE
SKIP_PRIVILEGE_CHECK = DEBUG_MODE

# Create directories if they don't exist
for directory in [LOGS_DIR, TEMP_DIR]:
    directory.mkdir(exist_ok=True, parents=True)
