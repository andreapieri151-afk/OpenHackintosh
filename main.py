#!/usr/bin/env python3
"""
OpenHackintosh - Crea EFI vere, non finte
Entry point da terminale: delega alla CLI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    # Console UTF-8 + VT mode (no-op fuori da Windows): evita crash di
    # encoding con emoji/box-drawing e attiva i colori su Windows 10+.
    from utils.console import setup_console

    setup_console()

    from cli.main import main as cli_main
    sys.exit(cli_main())
