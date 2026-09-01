"""
Final EFI Audit.

Esegue, in ordine:
1. EFI structure check
2. Binary check (kext/driver/opencore/booter/aml)
3. Zero-byte / placeholder recursive
4. Config consistency (cross-reference)
5. Required components check
6. ACPI / Drivers / Kext check

Solo se TUTTI i controlli passano -> status VALID.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from database import HardwareProfile
from efi.integrity import (
    collect_integrity_records,
    looks_placeholder,
    record_for_aml,
    record_for_binary,
    record_for_kext,
    validate_aml_file,
    validate_efi_binary,
    validate_kext,
)
from efi.selection import ComponentSelection, DRIVER_FILES, KEXT_BUNDLES
from efi_builder.validator import validate_efi


def _scan_placeholders(root: Path) -> List[str]:
    problems: List[str] = []
    if not root.exists():
        return problems
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.stat().st_size == 0 or looks_placeholder(path):
            problems.append(str(path.relative_to(root)))
    return problems


def final_audit(efi_root: Path, profile: HardwareProfile,
                selection: ComponentSelection) -> Dict[str, Any]:
    efi_root = Path(efi_root)
    checks: Dict[str, bool] = {}
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Struttura base
    structure = {
        "BOOT/BOOTx64.efi": efi_root / "BOOT" / "BOOTx64.efi",
        "OC/OpenCore.efi": efi_root / "OC" / "OpenCore.efi",
        "OC/config.plist": efi_root / "OC" / "config.plist",
        "OC/Kexts": efi_root / "OC" / "Kexts",
        "OC/Drivers": efi_root / "OC" / "Drivers",
        "OC/ACPI": efi_root / "OC" / "ACPI",
    }
    structure_ok = all(p.exists() for p in structure.values())
    checks["structure"] = structure_ok
    if not structure_ok:
        errors.extend(f"Missing structure: {name}" for name, p in structure.items() if not p.exists())

    # 2. Binary check
    kext_ok = True
    for kext in selection.required_kexts + selection.optional_kexts:
        bundle = KEXT_BUNDLES.get(kext, kext if kext.endswith(".kext") else kext + ".kext")
        res = validate_kext(efi_root / "OC" / "Kexts" / bundle)
        if not res.ok:
            errors.append(f"Kext invalid: {bundle} ({res.reason})")
            kext_ok = False

    driver_ok = True
    for driver in selection.required_drivers + selection.optional_drivers:
        fname = DRIVER_FILES.get(driver, driver if driver.endswith(".efi") else driver + ".efi")
        res = validate_efi_binary(efi_root / "OC" / "Drivers" / fname)
        if not res.ok:
            errors.append(f"Driver invalid: {fname} ({res.reason})")
            driver_ok = False

    oc_res = validate_efi_binary(efi_root / "OC" / "OpenCore.efi")
    boot_res = validate_efi_binary(efi_root / "BOOT" / "BOOTx64.efi")

    aml_ok = True
    for ssdt in selection.required_ssdts + selection.optional_ssdts:
        res = validate_aml_file(efi_root / "OC" / "ACPI" / f"{ssdt}.aml")
        if not res.ok:
            errors.append(f"AML invalid: {ssdt}.aml ({res.reason})")
            aml_ok = False

    checks["binaries"] = kext_ok and driver_ok and oc_res.ok and boot_res.ok and aml_ok
    if not oc_res.ok:
        errors.append(f"OpenCore.efi invalid ({oc_res.reason})")
    if not boot_res.ok:
        errors.append(f"BOOTx64.efi invalid ({boot_res.reason})")

    # 3. Zero-byte / placeholder
    placeholders = _scan_placeholders(efi_root)
    checks["zero_byte_placeholder"] = not placeholders
    if placeholders:
        errors.append("Placeholder/empty files: " + ", ".join(placeholders[:8]))

    # 4. Config consistency
    validation = validate_efi(efi_root)
    checks["config_consistency"] = validation.get("ready", False)
    if not validation.get("ready", False):
        errors.extend(validation.get("errors", []))
    warnings.extend(validation.get("warnings", []))

    # 5. Required components (indipendente dagli altri errori)
    required_missing: List[str] = []
    for kext in selection.required_kexts:
        bundle = KEXT_BUNDLES.get(kext, kext if kext.endswith(".kext") else kext + ".kext")
        res = validate_kext(efi_root / "OC" / "Kexts" / bundle)
        if not res.ok:
            required_missing.append(bundle)
            errors.append(f"Required kext missing/invalid: {bundle} ({res.reason})")
    for driver in selection.required_drivers:
        fname = DRIVER_FILES.get(driver, driver if driver.endswith(".efi") else driver + ".efi")
        res = validate_efi_binary(efi_root / "OC" / "Drivers" / fname)
        if not res.ok:
            required_missing.append(fname)
            errors.append(f"Required driver missing/invalid: {fname} ({res.reason})")
    for ssdt in selection.required_ssdts:
        res = validate_aml_file(efi_root / "OC" / "ACPI" / f"{ssdt}.aml")
        if not res.ok:
            required_missing.append(f"{ssdt}.aml")
            errors.append(f"Required ACPI missing/invalid: {ssdt}.aml ({res.reason})")
    checks["required_components"] = not required_missing

    # Integrità / report data
    integrity = collect_integrity_records(efi_root, selection.to_dict())
    invalid_integrity = [r for r in integrity if r["status"] != "REAL"]
    checks["integrity_records"] = not invalid_integrity
    if invalid_integrity:
        errors.extend(
            f"Integrity invalid: {r['name']} ({r['status']}: {r['reason']})"
            for r in invalid_integrity
        )

    status = "VALID" if checks["structure"] and checks["binaries"] and \
        checks["zero_byte_placeholder"] and checks["config_consistency"] and \
        checks["required_components"] and checks["integrity_records"] else "FAILED"

    report = {
        "profile": profile.name,
        "state": profile.state,
        "acpi": [("ok" if validate_aml_file(efi_root / "OC" / "ACPI" / f"{s}.aml").ok else "invalid", s + ".aml")
                 for s in selection.required_ssdts + selection.optional_ssdts],
        "drivers": [("ok" if validate_efi_binary(efi_root / "OC" / "Drivers" / (DRIVER_FILES.get(d, d + ".efi"))).ok else "invalid", d)
                    for d in selection.required_drivers + selection.optional_drivers],
        "kexts": [("ok" if validate_kext(efi_root / "OC" / "Kexts" / KEXT_BUNDLES.get(k, k + ".kext")).ok else "invalid", k)
                  for k in selection.required_kexts + selection.optional_kexts],
    }

    return {
        "status": status,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "integrity": integrity,
        "report": report,
        "ready": status == "VALID",
    }
