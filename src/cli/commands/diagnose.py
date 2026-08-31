"""openhackintosh diagnose — diagnosi completa hardware + compatibilita'."""

from __future__ import annotations

from hardware import detect_all, identify
from database import load_all_profiles
from compatibility import CompatibilityEngine
from ai import Assistant
from ..output import Out, status_icon


def run_diagnose(args, out: Out) -> dict:
    info = detect_all()
    identity = identify(info)
    engine = CompatibilityEngine(load_all_profiles())
    result = engine.analyze(identity=identity, info=info)

    if out.json_output:
        payload = {
            "mode": "diagnose",
            "computer": {
                "model": identity.model,
                "board": identity.board,
                "cpu": identity.cpu,
                "gpu": identity.gpu,
                "audio": identity.audio,
                "ethernet": identity.ethernet,
                "wifi": identity.wifi,
            },
            "profile": result.profile.to_dict() if result.profile else None,
            "overall": result.overall.value,
            "components": [c.to_dict() for c in result.components],
            "notes": result.notes,
            "requires_hardware_testing": result.requires_hardware_testing,
        }
        out.data(payload)
        return payload

    print("Computer:", identity.model if identity.model != "Unknown / Not detected" else "Unknown")
    icon_map = {"ok": "green", "partial": "yellow", "unsupported": "red", "unknown": "gray"}
    for c in result.components:
        print(f"  {c.name:<10} {status_icon(icon_map.get(c.status.value, 'gray'))}")

    print("\nmacOS compatibility:")
    if result.profile:
        for ver, info_v in result.profile.macos_compatibility.items():
            icon = "green" if info_v.get("status") == "verified" else (
                "yellow" if info_v.get("status") == "documented" else "gray")
            print(f"  {ver:<10} {status_icon(icon)}")
    else:
        print("  Nessun profilo corrispondente.")

    if result.profile:
        print("\nProfile:", result.profile.name)
        print("Status:", status_icon("green" if result.profile.verified else "yellow"),
              result.profile.state)

    print("\nSpiegazione:")
    assistant = Assistant()
    for line in assistant.explain(result):
        print("  " + line)

    return {
        "computer": {"model": identity.model},
        "profile": result.profile.id if result.profile else None,
        "overall": result.overall.value,
    }
