"""
Interfaccia interattiva da terminale (menù con frecce/invio).

Se il terminale non supporta i colori/unicode o non e' un TTY, si degrada
a un menu numerato semplice. Nessuna GUI.
"""

from __future__ import annotations

import os
import sys
from typing import Callable, List, Optional


def _getch() -> Optional[str]:
    try:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                seq = sys.stdin.read(2)
                return ch + seq
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        return None


def is_tty() -> bool:
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except Exception:
        return False


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


def run_menu(items: List[dict], title: str = "What would you like to do?",
             prompt: str = "Use arrows / numbers, Enter to select.") -> dict:
    print(banner())
    print(title)
    idx = 0
    while True:
        print("\r" + " " * 60 + "\r", end="")
        for i, item in enumerate(items):
            cursor = ">" if i == idx else " "
            label = item["label"]
            marker = "❯" if i == idx else " "
            print(f"  {marker} {label}{(30 - len(label)) * ' '}   [{i + 1}]")

        print(prompt)

        char = _getch()
        if char is None:
            # fallback input numerico
            try:
                sel = input("> ")
                if sel.strip().isdigit():
                    idx = int(sel.strip()) - 1
                    if 0 <= idx < len(items):
                        return items[idx]
                elif sel.strip().lower() in ("q", "exit"):
                    return items[-1]
            except EOFError:
                return items[-1]
            continue

        if char == "\r" or char == "\n":
            return items[idx]
        if char == "\x1b[A":
            idx = (idx - 1) % len(items)
        elif char == "\x1b[B":
            idx = (idx + 1) % len(items)
        elif char and char.isdigit():
            n = int(char) - 1
            if 0 <= n < len(items):
                return items[n]
        elif char and char.lower() == "q":
            return items[-1]
