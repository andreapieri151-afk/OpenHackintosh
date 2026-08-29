#!/usr/bin/env python3
"""
OpenHackintosh - Crea EFI vere, non finte
Entry point - prova GUI, se non va CLI
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    if len(sys.argv) == 1:
        try:
            from gui.app import EFICreatorGUI
            print("Ciao! Avvio GUI OpenHackintosh...")
            print("Se non parte, installa: pip install customtkinter")
            app = EFICreatorGUI()
            app.run()
        except ImportError as e:
            print(f"GUI non parte, mancano dipendenze: {e}")
            print("Provo CLI...")
            print("  pip install -r requirements.txt")
            print("  python src/cli.py --help")
            from cli import main as cli_main
            sys.argv.append("--help")
            cli_main()
        except Exception as e:
            print(f"GUI crashata: {e}")
            print("Usa CLI: python src/cli.py --help")
            print("Oppure web: python app.py -> http://localhost:5000")
    else:
        from cli import main as cli_main
        cli_main()
