"""
CLI OpenHackintosh — terminal-first.

Uso:
    openhackintosh                 -> menu interattivo
    openhackintosh detect [--json]
    openhackintosh info [--json]
    openhackintosh diagnose [--json]
    openhackintosh compatibility [--json]
    openhackintosh generate [--json] [--dev]
    openhackintosh validate ./EFI [--json]
    openhackintosh doctor [--json]
    openhackintosh database list|show [id] [--json]
    openhackintosh ask "<domanda>" [--json]

Ogni comando principale supporta --json per output strutturato.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .output import Out
from .interactive import run_menu

from .commands import (
    run_detect,
    run_info,
    run_diagnose,
    run_compatibility,
    run_generate,
    run_validate,
    run_doctor,
    run_database,
    run_bios,
)

VERSION = "2.0.2"


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="Output JSON strutturato")
    common.add_argument("--dev", action="store_true", help="Modalita' sviluppo: verbose/debug")
    common.add_argument("--force", action="store_true", help="Procedi anche se mancano evidenze")

    parser = argparse.ArgumentParser(
        prog="openhackintosh",
        description="Hardware & EFI Assistant per Hackintosh (OpenCore). CLI-first.",
    )
    parser.add_argument("--version", action="version", version=f"OpenHackintosh {VERSION}")

    sub = parser.add_subparsers(dest="command")

    p_detect = sub.add_parser("detect", parents=[common], help="Rileva l'hardware reale")
    p_detect.set_defaults(func=run_detect)

    p_info = sub.add_parser("info", parents=[common], help="Mostra informazioni su sistema")
    p_info.set_defaults(func=run_info)

    p_diag = sub.add_parser("diagnose", parents=[common], help="Diagnosi completa")
    p_diag.set_defaults(func=run_diagnose)

    p_comp = sub.add_parser("compatibility", parents=[common], help="Controlla compatibilita'")
    p_comp.set_defaults(func=run_compatibility)

    p_gen = sub.add_parser("generate", parents=[common], help="Genera EFI hardware-aware")
    p_gen.add_argument("--profile", help="ID profilo (es. fujitsu_q556_2)")
    p_gen.add_argument("--macos", default="Ventura 13.x", help="Versione macOS")
    p_gen.add_argument("--smbios", default="iMac18,1", help="SMBIOS model")
    p_gen.add_argument("--audio-layout", type=int, default=11)
    p_gen.add_argument("--wifi", action="store_true")
    p_gen.add_argument("--bluetooth", action="store_true")
    p_gen.add_argument("--output", default="output/EFI", help="Directory output")
    p_gen.add_argument("--no-zip", action="store_true", help="Non creare ZIP")
    p_gen.set_defaults(func=run_generate)

    p_val = sub.add_parser("validate", parents=[common], help="Valida una EFI")
    p_val.add_argument("efi_path", help="Percorso cartella EFI")
    p_val.set_defaults(func=run_validate)

    p_doc = sub.add_parser("doctor", parents=[common], help="Diagnostica ambiente/tool")
    p_doc.set_defaults(func=run_doctor)

    p_bios = sub.add_parser("bios", parents=[common], help="Guida BIOS specifica per profilo")
    p_bios.add_argument("--profile", default=None, help="ID profilo (es. fujitsu_q556_2)")
    p_bios.set_defaults(func=run_bios)

    p_db = sub.add_parser("database", parents=[common], help="Gestisci/consulta profili")
    db_sub = p_db.add_subparsers(dest="db_command")
    p_db_list = db_sub.add_parser("list", parents=[common], help="Elenca profili")
    p_db_list.set_defaults(func=run_database, db_command="list")
    p_show = db_sub.add_parser("show", parents=[common], help="Mostra profilo")
    p_show.add_argument("id")
    p_show.set_defaults(func=run_database, db_command="show")

    p_ask = sub.add_parser("ask", parents=[common], help="Fai una domanda all'assistant (dati strutturati)")
    p_ask.add_argument("question", nargs="*")
    p_ask.set_defaults(func=run_ask)

    return parser


def run_ask(args, out: Out) -> dict:
    from hardware import detect_all, identify
    from database import load_all_profiles
    from compatibility import CompatibilityEngine
    from ai import Assistant

    info = detect_all()
    identity = identify(info)
    engine = CompatibilityEngine(load_all_profiles())
    result = engine.analyze(identity=identity, info=info)
    question = " ".join(args.question) or "Riassunto"
    assistant = Assistant()
    answer = assistant.answer(question, result)
    payload = {"question": question, "answer": answer, "result": result.to_dict()}
    out.data(payload, "AI & EFI Assistant")
    return payload


def interactive_main(out: Out) -> None:
    items: List[dict] = [
        {"label": "Analyze this computer", "action": "diagnose"},
        {"label": "Generate EFI", "action": "generate"},
        {"label": "Validate EFI", "action": "validate"},
        {"label": "Check compatibility", "action": "compatibility"},
        {"label": "View hardware", "action": "detect"},
        {"label": "View database", "action": "database"},
        {"label": "BIOS guide", "action": "bios"},
        {"label": "Doctor", "action": "doctor"},
        {"label": "Ask the assistant", "action": "ask"},
        {"label": "Exit", "action": "exit"},
    ]
    choice = run_menu(items)
    if choice["action"] == "exit":
        return

    # Esegue la stessa logica dei sottocomandi
    import argparse
    parser = build_parser()
    mappings = {
        "diagnose": ["diagnose"],
        "generate": ["generate", "--output", "output/EFI"],
        "validate": ["validate", "output/EFI"],
        "compatibility": ["compatibility"],
        "detect": ["detect"],
        "database": ["database", "list"],
        "bios": ["bios", "--profile", "fujitsu_q556_2"],
        "doctor": ["doctor"],
        "ask": ["ask"],
    }
    argv = mappings.get(choice["action"], ["doctor"])
    if out.json_output:
        argv.append("--json")
    if out.dev:
        argv.append("--dev")
    args = parser.parse_args(argv)
    run_command(args, parser, Out(json_output=out.json_output, dev=out.dev))


def run_command(args, parser, out: Out) -> int:
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    try:
        result = args.func(args, out)
        if isinstance(result, dict):
            if result.get("ok") is False or result.get("success") is False:
                return 1
        return 0
    except SystemExit as e:
        return int(e.code or 0)
    except Exception as exc:
        if out.json_output:
            out.data({"ok": False, "error": str(exc)})
        else:
            print(f"Errore: {exc}")
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()

    # Nessun comando -> interfaccia interattiva
    if not argv:
        out = Out(json_output=False, dev=False)
        interactive_main(out)
        return 0

    # Se --json/--dev compare prima del sottocomando, lo spostiamo
    pre_flags = []
    rest = []
    for arg in argv:
        if arg in ("--json", "--dev", "--force") and not rest:
            pre_flags.append(arg)
        else:
            rest.append(arg)
    if pre_flags:
        argv = rest + pre_flags

    args = parser.parse_args(argv)
    out = Out(json_output=getattr(args, "json", False), dev=getattr(args, "dev", False))
    return run_command(args, parser, out)


if __name__ == "__main__":
    sys.exit(main())
