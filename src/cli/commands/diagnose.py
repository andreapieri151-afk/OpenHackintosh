"""openhackintosh diagnose — analisi completa hardware + matching + compatibilità.

Esegue, in ordine:
    1. Hardware detection (una sola volta, via HardwareSnapshot)
    2. Hardware identification
    3. Database matching
    4. Compatibility analysis
    5. Report diagnostico (testo o JSON)

NON genera/modifica EFI. Il risultato è deterministico, trasparente,
basato sul database e separato dall'AI.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from hardware import detect_and_capture, unknown, HardwareSnapshot, STATUS_NOT_DETECTED
from compatibility import ComponentStatus, OverallStatus
from cli.output import Out, status_icon


def _status_to_icon(status: str) -> str:
    mapping = {
        "ok": "green",
        "partial": "yellow",
        "unsupported": "red",
        "unknown": "gray",
        ComponentStatus.OK.value: "green",
        ComponentStatus.PARTIAL.value: "yellow",
        ComponentStatus.UNSUPPORTED.value: "red",
        ComponentStatus.UNKNOWN.value: "gray",
    }
    return mapping.get(status, "gray")


def _dmi(info, key: str) -> str:
    v = info.dmi.get(key) or unknown()
    return str(v)


def _field_status(info_dict: Dict[str, Any], key: str) -> str:
    v = info_dict.get(key) or unknown()
    return v.status if hasattr(v, "status") else STATUS_NOT_DETECTED


def _component_dict(info: Dict[str, Any]) -> Dict[str, Any]:
    """Converte la sezione di rilevamento in dict leggibile (value + status + source)."""
    return {k: v.to_dict() for k, v in info.items()}


def _macos_rows(profile) -> List[Dict[str, Any]]:
    if not profile:
        return []
    rows: List[Dict[str, Any]] = []
    compat = profile.macos_compatibility or {}
    for version, info_v in compat.items():
        status = str(info_v.get("status", "unknown")).lower()
        if status == "verified":
            icon = "green"
        elif status == "documented":
            icon = "yellow"
        else:
            icon = "gray"
        rows.append({
            "version": version,
            "status": status.upper(),
            "status_icon": icon,
            "requires_hardware_testing": bool(info_v.get("requires_hardware_testing", False)),
        })
    return rows


def _storage_status(info: HardwareSnapshot) -> Dict[str, Any]:
    storage = info.info.storage
    has_storage = storage.get("storage") and str(storage["storage"]) != "Unknown / Not detected"
    if has_storage:
        return {
            "status": "ok",
            "status_icon": "green",
            "detected": str(info.info.storage.get("storage", unknown())),
            "evidence": ["Storage controller/drive detected"],
        }
    return {
        "status": "unknown",
        "status_icon": "gray",
        "detected": "None",
        "evidence": ["Hardware not detected", "Requires real hardware testing"],
    }


def build_diagnosis_payload(snapshot: HardwareSnapshot) -> Dict[str, Any]:
    info = snapshot.info
    identity = snapshot.identity
    result = snapshot.result

    # Sezioni hardware complete (value null quando non rilevato).
    system = {
        "manufacturer": _component_value(info.dmi.get("system_vendor")),
        "model": _component_value(info.dmi.get("product_name")),
        "product_version": _component_value(info.dmi.get("product_version")),
        "board_vendor": _component_value(info.dmi.get("board_vendor")),
        "board_model": _component_value(info.dmi.get("board_name")),
        "board_version": _component_value(info.dmi.get("board_version")),
        "bios_vendor": _component_value(info.dmi.get("bios_vendor")),
        "bios_version": _component_value(info.dmi.get("bios_version")),
        "bios_date": _component_value(info.dmi.get("bios_date")),
        "uefi_mode": _component_value(info.platform.get("uefi_mode")),
    }

    cpu = _component_dict(info.cpu)
    gpu = _component_dict(info.gpu)
    audio = _component_dict(info.audio)
    ethernet = _component_dict(info.ethernet)
    wifi = _component_dict(info.wifi)
    bluetooth = _component_dict(info.bluetooth)
    storage = _component_dict(info.storage)
    usb = _component_dict(info.usb)
    acpi = _component_dict(info.acpi)

    components = [c.to_dict() for c in result.components] if result else []
    overall = result.overall.value if result else OverallStatus.UNKNOWN.value
    overall_icon = _status_to_icon(overall)

    # Diagnosi complessiva a livello di componenti principali.
    component_status = {c.name: c.status.value for c in result.components} if result else {}
    storage_status = _storage_status(snapshot)
    diagnosis_rows = []
    for name in ("CPU", "GPU", "Audio", "Ethernet", "Wi-Fi", "Storage"):
        if name == "Storage":
            rows_status = storage_status["status"]
        else:
            rows_status = component_status.get(name, "unknown")
        diagnosis_rows.append({
            "component": name,
            "status": rows_status,
            "status_icon": _status_to_icon(rows_status),
        })

    payload = {
        "mode": "diagnose",
        "detection_errors": list(info.detection_errors),
        "system": system,
        "cpu": cpu,
        "gpu": gpu,
        "audio": audio,
        "ethernet": ethernet,
        "wifi": wifi,
        "bluetooth": bluetooth,
        "storage": storage,
        "usb": usb,
        "acpi": acpi,
        "database": {
            "profile": snapshot.profile.id if snapshot.profile else None,
            "profile_name": snapshot.profile.name if snapshot.profile else None,
            "match": snapshot.match_type,
            "score": snapshot.match.score if snapshot.match else 0,
            "matched_fields": snapshot.match.matched_fields if snapshot.match else [],
            "reasons": snapshot.match.reasons if snapshot.match else [],
            "profile_status": snapshot.profile.state if snapshot.profile else None,
        },
        "compatibility": {
            "status": overall,
            "status_icon": overall_icon,
            "components": components,
            "notes": result.notes if result else [],
            "requires_hardware_testing": result.requires_hardware_testing if result else False,
        },
        "macos_compatibility": _macos_rows(snapshot.profile),
        "diagnosis": {
            "components": diagnosis_rows,
            "storage": storage_status,
        },
        "overall": overall,
        "notes": [
            "Hardware compatibility still requires real hardware testing."
            if (result and result.requires_hardware_testing) else
            "Detection and matching are based on database and detected hardware."
        ],
    }
    return payload


def _component_value(v) -> Dict[str, Any]:
    if v is None:
        return {"value": None, "status": STATUS_NOT_DETECTED, "source": "unknown"}
    return v.to_dict()


def _print_component(name: str, section: Dict[str, Any], *keys: str) -> None:
    key = keys[0] if keys else name.lower()
    entry = section.get(key, {})
    main = entry.get("value")
    status = entry.get("status", STATUS_NOT_DETECTED)
    icon = "green" if status == "DETECTED" else ("yellow" if status == "INFERRED" else "gray")
    label = main if main else "Not detected"
    print(f"{name:<10} {label}")
    print(f"{'':<10} Status: {status_icon(icon)} {status}")


def print_diagnosis(payload: Dict[str, Any]) -> None:
    system = payload["system"]
    print("========================================")
    print("       OpenHackintosh Diagnosis")
    print("========================================")
    print("\nSYSTEM")
    print(f"Manufacturer : {system['manufacturer']['value'] or 'Not detected'}")
    print(f"Model        : {system['model']['value'] or 'Not detected'}")
    print(f"Board        : {system['board_model']['value'] or 'Not detected'}")
    print(f"BIOS         : {system['bios_vendor']['value'] or ''} {system['bios_version']['value'] or ''}".strip())
    print(f"Boot mode    : {system['uefi_mode']['value'] or 'Not detected'}")

    _print_component("CPU", payload["cpu"], "model")
    _print_component("GPU", payload["gpu"], "gpu")
    _print_component("Audio", payload["audio"], "audio")
    _print_component("Ethernet", payload["ethernet"], "ethernet")
    _print_component("Wi-Fi", payload["wifi"], "wifi")
    _print_component("Storage", payload["storage"], "storage")

    print("\n----------------------------------------")
    print("\nDATABASE")
    db = payload["database"]
    print(f"Profile      : {db['profile_name'] or 'Unknown'}")
    print(f"Match        : {status_icon('green' if db['match'] == 'EXACT_MATCH' else 'yellow')} {db['match']}")
    print(f"Profile status: {db['profile_status'] or 'N/A'}")

    for err in payload.get("detection_errors", []):
        print(f"\n⚠️ Detection failed: {err} (diagnosis continued)")

    print("\n----------------------------------------")
    print("\nDIAGNOSIS")
    for row in payload["diagnosis"]["components"]:
        print(f"{row['component']:<8} {status_icon(row['status_icon'])} {row['status']}")

    print("\n----------------------------------------")
    print("\nmacOS Compatibility")
    rows = payload["macos_compatibility"]
    if rows:
        for row in rows:
            print(f"{row['version']:<16} {status_icon(row['status_icon'])} {row['status']}")
    else:
        print("Unknown")

    overall = payload["overall"]
    overall_icon = payload["compatibility"]["status_icon"]
    print(f"\nOverall: {status_icon(overall_icon)} {overall.upper()}")
    print("\nNOTE:")
    for note in payload["notes"]:
        print(f"  {note}")
    print("========================================")


def run_diagnose(args, out: Out) -> dict:
    snapshot = detect_and_capture()
    payload = build_diagnosis_payload(snapshot)

    if out.json_output:
        out.data(payload)
        return payload

    print_diagnosis(payload)
    return payload
