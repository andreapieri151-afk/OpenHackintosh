"""
Integrità e validazione binaria dei componenti EFI.

Regole:
- NO FAKE BINARIES.
- Un reale kext è un bundle con Contents/Info.plist + eseguibile Mach-O.
- Un reale driver EFI / OpenCore / BOOTx64 è un binario PE/COFF (MZ + PE\\0\\0).
- Un reale AML è un file ACPI con firma valida (SSDT/DSDT/...) e dimensione > 0.
- Ogni componente obbligatorio che non supera la validazione -> INVALID.
"""

from __future__ import annotations

import hashlib
import json
import struct
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from database import HardwareProfile


# ---------------------------------------------------------------------------
# Testi placeholder / segnaposto
# ---------------------------------------------------------------------------

PLACEHOLDER_MARKERS = [
    b"placeholder",
    b"fake",
    b"0 byte",
    b"todo",
    b"not implemented",
    b"sample",
    b"dummy",
]


def _head(path: Path, size: int = 2048) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(size)
    except Exception:
        return b""


def looks_placeholder(path: Path) -> bool:
    if not path.exists():
        return True
    if path.stat().st_size == 0:
        return True
    head = _head(path).lower()
    return any(marker in head for marker in PLACEHOLDER_MARKERS)


# ---------------------------------------------------------------------------
# SHA-256
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Mach-O (kext executables)
# ---------------------------------------------------------------------------

MACHO_MAGICS = (
    b"\xfe\xed\xfa\xce",  # 32-bit BE
    b"\xce\xfa\xed\xfe",  # 32-bit LE
    b"\xfe\xed\xfa\xcf",  # 64-bit BE
    b"\xcf\xfa\xed\xfe",  # 64-bit LE
    b"\xca\xfe\xba\xbe",  # fat 32-bit
    b"\xbe\xba\xfe\xca",  # fat 32-bit swapped
    b"\xca\xfe\xba\xbf",  # fat 64-bit
    b"\xbf\xba\xfe\xca",  # fat 64-bit swapped
)


def is_macho(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 4:
        return False
    return _head(path, 4) in MACHO_MAGICS


# ---------------------------------------------------------------------------
# PE/COFF (EFI binaries)
# ---------------------------------------------------------------------------

def is_pe(path: Path) -> bool:
    """Controlla firma DOS MZ + firma PE\\0\\0 nell'header PE."""
    if not path.exists() or path.stat().st_size < 0x40:
        return False
    data = _head(path, 4096)
    if len(data) < 0x40:
        return False
    if data[:2] != b"MZ":
        return False
    e_lfanew = struct.unpack("<I", data[0x3C:0x40])[0]
    if e_lfanew + 4 > len(data):
        return False
    return data[e_lfanew:e_lfanew + 4] == b"PE\x00\x00"


# ---------------------------------------------------------------------------
# AML / ACPI
# ---------------------------------------------------------------------------

ACPI_SIGNATURES = (b"SSDT", b"DSDT", b"FACP", b"APIC", b"HPET", b"FADT", b"SDT ")
# I compiled SSDT di Dortania iniziano con "SSDT" (se richiesti dal profilo).
AML_SIGNATURES = (b"SSDT", b"DSDT")


def is_aml(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 4:
        return False
    return _head(path, 4) in AML_SIGNATURES


# ---------------------------------------------------------------------------
# Kext bundle
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    ok: bool
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "reason": self.reason, "details": self.details}


def validate_kext(kext_dir: Path) -> ValidationResult:
    """Validazione di un bundle .kext reale."""
    if not kext_dir.exists():
        return ValidationResult(False, "MISSING", {"path": str(kext_dir)})
    if not kext_dir.is_dir() or not kext_dir.name.endswith(".kext"):
        return ValidationResult(False, "NOT_A_KEXT_BUNDLE", {"path": str(kext_dir)})

    contents = kext_dir / "Contents"
    info_plist = contents / "Info.plist"
    if not contents.is_dir():
        return ValidationResult(False, "MISSING_CONTENTS", {"bundle": kext_dir.name})
    if not info_plist.exists() or info_plist.stat().st_size < 50:
        return ValidationResult(False, "MISSING_OR_EMPTY_INFO_PLIST", {"bundle": kext_dir.name})

    macos_dir = contents / "MacOS"
    executable: Optional[Path] = None
    if macos_dir.exists():
        for f in macos_dir.iterdir():
            if f.is_file() and f.stat().st_size > 0:
                executable = f
                break
    if executable is None:
        return ValidationResult(False, "MISSING_EXECUTABLE", {"bundle": kext_dir.name})

    if not is_macho(executable):
        return ValidationResult(
            False, "NOT_MACH_O",
            {"bundle": kext_dir.name, "executable": str(executable)},
        )
    if looks_placeholder(info_plist) or looks_placeholder(executable):
        return ValidationResult(False, "PLACEHOLDER", {"bundle": kext_dir.name})

    return ValidationResult(
        True, "",
        {
            "bundle": kext_dir.name,
            "info_plist": str(info_plist),
            "executable": str(executable),
            "executable_size": executable.stat().st_size,
        },
    )


def validate_efi_binary(path: Path) -> ValidationResult:
    """Validazione binario EFI (driver, OpenCore.efi, BOOTx64.efi)."""
    if not path.exists():
        return ValidationResult(False, "MISSING", {"path": str(path)})
    if path.stat().st_size < 100:
        return ValidationResult(False, "EMPTY_TOO_SMALL", {"path": str(path)})
    if not is_pe(path):
        return ValidationResult(False, "NOT_PE_COFF", {"path": str(path)})
    if looks_placeholder(path):
        return ValidationResult(False, "PLACEHOLDER", {"path": str(path)})
    return ValidationResult(True, "", {"path": str(path), "size": path.stat().st_size})


def validate_aml_file(path: Path) -> ValidationResult:
    if not path.exists():
        return ValidationResult(False, "MISSING", {"path": str(path)})
    if path.stat().st_size < 4:
        return ValidationResult(False, "EMPTY_TOO_SMALL", {"path": str(path)})
    if not is_aml(path):
        return ValidationResult(False, "INVALID_AML_SIGNATURE", {"path": str(path)})
    if looks_placeholder(path):
        return ValidationResult(False, "PLACEHOLDER", {"path": str(path)})
    return ValidationResult(True, "", {"path": str(path), "size": path.stat().st_size})


# ---------------------------------------------------------------------------
# Record di integrità (hash/versione/fonte)
# ---------------------------------------------------------------------------

@dataclass
class IntegrityRecord:
    name: str
    kind: str  # kext | driver | opencore | booter | aml
    status: str  # REAL | INVALID | MISSING
    sha256: str = ""
    version: str = ""
    source: str = ""
    url: str = ""
    size: int = 0
    downloaded_at: str = ""
    reason: str = ""
    path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def record_for_kext(kext_dir: Path, source: str = "", url: str = "", version: str = "") -> IntegrityRecord:
    res = validate_kext(kext_dir)
    details = res.details
    exec_path = details.get("executable")
    record = IntegrityRecord(
        name=kext_dir.name,
        kind="kext",
        status="REAL" if res.ok else ("INVALID" if kext_dir.exists() else "MISSING"),
        version=version,
        source=source,
        url=url,
        downloaded_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        reason=res.reason,
        path=str(kext_dir),
    )
    if res.ok and exec_path:
        record.sha256 = sha256_file(Path(exec_path))
        record.size = Path(exec_path).stat().st_size
    elif kext_dir.exists() and (kext_dir / "Contents" / "Info.plist").exists():
        record.sha256 = sha256_file(kext_dir / "Contents" / "Info.plist")
        record.size = (kext_dir / "Contents" / "Info.plist").stat().st_size
    return record


def record_for_binary(path: Path, name: str, kind: str, source: str = "", url: str = "", version: str = "") -> IntegrityRecord:
    res = validate_efi_binary(path)
    record = IntegrityRecord(
        name=name,
        kind=kind,
        status="REAL" if res.ok else ("INVALID" if path.exists() else "MISSING"),
        version=version,
        source=source,
        url=url,
        downloaded_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        reason=res.reason,
        path=str(path),
    )
    if res.ok:
        record.sha256 = sha256_file(path)
        record.size = path.stat().st_size
    return record


def record_for_aml(path: Path, source: str = "", url: str = "", version: str = "") -> IntegrityRecord:
    res = validate_aml_file(path)
    record = IntegrityRecord(
        name=path.name,
        kind="aml",
        status="REAL" if res.ok else ("INVALID" if path.exists() else "MISSING"),
        version=version,
        source=source,
        url=url,
        downloaded_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        reason=res.reason,
        path=str(path),
    )
    if res.ok:
        record.sha256 = sha256_file(path)
        record.size = path.stat().st_size
    return record


def collect_integrity_records(efi_root: Path, selection: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """Raccoglie i record di integrità per i componenti selezionati."""
    # Import locale per evitare cicli: efi.selection importa solo database.
    from efi.selection import DRIVER_FILES, KEXT_BUNDLES

    records: List[IntegrityRecord] = []
    efi_root = Path(efi_root)
    oc = efi_root / "OC"

    for name in selection.get("required_kexts", []) + selection.get("optional_kexts", []):
        bundle = KEXT_BUNDLES.get(name, name if name.endswith(".kext") else name + ".kext")
        records.append(record_for_kext(oc / "Kexts" / bundle, source="GitHub official"))

    for driver in selection.get("required_drivers", []) + selection.get("optional_drivers", []):
        fname = DRIVER_FILES.get(driver, driver if driver.endswith(".efi") else driver + ".efi")
        records.append(record_for_binary(oc / "Drivers" / fname, fname, "driver", source="OpenCorePkg"))

    records.append(record_for_binary(oc / "OpenCore.efi", "OpenCore.efi", "opencore", source="Acidanthera"))
    records.append(record_for_binary(efi_root / "BOOT" / "BOOTx64.efi", "BOOTx64.efi", "booter", source="Acidanthera"))

    for ssdt in selection.get("required_ssdts", []) + selection.get("optional_ssdts", []):
        aml = oc / "ACPI" / f"{ssdt}.aml"
        records.append(record_for_aml(aml, source="Dortania"))

    return [r.to_dict() for r in records]
