"""
EFI Validator avanzato.

Stati componenti:
    REAL        -> file presente, non vuoto, sembra legittimo
    PLACEHOLDER -> file vuoto o con testo segnaposto
    INVALID     -> file presente ma chiaramente invalido (es. Info.plist mancante)
    MISSING     -> componente atteso ma assente
    UNKNOWN     -> non valutabile

Un'EFI NON deve mai essere dichiarata 'ready' con componenti PLACEHOLDER.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import plistlib

from efi.integrity import (
    validate_aml_file,
    validate_efi_binary,
    validate_kext,
)


PLACEHOLDER_MARKERS = [
    b"placeholder",
    b"fake",
    b"0 byte",
    b"todo",
    b"not implemented",
]


def _file_state(path: Path, min_size: int = 100) -> str:
    if not path.exists():
        return "MISSING"
    if path.stat().st_size < min_size:
        return "PLACEHOLDER"
    try:
        head = path.read_bytes()[:2048].lower()
        for marker in PLACEHOLDER_MARKERS:
            if marker in head:
                return "PLACEHOLDER"
    except Exception:
        pass
    return "REAL"


def _binary_state(path: Path) -> str:
    res = validate_efi_binary(path)
    if not path.exists():
        return "MISSING"
    if res.ok:
        return "REAL"
    return "INVALID"


def _aml_state(path: Path) -> str:
    res = validate_aml_file(path)
    if not path.exists():
        return "MISSING"
    if res.ok:
        return "REAL"
    if res.reason in ("EMPTY_TOO_SMALL", "PLACEHOLDER"):
        return "PLACEHOLDER"
    return "INVALID"


def _kext_state(kext_dir: Path) -> str:
    res = validate_kext(kext_dir)
    if not kext_dir.exists():
        return "MISSING"
    if res.ok:
        return "REAL"
    if res.reason in ("MISSING_OR_EMPTY_INFO_PLIST", "MISSING_EXECUTABLE", "NOT_MACH_O", "PLACEHOLDER"):
        return "INVALID"
    return "INVALID"


@dataclass
class ComponentState:
    name: str
    state: str
    path: str
    error: str = ""

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


def _read_config(config_path: Path) -> Optional[Dict[str, Any]]:
    if not config_path.exists():
        return None
    try:
        with open(config_path, "rb") as f:
            return plistlib.load(f)
    except Exception:
        return None


def _check_kext_consistency(config: Dict[str, Any], kexts_dir: Path,
                            components: List[ComponentState]) -> List[str]:
    issues: List[str] = []
    configured = config.get("Kernel", {}).get("Add", [])
    configured_paths = {entry.get("BundlePath", "") for entry in configured}

    # Kext configurato ma assente
    for entry in configured:
        bundle = entry.get("BundlePath", "")
        if not bundle:
            continue
        kext_dir = kexts_dir / bundle
        state = _kext_state(kext_dir)
        if state == "MISSING":
            components.append(ComponentState(bundle, "MISSING", str(kext_dir),
                                             "Kext configurato ma file assente"))
            issues.append(f"Kext configured but missing: {bundle}")
        elif state == "INVALID":
            components.append(ComponentState(bundle, "INVALID", str(kext_dir),
                                             "Kext non valido (binario Mach-O, Info.plist o eseguibile)"))
            issues.append(f"Kext invalid: {bundle}")
        elif state == "REAL":
            components.append(ComponentState(bundle, "REAL", str(kext_dir)))

    # Kext presente ma non configurato
    if kexts_dir.exists():
        for kext in kexts_dir.glob("*.kext"):
            if kext.name not in configured_paths:
                components.append(ComponentState(kext.name, "REAL", str(kext),
                                                 "Presente ma non configurato in Kernel/Add"))
                issues.append(f"Kext present but not configured: {kext.name}")

    return issues


def _check_acpi_consistency(config: Dict[str, Any], acpi_dir: Path,
                            components: List[ComponentState]) -> List[str]:
    issues: List[str] = []
    configured = config.get("ACPI", {}).get("Add", [])
    configured_paths = {entry.get("Path", "") for entry in configured}

    for entry in configured:
        name = entry.get("Path", "")
        if not name:
            continue
        aml = acpi_dir / name
        state = _aml_state(aml)
        if state == "MISSING":
            components.append(ComponentState(name, "MISSING", str(aml), "ACPI configurato ma assente"))
            issues.append(f"ACPI configured but missing: {name}")
        elif state == "PLACEHOLDER":
            components.append(ComponentState(name, "PLACEHOLDER", str(aml), "AML vuoto/placeholder"))
            issues.append(f"AML placeholder/invalid: {name}")
        elif state == "INVALID":
            components.append(ComponentState(name, "INVALID", str(aml), "AML non valido"))
            issues.append(f"AML invalid: {name}")
        elif state == "REAL":
            components.append(ComponentState(name, "REAL", str(aml)))

    if acpi_dir.exists():
        for aml in acpi_dir.glob("*.aml"):
            if aml.name not in configured_paths:
                issues.append(f"ACPI file present but not configured: {aml.name}")
                components.append(ComponentState(aml.name, "REAL", str(aml),
                                                 "ACPI presente ma non configurato"))
    return issues


def _check_driver_consistency(config: Dict[str, Any], drivers_dir: Path,
                              components: List[ComponentState]) -> List[str]:
    issues: List[str] = []
    configured = config.get("UEFI", {}).get("Drivers", [])
    configured_paths = {entry.get("Path", "") for entry in configured}

    for entry in configured:
        name = entry.get("Path", "")
        if not name:
            continue
        driver = drivers_dir / name
        state = _binary_state(driver)
        if state == "MISSING":
            components.append(ComponentState(name, "MISSING", str(driver), "Driver configurato ma assente"))
            issues.append(f"Driver configured but missing: {name}")
        elif state == "INVALID":
            components.append(ComponentState(name, "INVALID", str(driver), "Driver non valido (PE/COFF)"))
            issues.append(f"Driver invalid: {name}")
        elif state == "REAL":
            components.append(ComponentState(name, "REAL", str(driver)))

    if drivers_dir.exists():
        for driver in drivers_dir.glob("*.efi"):
            if driver.name not in configured_paths:
                issues.append(f"Driver present but not configured: {driver.name}")
                components.append(ComponentState(driver.name, "REAL", str(driver),
                                                 "Driver presente ma non configurato"))
    return issues


def validate_efi(efi_root: Path) -> dict:
    """Validation avanzata. Preserva il contratto esistente (valid/errors/warnings/checks)."""
    efi_root = Path(efi_root)
    results: Dict[str, Any] = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "checks": {},
        "components": [],
        "ready": False,
        "states": {"REAL": 0, "PLACEHOLDER": 0, "INVALID": 0, "MISSING": 0, "UNKNOWN": 0},
    }
    components: List[ComponentState] = []
    issues: List[str] = []

    required_paths = [
        ("BOOT/BOOTx64.efi", efi_root / "BOOT" / "BOOTx64.efi"),
        ("OC/OpenCore.efi", efi_root / "OC" / "OpenCore.efi"),
        ("OC/config.plist", efi_root / "OC" / "config.plist"),
    ]
    for label, path in required_paths:
        if label.endswith(".plist"):
            state = _file_state(path, min_size=50)
        else:
            state = _binary_state(path)
        results["checks"][label] = state
        components.append(ComponentState(label, state, str(path)))
        if state == "MISSING":
            results["errors"].append(f"Missing required: {label}")
            results["valid"] = False
        elif state == "PLACEHOLDER":
            results["errors"].append(f"Placeholder/empty: {label}")
            results["valid"] = False
        elif state == "INVALID":
            results["errors"].append(f"Invalid: {label}")
            results["valid"] = False

    config_path = efi_root / "OC" / "config.plist"
    config = _read_config(config_path)
    if config is None:
        results["errors"].append("config.plist non leggibile")
        results["valid"] = False
        results["checks"]["config.plist readable"] = False
    else:
        results["checks"]["config.plist readable"] = True
        kexts_dir = efi_root / "OC" / "Kexts"
        acpi_dir = efi_root / "OC" / "ACPI"
        drivers_dir = efi_root / "OC" / "Drivers"
        issues += _check_kext_consistency(config, kexts_dir, components)
        issues += _check_acpi_consistency(config, acpi_dir, components)
        issues += _check_driver_consistency(config, drivers_dir, components)

    kexts_found = len(list((efi_root / "OC" / "Kexts").glob("*.kext"))) if (efi_root / "OC" / "Kexts").exists() else 0
    acpi_found = len(list((efi_root / "OC" / "ACPI").glob("*.aml"))) if (efi_root / "OC" / "ACPI").exists() else 0
    drivers_found = len(list((efi_root / "OC" / "Drivers").glob("*.efi"))) if (efi_root / "OC" / "Drivers").exists() else 0
    results["checks"]["kexts found"] = kexts_found
    results["checks"]["acpi found"] = acpi_found
    results["checks"]["drivers found"] = drivers_found

    if kexts_found == 0:
        results["errors"].append("No kexts found in OC/Kexts")
        results["valid"] = False

    # SMBIOS
    if config and config.get("PlatformInfo", {}).get("Generic", {}).get("SystemSerialNumber") in (None, ""):
        results["errors"].append("Missing SystemSerialNumber")
        results["valid"] = False

    # Component states
    for comp in components:
        state = comp.state
        if state in results["states"]:
            results["states"][state] += 1
        else:
            results["states"]["UNKNOWN"] += 1
    results["components"] = [c.to_dict() for c in components]

    # Consistency
    seen: set = set()
    for issue in issues:
        results["warnings"].append(issue)
        if issue in seen:
            results["warnings"].append(f"Duplicate check: {issue}")
        seen.add(issue)

    has_placeholder = (
        results["states"]["PLACEHOLDER"] > 0
        or results["states"]["MISSING"] > 0
        or results["states"]["INVALID"] > 0
    )
    if has_placeholder:
        results["valid"] = False

    results["ready"] = bool(results["valid"] and not has_placeholder and not results["errors"])
    return results


def validate_efi_strict(efi_root: Path) -> dict:
    return validate_efi(efi_root)


def print_validation(results: dict):
    print("\n=== EFI Validation ===")
    print(f"Valid: {results.get('valid')}")
    print(f"Ready: {results.get('ready')}")
    print(f"States: {results.get('states')}")
    print("\nChecks:")
    for k, v in results.get("checks", {}).items():
        print(f"  {k}: {v}")
    print("\nComponents:")
    for c in results.get("components", []):
        print(f"  [{c['state']}] {c['name']}")
    if results.get("errors"):
        print("\nErrors:")
        for e in results["errors"]:
            print(f"  - {e}")
    if results.get("warnings"):
        print("\nWarnings:")
        for w in results["warnings"]:
            print(f"  ! {w}")
    if results.get("ready"):
        print("\nEFI appears ready (no placeholders).")
    else:
        print("\nEFI NOT ready. Do not declare it complete.")
