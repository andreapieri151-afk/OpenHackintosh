"""
CLI for Fujitsu Esprimo Q556/2 EFI Creator
"""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from efi_builder.hardware import PROFILES, MACOS_VERSIONS
from efi_builder.builder import EFIBuilder
from efi_builder.smbios import generate_smbios

def main():
    parser = argparse.ArgumentParser(
        description="Fujitsu Esprimo Q556/2 - Hackintosh EFI Creator (Real files, no fake)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py --profile Q556/2 --macos "Ventura 13.x" --smbios iMac18,1
  python cli.py --profile Q957 --macos "Sonoma 14.x" --smbios iMacPro1,1 --wifi --bluetooth
  python cli.py --list-profiles
  python cli.py --gui
        """
    )
    
    parser.add_argument("--profile", choices=list(PROFILES.keys()), default="Q556/2", help="Hardware profile")
    parser.add_argument("--macos", choices=list(MACOS_VERSIONS.keys()), default="Ventura 13.x", help="Target macOS version")
    parser.add_argument("--smbios", default="iMac18,1", help="SMBIOS model")
    parser.add_argument("--audio-layout", type=int, default=11, help="Audio layout ID for ALC671")
    parser.add_argument("--output", type=Path, default=Path.home() / "Desktop" / "EFI_Q5562", help="Output directory")
    parser.add_argument("--wifi", action="store_true", help="Include Intel WiFi kext")
    parser.add_argument("--bluetooth", action="store_true", help="Include Intel Bluetooth kext")
    parser.add_argument("--no-zip", action="store_true", help="Don't create ZIP")
    parser.add_argument("--list-profiles", action="store_true", help="List hardware profiles")
    parser.add_argument("--list-macos", action="store_true", help="List macOS versions")
    parser.add_argument("--gui", action="store_true", help="Launch GUI")
    
    args = parser.parse_args()
    
    if args.list_profiles:
        print("Available profiles:")
        for name, profile in PROFILES.items():
            print(f"  {name}: {profile.name}")
            print(f"    Board: {profile.board}, LAN: {profile.lan_chip}, Audio: {profile.audio_codec}")
        return
    
    if args.list_macos:
        print("Available macOS versions:")
        for name, info in MACOS_VERSIONS.items():
            rec = " (Recommended)" if info.get("recommended") else ""
            print(f"  {name}{rec} - Min OC: {info['min_oc']}, SMBIOS: {info['smbios']}")
        return
    
    if args.gui:
        try:
            from gui.app import EFICreatorGUI
            app = EFICreatorGUI()
            app.run()
        except Exception as e:
            print(f"Failed to launch GUI: {e}")
            print("Try: pip install customtkinter")
        return
    
    print(f"""
╔════════════════════════════════════════════════════════════╗
║  Fujitsu Esprimo Q556/2 - EFI Creator                      ║
║  Real files, no fake - Downloads from official sources    ║
╚════════════════════════════════════════════════════════════╝

Profile: {args.profile}
macOS: {args.macos}
SMBIOS: {args.smbios}
Audio Layout: {args.audio_layout}
Output: {args.output}
WiFi: {args.wifi}, Bluetooth: {args.bluetooth}
""")
    
    builder = EFIBuilder(args.output)
    
    result = builder.build(
        profile_name=args.profile,
        smbios_model=args.smbios,
        audio_layout=args.audio_layout,
        macos_version=args.macos,
        include_wifi=args.wifi,
        include_bluetooth=args.bluetooth,
        generate_zip=not args.no_zip
    )
    
    if result["success"]:
        print("\n" + "="*60)
        print("✓ BUILD SUCCESS")
        print("="*60)
        print(f"EFI Path: {result['efi_path']}")
        if result['zip_path']:
            print(f"ZIP Path: {result['zip_path']}")
        print(f"\nSMBIOS:")
        for k, v in result['smbios'].items():
            print(f"  {k}: {v}")
        print("\nKexts:")
        for k, ok in result['kext_results'].items():
            print(f"  {'✓' if ok else '✗'} {k}")
        print("\nNext steps:")
        print("1. Copy EFI folder to USB EFI partition")
        print("2. Install macOS")
        print("3. Copy EFI to internal drive EFI partition")
        print("="*60)
    else:
        print(f"\n✗ BUILD FAILED: {result.get('error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
