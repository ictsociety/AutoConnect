#!/usr/bin/env python3
"""
UNESWA WiFi AutoConnect - Utilities Package
ICT Society Initiative - University of Eswatini

Utility modules for system operations, connection testing, and helper functions.
"""

from src.utils.system_utils import (
    SystemInfo,
    PrivilegeManager,
    ProcessManager,
    PathManager,
    system_info,
    privilege_manager,
    process_manager,
    path_manager,
    get_os_type,
    get_distro_id,
    is_admin,
    can_configure_network,
    run_cmd,
    request_admin_elevation,
)

from src.utils.connection_test import (
    ConnectionStatus,
    ConnectionResult,
    WiFiTester,
    ProxyTester,
    InternetTester,
    RegistrationTester,
    ComprehensiveTester,
    quick_wifi_test,
    quick_internet_test,
    quick_proxy_test,
    run_quick_test,
)

__version__ = "1.0.0"
__author__ = "ICT Society - University of Eswatini"
__description__ = "System and network utilities for UNESWA WiFi AutoConnect"

# Expose main utility classes and functions
__all__ = [
    # System utilities
    "SystemInfo",
    "PrivilegeManager",
    "ProcessManager",
    "PathManager",
    "system_info",
    "privilege_manager",
    "process_manager",
    "path_manager",
    "get_os_type",
    "get_distro_id",
    "is_admin",
    "can_configure_network",
    "run_cmd",
    "request_admin_elevation",
    "ConnectionStatus",
    "ConnectionResult",
    "WiFiTester",
    "ProxyTester",
    "InternetTester",
    "RegistrationTester",
    "ComprehensiveTester",
    "quick_wifi_test",
    "quick_internet_test",
    "quick_proxy_test",
    "run_quick_test",
]
