"""Bootstrap e capability della console, cross-platform.

Problemi risolti qui (una sola volta, all'avvio):

1. **Encoding** — su Windows il codepage di default (cp850/cp1252) non puo'
   stampare emoji/box-drawing e provocava ``UnicodeEncodeError`` a meta' build.
   Riconfiguriamo stdout/stderr in UTF-8 con ``errors="replace"``: nel peggiore
   dei casi si vede un carattere di sostituzione, mai un crash.
2. **ANSI / colori** — le sequenze di escape funzionano su Windows 10+ solo se
   si attiva ENABLE_VIRTUAL_TERMINAL_PROCESSING sullo handle della console.
   Proviamo ad attivarlo; se non e' possibile -> niente ANSI (output pulito).

Tutto e' best-effort e idempotente: chiamare setup_console() piu' volte non ha
effetti collaterali.
"""

from __future__ import annotations

import os
import sys

from .platforms import is_windows

_ready = False
_vt_enabled = False


def _reconfigure_stream(stream) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def enable_windows_vt_mode() -> bool:
    """Abilita le sequenze ANSI sulla console di Windows 10+.

    Ritorna True se VT e' attivo (o gia' lo era). Fuori da Windows ritorna
    True subito: su Linux/macOS i terminali ANSI sono la norma.
    """
    global _vt_enabled
    if not is_windows():
        return True
    if _vt_enabled:
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004, STD_OUTPUT_HANDLE = -11
        kernel32.SetConsoleMode.restype = ctypes.c_int
        for handle_id in (-11, -12):  # stdout, stderr
            handle = kernel32.GetStdHandle(handle_id)
            mode = ctypes.c_ulong()
            if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                continue
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        _vt_enabled = True
    except Exception:
        _vt_enabled = False
    return _vt_enabled


def setup_console() -> None:
    """Prepara stdout/stderr: UTF-8 ovunque + VT mode su Windows. Idempotente."""
    global _ready
    if _ready:
        return
    _ready = True
    _reconfigure_stream(sys.stdout)
    _reconfigure_stream(sys.stderr)
    if is_windows():
        enable_windows_vt_mode()


def ansi_supported(stream=None) -> bool:
    """Unica fonte di verita' per "posso stampare sequenze ANSI?".

    Regole:
    - ``NO_COLOR`` (o ``OPENHACKINTOSH_NO_ANSI``) -> mai;
    - stream non TTY -> mai;
    - TERM=dumb -> mai;
    - Windows: solo se il VT mode e' attivo (lo tentiamo al volo).
    """
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR") or os.environ.get("OPENHACKINTOSH_NO_ANSI"):
        return False
    if os.environ.get("TERM", "") == "dumb":
        return False
    try:
        if not stream.isatty():
            return False
    except Exception:
        return False
    if is_windows():
        return enable_windows_vt_mode()
    return True
