#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from app import app

if __name__ == "__main__":
    print("Starting Fujitsu Q556/2 EFI Creator Web Dashboard")
    print("Open: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
