#!/bin/bash
# Fujitsu Esprimo Q556/2 EFI Creator - macOS Launcher
# Double-click this file on macOS to launch

cd "$(dirname "$0")"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Fujitsu Esprimo Q556/2 - EFI Creator                      ║"
echo "║  Real files, no fake                                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 non trovato. Installa Python 3.9+ da python.org"
    read -p "Premi INVIO per uscire..."
    exit 1
fi

echo "✓ Python: $(python3 --version)"

# Check pip
if ! python3 -m pip --version &> /dev/null; then
    echo "⚠️ pip non trovato, provo a installare..."
    python3 -m ensurepip --upgrade
fi

# Install dependencies if needed
echo "📦 Controllo dipendenze..."
python3 -m pip install -r requirements.txt --break-system-packages -q 2>/dev/null || python3 -m pip install -r requirements.txt -q

echo ""
echo "🚀 Avvio GUI..."
echo ""

# Try GUI
python3 main.py

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️ GUI fallita, avvio CLI..."
    python3 src/cli.py --help
    echo ""
    echo "Esempio: python3 src/cli.py --profile Q556/2 --macos 'Ventura 13.x'"
    read -p "Premi INVIO per uscire..."
fi
