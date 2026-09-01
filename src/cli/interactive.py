"""
Interfaccia interattiva da terminale (menu con frecce/numeri/Enter).

La logica del selettore vive in :mod:`cli.selector`: qui restano solo il
banner e l'adattatore ``run_menu`` usato dalla CLI.

Se il terminale non e' un TTY (pipe, CI, script) il menu degrada
automaticamente a un elenco numerato letto riga per riga. Nessuna GUI.
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional, Sequence

from .selector import (  # noqa: F401  (riesportati per compatibilita')
    KeyReader,
    SelectorState,
    decode_key,
    is_interactive,
    parse_line_selection,
    render_menu,
    select,
)

DEFAULT_PROMPT = "Use arrows or numbers (1-N), Enter to confirm, ESC/q to cancel."


def is_tty() -> bool:
    return is_interactive()


def supports_color() -> bool:
    return is_tty() and not os.environ.get("NO_COLOR")


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if supports_color() else text


def banner() -> str:
    return "\n".join([
        "╭────────────────────────────────────────╮",
        "│          OpenHackintosh                │",
        "│      Hardware & EFI Assistant          │",
        "╰────────────────────────────────────────╯",
        "",
    ])


def _cancel_item(items: Sequence[dict]) -> dict:
    """Voce da restituire quando l'utente annulla (ESC/q/EOF/Ctrl+C).

    Preferisce la voce con ``action == "exit"``; altrimenti l'ultima.
    """
    for item in items:
        if str(item.get("action", "")).lower() in ("exit", "quit"):
            return item
    return items[-1]


def run_menu(items: List[dict], title: str = "What would you like to do?",
             prompt: str = DEFAULT_PROMPT,
             index: int = 0) -> dict:
    """Mostra il menu e restituisce la voce scelta.

    Funziona con un numero qualsiasi di opzioni, comprese quelle multi-cifra
    ([10], [11], ...). In caso di annullamento restituisce la voce di uscita.
    """
    if not items:
        raise ValueError("run_menu richiede almeno una voce di menu")

    print(banner(), end="")
    chosen = select(items, title=title, prompt=prompt, index=index)
    if chosen is None:
        return _cancel_item(items)
    return items[chosen]


def _getch() -> Optional[str]:
    """Compatibilita' con la 2.0.1 Beta 1: legge un singolo tasto.

    Ora usa :class:`cli.selector.KeyReader`, quindi gestisce correttamente
    ESC isolato e le frecce in application mode.
    """
    if not is_interactive():
        return None
    reader = KeyReader()
    try:
        with reader:
            return reader.read_key()
    except Exception:
        return None
