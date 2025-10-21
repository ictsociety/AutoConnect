#!/usr/bin/env python3
"""
UNESWA WiFi AutoConnect - Application Entry Point
ICT Society Initiative - University of Eswatini

Main entry point script that sets up the Python path and launches the application.
This script should be run from the project root directory.
"""

import sys
import os
from pathlib import Path

# Get the directory containing this script (project root)
PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / "src"

# Add project root to Python path so we can import src as a package
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    """Main entry point"""
    try:
        # Import and run the main application module
        import src.main

        return src.main.main()

    except ImportError as e:
        print(f"Import error: {e}")
        print(
            f"Make sure you're running from the project root directory: {PROJECT_ROOT}"
        )
        print("Install dependencies with: pip install -r requirements.txt")
        return 1

    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 0

    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    # Ensure we're in the correct directory
    if not (PROJECT_ROOT / "src").exists():
        print("Error: src directory not found")
        print(f"Make sure you're running this script from: {PROJECT_ROOT}")
        print("Expected directory structure:")
        print("  AutoConnect/")
        print("  ├── main.py (this file)")
        print("  ├── requirements.txt")
        print("  └── src/")
        sys.exit(1)

    # Change to project root directory
    os.chdir(PROJECT_ROOT)

    # Run the application
    exit_code = main()
    sys.exit(exit_code)
