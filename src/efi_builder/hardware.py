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

# OpenCore drivers - solo quelli realmente necessari per Q556/2
# Dortania Skylake Desktop: HfsPlus + OpenRuntime sono REQUIRED
# OpenCanopy: opzionale per GUI, ResetNvramEntry: utile per debug
DRIVERS = {
    "HfsPlus": {
        "required": True, 
        "file": "HfsPlus.efi", 
        "desc": "HFS+ filesystem - REQUIRED per leggere installer macOS HFS+",
        "for_q5562": True
    },
    "OpenRuntime": {
        "required": True, 
        "file": "OpenRuntime.efi", 
        "desc": "Runtime services - REQUIRED sempre",
        "for_q5562": True
    },
    "OpenCanopy": {
        "required": False, 
        "file": "OpenCanopy.efi", 
        "desc": "GUI boot picker - opzionale, per avere interfaccia grafica invece di testo",
        "for_q5562": False,
        "note": "Utile ma non necessario. Se vuoi boot picker testuale, rimuovilo"
    },
    "ResetNvramEntry": {
        "required": False, 
        "file": "ResetNvramEntry.efi", 
        "desc": "Reset NVRAM entry - utile per debug, non per boot",
        "for_q5562": False,
        "note": "Utile se devi resettare NVRAM spesso durante test, altrimenti rimuovibile"
    },
    "OpenLinuxBoot": {
        "required": False, 
        "file": "OpenLinuxBoot.efi", 
        "desc": "Linux boot - solo se dual boot con Linux",
        "for_q5562": False,
        "note": "Non necessario per Q556/2 Hackintosh puro"
    },
}

# Drivers realmente necessari per Q556/2 minimal
Q556_2_REQUIRED_DRIVERS = ["HfsPlus", "OpenRuntime"]
Q556_2_OPTIONAL_DRIVERS = ["OpenCanopy", "ResetNvramEntry"]

# SSDTs - Corretti per Q556/2 basati su Dortania prebuilt table
# Per Skylake/Kaby Lake Desktop (Q556/2 H110, Q957 Q270): solo PLUG + EC-USBX-DESKTOP
# Per Coffee Lake (Q957 mod): + AWAC + PMC
# Vedi: https://deepwiki.com/dortania/Getting-Started-With-ACPI/3.1-prebuilt-ssdts
SSDTs = {
    "SSDT-PLUG-DRTNIA": {
        "required": True,
        "file": "SSDT-PLUG-DRTNIA.aml",
        "desc": "CPU power management - enables XCPM (Skylake/Kaby Lake)",
        "source": "Dortania",
        "url": "https://raw.githubusercontent.com/dortania/Getting-Started-With-ACPI/master/extra-files/compiled/SSDT-PLUG-DRTNIA.aml",
        "for_chipset": ["H110", "Q270", "H270", "Z270", "Q270", "B250"]
    },
    "SSDT-EC-USBX-DESKTOP": {
        "required": True,
        "file": "SSDT-EC-USBX-DESKTOP.aml",
        "desc": "Fix embedded controller + USB power - REQUIRED for all desktops",
        "source": "Dortania",
        "url": "https://raw.githubusercontent.com/dortania/Getting-Started-With-ACPI/master/extra-files/compiled/SSDT-EC-USBX-DESKTOP.aml",
        "for_chipset": ["H110", "Q270", "all"]
    },
    "SSDT-AWAC": {
        "required": False,
        "file": "SSDT-AWAC.aml",
        "desc": "Fix AWAC/RTC - ONLY for Coffee Lake+ (300 series) or boards with AWAC device. NOT needed for Q556/2 H110 Skylake",
        "source": "Dortania",
        "url": "https://raw.githubusercontent.com/dortania/Getting-Started-With-ACPI/master/extra-files/compiled/SSDT-AWAC.aml",
        "for_chipset": ["Z370", "Z390", "B360", "H310", "H370", "Q370"],
        "note": "Q556/2 H110 does NOT have AWAC, remove it. Only include if DSDT shows AWAC device"
    },
    "SSDT-PMC": {
        "required": False,
        "file": "SSDT-PMC.aml",
        "desc": "Fix NVRAM on 300 series (B360, H310, etc). H110 has native NVRAM, but Fujitsu might need it if NVRAM broken",
        "source": "Dortania",
        "url": "https://raw.githubusercontent.com/dortania/Getting-Started-With-ACPI/master/extra-files/compiled/SSDT-PMC.aml",
        "for_chipset": ["B360", "H310", "H370", "Z390", "Q370"],
        "note": "For Q556/2 H110, NVRAM is native with Aptio V. Include only if NVRAM test fails (no boot var). Many Q556/2 EFIs include it anyway, safe to include but not required"
    },
    "SSDT-RHUB": {
        "required": False,
        "file": "SSDT-RHUB.aml",
        "desc": "Fix USB RHUB - ONLY for Comet Lake+ (400 series)",
        "source": "Dortania",
        "url": "https://raw.githubusercontent.com/dortania/Getting-Started-With-ACPI/master/extra-files/compiled/SSDT-RHUB.aml",
        "for_chipset": ["Z490", "B460", "H410"],
        "note": "NOT needed for Q556/2"
    }
}

# SSDTs realmente necessari per Q556/2 (verificato su Dortania + hardware reale)
Q556_2_REQUIRED_SSDTS = ["SSDT-PLUG-DRTNIA", "SSDT-EC-USBX-DESKTOP"]
Q556_2_OPTIONAL_SSDTS = ["SSDT-PMC"]  # Opzionale se NVRAM non funziona
Q957_REQUIRED_SSDTS = ["SSDT-PLUG-DRTNIA", "SSDT-EC-USBX-DESKTOP"]
Q957_OPTIONAL_SSDTS = ["SSDT-PMC", "SSDT-AWAC"]  # Se mod Coffee Lake

# macOS versions support
MACOS_VERSIONS = {
    "Ventura 13.x": {"min_oc": "0.8.8", "smbios": ["iMac18,1", "iMac19,1", "Macmini8,1", "iMacPro1,1"], "recommended": True},
    "Monterey 12.x": {"min_oc": "0.7.6", "smbios": ["iMac17,1", "iMac18,1", "iMacPro1,1"], "recommended": True},
    "Sonoma 14.x": {"min_oc": "0.9.5", "smbios": ["iMacPro1,1", "Macmini8,1", "iMac19,1"], "recommended": True},
    "Sequoia 15.x": {"min_oc": "1.0.0", "smbios": ["iMacPro1,1", "Macmini8,1"], "recommended": False, "note": "Experimental, requires OCLP or extra patches"},
}

def get_kexts_for_profile(profile_name: str, include_wifi: bool = False, include_bluetooth: bool = False, include_optional: bool = False):
    """
    Ritorna kext realmente necessari per Q556/2
    Minimal: Lilu, VirtualSMC, WhateverGreen, AppleALC, RealtekRTL8111/IntelMausi
    Optional: NVMeFix, RestrictEvents, SMCProcessor, etc - solo se richiesti
    """
    profile = PROFILES.get(profile_name, Q556_2)
    # Solo kext essenziali per boot - verificati su Q556/2 reale
    kexts = ["Lilu", "VirtualSMC", "WhateverGreen", "AppleALC"]
    
    if profile.lan_kext == "RealtekRTL8111.kext":
        kexts.append("RealtekRTL8111")
    else:
        kexts.append("IntelMausi")
    
    # Opzionali solo se richiesti esplicitamente
    if include_optional:
        kexts.extend(["NVMeFix", "RestrictEvents"])
    
    if include_bluetooth:
        kexts.append("IntelBluetoothFirmware")
    if include_wifi:
        kexts.append("AirportItlwm")
    
    return kexts

def get_optional_kexts():
    """Kext opzionali per Q556/2 - utili ma non necessari per boot"""
    return ["NVMeFix", "RestrictEvents", "USBToolBox"]
