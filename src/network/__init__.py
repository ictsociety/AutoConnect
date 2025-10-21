#!/usr/bin/env python3
"""
UNESWA WiFi AutoConnect - Network Package
ICT Society Initiative - University of Eswatini

Network management package for WiFi, proxy, and device registration functionality.
"""

from typing import Tuple

from src.network.wifi_manager import (
    WiFiManager,
    WiFiCredentials,
    WindowsWiFiManager,
    LinuxWiFiManager,
    WiFiConnectionError,
    wifi_manager,
    connect_to_university_wifi,
    disconnect_from_wifi,
    is_connected_to_university_wifi,
    get_wifi_connection_status,
    validate_wifi_credentials,
)

from src.network.proxy_manager import (
    ProxyManager,
    WindowsProxyManager,
    LinuxProxyManager,
    ProxyConfigError,
    proxy_manager,
    enable_university_proxy,
    disable_university_proxy,
    is_university_proxy_configured,
    get_proxy_config_status,
)

from src.network.device_registry import (
    DeviceRegistrationManager,
    CampusRegistrar,
    RegistrationResult,
    RegistrationFormParser,
    DeviceRegistrationError,
    device_registry,
    register_device_on_network,
    test_registration_connectivity,
    get_available_registration_campuses,
    detect_current_campus,
)

__version__ = "1.0.0"
__author__ = "ICT Society - University of Eswatini"
__description__ = "Network management for UNESWA WiFi AutoConnect"

# Expose main network management classes and functions
__all__ = [
    # WiFi Management
    "WiFiManager",
    "WiFiCredentials",
    "WindowsWiFiManager",
    "LinuxWiFiManager",
    "WiFiConnectionError",
    "wifi_manager",
    "connect_to_university_wifi",
    "disconnect_from_wifi",
    "is_connected_to_university_wifi",
    "get_wifi_connection_status",
    "validate_wifi_credentials",
    # Proxy Management
    "ProxyManager",
    "WindowsProxyManager",
    "LinuxProxyManager",
    "ProxyConfigError",
    "proxy_manager",
    "enable_university_proxy",
    "disable_university_proxy",
    "is_university_proxy_configured",
    "get_proxy_config_status",
    # Device Registration
    "DeviceRegistrationManager",
    "CampusRegistrar",
    "RegistrationResult",
    "RegistrationFormParser",
    "DeviceRegistrationError",
    "device_registry",
    "register_device_on_network",
    "test_registration_connectivity",
    "get_available_registration_campuses",
    "detect_current_campus",
]


# Convenience class for complete network management
class NetworkManager:
    """
    Unified network management interface

    Provides a single interface for WiFi, proxy, and device registration operations.
    """

    def __init__(self):
        self.wifi = wifi_manager
        self.proxy = proxy_manager
        self.registry = device_registry

    def _ensure_proxy_enabled(self) -> Tuple[bool, str]:
        """Check proxy status and enable if needed"""
        is_configured = self.proxy.is_proxy_configured()
        
        if is_configured:
            return True, "Proxy already configured"
        
        # Enable proxy (always use manual proxy for reliability)
        return self.proxy.enable_proxy()

    def complete_setup(
        self, student_id: str, birthday_ddmmyy: str, campus: str = None
    ) -> dict:
        """
        Perform complete network setup: WiFi + Proxy + Registration

        Returns:
            dict: Status of each operation
        """
        results = {
            "wifi": {"success": False, "message": ""},
            "proxy": {"success": False, "message": ""},
            "registration": {"success": False, "message": ""},
            "overall": {"success": False, "message": ""},
        }

        try:
            # Step 1: Connect to WiFi
            wifi_success, wifi_message = self.wifi.connect(student_id, birthday_ddmmyy)
            results["wifi"] = {"success": wifi_success, "message": wifi_message}

            if not wifi_success:
                results["overall"] = {
                    "success": False,
                    "message": f"WiFi connection failed: {wifi_message}",
                }
                return results

            # Step 2: Configure proxy
            proxy_success, proxy_message = self._ensure_proxy_enabled()
            results["proxy"] = {"success": proxy_success, "message": proxy_message}

            # Step 3: Register device
            reg_result = self.registry.register_device(
                student_id, birthday_ddmmyy, campus
            )
            results["registration"] = {
                "success": reg_result.success,
                "message": reg_result.message,
            }

            # Overall success if WiFi connected (proxy and registration are less critical)
            overall_success = wifi_success
            if overall_success and proxy_success and reg_result.success:
                results["overall"] = {
                    "success": True,
                    "message": "Complete network setup successful",
                }
            elif overall_success:
                results["overall"] = {
                    "success": True,
                    "message": "WiFi connected, some additional setup may be incomplete",
                }
            else:
                results["overall"] = {
                    "success": False,
                    "message": "Network setup failed",
                }

            return results

        except Exception as e:
            results["overall"] = {"success": False, "message": f"Setup error: {e}"}
            return results

    def reset_all_settings(self) -> dict:
        """
        Reset all network settings (disconnect WiFi, disable proxy, remove profiles)

        Returns:
            dict: Status of each reset operation
        """
        results = {
            "wifi_disconnect": {"success": False, "message": ""},
            "wifi_profile_removal": {"success": False, "message": ""},
            "proxy_disable": {"success": False, "message": ""},
            "overall": {"success": False, "message": ""},
        }

        try:
            disconnect_success, disconnect_message = self.wifi.disconnect()
            results["wifi_disconnect"] = {
                "success": disconnect_success,
                "message": disconnect_message,
            }

            profile_success, profile_message = self.wifi.remove_profile()
            results["wifi_profile_removal"] = {
                "success": profile_success,
                "message": profile_message,
            }

            proxy_success, proxy_message = self.proxy.disable_proxy()
            results["proxy_disable"] = {
                "success": proxy_success,
                "message": proxy_message,
            }

            # Remove saved credentials
            try:
                from src.utils.credentials import remove_credentials
                remove_credentials()
            except Exception:
                pass

            # Overall success if most operations succeeded
            success_count = sum([disconnect_success, profile_success, proxy_success])

            if success_count >= 2:
                results["overall"] = {
                    "success": True,
                    "message": "UNESWA network settings reset successfully (other WiFi profiles preserved)",
                }
            else:
                results["overall"] = {
                    "success": False,
                    "message": "Some UNESWA settings may not have been reset properly",
                }

            return results

        except Exception as e:
            results["overall"] = {"success": False, "message": f"Reset error: {e}"}
            return results

    def get_connection_status(self) -> dict:
        """
        Get comprehensive connection status

        Returns:
            dict: Status of WiFi, proxy, and overall connectivity
        """
        return {
            "wifi": self.wifi.get_status(),
            "proxy": self.proxy.get_proxy_status(),
            "wifi_connected": self.wifi.is_connected(),
            "proxy_configured": self.proxy.is_proxy_configured(),
            "available_campuses": self.registry.get_available_campuses(),
        }


# Global network manager instance
network_manager = NetworkManager()

# Add to exports
__all__.append("NetworkManager")
__all__.append("network_manager")
