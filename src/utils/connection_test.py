#!/usr/bin/env python3
"""
UNESWA WiFi AutoConnect - Connection Testing Utilities
ICT Society Initiative - University of Eswatini

Network connectivity testing and validation utilities.

Change history:
 - 2025-10-14: Added Windows PAC detection in proxy configuration checks
 - 2025-10-14: Normalized type hints for Python 3.8 compatibility and removed duplicate exception block
"""

import requests
import time
from typing import Optional, Tuple, Any, Dict
from dataclasses import dataclass
from enum import Enum

from src.config.settings import (
    PROXY_HOST,
    PROXY_URL,
    TEST_URLS,
    CONNECTION_TIMEOUT,
    PROXY_TEST_TIMEOUT,
    WIFI_SSID,
    REGISTRATION_BASE_URL,
    PROXY_PAC_URL,
)
from src.utils.system_utils import get_os_type, run_cmd


class ConnectionStatus(Enum):
    """Connection status enumeration"""

    UNKNOWN = "unknown"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ConnectionResult:
    """Result of a connection test"""

    success: bool
    status: ConnectionStatus
    message: str
    details: Dict[str, Any] = None
    latency_ms: Optional[float] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class WiFiTester:
    """WiFi connection testing utilities"""

    @staticmethod
    def is_wifi_connected() -> ConnectionResult:
        """Check if connected to any WiFi network"""
        try:
            if get_os_type() == "Windows":
                success, stdout, stderr = run_cmd(
                    ["netsh", "wlan", "show", "interfaces"], timeout=10
                )
                if success and "connected" in stdout.lower():
                    # Extract SSID if possible
                    lines = stdout.split("\n")
                    current_ssid = None
                    for line in lines:
                        if "SSID" in line and ":" in line:
                            current_ssid = line.split(":", 1)[1].strip()
                            break

                    return ConnectionResult(
                        success=True,
                        status=ConnectionStatus.CONNECTED,
                        message=f"Connected to WiFi: {current_ssid or 'Unknown'}",
                        details={"ssid": current_ssid, "interface_info": stdout},
                    )
                else:
                    return ConnectionResult(
                        success=False,
                        status=ConnectionStatus.DISCONNECTED,
                        details={"error": stderr},
                    )
            else:
                # Linux - try nmcli first, then iwconfig
                success, stdout, stderr = run_cmd(
                    ["nmcli", "-t", "-f", "WIFI", "general", "status"], timeout=10
                )
                if success and "enabled" in stdout.lower():
                    success, stdout, stderr = run_cmd(
                        [
                            "nmcli",
                            "-t",
                            "-f",
                            "NAME,TYPE,DEVICE",
                            "connection",
                            "show",
                            "--active",
                        ],
                        timeout=10,
                    )
                    wifi_connections = [
                        line for line in stdout.split("\n") if "wifi" in line.lower()
                    ]

                    if wifi_connections:
                        ssid = wifi_connections[0].split(":")[0]
                        return ConnectionResult(
                            success=True,
                            status=ConnectionStatus.CONNECTED,
                            message=f"Connected to WiFi: {ssid}",
                            details={"ssid": ssid, "connections": wifi_connections},
                        )

                return ConnectionResult(
                    success=False,
                    status=ConnectionStatus.DISCONNECTED,
                    message="Not connected to WiFi",
                    details={"error": "No active WiFi connections"},
                )

        except Exception as e:
            return ConnectionResult(
                success=False,
                status=ConnectionStatus.ERROR,
                message=f"WiFi status check failed: {e}",
                details={"exception": str(e)},
            )

    @staticmethod
    def is_connected_to_uneswa() -> ConnectionResult:
        """Check if connected specifically to UNESWA WiFi"""
        try:
            wifi_result = WiFiTester.is_wifi_connected()
            if not wifi_result.success:
                return wifi_result

            current_ssid = wifi_result.details.get("ssid", "").lower()
            expected_ssid = WIFI_SSID.lower()

            if expected_ssid in current_ssid or current_ssid in expected_ssid:
                return ConnectionResult(
                    success=True,
                    status=ConnectionStatus.CONNECTED,
                    message=f"Connected to UNESWA WiFi: {wifi_result.details.get('ssid')}",
                    details=wifi_result.details,
                )
            else:
                return ConnectionResult(
                    success=False,
                    status=ConnectionStatus.DISCONNECTED,
                    message=f"Connected to different network: {wifi_result.details.get('ssid')}",
                    details=wifi_result.details,
                )
        except Exception as e:
            return ConnectionResult(
                success=False,
                status=ConnectionStatus.ERROR,
                message=f"WiFi status check failed: {e}",
                details={"exception": str(e)},
            )


class ProxyTester:
    """Proxy connection testing utilities"""

    @staticmethod
    def test_direct_connection() -> ConnectionResult:
        """Test direct internet connection (should fail on campus)"""
        start_time = time.time()

        try:
            response = requests.get(
                TEST_URLS[0],
                timeout=PROXY_TEST_TIMEOUT,
                proxies={"http": "", "https": ""},
            )

            latency = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return ConnectionResult(
                    success=True,
                    status=ConnectionStatus.CONNECTED,
                    message="Direct internet access available",
                    latency_ms=latency,
                    details={
                        "response_code": response.status_code,
                        "url": TEST_URLS[0],
                    },
                )
        except Exception as e:
            return ConnectionResult(
                success=False,
                status=ConnectionStatus.DISCONNECTED,
                message="Direct connection blocked (expected on campus)",
                details={"error": str(e), "url": TEST_URLS[0]},
            )

    @staticmethod
    def test_proxy_connection() -> ConnectionResult:
        """Test internet connection through proxy"""
        start_time = time.time()

        try:
            proxies = {
                "http": PROXY_URL,
                "https": PROXY_URL,
            }

            response = requests.get(
                TEST_URLS[0], timeout=PROXY_TEST_TIMEOUT, proxies=proxies
            )

            latency = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return ConnectionResult(
                    success=True,
                    status=ConnectionStatus.CONNECTED,
                    message="Proxy connection working",
                    latency_ms=latency,
                    details={
                        "response_code": response.status_code,
                        "proxy_url": PROXY_URL,
                        "test_url": TEST_URLS[0],
                    },
                )
            else:
                return ConnectionResult(
                    success=False,
                    status=ConnectionStatus.ERROR,
                    message=f"Proxy returned status {response.status_code}",
                    details={
                        "response_code": response.status_code,
                        "proxy_url": PROXY_URL,
                    },
                )

        except Exception as e:
            return ConnectionResult(
                success=False,
                status=ConnectionStatus.ERROR,
                message=f"Proxy connection failed: {e}",
                details={"error": str(e), "proxy_url": PROXY_URL},
            )

    @staticmethod
    def is_proxy_configured() -> ConnectionResult:
        """Check if proxy is properly configured in system"""
        try:
            if get_os_type() == "Windows":
                import winreg

                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                    )

                    try:
                        proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                    except FileNotFoundError:
                        proxy_enable = 0

                    try:
                        proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                    except FileNotFoundError:
                        proxy_server = ""

                    try:
                        pac_url, _ = winreg.QueryValueEx(key, "AutoConfigURL")
                    except FileNotFoundError:
                        pac_url = ""

                    winreg.CloseKey(key)

                    # Manual proxy path
                    if proxy_enable and PROXY_HOST in proxy_server:
                        return ConnectionResult(
                            success=True,
                            status=ConnectionStatus.CONNECTED,
                            message=f"Windows proxy configured: {proxy_server}",
                            details={
                                "proxy_server": proxy_server,
                                "enabled": bool(proxy_enable),
                            },
                        )

                    # PAC mode path
                    if pac_url and str(pac_url).lower() == PROXY_PAC_URL.lower():
                        return ConnectionResult(
                            success=True,
                            status=ConnectionStatus.CONNECTED,
                            message=f"Windows PAC configured: {pac_url}",
                            details={
                                "pac_url": pac_url,
                                "enabled": False,
                            },
                        )

                    return ConnectionResult(
                        success=False,
                        status=ConnectionStatus.DISCONNECTED,
                        message="Windows proxy not configured",
                        details={
                            "proxy_server": proxy_server,
                            "pac_url": pac_url,
                            "enabled": bool(proxy_enable),
                        },
                    )
                except Exception as e:
                    return ConnectionResult(
                        success=False,
                        status=ConnectionStatus.ERROR,
                        message=f"Failed to check Windows proxy settings: {e}",
                    )
            else:
                # Linux - check environment variables
                import os

                http_proxy = os.environ.get("http_proxy", "") or os.environ.get(
                    "HTTP_PROXY", ""
                )
                https_proxy = os.environ.get("https_proxy", "") or os.environ.get(
                    "HTTPS_PROXY", ""
                )

                if PROXY_HOST in http_proxy and PROXY_HOST in https_proxy:
                    return ConnectionResult(
                        success=True,
                        status=ConnectionStatus.CONNECTED,
                        message=f"Linux proxy configured: {http_proxy}",
                        details={"http_proxy": http_proxy, "https_proxy": https_proxy},
                    )
                else:
                    return ConnectionResult(
                        success=False,
                        status=ConnectionStatus.DISCONNECTED,
                        message="Linux proxy environment variables not set",
                        details={"http_proxy": http_proxy, "https_proxy": https_proxy},
                    )

        except Exception as e:
            return ConnectionResult(
                success=False,
                status=ConnectionStatus.ERROR,
                message=f"Proxy configuration check failed: {e}",
                details={"exception": str(e)},
            )


class InternetTester:
    """Internet connectivity testing utilities"""

    @staticmethod
    def test_internet_access(use_proxy: bool = True) -> ConnectionResult:
        """Test general internet access"""
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if use_proxy else {}

        results = []
        total_latency = 0
        successful_tests = 0

        for url in TEST_URLS:
            try:
                start_time = time.time()
                response = requests.get(
                    url, timeout=CONNECTION_TIMEOUT, proxies=proxies
                )
                latency = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    results.append({"url": url, "success": True, "latency": latency})
                    total_latency += latency
                    successful_tests += 1
                else:
                    results.append(
                        {
                            "url": url,
                            "success": False,
                            "status_code": response.status_code,
                        }
                    )

            except Exception as e:
                results.append({"url": url, "success": False, "error": str(e)})

        if successful_tests > 0:
            avg_latency = total_latency / successful_tests
            success_rate = successful_tests / len(TEST_URLS)

            return ConnectionResult(
                success=success_rate >= 0.5,  # At least 50% success rate
                status=ConnectionStatus.CONNECTED
                if success_rate >= 0.5
                else ConnectionStatus.ERROR,
                message=f"Internet access: {successful_tests}/{len(TEST_URLS)} sites reachable",
                latency_ms=avg_latency,
                details={
                    "success_rate": success_rate,
                    "successful_tests": successful_tests,
                    "total_tests": len(TEST_URLS),
                    "results": results,
                    "proxy_used": use_proxy,
                },
            )
        else:
            return ConnectionResult(
                success=False,
                status=ConnectionStatus.DISCONNECTED,
                message="No internet access detected",
                details={"results": results, "proxy_used": use_proxy},
            )

    @staticmethod
    def test_university_access() -> ConnectionResult:
        """Test access to university websites"""
        try:
            start_time = time.time()
            response = requests.get(
                "http://www.uniswa.sz",
                timeout=CONNECTION_TIMEOUT,
                proxies={"http": PROXY_URL, "https": PROXY_URL},
            )
            latency = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return ConnectionResult(
                    success=True,
                    status=ConnectionStatus.CONNECTED,
                    message="University website accessible",
                    latency_ms=latency,
                    details={"response_code": response.status_code},
                )
            else:
                return ConnectionResult(
                    success=False,
                    status=ConnectionStatus.ERROR,
                    message=f"University website returned {response.status_code}",
                    details={"response_code": response.status_code},
                )

        except Exception as e:
            return ConnectionResult(
                success=False,
                status=ConnectionStatus.ERROR,
                message=f"Cannot reach university website: {e}",
                details={"error": str(e)},
            )


class RegistrationTester:
    """Device registration testing utilities"""

    @staticmethod
    def test_registration_portal() -> ConnectionResult:
        """Test if registration portal is accessible"""
        try:
            start_time = time.time()
            response = requests.get(
                REGISTRATION_BASE_URL,
                timeout=CONNECTION_TIMEOUT,
                proxies={"http": PROXY_URL, "https": PROXY_URL},
            )
            latency = (time.time() - start_time) * 1000

            if response.status_code == 200:
                content_lower = response.text.lower()
                registration_indicators = [
                    "registration",
                    "register",
                    "device",
                    "username",
                    "password",
                ]
                found_indicators = sum(
                    1
                    for indicator in registration_indicators
                    if indicator in content_lower
                )

                return ConnectionResult(
                    success=True,
                    status=ConnectionStatus.CONNECTED,
                    message="Registration portal accessible",
                    latency_ms=latency,
                    details={
                        "response_code": response.status_code,
                        "content_length": len(response.text),
                        "registration_indicators": found_indicators,
                        "likely_registration_page": found_indicators >= 2,
                    },
                )
            else:
                return ConnectionResult(
                    success=False,
                    status=ConnectionStatus.ERROR,
                    message=f"Registration portal returned {response.status_code}",
                    details={"response_code": response.status_code},
                )

        except Exception as e:
            return ConnectionResult(
                success=False,
                status=ConnectionStatus.ERROR,
                message=f"Cannot reach registration portal: {e}",
                details={"error": str(e)},
            )


class ComprehensiveTester:
    """Comprehensive connection testing combining all test types"""

    def __init__(self, callback: Optional[callable] = None):
        self.callback = callback  # Progress callback function

    def run_all_tests(self) -> Dict[str, ConnectionResult]:
        """Run all connection tests and return results"""
        results = {}

        tests = [
            ("wifi", WiFiTester.is_wifi_connected),
            ("uneswa_wifi", WiFiTester.is_connected_to_uneswa),
            ("proxy_config", ProxyTester.is_proxy_configured),
            ("direct_connection", ProxyTester.test_direct_connection),
            ("proxy_connection", ProxyTester.test_proxy_connection),
            ("internet_access", InternetTester.test_internet_access),
            ("university_access", InternetTester.test_university_access),
            ("registration_portal", RegistrationTester.test_registration_portal),
        ]

        for i, (test_name, test_func) in enumerate(tests):
            if self.callback:
                self.callback(f"Running {test_name} test...", i + 1, len(tests))

            results[test_name] = test_func()

            # Small delay between tests
            time.sleep(0.5)

        return results

    def get_overall_status(
        self, results: Dict[str, ConnectionResult]
    ) -> ConnectionResult:
        """Determine overall connection status from all test results"""
        critical_tests = ["wifi", "uneswa_wifi", "proxy_config", "proxy_connection"]

        critical_passed = all(
            results.get(
                test, ConnectionResult(False, ConnectionStatus.ERROR, "")
            ).success
            for test in critical_tests
        )

        if critical_passed:
            optional_tests = ["internet_access", "university_access"]
            optional_passed = sum(
                1
                for test in optional_tests
                if results.get(
                    test, ConnectionResult(False, ConnectionStatus.ERROR, "")
                ).success
            )

            if optional_passed >= len(optional_tests) // 2:
                return ConnectionResult(
                    success=True,
                    status=ConnectionStatus.CONNECTED,
                    message="Fully connected to UNESWA network",
                    details={
                        "critical_tests_passed": True,
                        "optional_tests_passed": optional_passed,
                    },
                )
            else:
                return ConnectionResult(
                    success=True,
                    status=ConnectionStatus.CONNECTED,
                    message="Connected but some services may be limited",
                    details={
                        "critical_tests_passed": True,
                        "optional_tests_passed": optional_passed,
                    },
                )
        else:
            failed_critical = [
                test
                for test in critical_tests
                if not results.get(
                    test, ConnectionResult(False, ConnectionStatus.ERROR, "")
                ).success
            ]

            return ConnectionResult(
                success=False,
                status=ConnectionStatus.ERROR,
                message=f"Connection issues: {', '.join(failed_critical)}",
                details={"failed_critical_tests": failed_critical},
            )


# Convenience functions for quick testing
def quick_wifi_test() -> bool:
    """Quick WiFi connectivity test"""
    return WiFiTester.is_connected_to_uneswa().success


def quick_internet_test() -> bool:
    """Quick internet connectivity test"""
    return InternetTester.test_internet_access().success


def quick_proxy_test() -> bool:
    """Quick proxy connectivity test"""
    return ProxyTester.test_proxy_connection().success


def run_quick_test() -> Tuple[bool, str]:
    """Run a quick overall connectivity test"""
    tester = ComprehensiveTester()
    results = tester.run_all_tests()
    overall = tester.get_overall_status(results)

    return overall.success, overall.message
