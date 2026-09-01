"""
Hardware profiles for Fujitsu Esprimo Q556/2 and Q957
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class HardwareProfile:
    name: str
    board: str
    chipset: str
    cpu_generations: List[str]
    igpu: str
    lan_chip: str
    lan_kext: str
    audio_codec: str
    audio_layout_ids: List[int]
    usb_ports: Dict[str, int]
    smbios_recommended: List[str]
    notes: str = ""

# Fujitsu Esprimo Q556/2 - Real hardware specs
Q556_2 = HardwareProfile(
    name="Fujitsu Esprimo Q556/2",
    board="D3403-U",
    chipset="Intel H110",
    cpu_generations=["Skylake (6th Gen)", "Kaby Lake (7th Gen)"],
    igpu="Intel HD Graphics 530 / 630",
    lan_chip="Realtek RTL8111GN",
    lan_kext="RealtekRTL8111.kext",
    audio_codec="Realtek ALC671",
    audio_layout_ids=[11, 13, 15, 21, 27, 28],
    usb_ports={"USB2": 2, "USB3": 4},
    smbios_recommended=["iMac17,1", "iMac18,1", "Macmini8,1", "iMacPro1,1"],
    notes="DVMT Pre-Allocated must be set to 64MB in BIOS. Requires framebuffer patch if not."
)

Q957 = HardwareProfile(
    name="Fujitsu Esprimo Q957",
    board="D3403-U2 / D3600",
    chipset="Intel Q270 / H110",
    cpu_generations=["Kaby Lake (7th Gen)", "Coffee Lake (8th/9th) with mod"],
    igpu="Intel HD Graphics 630",
    lan_chip="Intel I219-LM/V",
    lan_kext="IntelMausi.kext",
    audio_codec="Realtek ALC671 / ALC255",
    audio_layout_ids=[11, 13, 15, 21],
    usb_ports={"USB2": 2, "USB3": 6},
    smbios_recommended=["iMac18,1", "iMac19,1", "Macmini8,1", "iMacPro1,1"],
    notes="Similar to Q556/2 but with Intel LAN. Same EFI, just swap LAN kext."
)

PROFILES = {
    "Q556/2": Q556_2,
    "Q957": Q957,
}

# Kext definitions with real download URLs
KEXTS = {
    "Lilu": {
        "repo": "acidanthera/Lilu",
        "required": True,
        "description": "Patch engine for many kexts",
        "bundle": "Lilu.kext"
    },
    "VirtualSMC": {
        "repo": "acidanthera/VirtualSMC",
        "required": True,
        "description": "SMC emulation",
        "bundle": "VirtualSMC.kext",
        "extra_bundles": ["SMCProcessor.kext", "SMCSuperIO.kext", "SMCLightSensor.kext", "SMCBatteryManager.kext"]
    },
    "WhateverGreen": {
        "repo": "acidanthera/WhateverGreen",
        "required": True,
        "description": "Graphics patching",
        "bundle": "WhateverGreen.kext"
    },
    "AppleALC": {
        "repo": "acidanthera/AppleALC",
        "required": True,
        "description": "Audio patching for ALC671",
        "bundle": "AppleALC.kext"
    },
    "RealtekRTL8111": {
        "repo": "Mieze/RTL8111_driver_for_OS_X",
        "required": False,
        "description": "Realtek LAN for Q556/2",
        "bundle": "RealtekRTL8111.kext"
    },
    "IntelMausi": {
        "repo": "acidanthera/IntelMausi",
        "required": False,
        "description": "Intel LAN for Q957",
        "bundle": "IntelMausi.kext"
    },
    "IntelBluetoothFirmware": {
        "repo": "OpenIntelWireless/IntelBluetoothFirmware",
        "required": False,
        "description": "Intel Bluetooth",
        "bundle": "IntelBluetoothFirmware.kext",
        "extra_bundles": ["IntelBTPatcher.kext", "BlueToolFixup.kext"]
    },
    "AirportItlwm": {
        "repo": "OpenIntelWireless/itlwm",
        "required": False,
        "description": "Intel WiFi",
        "bundle": "AirportItlwm.kext"
    },
    "NVMeFix": {
        "repo": "acidanthera/NVMeFix",
        "required": False,
        "description": "NVMe power management",
        "bundle": "NVMeFix.kext"
    },
    "RestrictEvents": {
        "repo": "acidanthera/RestrictEvents",
        "required": False,
        "description": "Block unwanted processes",
        "bundle": "RestrictEvents.kext"
    },
    "USBToolBox": {
        "repo": "USBToolBox/kext",
        "required": False,
        "description": "USB mapping placeholder",
        "bundle": "USBToolBox.kext"
    }
}

# OpenCore drivers
DRIVERS = {
    "HfsPlus": {"required": True, "file": "HfsPlus.efi", "desc": "HFS+ filesystem"},
    "OpenRuntime": {"required": True, "file": "OpenRuntime.efi", "desc": "Runtime services"},
    "OpenCanopy": {"required": False, "file": "OpenCanopy.efi", "desc": "GUI boot picker"},
    "ResetNvramEntry": {"required": False, "file": "ResetNvramEntry.efi", "desc": "Reset NVRAM"},
    "OpenLinuxBoot": {"required": False, "file": "OpenLinuxBoot.efi", "desc": "Linux boot"},
}

# SSDTs for Q556/2 - based on Dortania Skylake Desktop guide.
# Hardening: SOLO gli SSDT realmente richiesti dal profilo. Niente "just in case".
SSDTs = {
    "SSDT-PLUG-DRTNIA": {
        "required": True,
        "desc": "CPU power management - enables XCPM (DRTNIA variant)",
        "source": "Dortania"
    },
    "SSDT-EC-USBX-DESKTOP": {
        "required": True,
        "desc": "Fix embedded controller + USB power (Desktop variant)",
        "source": "Dortania"
    },
}

# Opzionali, aggiunti SOLO se una regola di profilo li richiede esplicitamente.
SSDT_OPTIONAL = {
    "SSDT-AWAC": {
        "required": False,
        "desc": "Fix AWAC/RTC clocks",
        "source": "Dortania"
    },
    "SSDT-PMC": {
        "required": False,
        "desc": "Fix NVRAM on H110 (PMC)",
        "source": "Dortania"
    },
    "SSDT-RHUB": {
        "required": False,
        "desc": "Fix USB RHUB (optional)",
        "source": "Dortania"
    }
}

# macOS versions support
MACOS_VERSIONS = {
    "Ventura 13.x": {"min_oc": "0.8.8", "smbios": ["iMac18,1", "iMac19,1", "Macmini8,1", "iMacPro1,1"], "recommended": True},
    "Monterey 12.x": {"min_oc": "0.7.6", "smbios": ["iMac17,1", "iMac18,1", "iMacPro1,1"], "recommended": True},
    "Sonoma 14.x": {"min_oc": "0.9.5", "smbios": ["iMacPro1,1", "Macmini8,1", "iMac19,1"], "recommended": True},
    "Sequoia 15.x": {"min_oc": "1.0.0", "smbios": ["iMacPro1,1", "Macmini8,1"], "recommended": False, "note": "Experimental, requires OCLP or extra patches"},
}

def get_kexts_for_profile(profile_name: str,
                          include_wifi: bool = False,
                          include_bluetooth: bool = False,
                          include_nvme: bool = False,
                          include_restrict_events: bool = False):
    """Kext obbligatori del profilo + opzionali SOLO se richiesti esplicitamente."""
    profile = PROFILES.get(profile_name, Q556_2)
    kexts = ["Lilu", "VirtualSMC", "WhateverGreen", "AppleALC"]

    if profile.lan_kext == "RealtekRTL8111.kext":
        kexts.append("RealtekRTL8111")
    else:
        kexts.append("IntelMausi")

    # Opzionali: mai "just in case".
    if include_nvme:
        kexts.append("NVMeFix")
    if include_restrict_events:
        kexts.append("RestrictEvents")
    if include_bluetooth:
        kexts.append("IntelBluetoothFirmware")
    if include_wifi:
        kexts.append("AirportItlwm")

    return kexts
