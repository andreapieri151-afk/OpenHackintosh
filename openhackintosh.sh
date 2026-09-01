#!/usr/bin/env bash
# OpenHackintosh 2.0.1 Beta 1 — Linux launcher
# Stesso comportamento del launcher macOS, ma pensato per Linux.

cd "$(dirname "$0")" || exit 1

# Usa il launcher principale (gestisce .venv e dipendenze).
if [ -x ./openhackintosh ]; then
    exec ./openhackintosh "$@"
fi

# Fallback minimo se ./openhackintosh non è eseguibile.
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python3 non trovato. Installalo con il gestore pacchetti della tua distro."
    exit 1
fi
exec python3 main.py "$@"
