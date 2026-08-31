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
    include_nvme: bool = False,
    include_restrict_events: bool = False,
    include_usb_toolbox: bool = False,
    include_optional_drivers: bool = False,
) -> ComponentSelection:
    """Seleziona i componenti a partire dal profilo. Nessun componente 'just in case'.

    Di default vengono inclusi SOLO i REQUIRED. Ogni opzionale (kext, driver, SSDT)
    entra esclusivamente se abilitato esplicitamente dal chiamante.
    """
    sel = ComponentSelection(
        required_kexts=list(profile.required_kexts),
        # Optional si parte vuoto: vanno abilitati su richiesta, mai "just in case".
        optional_kexts=[],
        required_drivers=list(profile.required_drivers),
        optional_drivers=[] if not include_optional_drivers else list(profile.optional_drivers),
        required_ssdts=list(profile.required_ssdts),
        optional_ssdts=[],
    )

    # Aggiunge gli opzionali SOLO se richiesti esplicitamente.
    if include_wifi and "AirportItlwm" in profile.optional_kexts:
        sel.optional_kexts.append("AirportItlwm")
    if include_bluetooth and "IntelBluetoothFirmware" in profile.optional_kexts:
        sel.optional_kexts.append("IntelBluetoothFirmware")
    if include_nvme and "NVMeFix" in profile.optional_kexts:
        sel.optional_kexts.append("NVMeFix")
    if include_restrict_events and "RestrictEvents" in profile.optional_kexts:
        sel.optional_kexts.append("RestrictEvents")
    if include_usb_toolbox and "USBToolBox" in profile.optional_kexts:
        sel.optional_kexts.append("USBToolBox")

    return sel
