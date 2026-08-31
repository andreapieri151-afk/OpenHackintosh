"""
Config.plist generator for Fujitsu Esprimo Q556/2
Based on Dortania Skylake Desktop guide
"""
import plistlib
from pathlib import Path
from typing import Dict, List
import uuid

def create_base_config() -> Dict:
    """Create base config.plist structure for Skylake Desktop"""
    config = {
        "ACPI": {
            "Add": [],
            "Delete": [],
            "Patch": [],
            "Quirks": {
                "FadtEnableReset": False,
                "NormalizeHeaders": False,
                "RebaseRegions": False,
                "ResetHwSig": False,
                "ResetLogoStatus": False,
                "SyncTableIds": False
            }
        },
        "Booter": {
            "MmioWhitelist": [],
            "Patch": [],
            "Quirks": {
                "AllowRelocationBlock": False,
                "AvoidRuntimeDefrag": True,
                "DevirtualiseMmio": False,
                "DisableSingleUser": False,
                "DisableVariableWrite": False,
                "DiscardHibernateMap": False,
                "EnableSafeModeSlide": True,
                "EnableWriteUnprotector": True,
                "ForceBooterSignature": False,
                "ForceExitBootServices": False,
                "ProtectMemoryRegions": False,
                "ProtectSecureBoot": False,
                "ProtectUefiServices": False,
                "ProvideCustomSlide": True,
                "ProvideMaxSlide": 0,
                "RebuildAppleMemoryMap": True,
                "ResizeAppleGpuBars": -1,
                "SetupVirtualMap": True,
                "SignalAppleOS": False,
                "SyncRuntimePermissions": True
            }
        },
        "DeviceProperties": {
            "Add": {
                "PciRoot(0x0)/Pci(0x2,0x0)": {
                    "AAPL,ig-platform-id": bytes.fromhex("00001219"),
                    "framebuffer-patch-enable": bytes.fromhex("01000000"),
                    "framebuffer-stolenmem": bytes.fromhex("00003001"),
                    "framebuffer-fbmem": bytes.fromhex("00009000"),
                    "device-id": bytes.fromhex("12190000")
                }
            },
            "Delete": {}
        },
        "Kernel": {
            "Add": [],
            "Block": [],
            "Emulate": {
                "Cpuid1Data": bytes(0),
                "Cpuid1Mask": bytes(0),
                "DummyPowerManagement": False,
                "MaxKernel": "",
                "MinKernel": ""
            },
            "Force": [],
            "Patch": [],
            "Quirks": {
                "AppleCpuPmCfgLock": False,
                "AppleXcpmCfgLock": True,
                "AppleXcpmExtraMsrs": False,
                "AppleXcpmForceBoost": False,
                "CustomSMBIOSGuid": False,
                "DisableIoMapper": True,
                "DisableLinkeditJettison": True,
                "DisableRtcChecksum": False,
                "ExtendBTFeatureFlags": False,
                "ExternalDiskIcons": False,
                "ForceAquantiaEthernet": False,
                "ForceSecureBootScheme": False,
                "IncreasePciBarSize": False,
                "LapicKernelPanic": False,
                "LegacyCommpage": False,
                "PanicNoKextDump": True,
                "PowerTimeoutKernelPanic": True,
                "ProvideCurrentCpuInfo": False,
                "SetApfsTrimTimeout": -1,
                "ThirdPartyDrives": False,
                "XhciPortLimit": False
            },
            "Scheme": {
                "CustomKernel": False,
                "FuzzyMatch": True,
                "KernelArch": "x86_64",
                "KernelCache": "Auto"
            }
        },
        "Misc": {
            "BlessOverride": [],
            "Boot": {
                "ConsoleAttributes": 0,
                "HibernateMode": "None",
                "HideAuxiliary": False,
                "LauncherOption": "Disabled",
                "LauncherPath": "Default",
                "PickerAttributes": 17,
                "PickerAudioAssist": False,
                "PickerMode": "Builtin",
                "PickerVariant": "Auto",
                "ShowPicker": True,
                "TakeoffDelay": 0,
                "Timeout": 5
            },
            "Debug": {
                "AppleDebug": True,
                "ApplePanic": True,
                "DisableWatchDog": True,
                "DisplayDelay": 0,
                "DisplayLevel": 2147483650,
                "SerialInit": False,
                "SysReport": False,
                "Target": 67
            },
            "Entries": [],
            "Security": {
                "AllowNvramReset": True,
                "AllowSetDefault": True,
                "AllowToggleSip": False,
                "ApECID": 0,
                "AuthRestart": False,
                "BlacklistAppleUpdate": True,
                "DmgLoading": "Signed",
                "EnablePassword": False,
                "ExposeSensitiveData": 6,
                "HaltLevel": 2147483648,
                "PasswordHash": bytes(0),
                "PasswordSalt": bytes(0),
                "ScanPolicy": 0,
                "SecureBootModel": "Disabled",
                "Vault": "Optional"
            },
            "Serial": {
                "Custom": {},
                "Init": False,
                "Override": False
            },
            "Tools": []
        },
        "NVRAM": {
            "Add": {
                "4D1EDE05-38C7-4A6A-9CC6-4BCCA8B38C14": {
                    "DefaultBackgroundColor": bytes.fromhex("00000000"),
                    "UIScale": bytes.fromhex("01")
                },
                "4D1FDA02-38C7-4A6A-9CC6-4BCCA8B30102": {
                    "rtc-blacklist": bytes(0)
                },
                "7C436110-AB2A-4BBB-A880-FE41995C9F82": {
                    "SystemAudioVolume": bytes.fromhex("46"),
                    "boot-args": "alcid=11",
                    "csr-active-config": bytes.fromhex("00000000"),
                    "prev-lang:kbd": bytes.fromhex("656E2D55533A30")
                }
            },
            "Delete": {
                "4D1EDE05-38C7-4A6A-9CC6-4BCCA8B38C14": [],
                "4D1FDA02-38C7-4A6A-9CC6-4BCCA8B30102": [],
                "7C436110-AB2A-4BBB-A880-FE41995C9F82": ["boot-args", "csr-active-config"]
            },
            "LegacyEnable": False,
            "LegacyOverwrite": False,
            "LegacySchema": {},
            "WriteFlash": True
        },
        "PlatformInfo": {
            "Automatic": True,
            "CustomMemory": False,
            "DataHub": {
                "ARTFrequency": 0,
                "BoardProduct": "",
                "BoardRevision": bytes(0),
                "DevicePathsSupported": 0,
                "FSBFrequency": 0,
                "InitialTSC": 0,
                "PlatformName": "",
                "SmcBranch": bytes(0),
                "SmcPlatform": bytes(0),
                "SmcRevision": bytes(0),
                "StartupPowerEvents": 0
            },
            "Generic": {
                "AdviseFeatures": False,
                "MaxBIOSVersion": False,
                "MLB": "",
                "ProcessorType": 0,
                "ROM": bytes.fromhex("112233000000"),
                "SpoofVendor": True,
                "SystemMemoryStatus": "Auto",
                "SystemProductName": "iMac18,1",
                "SystemSerialNumber": "",
                "SystemUUID": ""
            },
            "Memory": {
                "DataWidth": 0,
                "Devices": [],
                "ErrorCorrection": 0,
                "FormFactor": 0,
                "MaxCapacity": 0,
                "TotalWidth": 0,
                "Type": 0,
                "TypeDetail": 0
            },
            "PlatformNVRAM": {
                "BID": "",
                "FirmwareFeatures": bytes(0),
                "FirmwareFeaturesMask": bytes(0),
                "MLB": "",
                "ROM": bytes(0),
                "SystemSerialNumber": "",
                "SystemUUID": ""
            },
            "SMBIOS": {
                "BIOSReleaseDate": "",
                "BIOSVendor": "",
                "BIOSVersion": "",
                "BoardAssetTag": "",
                "BoardLocationInChassis": "",
                "BoardManufacturer": "",
                "BoardProduct": "",
                "BoardSerialNumber": "",
                "BoardType": 0,
                "BoardVersion": "",
                "ChassisAssetTag": "",
                "ChassisManufacturer": "",
                "ChassisSerialNumber": "",
                "ChassisType": 0,
                "ChassisVersion": "",
                "FirmwareFeatures": bytes(0),
                "FirmwareFeaturesMask": bytes(0),
                "PlatformFeature": -1,
                "ProcessorType": 0,
                "SmcVersion": bytes(0),
                "SystemFamily": "",
                "SystemManufacturer": "",
                "SystemProductName": "",
                "SystemSKUNumber": "",
                "SystemSerialNumber": "",
                "SystemUUID": "",
                "SystemVersion": ""
            },
            "UpdateDataHub": True,
            "UpdateNVRAM": True,
            "UpdateSMBIOS": True,
            "UpdateSMBIOSMode": "Create",
            "UseRawUuidEncoding": False
        },
        "UEFI": {
            "APFS": {
                "EnableJumpstart": True,
                "GlobalConnect": False,
                "HideVerbose": True,
                "JumpstartHotPlug": False,
                "MinDate": 0,
                "MinVersion": 0
            },
            "AppleInput": {
                "AppleEvent": "Auto",
                "CustomDelays": False,
                "GraphicsInputMirroring": True,
                "KeyInitialDelay": 50,
                "KeySubsequentDelay": 5,
                "PointerSpeedDiv": 1,
                "PointerSpeedMul": 1
            },
            "Audio": {
                "AudioCodec": 0,
                "AudioDevice": "",
                "AudioOutMask": 1,
                "AudioSupport": False,
                "DisconnectHda": False,
                "MaximumGain": -15,
                "MinimumAssistGain": -30,
                "MinimumAudibleGain": -55,
                "PlayChime": "Auto",
                "ResetTrafficClass": False,
                "SetupDelay": 0
            },
            "ConnectDrivers": True,
            "Drivers": [],
            "Input": {
                "KeyFiltering": False,
                "KeyForgetThreshold": 5,
                "KeySupport": True,
                "KeySupportMode": "Auto",
                "KeySwap": False,
                "PointerSupport": False,
                "PointerSupportMode": "",
                "TimerResolution": 50000
            },
            "Output": {
                "ClearScreenOnModeSwitch": False,
                "ConsoleMode": "",
                "DirectGopRendering": False,
                "ForceResolution": False,
                "GopBurstMode": False,
                "GopPassThrough": "Disabled",
                "IgnoreTextInGraphics": False,
                "ProvideConsoleGop": True,
                "ReconnectGraphicsOnConnect": False,
                "ReconnectOnResChange": False,
                "ReplaceTabWithSpace": False,
                "Resolution": "",
                "SanitiseClearScreen": False,
                "TextRenderer": "BuiltinGraphics",
                "UgaPassThrough": False
            },
            "ProtocolOverrides": {
                "AppleAudio": False,
                "AppleBootPolicy": False,
                "AppleDebugLog": False,
                "AppleEg2Info": False,
                "AppleFramebufferInfo": False,
                "AppleImageConversion": False,
                "AppleImg4Verification": False,
                "AppleKeyMap": False,
                "AppleRtcRam": False,
                "AppleSecureBoot": False,
                "AppleSmcIo": False,
                "AppleUserInterfaceTheme": False,
                "DataHub": False,
                "DeviceProperties": False,
                "FirmwareVolume": True,
                "HashServices": False,
                "OSInfo": False,
                "UnicodeCollation": False
            },
            "Quirks": {
                "ActivateHpetSupport": False,
                "DisableSecurityPolicy": False,
                "EnableVectorAcceleration": True,
                "EnableVmx": False,
                "ExitBootServicesDelay": 0,
                "ForceBooterSignature": False,
                "ForgeUefiSupport": False,
                "IgnoreInvalidFlexRatio": False,
                "ReleaseUsbOwnership": True,
                "ReloadOptionRoms": False,
                "RequestBootVarRouting": True,
                "ResizeGpuBars": -1,
                "TscSyncTimeout": 0,
                "UnblockFsConnect": False
            },
            "ReservedMemory": []
        }
    }
    return config

def add_kexts_to_config(config: Dict, kexts_dir: Path) -> Dict:
    """Add kexts found in directory to config.plist"""
    if not kexts_dir.exists():
        return config
    
    kexts = []
    for kext_path in sorted(kexts_dir.glob("*.kext")):
        # Read Info.plist to get bundle info
        info_plist = kext_path / "Contents" / "Info.plist"
        bundle_id = ""
        executable = ""
        if info_plist.exists():
            try:
                with open(info_plist, 'rb') as f:
                    info = plistlib.load(f)
                    bundle_id = info.get("CFBundleIdentifier", "")
                    # Find executable
                    exec_path = info.get("CFBundleExecutable", "")
                    if exec_path:
                        # Check common locations
                        possible = [
                            f"Contents/MacOS/{exec_path}",
                            f"Contents/MacOS/{kext_path.name.split('.')[0]}",
                        ]
                        for p in possible:
                            if (kext_path / p).exists():
                                executable = p
                                break
                        if not executable:
                            # Search
                            for macos_file in (kext_path / "Contents" / "MacOS").glob("*") if (kext_path / "Contents" / "MacOS").exists() else []:
                                if macos_file.is_file():
                                    executable = f"Contents/MacOS/{macos_file.name}"
                                    break
            except:
                pass
        
        # Default executable path if not found
        if not executable:
            # Check if plist-only kext
            has_executable = (kext_path / "Contents" / "MacOS").exists() and any((kext_path / "Contents" / "MacOS").iterdir())
            if has_executable:
                # Try to guess
                executable = f"Contents/MacOS/{kext_path.name.replace('.kext','')}"
            else:
                executable = ""
        
        kext_entry = {
            "Arch": "x86_64",
            "BundlePath": kext_path.name,
            "Comment": bundle_id or kext_path.name,
            "Enabled": True,
            "ExecutablePath": executable,
            "MaxKernel": "",
            "MinKernel": "",
            "PlistPath": "Contents/Info.plist"
        }
        kexts.append(kext_entry)
    
    # Sort with Lilu first
    def kext_sort_key(k):
        name = k["BundlePath"]
        order = {
            "Lilu.kext": 0,
            "VirtualSMC.kext": 1,
            "WhateverGreen.kext": 2,
            "AppleALC.kext": 3,
        }
        return (order.get(name, 99), name)
    
    kexts.sort(key=kext_sort_key)
    config["Kernel"]["Add"] = kexts
    return config

def add_acpi_to_config(config: Dict, acpi_dir: Path) -> Dict:
    """Add SSDTs to config"""
    if not acpi_dir.exists():
        return config
    
    acpi_entries = []
    for aml in sorted(acpi_dir.glob("*.aml")):
        entry = {
            "Comment": aml.stem,
            "Enabled": True,
            "Path": aml.name
        }
        acpi_entries.append(entry)
    
    config["ACPI"]["Add"] = acpi_entries
    return config

def add_drivers_to_config(config: Dict, drivers_dir: Path) -> Dict:
    """Add drivers to config"""
    if not drivers_dir.exists():
        return config
    
    drivers = []
    # Required order
    order = ["HfsPlus.efi", "OpenRuntime.efi", "OpenCanopy.efi", "ResetNvramEntry.efi"]
    
    found_drivers = {f.name: f for f in drivers_dir.glob("*.efi")}
    
    for driver_name in order:
        if driver_name in found_drivers:
            entry = {
                "Arguments": "",
                "Comment": driver_name,
                "Enabled": True,
                "LoadEarly": driver_name == "OpenRuntime.efi",
                "Path": driver_name
            }
            drivers.append(entry)
    
    # Add any other drivers
    for name, path in found_drivers.items():
        if name not in order:
            entry = {
                "Arguments": "",
                "Comment": name,
                "Enabled": True,
                "LoadEarly": False,
                "Path": name
            }
            drivers.append(entry)
    
    config["UEFI"]["Drivers"] = drivers
    return config

def set_smbios(config: Dict, smbios_data: Dict) -> Dict:
    """Set SMBIOS data"""
    generic = config["PlatformInfo"]["Generic"]
    generic["SystemProductName"] = smbios_data.get("ProductName", "iMac18,1")
    generic["SystemSerialNumber"] = smbios_data.get("SerialNumber", "")
    generic["MLB"] = smbios_data.get("MLB", "")
    generic["SystemUUID"] = smbios_data.get("SystemUUID", "")
    
    # ROM is hex string to bytes
    rom_hex = smbios_data.get("ROM", "112233445566")
    try:
        generic["ROM"] = bytes.fromhex(rom_hex)
    except:
        generic["ROM"] = bytes.fromhex("112233445566")
    
    return config

def set_boot_args(config: Dict, profile_name: str, audio_layout: int = 11, extra_args: str = "", dev: bool = False) -> Dict:
    """Set boot-args for Q556/2. In release niente argomenti di debug."""
    if dev:
        base_args = f"-v keepsyms=1 debug=0x100 alcid={audio_layout}"
    else:
        base_args = f"alcid={audio_layout}"
    if extra_args:
        base_args += f" {extra_args}"
    
    # Add specific args for Q556/2
    # igfxonln=1 for online fix, etc
    config["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]["boot-args"] = base_args
    return config

def set_device_properties(config: Dict, profile_name: str) -> Dict:
    """Set device properties for HD 530"""
    # For Q556/2 with HD 530
    igpu_props = {
        "AAPL,ig-platform-id": bytes.fromhex("00001219"),
        "framebuffer-patch-enable": bytes.fromhex("01000000"),
        "framebuffer-stolenmem": bytes.fromhex("00003001"),
        "framebuffer-fbmem": bytes.fromhex("00009000"),
        "device-id": bytes.fromhex("12190000"),
        "enable-hdmi20": bytes.fromhex("01000000"),
        "framebuffer-con1-enable": bytes.fromhex("01000000"),
        "framebuffer-con1-type": bytes.fromhex("00080000"),
    }
    
    # If 7th gen, use different platform-id
    if "Kaby" in profile_name or "Q957" in profile_name:
        igpu_props["AAPL,ig-platform-id"] = bytes.fromhex("00001259")
        igpu_props["device-id"] = bytes.fromhex("12590000")
    
    config["DeviceProperties"]["Add"]["PciRoot(0x0)/Pci(0x2,0x0)"] = igpu_props
    return config

def generate_config(
    efi_root: Path,
    smbios_data: Dict,
    profile_name: str = "Q556/2",
    audio_layout: int = 11,
    macos_version: str = "Ventura 13.x"
) -> Dict:
    """Generate complete config.plist"""
    config = create_base_config()
    
    oc_dir = efi_root / "OC"
    kexts_dir = oc_dir / "Kexts"
    acpi_dir = oc_dir / "ACPI"
    drivers_dir = oc_dir / "Drivers"
    
    config = add_kexts_to_config(config, kexts_dir)
    config = add_acpi_to_config(config, acpi_dir)
    config = add_drivers_to_config(config, drivers_dir)
    config = set_smbios(config, smbios_data)
    config = set_boot_args(config, profile_name, audio_layout)
    config = set_device_properties(config, profile_name)
    
    # Adjust for macOS version
    if "Sonoma" in macos_version or "Sequoia" in macos_version:
        config["PlatformInfo"]["Generic"]["SystemProductName"] = smbios_data.get("ProductName", "iMacPro1,1")
        config["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]["boot-args"] += " -lilubetaall -wegbeta"
        config["UEFI"]["APFS"]["MinDate"] = -1
        config["UEFI"]["APFS"]["MinVersion"] = -1
    elif "Ventura" in macos_version:
        config["UEFI"]["APFS"]["MinDate"] = 0
        config["UEFI"]["APFS"]["MinVersion"] = 0
    
    # SecureBootModel for compatibility
    if smbios_data.get("ProductName", "") in ["iMacPro1,1", "MacPro7,1"]:
        config["Misc"]["Security"]["SecureBootModel"] = "j137" if "iMacPro" in smbios_data.get("ProductName", "") else "Disabled"
    else:
        config["Misc"]["Security"]["SecureBootModel"] = "Disabled"
    
    return config

def save_config(config: Dict, dest_path: Path):
    """Save config.plist"""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, 'wb') as f:
        plistlib.dump(config, f, sort_keys=False)
    print(f"Config saved to {dest_path}")

# For testing
if __name__ == "__main__":
    import tempfile
    from .smbios import generate_smbios
    smbios = generate_smbios("iMac18,1")
    config = create_base_config()
    config = set_smbios(config, smbios)
    print("Config generated")
