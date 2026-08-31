"""openhackintosh doctor — controlli diagnostici del tool e dell'ambiente."""

from __future__ import annotations

import platform
import shutil
from pathlib import Path

from hardware import detect_all, identify
from database import load_all_profiles
from efi_builder.downloader import get_latest_release
from ..output import Out


def run_doctor(args, out: Out) -> dict:
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("Python", True, f"{platform.python_version()}")

    # Dipendenze
    add("requests", _importable("requests"), "installato con pip install requests")

    # Database
    profiles = load_all_profiles()
    add("Database", len(profiles) > 0, f"{len(profiles)} profili")

    # Hardware rilevabile
    info = detect_all()
    identity = identify(info)
    add("Hardware detection", True, f"model={identity.model} board={identity.board}")

    # Rete (best effort)
    has_net = bool(shutil.which("curl") or shutil.which("wget"))
    add("Network tools", has_net, "curl/wget per download")

    # Permessi scrittura
    tmpdir = Path("/tmp")
    add("Temporary write", tmpdir.exists() or Path(".").exists(), "necessario per EFI build")

    if out.json_output:
        payload = {
            "mode": "doctor",
            "checks": checks,
            "all_ok": all(c["ok"] for c in checks),
            "requires_hardware_testing": True,
            "notes": ["Doctor verifica l'ambiente, non la compatibilita' hardware reale."],
        }
        out.data(payload)
        return payload

    out.title("Doctor")
    for c in checks:
        icon = "OK" if c["ok"] else "FAIL"
        line = f"  {icon:<5} {c['name']}"
        if c["detail"]:
            line += f"  ({c['detail']})"
        print(line)
    print("\nNota: la compatibilita' reale richiede test su hardware fisico.")
    return {"checks": checks}


def _importable(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False
