#!/usr/bin/env python3
"""
UNESWA WiFi AutoConnect - Main Application Entry Point
ICT Society Initiative - University of Eswatini

Entry point for the application. Checks system requirements, validates dependencies,
and starts up the GUI.
"""

import sys
import os
import argparse
import platform
from pathlib import Path

src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

try:
    from src.config import APP_NAME, VERSION, DEBUG_MODE
    from src.utils import (
        system_info,
        is_admin,
        can_configure_network,
        get_os_type,
        request_admin_elevation,
    )
    from src.ui import main as ui_main
    from src.network import network_manager

except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


def check_system_requirements() -> tuple[bool, list[str]]:
    """
    Check system requirements and compatibility

    Returns:
        tuple: (requirements_met, issues_list)
    """
    issues: list[str] = []

    if sys.version_info < (3, 8):
        issues.append(
            f"Python 3.8+ required, found {sys.version_info.major}.{sys.version_info.minor}"
        )

    if not system_info.is_supported_distro():
        issues.append(f"Unsupported OS: {system_info.get_system_summary()}")

    if not can_configure_network():
        issues.append("Insufficient privileges for network configuration")

    if get_os_type() == "Windows":
        from src.utils import process_manager

        tools = process_manager.get_available_network_tools()

        if not tools.get("netsh", False):
            issues.append("Windows netsh command not available")
    else:
        from src.utils import process_manager

        tools = process_manager.get_available_network_tools()

        if not tools.get("nmcli", False) and not tools.get("iwconfig", False):
            issues.append(
                "No suitable network management tools found (nmcli or iwconfig)"
            )

    return len(issues) == 0, issues


def check_dependencies() -> tuple[bool, list[str]]:
    """
    Check if all required dependencies are available

    Returns:
        tuple: (dependencies_met, missing_list)
    """
    required_modules = [
        "customtkinter",
        "requests",
        "psutil",
    ]

    # Platform-specific requirements
    if platform.system() == "Windows":
        required_modules.append("winreg")  # Built-in but check anyway

    missing: list[str] = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)

    return len(missing) == 0, missing


def print_system_info():
    """Print system information for debugging"""
    print(f"System: {system_info.get_system_summary()}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Privileges: {'Administrator' if is_admin() else 'Standard User'}")
    print(f"Network Config: {'Available' if can_configure_network() else 'Limited'}")

    if system_info.is_linux():
        distro_info = system_info.get_linux_distro()
        if distro_info:
            print(f"Distribution: {distro_info['pretty_name']}")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
    description="University WiFi AutoConnect - Network setup helper for UNESWA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Start GUI application
  %(prog)s --cli              # Command-line interface (future feature)
  %(prog)s --check            # Check system compatibility
  %(prog)s --version          # Show version information
        """,
    )

    parser.add_argument("--version", action="version", version=f"{APP_NAME} v{VERSION}")

    parser.add_argument(
        "--check", action="store_true", help="Check system requirements and exit"
    )

    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode with verbose logging"
    )

    parser.add_argument(
        "--no-gui", action="store_true", help="Run in console mode (future feature)"
    )

    parser.add_argument(
        "--system-info", action="store_true", help="Display system information and exit"
    )

    return parser


def handle_check_mode():
    """Handle system requirements check mode"""
    print(f"Checking system requirements for {APP_NAME} v{VERSION}...")
    print()

    print_system_info()
    print()

    print("System requirements check:")
    req_ok, req_issues = check_system_requirements()

    if req_ok:
        print("System requirements: PASSED")
    else:
        print("System requirements: FAILED")
        for issue in req_issues:
            print(f"   • {issue}")
    print()

    print("Dependency check:")
    dep_ok, missing_deps = check_dependencies()

    if dep_ok:
        print("Dependencies: PASSED")
    else:
        print("Dependencies: FAILED")
        print("   Missing modules:")
        for dep in missing_deps:
            print(f"   • {dep}")
        print("\n   Install missing dependencies:")
        print("   pip install -r requirements.txt")
    print()

    print("Network tools check:")
    from src.utils import process_manager

    tools = process_manager.get_available_network_tools()

    for tool, available in tools.items():
        status = "OK" if available else "MISSING"
        print(f"   {tool}: {status}")
    print()

    overall_ok = req_ok and dep_ok
    if overall_ok:
        print("System is ready to run UNESWA WiFi AutoConnect!")
        return 0
    else:
        print("System is not ready. Please fix the issues above.")
        return 1


def handle_system_info_mode():
    """Handle system information display mode"""
    print(f"{APP_NAME} v{VERSION} - System information")
    print("=" * 60)
    print_system_info()

    print("\nNetwork status:")
    status = network_manager.get_connection_status()

    print(f"   WiFi connected: {'Yes' if status['wifi_connected'] else 'No'}")
    print(f"   Proxy configured: {'Yes' if status['proxy_configured'] else 'No'}")

    if status["available_campuses"]:
        print(f"   Available Campuses: {', '.join(status['available_campuses'])}")
    else:
        print("   Available Campuses: None detected")

    print("\nApplication paths:")
    from src.config.settings import APP_DIR, LOGS_DIR, TEMP_DIR

    print(f"   App Directory: {APP_DIR}")
    print(f"   Logs Directory: {LOGS_DIR}")
    print(f"   Temp Directory: {TEMP_DIR}")

    return 0


def main():
    """Main application entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()

    if args.system_info:
        return handle_system_info_mode()

    if args.check:
        return handle_check_mode()

    if args.debug:
        os.environ["UNESWA_DEBUG"] = "true"
        print("Debug mode enabled")

    # On Windows, require administrator privileges for network configuration
    if get_os_type() == "Windows" and not is_admin():
        print(f"{APP_NAME} requires administrator privileges to configure network settings.")
        print("Requesting elevation...")
        
        if not request_admin_elevation():
            print("\nAdministrator privileges are required to run this application.")
            print("Please right-click the application and select 'Run as administrator'.")
            input("\nPress Enter to exit...")
            return 1
        
        # If we get here, elevation was requested and a new process started
        # This process should exit
        return 0

    print(f"Starting {APP_NAME} v{VERSION}...")

    req_ok, req_issues = check_system_requirements()
    dep_ok, missing_deps = check_dependencies()

    if not dep_ok:
        print("Missing dependencies:")
        for dep in missing_deps:
            print(f"   • {dep}")
        print("\nInstall with: pip install -r requirements.txt")
        return 1

    if not req_ok:
        print("System issues detected:")
        for issue in req_issues:
            print(f"   • {issue}")

        try:
            response = input("\nContinue anyway? (y/N): ").lower().strip()
            if response not in ["y", "yes"]:
                print("Startup cancelled by user")
                return 1
        except KeyboardInterrupt:
            print("\nStartup cancelled by user")
            return 1

    if args.no_gui:
        print("Console mode not yet implemented")
        print("   Use GUI mode by running without --no-gui")
        return 1

    try:
        if DEBUG_MODE:
            print_system_info()
            print()

        print("Starting GUI application...")
        print()

        ui_main()

        print("Application closed normally")
        return 0

    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 0

    except Exception as e:
        print(f"Unexpected error: {e}")

        if DEBUG_MODE:
            import traceback

            traceback.print_exc()

        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
