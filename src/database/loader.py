"""
Caricamento dei profili hardware dal database (hardware_profiles).

Ogni profilo e' un JSON autonomo. Il core del programma non deve cambiare
per aggiungere un nuovo computer: basta aggiungere una cartella con profile.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


DB_DIR = Path(__file__).parent / "profiles"

VALID_STATES = {"VERIFIED", "DOCUMENTED", "UNSUPPORTED", "UNKNOWN"}


@dataclass
class HardwareProfile:
    id: str
    name: str
    manufacturer: str = ""
    model: str = ""
    aliases: List[str] = field(default_factory=list)
    board: Dict[str, Any] = field(default_factory=dict)
    chipset: str = ""
    cpu: Dict[str, Any] = field(default_factory=dict)
    gpu: Dict[str, Any] = field(default_factory=dict)
    audio: Dict[str, Any] = field(default_factory=dict)
    ethernet: Dict[str, Any] = field(default_factory=dict)
    wifi: Dict[str, Any] = field(default_factory=dict)
    bluetooth: Dict[str, Any] = field(default_factory=dict)
    usb: Dict[str, Any] = field(default_factory=dict)
    storage: Dict[str, Any] = field(default_factory=dict)
    smbios: Dict[str, Any] = field(default_factory=dict)
    required_kexts: List[str] = field(default_factory=list)
    optional_kexts: List[str] = field(default_factory=list)
    required_drivers: List[str] = field(default_factory=list)
    optional_drivers: List[str] = field(default_factory=list)
    required_ssdts: List[str] = field(default_factory=list)
    optional_ssdts: List[str] = field(default_factory=list)
    device_properties: Dict[str, Any] = field(default_factory=dict)
    booter_quirks: Dict[str, Any] = field(default_factory=dict)
    kernel_quirks: Dict[str, Any] = field(default_factory=dict)
    nvram: Dict[str, Any] = field(default_factory=dict)
    uefi: Dict[str, Any] = field(default_factory=dict)
    macos_compatibility: Dict[str, Any] = field(default_factory=dict)
    bios_configuration: List[Dict[str, Any]] = field(default_factory=list)
    compatibility: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)
    notes: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def state(self) -> str:
        raw_state = str(self.compatibility.get("state", "UNKNOWN")).upper()
        return raw_state if raw_state in VALID_STATES else "UNKNOWN"

    @property
    def verified(self) -> bool:
        return self.state == "VERIFIED"

    @property
    def requires_hardware_testing(self) -> bool:
        return bool(self.compatibility.get("requires_hardware_testing", self.state != "VERIFIED"))

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop("raw", None)
        data["state"] = self.state
        data["verified"] = self.verified
        data["requires_hardware_testing"] = self.requires_hardware_testing
        return data


class ProfileLoadError(Exception):
    pass


def load_profile(path: Path) -> HardwareProfile:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ProfileLoadError(f"Impossibile leggere {path}: {exc}") from exc

    profile = HardwareProfile(
        id=raw.get("id", path.parent.name),
        name=raw.get("name", path.parent.name),
        manufacturer=raw.get("manufacturer", ""),
        model=raw.get("model", ""),
        aliases=raw.get("aliases", []),
        board=raw.get("board", {}),
        chipset=raw.get("chipset", ""),
        cpu=raw.get("cpu", {}),
        gpu=raw.get("gpu", {}),
        audio=raw.get("audio", {}),
        ethernet=raw.get("ethernet", {}),
        wifi=raw.get("wifi", {}),
        bluetooth=raw.get("bluetooth", {}),
        usb=raw.get("usb", {}),
        storage=raw.get("storage", {}),
        smbios=raw.get("smbios", {}),
        required_kexts=raw.get("required_kexts", []),
        optional_kexts=raw.get("optional_kexts", []),
        required_drivers=raw.get("required_drivers", []),
        optional_drivers=raw.get("optional_drivers", []),
        required_ssdts=raw.get("required_ssdts", []),
        optional_ssdts=raw.get("optional_ssdts", []),
        device_properties=raw.get("device_properties", {}),
        booter_quirks=raw.get("booter_quirks", {}),
        kernel_quirks=raw.get("kernel_quirks", {}),
        nvram=raw.get("nvram", {}),
        uefi=raw.get("uefi", {}),
        macos_compatibility=raw.get("macos_compatibility", {}),
        bios_configuration=raw.get("bios_configuration", []),
        compatibility=raw.get("compatibility", {}),
        limitations=raw.get("limitations", []),
        notes=raw.get("notes", ""),
        raw=raw,
    )
    return profile


def load_all_profiles(db_dir: Optional[Path] = None, include_unknown: bool = True) -> Dict[str, HardwareProfile]:
    db_dir = db_dir or DB_DIR
    profiles: Dict[str, HardwareProfile] = {}
    if not db_dir.exists():
        return profiles
    for profile_dir in sorted(db_dir.iterdir()):
        if not profile_dir.is_dir():
            continue
        profile_json = profile_dir / "profile.json"
        if profile_json.exists():
            try:
                profile = load_profile(profile_json)
                profiles[profile.id] = profile
            except ProfileLoadError:
                if include_unknown:
                    continue
                raise
    return profiles


def get_profile(profile_id: str, db_dir: Optional[Path] = None) -> Optional[HardwareProfile]:
    return load_all_profiles(db_dir=db_dir).get(profile_id)
