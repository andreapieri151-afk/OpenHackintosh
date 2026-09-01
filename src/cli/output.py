"""
Output CLI: testo leggibile oppure JSON.

JSON e' la sorgente di verita' per script/CI/AI. Il testo e' solo per l'uomo.
Colori: attivi solo se il terminale li supporta e NO_COLOR non e' settato.
Unicode: fallback pulito se il terminale non lo supporta.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional


def supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty() and os.environ.get("TERM") != "dumb"


class Out:
    def __init__(self, json_output: bool = False, dev: bool = False):
        self.json_output = json_output
        self.dev = dev

    def title(self, text: str) -> None:
        """Stampa un titolo di sezione (delega alla funzione modulo omonima)."""
        print(title(text))

    def data(self, data: Any, label: Optional[str] = None) -> None:
        if self.json_output:
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return
        if isinstance(data, dict):
            self._print_dict(data, label)
        elif isinstance(data, (list, tuple)):
            for item in data:
                print(item)
        else:
            print(data)

    def _print_dict(self, data: Dict[str, Any], label: Optional[str]) -> None:
        if label:
            print(title(label))
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for sub, val in value.items():
                    if isinstance(val, dict):
                        print(f"  {sub}:")
                        for k2, v2 in val.items():
                            print(f"    {k2}: {v2}")
                    else:
                        print(f"  {sub}: {val}")
            elif isinstance(value, (list, tuple)):
                print(f"{key}:")
                for item in value:
                    print(f"  - {item}")
            else:
                print(f"{key}: {value}")

    def table(self, headers: List[str], rows: List[List[Any]]) -> None:
        if self.json_output:
            payload = [dict(zip(headers, row)) for row in rows]
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return
        print("  ".join(h.ljust(18) for h in headers))
        print("  ".join("-" * 18 for _ in headers))
        for row in rows:
            print("  ".join(str(x).ljust(18) for x in row))


def title(text: str) -> str:
    return f"\n{text}\n{'=' * len(text)}\n"


def color(text: str, code: str = "36") -> str:
    if not supports_color():
        return text
    return f"\033[{code}m{text}\033[0m"


def green(text: str) -> str:
    return color(text, "32")


def yellow(text: str) -> str:
    return color(text, "33")


def red(text: str) -> str:
    return color(text, "31")


def cyan(text: str) -> str:
    return color(text, "36")


def dim(text: str) -> str:
    return color(text, "2")


def status_icon(status: str) -> str:
    icons = {
        "green": "\u2705",
        "yellow": "\u26a0\ufe0f",
        "red": "\u274c",
        "gray": "\u26aa",
    }
    return icons.get(status, status)
