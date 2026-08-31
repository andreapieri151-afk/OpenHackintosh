#!/bin/bash
# OpenHackintosh - macOS Launcher (da terminale)
# Doppio click su macOS per aprire il terminale e usare la CLI

cd "$(dirname "$0")"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  OpenHackintosh - EFI Builder (terminal)                   ║"
echo "║  File veri, non finti                                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python3 non trovato. Installa Python 3.9+ da python.org"
    read -p "Premi INVIO per uscire..."
    exit 1
fi

echo "Python: $(python3 --version)"

# Check pip
if ! python3 -m pip --version &> /dev/null; then
    echo "pip non trovato, provo a installare..."
    python3 -m ensurepip --upgrade
fi

# Install dependencies if needed
echo "Controllo dipendenze..."
python3 -m pip install -r requirements.txt --break-system-packages -q 2>/dev/null || python3 -m pip install -r requirements.txt -q

echo ""
echo "Avvio OpenHackintosh da terminale..."
echo ""

# CLI (se nessun argomento, mostra i profili disponibili e l'help)
if [ "$#" -eq 0 ]; then
    python3 src/cli.py --list-profiles
    echo ""
    echo "Usa --help per vedere tutte le opzioni."
    echo "Esempio: python3 src/cli.py --profile Q556/2 --macos 'Ventura 13.x'"
    echo ""
    read -p "Premi INVIO per uscire..."
else
    python3 src/cli.py "$@"
    echo ""
    read -p "Premi INVIO per uscire..."
fi
