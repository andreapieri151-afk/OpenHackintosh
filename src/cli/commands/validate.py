"""openhackintosh validate — valida una EFI esistente."""

from __future__ import annotations

from pathlib import Path

from efi import validate_efi, print_validation
from ..output import Out


def run_validate(args, out: Out) -> dict:
    efi_root = Path(args.efi_path)
    if not efi_root.exists():
        msg = f"Percorso EFI non trovato: {efi_root}"
        if out.json_output:
            out.data({"ok": False, "error": msg})
        else:
            print(msg)
        raise SystemExit(2)

    results = validate_efi(efi_root)

    if out.json_output:
        out.data(results)
    else:
        print_validation(results)

    return results
