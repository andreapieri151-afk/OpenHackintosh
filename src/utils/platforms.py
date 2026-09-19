"""Helper di piattaforma, condivisi da tutto il progetto.

Nessuna dipendenza esterna: solo stdlib. Questo modulo NON conosce la CLI,
la detection o l'EFI builder: risponde solo a "dove sto girando?".

Supporto per-piattaforma (2.0.1 Stable):
- Linux   -> completo
- Windows -> completo (PowerShell CIM per la detection)
- macOS   -> host di build; detection best-effort (documentata)
"""

from __future__ import annotations

import os
import platform
from pathlib import Path

PLATFORM_LINUX = "linux"
PLATFORM_WINDOWS = "windows"
PLATFORM_MACOS = "macos"


def current_platform() -> str:
    """Restituisce "linux" | "windows" | "macos" | nome grezzo in minuscolo."""
    name = platform.system().lower()
    if name.startswith("linux"):
        return PLATFORM_LINUX
    if name in ("windows", "msys", "cygwin") or os.name == "nt":
        return PLATFORM_WINDOWS
    if name == "darwin":
        return PLATFORM_MACOS
    return name or "unknown"


def is_windows() -> bool:
    return current_platform() == PLATFORM_WINDOWS


def is_linux() -> bool:
    return current_platform() == PLATFORM_LINUX


def is_macos() -> bool:
    return current_platform() == PLATFORM_MACOS


def default_cache_dir(app_name: str = "openhackintosh") -> Path:
    """Directory cache cross-platform per i download del tool.

    Priorita':
    1. ``OPENHACKINTOSH_CACHE`` (override esplicito, tutte le piattaforme);
    2. Windows -> ``%LOCALAPPDATA%\\OpenHackintosh\\Cache``
       (fallback ``%APPDATA%`` se LOCALAPPDATA mancasse);
    3. Linux/macOS -> ``~/.cache/openhackintosh`` (comportamento storico).

    Nota: su Windows ``HOME`` spesso non e' definito, quindi NON lo usiamo.
    """
    override = os.environ.get("OPENHACKINTOSH_CACHE")
    if override:
        return Path(override)

    if is_windows():
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / "OpenHackintosh" / "Cache"
        return Path.home() / "AppData" / "Local" / "OpenHackintosh" / "Cache"

    return Path.home() / ".cache" / app_name
