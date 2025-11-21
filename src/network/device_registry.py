#!/usr/bin/env python3
#updating this in due course. AI generated it as placeholder because registration site doesn't work outside of school sometimes.
"""
UNESWA WiFi AutoConnect - Device Registration Manager
ICT Society Initiative - University of Eswatini

Device registration management for university network access.
"""

import re
import time
import requests
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
import html
from bs4 import BeautifulSoup

from src.config.settings import (
    REGISTRATION_BASE_URL,
    REGISTRATION_ENDPOINTS,
    REGISTRATION_TIMEOUT,
    PROXY_URL,
    PASSWORD_PREFIX,
)
from src.utils.system_utils import get_os_type


class DeviceRegistrationError(Exception):
    """Device registration errors"""

    pass


@dataclass
class RegistrationResult:
    """Result of device registration attempt"""

    success: bool
    message: str
    details: Dict[str, Any] = None
    response_data: Optional[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class RegistrationFormParser:
    """Parse registration forms to find submission details"""

    @staticmethod
    def parse_registration_form(html_content: str, base_url: str) -> Dict[str, Any]:
        """
        Parse HTML registration form to extract submission details
        Returns dict with action URL, method, and required fields
        
        This is like reverse-engineering a web form - we look at the HTML and figure out
        where to POST the data and what field names to use.
        
        BeautifulSoup is a library that parses HTML (web page code) and lets us search
        through it like a tree structure. We use it to find forms, input fields, etc.
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Look for forms that might be registration forms
            forms = soup.find_all("form")

            for form in forms:
                form_action = form.get("action", "")
                form_method = form.get("method", "post").lower()

                # Look for common registration form indicators
                # We check if the form text contains words like "registration", "username", etc.
                # If we find 2+ of these keywords, it's probably the right form.
                form_text = form.get_text().lower()
                registration_indicators = [
                    "registration",
                    "register",
                    "username",
                    "password",
                    "student",
                    "device",
                    "login",
                    "authenticate",
                ]

                indicator_count = sum(
                    1 for indicator in registration_indicators if indicator in form_text
                )

                # If this looks like a registration form
                if indicator_count >= 2:
                    # Extract form fields
                    inputs = form.find_all(["input", "select", "textarea"])
                    fields = {}

                    for input_elem in inputs:
                        input_name = input_elem.get("name", "")
                        input_type = input_elem.get("type", "text").lower()
                        input_value = input_elem.get("value", "")

                        if input_name:
                            fields[input_name] = {
                                "type": input_type,
                                "value": input_value,
                                "required": input_elem.has_attr("required"),
                            }

                    # Resolve action URL
                    if form_action:
                        if form_action.startswith("http"):
                            action_url = form_action
                        else:
                            action_url = urljoin(base_url, form_action)
                    else:
                        action_url = base_url

                    return {
                        "action_url": action_url,
                        "method": form_method,
                        "fields": fields,
                        "form_html": str(form),
                    }

            # No suitable form found
            return {
                "action_url": base_url,
                "method": "post",
                "fields": {},
                "form_html": None,
            }

        except Exception as e:
            return {
                "action_url": base_url,
                "method": "post",
                "fields": {},
                "error": str(e),
            }

    @staticmethod
    def guess_field_mappings(fields: Dict[str, Dict]) -> Dict[str, str]:
        """
        Guess which form fields correspond to username/password
        Returns mapping of standard names to form field names
        
        Different registration portals use different field names ("user" vs "username"
        vs "student_id"). We use keyword matching to figure out which is which.
        """
        mapping = {}

        for field_name, field_info in fields.items():
            field_name_lower = field_name.lower()
            field_type = field_info.get("type", "").lower()

            # Username field detection
            # If a field name contains any of these words, it's probably the username field
            username_indicators = [
                "username",
                "user",
                "login",
                "student",
                "id",
                "email",
                "account",
                "userid",
                "studentid",
            ]

            if any(
                indicator in field_name_lower for indicator in username_indicators
            ) and field_type in ["text", "email", ""]:
                mapping["username"] = field_name

            # Password field detection
            password_indicators = ["password", "pass", "pwd"]

            if (
                any(indicator in field_name_lower for indicator in password_indicators)
                or field_type == "password"
            ):
                mapping["password"] = field_name

            # Other common fields
            if "submit" in field_name_lower or field_type == "submit":
                mapping["submit"] = field_name
            elif "accept" in field_name_lower and field_type in ["checkbox", "hidden"]:
                mapping["accept"] = field_name
            elif "agree" in field_name_lower and field_type in ["checkbox", "hidden"]:
                mapping["agree"] = field_name

        return mapping


class CampusRegistrar:
    """Handle registration for specific campus"""

    def __init__(self, campus_name: str, registration_url: str):
        self.campus_name = campus_name
        self.registration_url = registration_url
        self.session = requests.Session()

        self.session.proxies = {"http": PROXY_URL, "https": PROXY_URL}
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self.session.timeout = REGISTRATION_TIMEOUT

    def test_connectivity(self) -> Tuple[bool, str]:
        """Test if registration portal is accessible"""
        try:
            response = self.session.get(self.registration_url, timeout=REGISTRATION_TIMEOUT)

            if response.status_code == 200:
                return True, f"Registration portal accessible ({response.status_code})"
            else:
                return (
                    False,
                    f"Registration portal returned status {response.status_code}",
                )

        except requests.exceptions.Timeout:
            return False, "Registration portal connection timeout"
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to registration portal"
        except Exception as e:
            return False, f"Registration portal test failed: {e}"

    def get_registration_form(self) -> Tuple[bool, Dict[str, Any], str]:
        """
        Get registration form details from the portal
        Returns: (success, form_details, message)
        """
        try:
            response = self.session.get(
                self.registration_url, timeout=REGISTRATION_TIMEOUT
            )

            if response.status_code != 200:
                return False, {}, f"Portal returned status {response.status_code}"

            form_details = RegistrationFormParser.parse_registration_form(
                response.text, response.url
            )

            if not form_details.get("fields"):
                form_details = self._simple_form_detection(response.text)

            return True, form_details, "Registration form retrieved successfully"

        except Exception as e:
            return False, {}, f"Failed to get registration form: {e}"

    def _simple_form_detection(self, html_content: str) -> Dict[str, Any]:
        """Simple form detection using regex (fallback)"""
        action_match = re.search(
            r'<form[^>]*action=["\']([^"\']*)["\']', html_content, re.IGNORECASE
        )
        action_url = action_match.group(1) if action_match else self.registration_url

        if action_url and not action_url.startswith("http"):
            action_url = urljoin(self.registration_url, action_url)

        input_pattern = r'<input[^>]*name=["\']([^"\']*)["\'][^>]*>'
        inputs = re.findall(input_pattern, html_content, re.IGNORECASE)

        fields = {}
        for input_name in inputs:
            fields[input_name] = {"type": "text", "value": "", "required": False}

        return {
            "action_url": action_url or self.registration_url,
            "method": "post",
            "fields": fields,
            "form_html": None,
        }

    def submit_registration(self, student_id: str, password: str) -> RegistrationResult:
        """Submit device registration with credentials"""
        try:
            form_success, form_details, form_message = self.get_registration_form()

            if not form_success:
                return RegistrationResult(
                    success=False,
                    message=f"Could not access registration form: {form_message}",
                    details={"campus": self.campus_name},
                )

            field_mapping = RegistrationFormParser.guess_field_mappings(
                form_details.get("fields", {})
            )

            # Known common mapping for the NetReg portal used on https://netreg.uniswa.sz
            # The portal posts 'user' and 'pass' with a 'submit' button named 'submit'.
            # If our heuristics didn't find these, add them explicitly (we know the portal).
            if not field_mapping.get("username") and "user" in form_details.get("fields", {}):
                field_mapping["username"] = "user"
            if not field_mapping.get("password") and "pass" in form_details.get("fields", {}):
                field_mapping["password"] = "pass"
            if not field_mapping.get("submit") and "submit" in form_details.get("fields", {}):
                field_mapping["submit"] = "submit"

            form_data = {}

            if "username" in field_mapping:
                form_data[field_mapping["username"]] = student_id
            else:
                # Try common field names
                for common_name in [
                    "username",
                    "user",
                    "login",
                    "student_id",
                    "studentid",
                ]:
                    if common_name in form_details.get("fields", {}):
                        form_data[common_name] = student_id
                        break
                else:
                    form_data["username"] = student_id

            if "password" in field_mapping:
                form_data[field_mapping["password"]] = password
            else:
                # Try common password field names
                for common_name in ["password", "pass", "pwd"]:
                    if common_name in form_details.get("fields", {}):
                        form_data[common_name] = password
                        break
                else:
                    form_data["password"] = password

            for field_name, field_info in form_details.get("fields", {}).items():
                if field_info.get("type") == "hidden" and field_info.get("value"):
                    form_data[field_name] = field_info["value"]
                elif field_name.lower() in ["accept", "agree", "terms"]:
                    form_data[field_name] = "1"
                elif field_info.get("type") == "submit" and field_name not in form_data:
                    form_data[field_name] = field_info.get("value", "Submit")

            action_url = form_details.get("action_url", self.registration_url)
            method = form_details.get("method", "post").lower()

            submit_headers = {}
            try:
                submit_headers["Referer"] = self.registration_url
                parsed = urlparse(action_url)
                if parsed.scheme and parsed.netloc:
                    submit_headers["Origin"] = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                pass

            if method == "get":
                response = self.session.get(
                    action_url,
                    params=form_data,
                    timeout=REGISTRATION_TIMEOUT,
                    headers=submit_headers,
                )
            else:
                submit_headers.setdefault(
                    "Content-Type", "application/x-www-form-urlencoded"
                )
                response = self.session.post(
                    action_url,
                    data=form_data,
                    timeout=REGISTRATION_TIMEOUT,
                    headers=submit_headers,
                )

            primary_result = self._analyze_registration_response(
                response, student_id, form_data
            )

            if primary_result.success:
                return primary_result

            legacy_result = self._submit_legacy_cgi(student_id, password)
            if legacy_result.success:
                return legacy_result

            return primary_result

        except requests.exceptions.Timeout:
            return RegistrationResult(
                success=False,
                message="Registration request timed out",
                details={"campus": self.campus_name, "timeout": REGISTRATION_TIMEOUT},
            )
        except Exception as e:
            return RegistrationResult(
                success=False,
                message=f"Registration submission failed: {e}",
                details={"campus": self.campus_name, "error": str(e)},
            )

    def _submit_legacy_cgi(self, student_id: str, password: str) -> RegistrationResult:
        """Direct CGI submit fallback when the modern form flow fails.
        
        Some older registration portals use a direct CGI script instead of a fancy form.
        If the HTML parsing fails, we try POSTing directly to known CGI endpoints.
        """
        try:
            candidates = []
            try:
                candidates.append(urljoin(self.registration_url, "/cgi-bin/register.cgi"))
            except Exception:
                pass

            # Known UNESWA registration endpoints (Kwaluseni and main campus)
            # We try HTTPS first for security, then fall back to HTTP if needed
            candidates.extend(
                [
                    "http://kwnetreg.uniswa.sz/cgi-bin/register.cgi",
                    "http://netreg.uniswa.sz/cgi-bin/register.cgi",
                    "https://netreg.uniswa.sz/cgi-bin/register.cgi",
                ]
            )

            payload = {"user": student_id, "pass": password, "submit": "ACCEPT"}

            for url in candidates:
                try:
                    resp = self.session.post(url, data=payload, timeout=REGISTRATION_TIMEOUT)
                    if resp.status_code in (200, 302):
                        text_l = resp.text.lower()
                        if any(w in text_l for w in ("success", "registered", "accept", "approved")):
                            return RegistrationResult(
                                success=True,
                                message=f"Device registration successful on {self.campus_name} (legacy)",
                                details={"campus": self.campus_name, "endpoint": url, "legacy": True},
                            )
                        return RegistrationResult(
                            success=True,
                            message="Registration submitted (legacy flow)",
                            details={"campus": self.campus_name, "endpoint": url, "legacy": True},
                        )
                except requests.exceptions.RequestException:
                    continue

            return RegistrationResult(
                success=False,
                message="Legacy registration endpoints not reachable",
                details={"campus": self.campus_name},
            )
        except Exception as e:
            return RegistrationResult(
                success=False,
                message=f"Legacy registration fallback failed: {e}",
                details={"campus": self.campus_name, "error": str(e)},
            )

    def _analyze_registration_response(
        self, response: requests.Response, student_id: str, form_data: dict
    ) -> RegistrationResult:
        """Analyze registration response to determine success/failure"""

        response_text = response.text.lower()

        success_indicators = [
            "success",
            "successful",
            "registered",
            "complete",
            "approved",
            "welcome",
            "activated",
            "enabled",
            "confirmed",
        ]

        failure_indicators = [
            "error",
            "failed",
            "invalid",
            "incorrect",
            "denied",
            "rejected",
            "unauthorized",
            "forbidden",
            "expired",
        ]

        success_count = sum(
            1 for indicator in success_indicators if indicator in response_text
        )
        failure_count = sum(
            1 for indicator in failure_indicators if indicator in response_text
        )

        if response.status_code == 200:
            if success_count > failure_count and success_count > 0:
                return RegistrationResult(
                    success=True,
                    message=f"Device registration successful on {self.campus_name} campus",
                    details={
                        "campus": self.campus_name,
                        "student_id": student_id,
                        "status_code": response.status_code,
                        "success_indicators": success_count,
                    },
                )
            elif failure_count > 0:
                return RegistrationResult(
                    success=False,
                    message=f"Registration failed - check credentials",
                    details={
                        "campus": self.campus_name,
                        "status_code": response.status_code,
                        "failure_indicators": failure_count,
                    },
                )
            else:
                return RegistrationResult(
                    success=True,
                    message=f"Registration completed (response unclear)",
                    details={
                        "campus": self.campus_name,
                        "status_code": response.status_code,
                        "response_length": len(response.text),
                    },
                )
        else:
            return RegistrationResult(
                success=False,
                message=f"Registration failed with HTTP {response.status_code}",
                details={
                    "campus": self.campus_name,
                    "status_code": response.status_code,
                },
            )


class DeviceRegistrationManager:
    """Main device registration manager"""

    def __init__(self):
        self.campus_registrars = {}

        for campus_name, url in REGISTRATION_ENDPOINTS.items():
            self.campus_registrars[campus_name] = CampusRegistrar(campus_name, url)

    def detect_campus(self) -> Optional[str]:
        """Try to detect which portal we can connect to"""
        for campus_name, registrar in self.campus_registrars.items():
            can_connect, message = registrar.test_connectivity()
            if can_connect:
                return campus_name

        return None

    def register_device(
        self, student_id: str, birthday_ddmmyy: str, campus: Optional[str] = None
    ) -> RegistrationResult:
        """
        Register device on university network

        Args:
            student_id: Student ID number
            birthday_ddmmyy: Birthday in ddmmyy format
            campus: Specific campus to try (None for auto-detect)
        """

        try:
            from src.network.wifi_manager import WiFiCredentials

            creds = WiFiCredentials(student_id, birthday_ddmmyy)
            password = creds.get_password()
        except Exception:
            password = f"{PASSWORD_PREFIX}{birthday_ddmmyy}"

        if campus and campus in self.campus_registrars:
            campuses_to_try = [campus]
        else:
            detected_campus = self.detect_campus()
            if detected_campus:
                campuses_to_try = [detected_campus]
            else:
                campuses_to_try = list(self.campus_registrars.keys())

        last_result = None
        for campus_name in campuses_to_try:
            registrar = self.campus_registrars[campus_name]

            can_connect, connect_message = registrar.test_connectivity()
            if not can_connect:
                last_result = RegistrationResult(
                    success=False,
                    message=f"Cannot connect to {campus_name}: {connect_message}",
                    details={"campus": campus_name},
                )
                continue

            result = registrar.submit_registration(student_id, password)

            if result.success:
                return result

            last_result = result
            time.sleep(2)

        if last_result:
            return last_result
        else:
            return RegistrationResult(
                success=False,
                message="Device registration failed - no accessible registration portals",
                details={"attempted_campuses": campuses_to_try},
            )

    def test_registration_portals(self) -> Dict[str, Tuple[bool, str]]:
        """Test connectivity to all registration portals"""
        results = {}

        for campus_name, registrar in self.campus_registrars.items():
            can_connect, message = registrar.test_connectivity()
            results[campus_name] = (can_connect, message)

        return results

    def get_available_campuses(self) -> List[str]:
        """Get list of available registration portals"""
        available = []

        for campus_name, registrar in self.campus_registrars.items():
            can_connect, _ = registrar.test_connectivity()
            if can_connect:
                available.append(campus_name)

        return available


# Global device registration manager
device_registry = DeviceRegistrationManager()


# Convenience functions
def register_device_on_network(
    student_id: str, birthday_ddmmyy: str, campus: Optional[str] = None
) -> RegistrationResult:
    """Register device on university network"""
    return device_registry.register_device(student_id, birthday_ddmmyy, campus)


def test_registration_connectivity() -> Dict[str, Tuple[bool, str]]:
    """Test connectivity to registration portals"""
    return device_registry.test_registration_portals()


def get_available_registration_campuses() -> List[str]:
    """Get list of accessible registration portals"""
    return device_registry.get_available_campuses()


def detect_current_campus() -> Optional[str]:
    """Try to detect current portal from registration portal access"""
    return device_registry.detect_campus()
