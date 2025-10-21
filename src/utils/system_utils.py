#!/usr/bin/env python3
"""
UNESWA WiFi AutoConnect - System Utilities
ICT Society Initiative - University of Eswatini

System utilities for detecting the OS, checking privileges, and running platform-specific commands.
"""

import os
import sys
import platform
import subprocess
import ctypes
from pathlib import Path
from typing import Dict, Optional, Tuple, List

# Windows privilege check
if platform.system() == "Windows":
    import ctypes.wintypes


class SystemInfo:
    """System information and utilities"""

    def __init__(self):
        self.os_type = platform.system()
        self.os_release = platform.release()
        self.os_version = platform.version()
        self.architecture = platform.architecture()[0]
        self.machine = platform.machine()
        self._distro_info = None
        self._windows_build = None

    def is_windows(self) -> bool:
        return self.os_type == "Windows"

    def is_linux(self) -> bool:
        return self.os_type == "Linux"

    def is_macos(self) -> bool:
        return self.os_type == "Darwin"

    def get_linux_distro(self) -> Optional[Dict[str, str]]:
        """Get Linux distribution information"""
        if not self.is_linux() or self._distro_info:
            return self._distro_info

        try:
            if os.path.exists("/etc/os-release"):
                distro_info = {}
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            distro_info[key] = value.strip('"')

                self._distro_info = {
                    "id": distro_info.get("ID", "unknown").lower(),
                    "name": distro_info.get("NAME", "Unknown"),
                    "version": distro_info.get("VERSION_ID", ""),
                    "pretty_name": distro_info.get("PRETTY_NAME", "Unknown Linux"),
                }
                return self._distro_info

            distro_files = [
                ("/etc/debian_version", "debian"),
                ("/etc/redhat-release", "rhel"),
                ("/etc/fedora-release", "fedora"),
                ("/etc/arch-release", "arch"),
                ("/etc/manjaro-release", "manjaro"),
            ]

            for file_path, distro_id in distro_files:
                if os.path.exists(file_path):
                    with open(file_path, "r") as f:
                        content = f.read().strip()

                    self._distro_info = {
                        "id": distro_id,
                        "name": content,
                        "version": "",
                        "pretty_name": content,
                    }
                    return self._distro_info

        except Exception:
            pass

        self._distro_info = {
            "id": "unknown",
            "name": "Unknown Linux",
            "version": "",
            "pretty_name": "Unknown Linux Distribution",
        }
        return self._distro_info

    def get_distro_id(self) -> str:
        """Get simple distro ID (ubuntu, fedora, arch, etc.)"""
        distro = self.get_linux_distro()
        return distro["id"] if distro else "unknown"

    def is_supported_distro(self) -> bool:
        """Check if current distro is supported"""
        if not self.is_linux():
            return self.is_windows()  # Windows is supported

        supported_distros = [
            "ubuntu",
            "debian",
            "arch",
            "manjaro",
            "fedora",
            "centos",
            "rhel",
            "opensuse",
        ]
        return self.get_distro_id() in supported_distros

    def get_windows_build_number(self) -> Optional[int]:
        """Get Windows build number"""
        if not self.is_windows():
            return None
        
        if self._windows_build is not None:
            return self._windows_build
        
        try:
            version_str = platform.version()
            parts = version_str.split('.')
            if len(parts) >= 3:
                self._windows_build = int(parts[2])
                return self._windows_build
        except Exception:
            pass
        
        return None
    
    def is_windows_11_or_newer(self) -> bool:
        """Check if running Windows 11 or newer (build 22000+)"""
        if not self.is_windows():
            return False
        
        build = self.get_windows_build_number()
        if build is None:
            return False
        
        return build >= 22000
    
    def should_use_native_wifi_connection(self) -> bool:
        """Determine if native Windows WiFi connection should be used"""
        if not self.is_windows():
            return False
        
        return self.is_windows_11_or_newer()

    def get_system_summary(self) -> str:
        """Get human-readable system summary"""
        if self.is_windows():
            summary = f"Windows {self.os_release} ({self.architecture})"
            build = self.get_windows_build_number()
            if build:
                summary += f" Build {build}"
            return summary
        elif self.is_linux():
            distro = self.get_linux_distro()
            return distro["pretty_name"] if distro else f"Linux ({self.architecture})"
        else:
            return f"{self.os_type} {self.os_release} ({self.architecture})"


class PrivilegeManager:
    """Handle privilege checking and elevation"""

    @staticmethod
    def is_admin() -> bool:
        """Check if running with administrator/root privileges"""
        try:
            if platform.system() == "Windows":
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except Exception:
            return False

    @staticmethod
    def can_modify_system() -> bool:
        """Check if we can modify system settings"""
        if PrivilegeManager.is_admin():
            return True

        if platform.system() == "Windows":
            try:
                import winreg

                test_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    "Software",
                    0,
                    winreg.KEY_READ | winreg.KEY_WRITE,
                )
                winreg.CloseKey(test_key)
                return True
            except Exception:
                return False
        else:
            # On Linux, check if we can write to user config files
            home = Path.home()
            return os.access(home, os.W_OK)

    @staticmethod
    def get_privilege_status() -> Tuple[bool, str]:
        """Get privilege status with explanation"""
        if PrivilegeManager.is_admin():
            return True, "Running with administrator privileges"

        if PrivilegeManager.can_modify_system():
            return True, "Can modify user-level network settings"

        return False, "Insufficient privileges for network configuration"


class ProcessManager:
    """Process and command execution utilities"""

    @staticmethod
    def run_command(
        cmd: List[str], timeout: int = 30, shell: bool = False
    ) -> Tuple[bool, str, str]:
        """
        Run a command and return success, stdout, stderr
        Returns: (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=shell,
                check=False,
            )

            success = result.returncode == 0
            return success, result.stdout.strip(), result.stderr.strip()

        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", f"Command execution failed: {e}"

    @staticmethod
    def is_command_available(command: str) -> bool:
        """Check if a command is available in PATH"""
        try:
            subprocess.run(
                ["which" if platform.system() != "Windows" else "where", command],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def get_available_network_tools() -> Dict[str, bool]:
        """Check availability of network management tools"""
        tools = {}

        if platform.system() == "Windows":
            tools["netsh"] = ProcessManager.is_command_available("netsh")
            tools["powershell"] = ProcessManager.is_command_available("powershell")
        else:
            tools["nmcli"] = ProcessManager.is_command_available("nmcli")
            tools["iwconfig"] = ProcessManager.is_command_available("iwconfig")
            tools["wpa_supplicant"] = ProcessManager.is_command_available(
                "wpa_supplicant"
            )
            tools["systemctl"] = ProcessManager.is_command_available("systemctl")

        return tools


class PathManager:
    """Path and file system utilities"""

    @staticmethod
    def get_config_dir() -> Path:
        """Get user configuration directory"""
        if platform.system() == "Windows":
            return Path(os.environ.get("APPDATA", "")) / "UNESWAWiFi"
        else:
            return Path.home() / ".config" / "uneswa-wifi"

    @staticmethod
    def get_temp_dir() -> Path:
        """Get temporary directory for app files"""
        import tempfile

        temp_base = Path(tempfile.gettempdir())
        temp_dir = temp_base / "uneswa-wifi"
        temp_dir.mkdir(exist_ok=True)
        return temp_dir

    @staticmethod
    def ensure_directory(path: Path) -> bool:
        """Ensure directory exists, create if needed"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    @staticmethod
    def safe_write_file(path: Path, content: str, backup: bool = True) -> bool:
        """Safely write to file with optional backup"""
        try:
            if backup and path.exists():
                backup_path = path.with_suffix(path.suffix + ".backup")
                path.rename(backup_path)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return True
        except Exception:
            return False


# Global system info instance
system_info = SystemInfo()
privilege_manager = PrivilegeManager()
process_manager = ProcessManager()
path_manager = PathManager()


# Convenience functions
def get_os_type() -> str:
    return system_info.os_type


def get_distro_id() -> str:
    return system_info.get_distro_id()


def is_admin() -> bool:
    return privilege_manager.is_admin()


def can_configure_network() -> bool:
    return privilege_manager.can_modify_system()


def run_cmd(cmd: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
    return process_manager.run_command(cmd, timeout)


def request_admin_elevation() -> bool:
    """
    Request admin elevation on Windows via UAC prompt.
    Returns True if already admin or elevation succeeded, False otherwise.
    """
    if platform.system() != "Windows":
        return True
    
    if is_admin():
        return True
    
    try:
        import ctypes
        import sys
        
        # Re-run the script with admin rights
        script = sys.argv[0]
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        
        # If ShellExecuteW returns > 32, it succeeded
        if ret > 32:
            # The elevated process is now running, exit this one
            sys.exit(0)
        else:
            return False
    except Exception:
        return False
