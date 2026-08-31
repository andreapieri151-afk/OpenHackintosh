"""openhackintosh compatibility — confronta hardware rilevato con database."""

from __future__ import annotations

from hardware import detect_all, identify
from database import load_all_profiles
from compatibility import CompatibilityEngine, OverallStatus
from ai import Assistant
from ..output import Out, status_icon


def run_compatibility(args, out: Out) -> dict:
    info = detect_all()
    identity = identify(info)
    profiles = load_all_profiles()
    engine = CompatibilityEngine(profiles)
    result = engine.analyze(identity=identity, info=info)

    if out.json_output:
        payload = {
            "mode": "compatibility",
            "identity": identity.to_dict(),
            "result": result.to_dict(),
        }
        out.data(payload)
        return payload

    out.title("Compatibility")
    if result.profile:
        out.table(["Component", "Detected", "Expected", "Status"], [
            [c.name, c.detected, c.expected or "-", c.status.value]
            for c in result.components
        ])
    else:
        print("Nessun profilo corrispondente trovato.")

    print("\nOverall: " + status_icon(result.to_dict()["status_icon"]) + " " + result.overall.value)
    for note in result.notes:
        print("  " + note)

    if result.requires_hardware_testing:
        print("  Requires real hardware testing")

    assistant = Assistant()
    print("\nSpiegazione:")
    for line in assistant.explain(result):
        print("  " + line)

    return result.to_dict()
