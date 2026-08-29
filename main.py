#!/usr/bin/env python3
"""
Fujitsu Esprimo Q556/2 - Hackintosh EFI Creator
Main entry point

This tool automates EFI creation with REAL files, not fake.
"""
import sys
from pathlib import Path

# Ensure src in path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    # Try GUI first if no args, else CLI
    if len(sys.argv) == 1:
        try:
            from gui.app import EFICreatorGUI
            print("Launching GUI...")
            app = EFICreatorGUI()
            app.run()
        except ImportError as e:
            print(f"GUI dependencies missing: {e}")
            print("Falling back to CLI. Use --gui after installing dependencies:")
            print("  pip install -r requirements.txt")
            print("\nOr run CLI:")
            print("  python src/cli.py --help")
            from cli import main as cli_main
            # Show help
            sys.argv.append("--help")
            cli_main()
        except Exception as e:
            print(f"GUI failed: {e}")
            print("Use CLI: python src/cli.py --help")
    else:
        from cli import main as cli_main
        cli_main()
