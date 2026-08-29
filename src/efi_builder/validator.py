"""
EFI Validator - checks if EFI is valid
"""
from pathlib import Path
import plistlib

def validate_efi(efi_root: Path) -> dict:
    """Validate EFI structure"""
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "checks": {}
    }
    
    # Check structure
    required_paths = [
        efi_root / "BOOT" / "BOOTx64.efi",
        efi_root / "OC" / "OpenCore.efi",
        efi_root / "OC" / "config.plist",
        efi_root / "OC" / "Drivers",
        efi_root / "OC" / "Kexts",
        efi_root / "OC" / "ACPI",
    ]
    
    for p in required_paths:
        exists = p.exists()
        results["checks"][str(p.relative_to(efi_root))] = exists
        if not exists:
            if p.suffix in [".efi", ".plist"]:
                results["errors"].append(f"Missing required: {p.relative_to(efi_root)}")
                results["valid"] = False
            else:
                results["warnings"].append(f"Missing: {p.relative_to(efi_root)}")
    
    # Check config.plist
    config_path = efi_root / "OC" / "config.plist"
    if config_path.exists():
        try:
            with open(config_path, 'rb') as f:
                config = plistlib.load(f)
            
            # Check kexts
            kexts = config.get("Kernel", {}).get("Add", [])
            if not kexts:
                results["warnings"].append("No kexts in config.plist")
            else:
                # Check Lilu first
                if kexts and kexts[0].get("BundlePath") != "Lilu.kext":
                    results["warnings"].append("Lilu.kext should be first in Kernel/Add")
            
            # Check SMBIOS
            smbios = config.get("PlatformInfo", {}).get("Generic", {})
            if not smbios.get("SystemSerialNumber"):
                results["errors"].append("Missing SystemSerialNumber")
                results["valid"] = False
            if not smbios.get("MLB"):
                results["errors"].append("Missing MLB")
                results["valid"] = False
            
            results["checks"]["config.plist readable"] = True
            results["checks"]["kexts count"] = len(kexts)
            
        except Exception as e:
            results["errors"].append(f"Invalid config.plist: {e}")
            results["valid"] = False
            results["checks"]["config.plist readable"] = False
    else:
        results["checks"]["config.plist readable"] = False
    
    # Check kexts actually exist
    kexts_dir = efi_root / "OC" / "Kexts"
    if kexts_dir.exists():
        kexts_found = list(kexts_dir.glob("*.kext"))
        results["checks"]["kexts found"] = len(kexts_found)
        if len(kexts_found) == 0:
            results["errors"].append("No kexts found in OC/Kexts")
            results["valid"] = False
        
        # Check for fake/empty kexts
        for kext in kexts_found:
            info = kext / "Contents" / "Info.plist"
            if not info.exists():
                results["warnings"].append(f"{kext.name} missing Info.plist - might be fake/empty")
            else:
                # Check size
                if info.stat().st_size < 100:
                    results["warnings"].append(f"{kext.name} Info.plist too small - might be fake")
    
    # Check drivers
    drivers_dir = efi_root / "OC" / "Drivers"
    if drivers_dir.exists():
        drivers = list(drivers_dir.glob("*.efi"))
        results["checks"]["drivers found"] = len(drivers)
        if len(drivers) == 0:
            results["warnings"].append("No drivers in OC/Drivers")
    
    # Check ACPI
    acpi_dir = efi_root / "OC" / "ACPI"
    if acpi_dir.exists():
        acpis = list(acpi_dir.glob("*.aml"))
        results["checks"]["acpi found"] = len(acpis)
        for aml in acpis:
            if aml.stat().st_size < 100:
                results["warnings"].append(f"{aml.name} too small ({aml.stat().st_size} bytes) - might be fake/empty")
    
    return results

def print_validation(results: dict):
    print("\n=== EFI Validation ===")
    print(f"Valid: {results['valid']}")
    print("\nChecks:")
    for k, v in results["checks"].items():
        print(f"  {k}: {v}")
    
    if results["errors"]:
        print("\nErrors:")
        for e in results["errors"]:
            print(f"  ✗ {e}")
    
    if results["warnings"]:
        print("\nWarnings:")
        for w in results["warnings"]:
            print(f"  ! {w}")
    
    if results["valid"] and not results["errors"]:
        print("\n✓ EFI appears valid!")
    else:
        print("\n✗ EFI has issues")
