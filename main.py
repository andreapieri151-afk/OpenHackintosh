#!/usr/bin/env python3
"""
OpenHackintosh - Crea EFI vere, non finte
Entry point da terminale: delega alla CLI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    from cli.main import main as cli_main
    sys.exit(cli_main())
