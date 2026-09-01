#!/bin/bash
# OpenHackintosh 2.0.1 Beta 1 — macOS launcher
# Doppio click su macOS: apre il Terminale e avvia la CLI.
# Non usa path assoluti: lavora nella directory del progetto.

cd "$(dirname "$0")" || exit 1

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  OpenHackintosh 2.0.1 Beta 1 (macOS)                       ║"
echo "║  CLI-first · Hardware Detection · EFI hardenizzata          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 1. Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python3 non trovato."
    echo "   Installa Python 3.9+ da https://www.python.org/downloads/"
    echo "   oppure con: brew install python"
    read -r -p "Premi INVIO per uscire..."
    exit 1
fi
echo "✅ Python: $(python3 --version)"

# 2. Ambiente virtuale (creato solo se manca)
if [ ! -d .venv ]; then
    echo "Creo ambiente Python (.venv)..."
    python3 -m venv .venv || {
        echo "❌ Impossibile creare .venv."
        read -r -p "Premi INVIO per uscire..."
        exit 1
    }
fi

# 3. Dipendenze
if ! .venv/bin/python -c "import requests" >/dev/null 2>&1; then
    echo "Installo dipendenze (requests)..."
    .venv/bin/python -m pip install -r requirements.txt -q \
        || .venv/bin/python -m pip install requests -q
fi

# 4. Avvia
echo ""
echo "Avvio OpenHackintosh..."
echo ""
.venv/bin/python main.py "$@"
rc=$?

echo ""
read -r -p "Premi INVIO per chiudere..." >/dev/null 2>&1 || true
exit $rc
