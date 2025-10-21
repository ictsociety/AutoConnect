#!/usr/bin/env python3
"""
UNESWA WiFi AutoConnect - Proxy Manager
ICT Society Initiative - University of Eswatini

Manages proxy configuration across different platforms.
On Windows: Registry settings for IE/Edge and WinHTTP for system services.
On Linux: Environment variables, shell configs, and distro-specific package manager settings.
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile
import shutil

if platform.system() == "Windows":
    import winreg

from src.config.settings import (
    PROXY_HOST,
    PROXY_PORT,
    PROXY_URL,
    LINUX_SETTINGS,
    WINDOWS_SETTINGS,
    PROXY_PAC_URL,
)
from src.utils.system_utils import (
    get_os_type,
    get_distro_id,
    is_admin,
    run_cmd,
    PathManager,
)


class ProxyConfigError(Exception):
    """Proxy configuration errors"""

    pass


class WindowsProxyManager:
    """Windows-specific proxy management via registry"""

    @staticmethod
    def enable_proxy() -> Tuple[bool, str]:
        """Enable manual proxy in Windows registry"""
        try:
            # Open the Internet Settings key in the registry
            reg_path = WINDOWS_SETTINGS["registry_path"]
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_ALL_ACCESS
            )

            # Set proxy server
            proxy_server = f"{PROXY_HOST}:{PROXY_PORT}"
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_server)

            # Turn on the proxy (1 = enabled, 0 = disabled)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)

            # Clear any auto-config URL so we use the manual proxy instead
            try:
                winreg.DeleteValue(key, "AutoConfigURL")
            except FileNotFoundError:
                pass  # Not set anyway, no problem

            winreg.SetValueEx(key, "AutoDetect", 0, winreg.REG_DWORD, 0)

            winreg.CloseKey(key)

            # Tell Windows to reload the proxy settings
            import ctypes

            ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)  # Refresh settings
            ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)  # Notify of changes

            extra = ""
            if WINDOWS_SETTINGS.get("configure_winhttp", False):
                ok, _, err = run_cmd(["netsh", "winhttp", "set", "proxy", proxy_server], timeout=10)
                if ok:
                    extra = " + WinHTTP set"
                else:
                    hint = " (run as Administrator to configure CLI/system services)"
                    extra = f" + WinHTTP failed: {err}{hint}"

            return True, f"Windows proxy enabled: {proxy_server}" + extra

        except Exception as e:
            return False, f"Failed to enable Windows proxy: {e}"

    @staticmethod
    def enable_pac() -> Tuple[bool, str]:
        """Enable PAC proxy in Windows registry"""
        try:
            reg_path = WINDOWS_SETTINGS["registry_path"]
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_ALL_ACCESS
            )

            winreg.SetValueEx(key, "AutoConfigURL", 0, winreg.REG_SZ, PROXY_PAC_URL)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            try:
                winreg.DeleteValue(key, "ProxyServer")
            except FileNotFoundError:
                pass

            winreg.SetValueEx(key, "AutoDetect", 0, winreg.REG_DWORD, 1)

            winreg.CloseKey(key)

            import ctypes
            ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
            ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)

            # Also configure WinHTTP if enabled (used by system services and some CLI tools)
            extra = ""
            if WINDOWS_SETTINGS.get("configure_winhttp", False):
                ok, _, err = run_cmd(["netsh", "winhttp", "set", "proxy", f"{PROXY_HOST}:{PROXY_PORT}"], timeout=10)
                if ok:
                    extra = " + WinHTTP set"
                else:
                    hint = " (run as Administrator to configure CLI/system services)"
                    extra = f" + WinHTTP failed: {err}{hint}"

            return True, f"PAC proxy enabled: {PROXY_PAC_URL}" + extra

        except Exception as e:
            return False, f"Failed to enable PAC proxy: {e}"

    @staticmethod
    def disable_proxy() -> Tuple[bool, str]:
        """Disable proxy in Windows registry"""
        try:
            reg_path = WINDOWS_SETTINGS["registry_path"]
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_ALL_ACCESS
            )

            # Disable proxy
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)

            # Clear proxy server setting
            try:
                winreg.DeleteValue(key, "ProxyServer")
            except FileNotFoundError:
                pass

            # Clear PAC setting if present
            try:
                winreg.DeleteValue(key, "AutoConfigURL")
            except FileNotFoundError:
                pass

            winreg.CloseKey(key)

            # Refresh system proxy settings
            import ctypes

            ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
            ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)

            extra = ""
            if WINDOWS_SETTINGS.get("configure_winhttp", False):
                ok, _, err = run_cmd(["netsh", "winhttp", "reset", "proxy"], timeout=10)
                extra = " + WinHTTP reset" if ok else f" + WinHTTP reset failed: {err}"

            return True, "Windows proxy disabled" + extra

        except Exception as e:
            return False, f"Failed to disable Windows proxy: {e}"

    @staticmethod
    def get_proxy_status() -> Tuple[bool, Dict[str, str]]:
        """Get current Windows proxy status"""
        try:
            reg_path = WINDOWS_SETTINGS["registry_path"]
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)

            proxy_enabled = False
            proxy_server = ""
            pac_url = ""

            try:
                proxy_enable_value, _ = winreg.QueryValueEx(key, "ProxyEnable")
                proxy_enabled = bool(proxy_enable_value)
            except FileNotFoundError:
                pass

            try:
                proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
            except FileNotFoundError:
                pass

            try:
                pac_url, _ = winreg.QueryValueEx(key, "AutoConfigURL")
            except FileNotFoundError:
                pac_url = ""

            winreg.CloseKey(key)

            pac_active = bool(pac_url)
            pac_matches = pac_active and (PROXY_PAC_URL.lower() == str(pac_url).lower())
            is_uneswa_proxy = (PROXY_HOST in proxy_server and proxy_enabled) or pac_matches

            return is_uneswa_proxy, {
                "enabled": proxy_enabled,
                "server": proxy_server,
                "pac_url": pac_url,
                "pac_active": pac_active,
                "is_uneswa": is_uneswa_proxy,
            }

        except Exception as e:
            return False, {"error": str(e)}


class LinuxProxyManager:
    """Linux-specific proxy management via environment variables and configs"""

    @staticmethod
    def _get_shell_files() -> List[Path]:
        """Get list of shell configuration files to modify"""
        shell_files = []
        home = Path.home()

        for shell_file in LINUX_SETTINGS["shell_files"]:
            if shell_file.startswith("~"):
                file_path = home / shell_file[2:]  # Remove ~/
            else:
                file_path = Path(shell_file)

            if file_path.exists() or shell_file in ["~/.bashrc", "~/.zshrc"]:
                shell_files.append(file_path)

        return shell_files

    @staticmethod
    def _add_proxy_to_file(file_path: Path, backup: bool = True) -> bool:
        """Add proxy exports to a shell configuration file"""
        try:
            # Read what's already in the file
            content = ""
            if file_path.exists():
                with open(file_path, "r") as f:
                    content = f.read()

                # Make a backup before we change anything
                if backup:
                    backup_path = file_path.with_suffix(
                        file_path.suffix + ".uneswa_backup"
                    )
                    shutil.copy2(file_path, backup_path)

            # If we've already added proxy settings before, remove them first
            # so we don't end up with duplicates
            if "# UNESWA WiFi AutoConnect proxy settings" in content:
                # Strip out the old block
                lines = content.split("\n")
                new_lines = []
                skip_until_end = False

                for line in lines:
                    if "# UNESWA WiFi AutoConnect proxy settings" in line:
                        skip_until_end = True
                    elif (
                        skip_until_end
                        and line.strip()
                        and not line.startswith("#")
                        and not line.startswith("export")
                    ):
                        skip_until_end = False
                        new_lines.append(line)
                    elif not skip_until_end:
                        new_lines.append(line)

                content = "\n".join(new_lines)

            # Add new proxy settings
            proxy_block = "\n\n# UNESWA WiFi AutoConnect proxy settings\n"
            proxy_block += "# Proxy settings block managed by UNESWA WiFi AutoConnect\n"

            for export_line in LINUX_SETTINGS["proxy_exports"]:
                proxy_block += f"{export_line}\n"

            proxy_block += "# End UNESWA proxy settings\n"

            # Write updated content
            with open(file_path, "w") as f:
                f.write(content + proxy_block)

            return True

        except Exception:
            return False

    @staticmethod
    def _remove_proxy_from_file(file_path: Path) -> bool:
        """Remove proxy exports from shell configuration file"""
        try:
            if not file_path.exists():
                return True

            with open(file_path, "r") as f:
                content = f.read()

            if "# UNESWA WiFi AutoConnect proxy settings" not in content:
                return True  # Nothing to remove

            # Remove UNESWA proxy block
            lines = content.split("\n")
            new_lines = []
            skip_block = False

            for line in lines:
                if "# UNESWA WiFi AutoConnect proxy settings" in line:
                    skip_block = True
                elif "# End UNESWA proxy settings" in line:
                    skip_block = False
                elif not skip_block:
                    new_lines.append(line)

            # Write updated content
            with open(file_path, "w") as f:
                f.write("\n".join(new_lines))

            return True

        except Exception:
            return False

    @staticmethod
    def _configure_fedora_dnf() -> Tuple[bool, str]:
        """Configure DNF proxy for Fedora-based distros"""
        try:
            dnf_config = Path(
                LINUX_SETTINGS["distro_configs"]["fedora"]["dnf_config_file"]
            )
            proxy_line = LINUX_SETTINGS["distro_configs"]["fedora"]["dnf_proxy_line"]

            if not dnf_config.exists():
                return False, "DNF configuration file not found"

            # Read current config
            with open(dnf_config, "r") as f:
                lines = f.readlines()

            # Remove existing proxy lines
            lines = [line for line in lines if not line.strip().startswith("proxy=")]

            # Add our proxy line
            lines.append(f"\n{proxy_line}\n")

            # Write back (requires elevation)
            temp_file = Path(tempfile.mktemp())
            with open(temp_file, "w") as f:
                f.writelines(lines)

            success, stdout, stderr = run_cmd(
                ["pkexec", "cp", str(temp_file), str(dnf_config)], timeout=10
            )

            # Cleanup temp file
            temp_file.unlink(missing_ok=True)

            if success:
                return True, "DNF proxy configured successfully"
            else:
                return False, f"Failed to update DNF config: {stderr}"

        except Exception as e:
            return False, f"DNF configuration error: {e}"

    @staticmethod
    def _configure_gsettings() -> Tuple[bool, str]:
        """Configure GNOME proxy settings via gsettings (if available)"""
        try:
            ok, _, _ = run_cmd(["which", "gsettings"], timeout=5)
            if not ok:
                return False, "gsettings not available"

            # Mode manual and set hosts/ports
            cmds = [
                ["gsettings", "set", "org.gnome.system.proxy", "mode", "manual"],
                ["gsettings", "set", "org.gnome.system.proxy.http", "host", PROXY_HOST],
                ["gsettings", "set", "org.gnome.system.proxy.http", "port", str(PROXY_PORT)],
                ["gsettings", "set", "org.gnome.system.proxy.https", "host", PROXY_HOST],
                ["gsettings", "set", "org.gnome.system.proxy.https", "port", str(PROXY_PORT)],
            ]
            for cmd in cmds:
                run_cmd(cmd, timeout=5)
            return True, "GNOME proxy configured"
        except Exception as e:
            return False, f"GNOME config error: {e}"

    @staticmethod
    def _remove_gsettings() -> Tuple[bool, str]:
        """Disable GNOME proxy via gsettings (if available)"""
        try:
            ok, _, _ = run_cmd(["which", "gsettings"], timeout=5)
            if not ok:
                return False, "gsettings not available"
            run_cmd(["gsettings", "set", "org.gnome.system.proxy", "mode", "none"], timeout=5)
            return True, "GNOME proxy disabled"
        except Exception as e:
            return False, f"GNOME disable error: {e}"

    @staticmethod
    def _configure_kde() -> Tuple[bool, str]:
        """Configure KDE proxy settings via kwriteconfig5 (if available)"""
        try:
            ok, _, _ = run_cmd(["which", "kwriteconfig5"], timeout=5)
            if not ok:
                return False, "kwriteconfig5 not available"
            proxy_url = f"http://{PROXY_HOST}:{PROXY_PORT}"
            cmds = [
                [
                    "kwriteconfig5",
                    "--file",
                    "kioslaverc",
                    "--group",
                    "Proxy Settings",
                    "--key",
                    "ProxyType",
                    "1",
                ],
                [
                    "kwriteconfig5",
                    "--file",
                    "kioslaverc",
                    "--group",
                    "Proxy Settings",
                    "--key",
                    "httpProxy",
                    proxy_url,
                ],
                [
                    "kwriteconfig5",
                    "--file",
                    "kioslaverc",
                    "--group",
                    "Proxy Settings",
                    "--key",
                    "httpsProxy",
                    proxy_url,
                ],
            ]
            for cmd in cmds:
                run_cmd(cmd, timeout=5)
            return True, "KDE proxy configured"
        except Exception as e:
            return False, f"KDE config error: {e}"

    @staticmethod
    def _remove_kde() -> Tuple[bool, str]:
        """Disable KDE proxy via kwriteconfig5 (if available)"""
        try:
            ok, _, _ = run_cmd(["which", "kwriteconfig5"], timeout=5)
            if not ok:
                return False, "kwriteconfig5 not available"
            cmds = [
                [
                    "kwriteconfig5",
                    "--file",
                    "kioslaverc",
                    "--group",
                    "Proxy Settings",
                    "--key",
                    "ProxyType",
                    "0",
                ],
                [
                    "kwriteconfig5",
                    "--file",
                    "kioslaverc",
                    "--group",
                    "Proxy Settings",
                    "--key",
                    "httpProxy",
                    "",
                ],
                [
                    "kwriteconfig5",
                    "--file",
                    "kioslaverc",
                    "--group",
                    "Proxy Settings",
                    "--key",
                    "httpsProxy",
                    "",
                ],
            ]
            for cmd in cmds:
                run_cmd(cmd, timeout=5)
            return True, "KDE proxy disabled"
        except Exception as e:
            return False, f"KDE disable error: {e}"

    @staticmethod
    def _remove_fedora_dnf_proxy() -> Tuple[bool, str]:
        """Remove DNF proxy configuration"""
        try:
            dnf_config = Path(
                LINUX_SETTINGS["distro_configs"]["fedora"]["dnf_config_file"]
            )

            if not dnf_config.exists():
                return True, "DNF config file doesn't exist"

            # Read and filter out proxy lines
            with open(dnf_config, "r") as f:
                lines = f.readlines()

            # Remove proxy lines
            filtered_lines = [
                line for line in lines if not line.strip().startswith("proxy=")
            ]

            # Write back (requires elevation)
            temp_file = Path(tempfile.mktemp())
            with open(temp_file, "w") as f:
                f.writelines(filtered_lines)

            success, stdout, stderr = run_cmd(
                ["pkexec", "cp", str(temp_file), str(dnf_config)], timeout=10
            )

            temp_file.unlink(missing_ok=True)

            if success:
                return True, "DNF proxy configuration removed"
            else:
                return False, f"Failed to update DNF config: {stderr}"

        except Exception as e:
            return False, f"DNF proxy removal error: {e}"

    @staticmethod
    def enable_proxy() -> Tuple[bool, str]:
        """Enable proxy on Linux system"""
        distro_id = get_distro_id()
        results = []

        # Set environment variables for current session
        for export_line in LINUX_SETTINGS["proxy_exports"]:
            var_assignment = export_line.replace("export ", "")
            var_name, var_value = var_assignment.split("=", 1)
            var_value = var_value.strip("'\"")
            os.environ[var_name] = var_value

        # Configure shell files
        shell_files = LinuxProxyManager._get_shell_files()
        for shell_file in shell_files:
            if LinuxProxyManager._add_proxy_to_file(shell_file):
                results.append(f"Updated {shell_file.name}")
            else:
                results.append(f"Failed to update {shell_file.name}")

        # Handle distro-specific configuration
        if distro_id in ["fedora", "centos", "rhel"]:
            dnf_success, dnf_message = LinuxProxyManager._configure_fedora_dnf()
            results.append(dnf_message)

        # Desktop environment integrations (best-effort)
        gset_ok, gset_msg = LinuxProxyManager._configure_gsettings()
        if gset_ok:
            results.append(gset_msg)
        kde_ok, kde_msg = LinuxProxyManager._configure_kde()
        if kde_ok:
            results.append(kde_msg)

        # Try to restart NetworkManager if available
        if LinuxProxyManager._restart_networkmanager():
            results.append("NetworkManager restarted")

        success = len([r for r in results if "Failed" not in r]) > 0
        return success, "; ".join(results)

    @staticmethod
    def disable_proxy() -> Tuple[bool, str]:
        """Disable proxy on Linux system"""
        distro_id = get_distro_id()
        results = []

        # Clear environment variables
        proxy_vars = [
            "http_proxy",
            "https_proxy",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ftp_proxy",
            "FTP_PROXY",
        ]
        for var in proxy_vars:
            os.environ.pop(var, None)

        # Remove from shell files
        shell_files = LinuxProxyManager._get_shell_files()
        for shell_file in shell_files:
            if LinuxProxyManager._remove_proxy_from_file(shell_file):
                results.append(f"Cleaned {shell_file.name}")
            else:
                results.append(f"Failed to clean {shell_file.name}")

        # Handle distro-specific cleanup
        if distro_id in ["fedora", "centos", "rhel"]:
            dnf_success, dnf_message = LinuxProxyManager._remove_fedora_dnf_proxy()
            results.append(dnf_message)

        # Desktop integrations
        gset_off, gset_msg = LinuxProxyManager._remove_gsettings()
        if gset_off:
            results.append(gset_msg)
        kde_off, kde_msg = LinuxProxyManager._remove_kde()
        if kde_off:
            results.append(kde_msg)

        # Restart NetworkManager
        if LinuxProxyManager._restart_networkmanager():
            results.append("NetworkManager restarted")

        return True, "; ".join(results)

    @staticmethod
    def _restart_networkmanager() -> bool:
        """Attempt to restart NetworkManager service"""
        try:
            success, stdout, stderr = run_cmd(
                ["pkexec", "systemctl", "restart", "NetworkManager"], timeout=15
            )
            return success
        except Exception:
            return False

    @staticmethod
    def get_proxy_status() -> Tuple[bool, Dict[str, str]]:
        """Get current Linux proxy status"""
        proxy_vars = {
            "http_proxy": os.environ.get("http_proxy", ""),
            "https_proxy": os.environ.get("https_proxy", ""),
            "HTTP_PROXY": os.environ.get("HTTP_PROXY", ""),
            "HTTPS_PROXY": os.environ.get("HTTPS_PROXY", ""),
        }

        # Check if UNESWA proxy is configured
        is_configured = any(
            PROXY_HOST in proxy_url for proxy_url in proxy_vars.values()
        )

        status = {
            "configured": is_configured,
            "proxy_vars": proxy_vars,
        }

        return is_configured, status


class ProxyManager:
    """Cross-platform proxy management"""

    def __init__(self):
        self.os_type = get_os_type()

        if self.os_type == "Windows":
            self.manager = WindowsProxyManager()
        else:
            self.manager = LinuxProxyManager()

    def enable_proxy(self) -> Tuple[bool, str]:
        """Enable university proxy configuration"""
        return self.manager.enable_proxy()

    def disable_proxy(self) -> Tuple[bool, str]:
        """Disable proxy configuration"""
        return self.manager.disable_proxy()

    def is_proxy_configured(self) -> bool:
        """Check if proxy is currently configured"""
        is_configured, _ = self.manager.get_proxy_status()
        return is_configured

    def get_proxy_status(self) -> Dict[str, any]:
        """Get detailed proxy status information"""
        is_configured, status = self.manager.get_proxy_status()

        return {
            "configured": is_configured,
            "proxy_url": PROXY_URL,
            "os_type": self.os_type,
            "details": status,
        }

    def test_proxy_connectivity(self) -> Tuple[bool, str]:
        """Test if proxy is working for internet access"""
        try:
            import requests

            # Test with our proxy
            proxies = {"http": PROXY_URL, "https": PROXY_URL}

            response = requests.get(
                "http://httpbin.org/ip", proxies=proxies, timeout=10
            )

            if response.status_code == 200:
                return True, "Proxy connectivity test successful"
            else:
                return False, f"Proxy test failed with status {response.status_code}"

        except Exception as e:
            return False, f"Proxy connectivity test failed: {e}"


# Global proxy manager instance
proxy_manager = ProxyManager()


# Convenience functions
def enable_university_proxy() -> Tuple[bool, str]:
    """Enable UNESWA proxy configuration"""
    return proxy_manager.enable_proxy()


def disable_university_proxy() -> Tuple[bool, str]:
    """Disable proxy configuration"""
    return proxy_manager.disable_proxy()


def is_university_proxy_configured() -> bool:
    """Check if UNESWA proxy is configured"""
    return proxy_manager.is_proxy_configured()


def get_proxy_config_status() -> Dict[str, any]:
    """Get current proxy configuration status"""
    return proxy_manager.get_proxy_status()
