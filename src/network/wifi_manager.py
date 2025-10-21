#!/usr/bin/env python3
"""
UNESWA WiFi AutoConnect - WiFi Manager
ICT Society Initiative - University of Eswatini

Handles WiFi connection setup for WPA2-Enterprise networks.
Uses netsh on Windows and NetworkManager on Linux.
"""

import os
import platform
import subprocess
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

from src.config.settings import (
    WIFI_SSID,
    WIFI_SECURITY,
    WIFI_EAP_METHOD,
    WIFI_PHASE2_AUTH,
    WIFI_CONNECT_TIMEOUT,
    WINDOWS_SETTINGS,
    PASSWORD_PREFIX,
    EXPECTED_PASSWORD_LENGTH,
)
from src.config.translations import translator, t
from src.utils.system_utils import (
    get_os_type,
    is_admin,
    run_cmd,
    system_info,
)

# Import Windows EAP credential manager (only on Windows)
if get_os_type() == "Windows":
    try:
        from src.utils.windows_eap_credentials import (
            store_windows_eap_credentials,
            clear_windows_eap_credentials,
            check_windows_eap_credentials,
        )
    except ImportError:
        store_windows_eap_credentials = None
        clear_windows_eap_credentials = None
        check_windows_eap_credentials = None
else:
    store_windows_eap_credentials = None
    clear_windows_eap_credentials = None
    check_windows_eap_credentials = None


class WiFiConnectionError(Exception):
    """WiFi connection errors"""

    pass


class WiFiCredentials:
    """WiFi authentication credentials"""

    def __init__(self, student_id: str, birthday: str = ""):
        self.student_id = student_id.strip()
        self.birthday = ""  # stored as ddmmyyyy (8 digits) when set
        if birthday:
            # Accept a variety of birthday/password formats and normalize
            self.set_birthday(birthday.strip())

        self._validate_credentials()

    def _validate_credentials(self):
        """Validate credential format"""
        if not self.student_id:
            raise ValueError(t("student_id_empty"))

        # Basic student ID validation (typically numeric)
        if not self.student_id.replace("-", "").replace("/", "").isdigit():
            # Allow some common formats like 2019/1234 or 2019-1234
            pass

    def get_username(self) -> str:
        """Get username for WiFi authentication"""
        return self.student_id

    def get_password(self, birthday_ddmmyy: str = None) -> str:
        """
        Build the password in UneswaDDMMYYYY format.

        Takes different input formats:
        - "UneswaDDMMYYYY" (already complete)
        - "DDMMYYYY" (8 digits) - adds the Uneswa prefix
        - "DDMMYY" (6 digits) - expands year to 20YY and adds prefix

        Returns complete password like "Uneswa01011999"
        """
        # If birthday was passed in, normalize and use it
        if birthday_ddmmyy:
            normalized = self._normalize_birthday_input(birthday_ddmmyy.strip())
            return f"{PASSWORD_PREFIX}{normalized}"

        # Otherwise use the stored birthday if we have one
        if self.birthday:
            return f"{PASSWORD_PREFIX}{self.birthday}"

        # Nothing to work with, just return the prefix
        return PASSWORD_PREFIX

    def set_birthday(self, birthday_ddmmyy: str):
        """Store birthday from various formats.

        Handles these inputs:
        - "UneswaDDMMYYYY" - strips prefix, stores the date part
        - "DDMMYYYY" - stores as-is
        - "DDMMYY" - expands to DDMM20YY first
        """
        if not birthday_ddmmyy or not isinstance(birthday_ddmmyy, str):
            raise ValueError("Birthday must be a non-empty string")

        val = birthday_ddmmyy.strip()

        # Strip the password prefix if it's there
        if val.startswith(PASSWORD_PREFIX):
            remainder = val[len(PASSWORD_PREFIX) :]
            val = remainder

        # Now we should have just the birthday digits
        if val.isdigit() and len(val) == 8:
            # Quick sanity check on the date
            day = int(val[:2])
            month = int(val[2:4])
            if not (1 <= day <= 31 and 1 <= month <= 12):
                raise ValueError("Invalid date in birthday")

            self.birthday = val
            return

        if val.isdigit() and len(val) == 6:
            # Expand 2-digit year to 4 digits (assumes 2000s)
            day = int(val[:2])
            month = int(val[2:4])
            if not (1 <= day <= 31 and 1 <= month <= 12):
                raise ValueError("Invalid date in birthday")

            yy = val[4:6]
            expanded = f"{val[:4]}20{yy}"
            self.birthday = expanded
            return

        raise ValueError(t("birthday_invalid"))

    @staticmethod
    def _normalize_birthday_input(raw: str) -> str:
        """Convert various birthday formats to standard 8-digit DDMMYYYY."""
        if not raw:
            raise ValueError("Empty birthday input")

        s = raw.strip()

        # Strip password prefix if present
        if s.startswith(PASSWORD_PREFIX):
            remainder = s[len(PASSWORD_PREFIX) :]
            if remainder.isdigit() and len(remainder) == 8:
                return remainder
            if remainder.isdigit() and len(remainder) == 6:
                return f"{remainder[:4]}20{remainder[4:]}"
            raise ValueError("Invalid password format after prefix")

        # Already 8 digits, good to go
        if s.isdigit() and len(s) == 8:
            return s

        # 6 digits - expand to 8
        if s.isdigit() and len(s) == 6:
            return f"{s[:4]}20{s[4:]}"

        raise ValueError(t("birthday_invalid"))


class WindowsWiFiManager:
    """Windows-specific WiFi management using netsh"""

    @staticmethod
    def create_wpa2_enterprise_profile(credentials: WiFiCredentials) -> str:
        """Create WPA2-Enterprise XML profile for Windows using configured settings"""
        # Figure out which auth type to use based on config
        auth = "WPA2"
        if isinstance(WIFI_SECURITY, str):
            sec = WIFI_SECURITY.lower()
            if "wpa2" in sec:
                auth = "WPA2"
            elif "wpa" in sec:
                auth = "WPA"

        eap_method = (WIFI_EAP_METHOD or "PEAP").strip().upper()
        phase2 = (WIFI_PHASE2_AUTH or "MSCHAPv2").strip().upper()

        # Windows natively supports PEAP and MSCHAPv2. Other EAP methods require
        # third-party supplicants, so we're sticking with what works out of the box.
        eap_type_outer = 25  # PEAP
        eap_type_inner = 26  # MSCHAPv2

        # Build the profile XML. Server cert validation is disabled because that's how
        # the university network is configured (no cert validation required).
        profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{WIFI_SSID}</name>
    <SSIDConfig>
        <SSID>
            <name>{WIFI_SSID}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>{auth}</authentication>
                <encryption>AES</encryption>
                <useOneX>true</useOneX>
            </authEncryption>
            <OneX xmlns="http://www.microsoft.com/networking/OneX/v1">
                <cacheUserData>true</cacheUserData>
                <authMode>user</authMode>
                <singleSignOn>
                    <type>preLogon</type>
                    <maxDelay>10</maxDelay>
                    <allowAdditionalDialogs>false</allowAdditionalDialogs>
                    <userBasedVirtualLan>false</userBasedVirtualLan>
                </singleSignOn>
                <EAPConfig>
                    <EapHostConfig xmlns="http://www.microsoft.com/provisioning/EapHostConfig">
                        <EapMethod>
                            <Type xmlns="http://www.microsoft.com/provisioning/EapCommon">{eap_type_outer}</Type>
                            <VendorId xmlns="http://www.microsoft.com/provisioning/EapCommon">0</VendorId>
                            <VendorType xmlns="http://www.microsoft.com/provisioning/EapCommon">0</VendorType>
                            <AuthorId xmlns="http://www.microsoft.com/provisioning/EapCommon">0</AuthorId>
                        </EapMethod>
                        <Config xmlns="http://www.microsoft.com/provisioning/EapHostConfig">
                            <Eap xmlns="http://www.microsoft.com/provisioning/BaseEapConnectionPropertiesV1">
                                <Type>{eap_type_outer}</Type>
                                <EapType xmlns="http://www.microsoft.com/provisioning/MsPeapConnectionPropertiesV1">
                                    <ServerValidation>
                                        <DisableUserPromptForServerValidation>true</DisableUserPromptForServerValidation>
                                        <ServerNames></ServerNames>
                                        <TrustedRootCA></TrustedRootCA>
                                    </ServerValidation>
                                    <FastReconnect>true</FastReconnect>
                                    <InnerEapOptional>false</InnerEapOptional>
                                    <Eap xmlns="http://www.microsoft.com/provisioning/BaseEapConnectionPropertiesV1">
                                        <Type>{eap_type_inner}</Type>
                                        <EapType xmlns="http://www.microsoft.com/provisioning/MsChapV2ConnectionPropertiesV1">
                                            <UseWinLogonCredentials>false</UseWinLogonCredentials>
                                        </EapType>
                                    </Eap>
                                    <EnableQuarantineChecks>false</EnableQuarantineChecks>
                                    <RequireCryptoBinding>false</RequireCryptoBinding>
                                    <PeapExtensions>
                                        <PerformServerValidation xmlns="http://www.microsoft.com/provisioning/MsPeapConnectionPropertiesV2">false</PerformServerValidation>
                                        <AcceptServerName xmlns="http://www.microsoft.com/provisioning/MsPeapConnectionPropertiesV2">false</AcceptServerName>
                                    </PeapExtensions>
                                </EapType>
                            </Eap>
                        </Config>
                    </EapHostConfig>
                </EAPConfig>
            </OneX>
        </security>
    </MSM>
</WLANProfile>"""
        return profile_xml

    @staticmethod
    def add_wifi_profile(credentials: WiFiCredentials) -> Tuple[bool, str]:
        """Add WiFi profile to Windows"""
        try:
            profile_xml = WindowsWiFiManager.create_wpa2_enterprise_profile(credentials)

            temp_file = (
                Path(tempfile.gettempdir()) / WINDOWS_SETTINGS["temp_profile_name"]
            )

            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(profile_xml)

            success, stdout, stderr = run_cmd(
                [
                    "netsh",
                    "wlan",
                    "add",
                    "profile",
                    f"filename={temp_file}",
                    "user=current",
                ],
                timeout=WINDOWS_SETTINGS["netsh_timeout"],
            )

            temp_file.unlink(missing_ok=True)

            if success:
                return True, t("profile_added", ssid=WIFI_SSID)
            else:
                return False, f"Failed to add WiFi profile: {stderr}"

        except Exception as e:
            return False, f"Profile creation error: {e}"

    @staticmethod
    def connect_to_wifi_native(
        credentials: WiFiCredentials, password: str
    ) -> Tuple[bool, str]:
        """Connect to WiFi using native Windows method (Windows 11+)"""
        try:
            profile_success, profile_msg = WindowsWiFiManager.add_wifi_profile(
                credentials
            )
            if not profile_success:
                return False, t("profile_setup_failed", message=profile_msg)

            try:
                run_cmd(["netsh", "wlan", "disconnect"], timeout=5)
                time.sleep(1)
            except Exception:
                pass

            connect_cmd = [
                "netsh",
                "wlan",
                "connect",
                f"ssid={WIFI_SSID}",
                f"name={WIFI_SSID}",
            ]

            success, stdout, stderr = run_cmd(connect_cmd, timeout=WIFI_CONNECT_TIMEOUT)

            if success:
                try:
                    import threading
                    def show_credential_prompt():
                        import tkinter.messagebox as msgbox
                        time.sleep(2)
                        msgbox.showinfo(
                            "Enter Credentials",
                            f"Windows will prompt for credentials.\n\nUsername: {credentials.student_id}\nPassword: {password}\n\nEnter these when prompted."
                        )
                    
                    thread = threading.Thread(target=show_credential_prompt, daemon=True)
                    thread.start()
                except Exception:
                    pass

                for attempt in range(15):
                    time.sleep(2)
                    if WindowsWiFiManager.is_connected_to_network():
                        return True, t("connection_success")
                
                return (False, "Connection initiated. Please enter credentials when Windows prompts you.")
            else:
                return False, t("connection_failed") + f": {stderr}"

        except Exception as e:
            return False, t("connection_error", error=str(e))

    @staticmethod
    def connect_to_wifi(
        credentials: WiFiCredentials, password: str
    ) -> Tuple[bool, str]:
        """Connect to WiFi using credentials"""
        try:
            # Windows 11: Try native connection first, then fall back to traditional method
            if system_info.should_use_native_wifi_connection():
                native_success, native_msg = WindowsWiFiManager.connect_to_wifi_native(credentials, password)
                
                if native_success:
                    return True, native_msg
                
                # Native method didn't work, wait a bit then try the traditional approach
                wait_time = WINDOWS_SETTINGS.get("win11_native_wait_seconds", 15)
                time.sleep(wait_time)
                
                # Check one more time if the connection succeeded during the wait
                if WindowsWiFiManager.is_connected_to_network():
                    return True, "Connected successfully (native method)"
                
                # Fall through to traditional method below
            # Delete any old profiles first to start fresh
            try:
                delete_cmd = ["netsh", "wlan", "delete", "profile", f"name={WIFI_SSID}"]
                if is_admin():
                    delete_cmd.append("user=all")  # Remove for all users if we can
                else:
                    delete_cmd.append("user=current")
                run_cmd(delete_cmd, timeout=10)
            except Exception:
                pass  # Profile might not exist yet, that's fine

            profile_success, profile_msg = WindowsWiFiManager.add_wifi_profile(
                credentials
            )
            if not profile_success:
                return False, t("profile_setup_failed", message=profile_msg)

            # Set these profile parameters before storing credentials.
            # If you change them afterwards, Windows sometimes wipes the stored credentials.
            try:
                # Set to user auth mode
                run_cmd([
                    "netsh", "wlan", "set", "profileparameter",
                    f"name={WIFI_SSID}", "authMode=userOnly"
                ], timeout=10)
                
                # Enable auto-connect
                run_cmd([
                    "netsh", "wlan", "set", "profileparameter",
                    f"name={WIFI_SSID}", "connectionMode=auto"
                ], timeout=10)
                
                # Set connection type
                run_cmd([
                    "netsh", "wlan", "set", "profileparameter",
                    f"name={WIFI_SSID}", "connectionType=ESS"
                ], timeout=10)
            except Exception:
                pass

            # Try to store the credentials in Windows credential manager.
            # On Windows 11 22H2+ with Credential Guard enabled, this usually fails
            # silently due to security restrictions. Not much we can do about that.
            cred_stored = False
            credential_guard_active = WindowsWiFiManager.is_credential_guard_enabled()
            
            if store_windows_eap_credentials and not credential_guard_active:
                try:
                    cred_success, cred_msg = store_windows_eap_credentials(
                        WIFI_SSID, credentials.student_id, password
                    )
                    cred_stored = bool(cred_success)
                    
                    # Double-check the credentials actually stuck
                    if cred_stored and check_windows_eap_credentials:
                        time.sleep(0.5)  # Windows needs a moment to write to credential store
                        present, msg = check_windows_eap_credentials(WIFI_SSID)
                        cred_stored = bool(present)
                except Exception:
                    cred_stored = False

            # Disconnect first to start fresh
            try:
                run_cmd(["netsh", "wlan", "disconnect"], timeout=5)
                time.sleep(1)
            except Exception:
                pass  # Already disconnected, that's fine

            # Connect to the WiFi network
            connect_cmd = [
                "netsh",
                "wlan",
                "connect",
                f"ssid={WIFI_SSID}",
                f"name={WIFI_SSID}",
            ]

            success, stdout, stderr = run_cmd(connect_cmd, timeout=WIFI_CONNECT_TIMEOUT)
            
            # If we couldn't store credentials, show a popup to guide the user
            if not cred_stored or credential_guard_active:
                try:
                    import threading
                    def show_credential_prompt():
                        import tkinter.messagebox as msgbox
                        time.sleep(2)
                        msgbox.showinfo(
                            t("credentials_required"),
                            t("windows_prompt_message", username=credentials.student_id)
                        )
                    
                    thread = threading.Thread(target=show_credential_prompt, daemon=True)
                    thread.start()
                except Exception:
                    pass

            if success:
                # Wait for EAP authentication to complete
                max_wait_seconds = 30 if cred_stored else 15
                for attempt in range(max_wait_seconds // 2):
                    time.sleep(2)
                    if WindowsWiFiManager.is_connected_to_network():
                        return True, t("connection_success")
                
                # Timed out waiting for connection
                if not cred_stored or credential_guard_active:
                    msg = t("action_needed_message", ssid=WIFI_SSID)
                    if credential_guard_active:
                        msg += "\n\nNote: Windows Credential Guard is active. You'll need to enter credentials each time you connect. This is a Windows security feature."
                    else:
                        msg += " Credentials could not be stored automatically. Please enter them manually in Windows."
                    return (False, msg)
                else:
                    return (False, t("connection_pending") + " Authentication may still be in progress.")
            else:
                return False, t("connection_failed") + f": {stderr}"

        except Exception as e:
            return False, t("connection_error", error=str(e))

    @staticmethod
    def is_credential_guard_enabled() -> bool:
        """
        Check if Windows Credential Guard is active.
        When enabled, it blocks MSCHAPv2 credential caching for security.
        Common on Windows 11 22H2+ and enterprise configs.
        """
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Lsa\MSV1_0"
            )
            try:
                winreg.QueryValueEx(key, "IsolatedCredentialsRootSecret")
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception:
            return False

    @staticmethod
    def disconnect_wifi() -> Tuple[bool, str]:
        """Disconnect from current WiFi"""
        try:
            success, stdout, stderr = run_cmd(
                ["netsh", "wlan", "disconnect"], timeout=10
            )

            if success:
                return True, t("disconnected")
            else:
                return False, t("connection_failed") + f": {stderr}"

        except Exception as e:
            return False, f"Disconnect error: {e}"

    @staticmethod
    def remove_wifi_profile() -> Tuple[bool, str]:
        """Remove UNESWA WiFi profile only (leaves other WiFi profiles intact)"""
        try:
            # Clear stored EAP credentials first
            if clear_windows_eap_credentials:
                clear_windows_eap_credentials(WIFI_SSID)
            
            # Only remove the specific UNESWA WiFi profile
            delete_cmd = ["netsh", "wlan", "delete", "profile", f"name={WIFI_SSID}"]
            if is_admin():
                delete_cmd.append("user=all")
            else:
                delete_cmd.append("user=current")
            success, stdout, stderr = run_cmd(delete_cmd, timeout=10)

            if success:
                return True, t("profile_removed", ssid=WIFI_SSID)
            else:
                # Some Windows builds print errors to stdout rather than stderr
                combined = f"{stdout}\n{stderr}".lower()
                if ("not found" in combined) or ("cannot find" in combined) or ("no profiles" in combined):
                    return (
                        True,
                        t("profile_not_found", ssid=WIFI_SSID),
                    )
                # Try alternate user scope once if first attempt failed
                try:
                    alt_cmd = delete_cmd[:-1] + (["user=current"] if "user=all" in delete_cmd[-1] else ["user=all"])
                    alt_success, alt_out, alt_err = run_cmd(alt_cmd, timeout=10)
                    if alt_success:
                        return True, t("profile_removed", ssid=WIFI_SSID)
                    combined2 = f"{alt_out}\n{alt_err}".lower()
                    if ("not found" in combined2) or ("cannot find" in combined2) or ("no profiles" in combined2):
                        return (
                            True,
                            t("profile_not_found", ssid=WIFI_SSID),
                        )
                except Exception:
                    pass
                return False, f"Failed to remove UNESWA profile '{WIFI_SSID}': {stderr or stdout}"

        except Exception as e:
            return False, f"UNESWA profile removal error: {e}"

    @staticmethod
    def is_connected_to_network() -> bool:
        """Check if connected to UNESWA WiFi"""
        try:
            success, stdout, stderr = run_cmd(
                ["netsh", "wlan", "show", "interfaces"], timeout=10
            )

            if success:
                lines = stdout.lower().split("\n")
                connected = any(
                    "state" in line and "connected" in line for line in lines
                )
                uneswa_network = any(WIFI_SSID.lower() in line for line in lines)

                return connected and uneswa_network

            return False

        except Exception:
            return False

    @staticmethod
    def get_wifi_status() -> Dict[str, str]:
        """Get detailed WiFi status information"""
        try:
            success, stdout, stderr = run_cmd(
                ["netsh", "wlan", "show", "interfaces"], timeout=10
            )

            if not success:
                return {"status": "error", "message": stderr}

            status = {"status": "disconnected"}
            current_ssid = None
            state = None

            for line in stdout.split("\n"):
                line = line.strip()
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()

                    if "ssid" in key and not "bssid" in key:
                        current_ssid = value
                    elif "state" in key:
                        state = value.lower()

            if state and "connected" in state:
                if current_ssid and WIFI_SSID.lower() in current_ssid.lower():
                    status = {
                        "status": "connected",
                        "ssid": current_ssid,
                        "network_type": "UNESWA",
                    }
                else:
                    status = {
                        "status": "connected_other",
                        "ssid": current_ssid or "Unknown",
                        "network_type": "Other",
                    }

            return status

        except Exception as e:
            return {"status": "error", "message": str(e)}


class LinuxWiFiManager:
    """Linux-specific WiFi management using NetworkManager"""

    @staticmethod
    def connect_to_wifi(
        credentials: WiFiCredentials, password: str
    ) -> Tuple[bool, str]:
        """Connect to WiFi using NetworkManager"""
        try:
            # Delete any existing connection to start fresh
            LinuxWiFiManager._remove_existing_connection(WIFI_SSID)
            
            # Build the nmcli command for WPA2-Enterprise.
            # This matches what we do on Windows:
            # - Save credentials in the keyring so you don't have to re-enter them
            # - Don't validate server certificates (university network doesn't require it)
            # - Auto-connect when the network is in range
            key_mgmt = "wpa-eap" if "wpa" in (WIFI_SECURITY or "").lower() else "wpa-eap"
            eap_method = (WIFI_EAP_METHOD or "peap").lower()
            phase2_auth = (WIFI_PHASE2_AUTH or "mschapv2").lower()

            cmd = [
                "nmcli",
                "connection",
                "add",
                "type",
                "wifi",
                "con-name",
                WIFI_SSID,
                "ifname",
                "*",
                "ssid",
                WIFI_SSID,
                "wifi-sec.key-mgmt",
                key_mgmt,
                "802-1x.eap",
                eap_method,
                "802-1x.phase2-auth",
                phase2_auth,
                "802-1x.identity",
                credentials.get_username(),
                "802-1x.password",
                password,
                # Skip server cert validation (not needed for this network)
                "802-1x.system-ca-certs",
                "false",
                # Save password in keyring (0 = store it, don't prompt every time)
                "802-1x.password-flags",
                "0",
                "connection.autoconnect",
                "yes",
            ]

            success, stdout, stderr = run_cmd(cmd, timeout=WIFI_CONNECT_TIMEOUT)

            if success:
                # Connection created, now try to activate it
                activate_cmd = ["nmcli", "connection", "up", WIFI_SSID]
                activate_success, activate_stdout, activate_stderr = run_cmd(
                    activate_cmd, timeout=WIFI_CONNECT_TIMEOUT
                )
                
                if activate_success:
                    time.sleep(3)
                    if LinuxWiFiManager.is_connected_to_network():
                        return True, t("connection_success")
                    else:
                        return (
                            False,
                            "Connection created but authentication failed - check credentials",
                        )
                else:
                    if "authentication" in activate_stderr.lower():
                        return False, "Authentication failed - check credentials"
                    else:
                        return False, f"Connection activation failed: {activate_stderr}"
            else:
                if "already exists" in stderr.lower():
                    # Connection exists - delete it first to ensure fresh credentials
                    LinuxWiFiManager._remove_existing_connection(WIFI_SSID)
                    # Retry connection creation
                    success2, stdout2, stderr2 = run_cmd(cmd, timeout=WIFI_CONNECT_TIMEOUT)
                    if success2:
                        activate_cmd = ["nmcli", "connection", "up", WIFI_SSID]
                        activate_success, activate_stdout, activate_stderr = run_cmd(
                            activate_cmd, timeout=WIFI_CONNECT_TIMEOUT
                        )
                        if activate_success:
                            return True, t("connection_success")
                        else:
                            return False, f"Connection activation failed: {activate_stderr}"
                    else:
                        return False, f"Failed to recreate connection: {stderr2}"
                elif "not found" in stderr.lower():
                    return False, t("network_not_found", ssid=WIFI_SSID)
                else:
                    return False, t("connection_failed") + f": {stderr}"

        except Exception as e:
            return False, t("connection_error", error=str(e))
    
    @staticmethod
    def _remove_existing_connection(connection_name: str) -> None:
        """Delete an existing connection if found"""
        try:
            run_cmd(["nmcli", "connection", "delete", connection_name], timeout=10)
        except Exception:
            pass  # Connection doesn't exist, that's fine

    @staticmethod
    def disconnect_wifi() -> Tuple[bool, str]:
        """Disconnect from current WiFi"""
        try:
            success, stdout, stderr = run_cmd(
                ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"],
                timeout=10,
            )

            wifi_connections = []
            if success:
                for line in stdout.split("\n"):
                    if line and "wifi" in line.lower():
                        conn_name = line.split(":")[0]
                        wifi_connections.append(conn_name)

            results = []
            for conn_name in wifi_connections:
                success, stdout, stderr = run_cmd(
                    ["nmcli", "connection", "down", conn_name], timeout=10
                )

                if success:
                    results.append(f"Disconnected from {conn_name}")
                else:
                    results.append(f"Failed to disconnect {conn_name}: {stderr}")

            if results:
                return True, "; ".join(results)
            else:
                return True, "No active WiFi connections to disconnect"

        except Exception as e:
            return False, f"Disconnect error: {e}"

    @staticmethod
    def remove_wifi_profile() -> Tuple[bool, str]:
        """Remove UNESWA WiFi connection profiles only (preserves other WiFi profiles)"""
        try:
            success, stdout, stderr = run_cmd(
                ["nmcli", "-t", "-f", "NAME", "connection", "show"], timeout=10
            )

            if not success:
                return False, f"Failed to list connections: {stderr}"

            uneswa_connections = []
            for line in stdout.split("\n"):
                line = line.strip()
                if line:
                    if (
                        WIFI_SSID.lower() in line.lower()
                        or line.lower() == WIFI_SSID.lower()
                        or line.lower().startswith(WIFI_SSID.lower())
                    ):
                        uneswa_connections.append(line)

            if not uneswa_connections:
                return True, f"No UNESWA WiFi profiles found (SSID: '{WIFI_SSID}')"

            results = []
            removed_count = 0

            for conn_name in uneswa_connections:
                if WIFI_SSID.lower() not in conn_name.lower():
                    results.append(f"Skipped non-UNESWA profile: {conn_name}")
                    continue

                # Remove connection (this also removes stored credentials)
                success, stdout, stderr = run_cmd(
                    ["nmcli", "connection", "delete", conn_name], timeout=10
                )

                if success:
                    results.append(f"Removed UNESWA profile and credentials: {conn_name}")
                    removed_count += 1
                else:
                    results.append(
                        f"Failed to remove UNESWA profile {conn_name}: {stderr}"
                    )

            summary = f"Processed {len(uneswa_connections)} UNESWA profile(s), removed {removed_count}"
            full_message = f"{summary}. Details: " + "; ".join(results)

            return True, full_message

        except Exception as e:
            return False, f"UNESWA profile removal error: {e}"

    @staticmethod
    def is_connected_to_network() -> bool:
        """Check if connected to UNESWA WiFi"""
        try:
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

            if success:
                for line in stdout.split("\n"):
                    if (
                        line
                        and "wifi" in line.lower()
                        and WIFI_SSID.lower() in line.lower()
                    ):
                        return True

            return False

        except Exception:
            return False

    @staticmethod
    def get_wifi_status() -> Dict[str, str]:
        """Get detailed WiFi status information"""
        try:
            success, stdout, stderr = run_cmd(
                ["nmcli", "-t", "-f", "WIFI", "general", "status"], timeout=10
            )

            if not success:
                return {"status": "error", "message": "Failed to get WiFi status"}

            wifi_enabled = "enabled" in stdout.lower()
            if not wifi_enabled:
                return {"status": "disabled", "message": "WiFi is disabled"}

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

            if not success:
                return {"status": "disconnected", "message": "No active connections"}

            for line in stdout.split("\n"):
                if line and "wifi" in line.lower():
                    parts = line.split(":")
                    if len(parts) >= 1:
                        conn_name = parts[0]
                        if WIFI_SSID.lower() in conn_name.lower():
                            return {
                                "status": "connected",
                                "ssid": WIFI_SSID,
                                "connection_name": conn_name,
                                "network_type": "UNESWA",
                            }
                        else:
                            return {
                                "status": "connected_other",
                                "connection_name": conn_name,
                                "network_type": "Other",
                            }

            return {"status": "disconnected", "message": "Not connected to any WiFi"}

        except Exception as e:
            return {"status": "error", "message": str(e)}


class WiFiManager:
    """Cross-platform WiFi management"""

    def __init__(self):
        self.os_type = get_os_type()
        self.use_native_connection = system_info.should_use_native_wifi_connection()

        if self.os_type == "Windows":
            self.manager = WindowsWiFiManager()
        else:
            self.manager = LinuxWiFiManager()

    def connect(self, student_id: str, birthday_ddmmyy: str) -> Tuple[bool, str]:
        """Connect to UNESWA WiFi with credentials"""
        try:
            credentials = WiFiCredentials(student_id, birthday_ddmmyy)
            password = credentials.get_password()

            if len(password) != len(PASSWORD_PREFIX) + 8:
                return (
                    False,
                    "Invalid password format - expected format: UneswaDDMMYYYY",
                )

            return self.manager.connect_to_wifi(credentials, password)

        except ValueError as e:
            return False, t("credential_error", error=str(e))
        except Exception as e:
            return False, t("connection_error", error=str(e))

    def disconnect(self) -> Tuple[bool, str]:
        """Disconnect from WiFi"""
        return self.manager.disconnect_wifi()

    def remove_profile(self) -> Tuple[bool, str]:
        """Remove UNESWA WiFi profiles only (preserves other network profiles)"""
        return self.manager.remove_wifi_profile()

    def is_connected(self) -> bool:
        """Check if connected to UNESWA WiFi"""
        return self.manager.is_connected_to_network()

    def get_status(self) -> Dict[str, str]:
        """Get current WiFi connection status"""
        return self.manager.get_wifi_status()

    def is_network_available(self) -> Tuple[bool, str]:
        """Check if UNESWA WiFi network is available"""
        try:
            if self.os_type == "Windows":
                success, stdout, stderr = run_cmd(
                    ["netsh", "wlan", "show", "networks", "mode=bssid"], timeout=20
                )
                if success and WIFI_SSID.lower() in stdout.lower():
                    return True, f"Network '{WIFI_SSID}' is available"

            else:
                success, stdout, stderr = run_cmd(
                    ["nmcli", "dev", "wifi", "list", "--rescan", "yes"], timeout=20
                )

                if success and WIFI_SSID in stdout:
                    return True, f"Network '{WIFI_SSID}' is available"

            if success:
                return True, "Network scanning completed"
            else:
                return False, f"Network scan failed: {stderr}"

        except Exception as e:
            return False, f"Network availability check failed: {e}"


# Global WiFi manager instance
wifi_manager = WiFiManager()


# Convenience functions
def connect_to_university_wifi(
    student_id: str, birthday_ddmmyy: str
) -> Tuple[bool, str]:
    """Connect to UNESWA WiFi"""
    return wifi_manager.connect(student_id, birthday_ddmmyy)


def disconnect_from_wifi() -> Tuple[bool, str]:
    """Disconnect from WiFi"""
    return wifi_manager.disconnect()


def is_connected_to_university_wifi() -> bool:
    """Check if connected to UNESWA WiFi"""
    return wifi_manager.is_connected()


def get_wifi_connection_status() -> Dict[str, str]:
    """Get WiFi connection status"""
    return wifi_manager.get_status()


def validate_wifi_credentials(
    student_id: str, birthday_ddmmyy: str
) -> Tuple[bool, str]:
    """Validate WiFi credentials format"""
    try:
        credentials = WiFiCredentials(student_id, birthday_ddmmyy)
        password = credentials.get_password()

        if len(password) == EXPECTED_PASSWORD_LENGTH:
            return True, t("credentials_valid")
        else:
            return False, t("credentials_invalid")

    except Exception as e:
        return False, str(e)
