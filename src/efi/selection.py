"""
Selezione componenti dettata da hardware + profilo.

Filosofia:
    Hardware -> Profilo -> Regole -> Componenti necessari -> EFI personalizzata.

Vengono inclusi SOLO i componenti necessari. Gli opzionali restano separati
e vengono inclusi solo su richiesta esplicita (cli switch o config).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from database import HardwareProfile

# Nomi logici -> file EFI dentro OC/Drivers
DRIVER_FILES = {
    "HfsPlus": "HfsPlus.efi",
    "OpenRuntime": "OpenRuntime.efi",
    "OpenCanopy": "OpenCanopy.efi",
    "ResetNvramEntry": "ResetNvramEntry.efi",
    "OpenLinuxBoot": "OpenLinuxBoot.efi",
}

# Nomi logici -> bundle kext (usato solo per verificare; il downloader usa i repo)
KEXT_BUNDLES = {
    "Lilu": "Lilu.kext",
    "VirtualSMC": "VirtualSMC.kext",
    "WhateverGreen": "WhateverGreen.kext",
    "AppleALC": "AppleALC.kext",
    "RealtekRTL8111": "RealtekRTL8111.kext",
    "IntelMausi": "IntelMausi.kext",
    "NVMeFix": "NVMeFix.kext",
    "RestrictEvents": "RestrictEvents.kext",
    "AirportItlwm": "AirportItlwm.kext",
    "IntelBluetoothFirmware": "IntelBluetoothFirmware.kext",
    "USBToolBox": "USBToolBox.kext",
}


@dataclass
class ComponentSelection:
    required_kexts: List[str] = field(default_factory=list)
    optional_kexts: List[str] = field(default_factory=list)
    required_drivers: List[str] = field(default_factory=list)
    optional_drivers: List[str] = field(default_factory=list)
    required_ssdts: List[str] = field(default_factory=list)
    optional_ssdts: List[str] = field(default_factory=list)

    def kexts(self) -> List[str]:
        return self.required_kexts + self.optional_kexts

    def drivers(self) -> List[str]:
        return self.required_drivers + self.optional_drivers

    def ssdts(self) -> List[str]:
        return self.required_ssdts + self.optional_ssdts

    def driver_files(self) -> List[str]:
        return [DRIVER_FILES.get(d, d) for d in self.drivers()]

    def to_dict(self) -> Dict[str, List[str]]:
        return {
            "required_kexts": self.required_kexts,
            "optional_kexts": self.optional_kexts,
            "required_drivers": self.required_drivers,
            "optional_drivers": self.optional_drivers,
            "required_ssdts": self.required_ssdts,
            "optional_ssdts": self.optional_ssdts,
        }


def select_components(
    profile: HardwareProfile,
    include_wifi: bool = False,
    include_bluetooth: bool = False,
    include_nvme: bool = True,
    include_restrict_events: bool = True,
    include_usb_toolbox: bool = False,
) -> ComponentSelection:
    """Seleziona i componenti a partire dal profilo. Non include cose inutili."""
    sel = ComponentSelection(
        required_kexts=list(profile.required_kexts),
        optional_kexts=list(profile.optional_kexts),
        required_drivers=list(profile.required_drivers),
        optional_drivers=list(profile.optional_drivers),
        required_ssdts=list(profile.required_ssdts),
        optional_ssdts=list(profile.optional_ssdts),
    )

    # Filtro opzionali che non devono entrare di default
    optional_excluded: List[str] = []
    if not include_wifi:
        optional_excluded.append("AirportItlwm")
    if not include_bluetooth:
        optional_excluded.append("IntelBluetoothFirmware")
    if not include_nvme:
        optional_excluded.append("NVMeFix")
    if not include_restrict_events:
        optional_excluded.append("RestrictEvents")
    if not include_usb_toolbox:
        optional_excluded.append("USBToolBox")

    # Driver OpenCanopy e' opzionale: non incluso di default per EFI minimale
    optional_driver_excluded = ["OpenCanopy", "OpenLinuxBoot"]
    sel.optional_drivers = [
        d for d in sel.optional_drivers if d not in optional_driver_excluded
    ]

    sel.optional_kexts = [
        k for k in sel.optional_kexts if k not in optional_excluded
    ]
    return sel
