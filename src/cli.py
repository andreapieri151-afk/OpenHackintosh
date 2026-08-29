"""
CLI per OpenHackintosh - Parla come una persona, non come un robot
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from efi_builder.hardware import PROFILES, MACOS_VERSIONS
from efi_builder.builder import EFIBuilder
from efi_builder.smbios import generate_smbios

def main():
    parser = argparse.ArgumentParser(
        description="OpenHackintosh - Crea EFI vere, non finte. Nato per Q556/2, ora per tutti.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi, così capisci al volo:

  # Lista cosa supporta
  python cli.py --list-profiles

  # Fai EFI base per Q556/2 con Ventura (quello che uso io)
  python cli.py --profile Q556/2 --macos "Ventura 13.x" --smbios iMac18,1

  # Fai EFI cattiva per Sonoma con WiFi Intel
  python cli.py --profile Q556/2 --macos "Sonoma 14.x" --smbios iMacPro1,1 --wifi --bluetooth

  # Per Q957 (cambia solo kext LAN)
  python cli.py --profile Q957 --macos "Ventura 13.x"

  # Metti output dove vuoi
  python cli.py --output ~/Desktop/MiaEFI --audio-layout 13

Se non sai cosa fare, lancia la GUI: python main.py
        """
    )
    
    parser.add_argument("--profile", choices=list(PROFILES.keys()), default="Q556/2", help="Che PC hai? Q556/2 ha Realtek LAN, Q957 ha Intel")
    parser.add_argument("--macos", choices=list(MACOS_VERSIONS.keys()), default="Ventura 13.x", help="Che macOS vuoi installare? Ventura è il più stabile per Q556/2")
    parser.add_argument("--smbios", default="iMac18,1", help="Che modello Mac fingiamo di essere? iMac18,1 per Skylake, iMacPro1,1 per Sonoma/Sequoia")
    parser.add_argument("--audio-layout", type=int, default=11, help="Layout audio per ALC671 - prova 11, se non va 13,15,21")
    parser.add_argument("--output", type=Path, default=Path.home() / "Desktop" / "EFI_Q5562", help="Dove metto EFI generata? Default Desktop")
    parser.add_argument("--wifi", action="store_true", help="Metti anche kext per WiFi Intel (AirportItlwm)")
    parser.add_argument("--bluetooth", action="store_true", help="Metti anche kext per Bluetooth Intel")
    parser.add_argument("--no-zip", action="store_true", help="Non creare ZIP, lascia solo cartella")
    parser.add_argument("--list-profiles", action="store_true", help="Fammi vedere che PC supporti")
    parser.add_argument("--list-macos", action="store_true", help="Fammi vedere che macOS supporti")
    parser.add_argument("--gui", action="store_true", help="Apri interfaccia grafica bella")
    
    args = parser.parse_args()
    
    if args.list_profiles:
        print("\n🔧 PC supportati:")
        for name, profile in PROFILES.items():
            print(f"\n  {name}: {profile.name}")
            print(f"    Board: {profile.board}, LAN: {profile.lan_chip}, Audio: {profile.audio_codec}")
            print(f"    CPU: {', '.join(profile.cpu_generations)}")
        print("\nSe il tuo non c'è, puoi aggiungerlo in src/efi_builder/hardware.py - è facile")
        return
    
    if args.list_macos:
        print("\n🍎 macOS supportati:")
        for name, info in MACOS_VERSIONS.items():
            rec = " (consigliato per Q556/2)" if info.get("recommended") else ""
            print(f"  {name}{rec} - Min OpenCore: {info['min_oc']}, SMBIOS consigliati: {info['smbios']}")
        return
    
    if args.gui:
        try:
            from gui.app import EFICreatorGUI
            app = EFICreatorGUI()
            app.run()
        except Exception as e:
            print(f"GUI non parte: {e}")
            print("Prova: pip install customtkinter")
        return
    
    print(f"""
╔════════════════════════════════════════════════════════════╗
║  OpenHackintosh - EFI vere, non finte                      ║
║  Nato per Q556/2 perché mi ero rotto di file vuoti         ║
╚════════════════════════════════════════════════════════════╝

Ok, genero EFI per:
  PC: {args.profile}
  macOS: {args.macos}
  SMBIOS: {args.smbios}
  Audio layout: {args.audio_layout}
  Dove la metto: {args.output}
  WiFi: {args.wifi}, Bluetooth: {args.bluetooth}

Se va tutto bene, ti trovo file veri scaricati da GitHub ufficiale,
non roba finta da 0 byte come faceva il tool di prima.
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
        print("🎉 FATTO! EFI pronta!")
        print("="*60)
        print(f"📁 Cartella: {result['efi_path']}")
        if result['zip_path']:
            print(f"📦 ZIP: {result['zip_path']}")
        print(f"\n🎲 SMBIOS generato (ricordati di rigenerarlo con GenSMBIOS per uso tuo):")
        for k, v in result['smbios'].items():
            print(f"  {k}: {v}")
        print("\n🔌 Kext scaricati:")
        for k, ok in result['kext_results'].items():
            print(f"  {'✓ vero' if ok else '✗ fallito'} {k}")
        print("\n👉 Prossimi passi:")
        print("1. Monta EFI della chiavetta USB")
        print("2. Copia cartella EFI dentro")
        print("3. Boota da USB (F12 all'avvio)")
        print("4. Installa macOS")
        print("5. Dopo install, copia EFI su disco interno")
        print("\n⚠️  Se non boota, 99% è BIOS - controlla DVMT 64MB!")
        print("   Leggi docs/BIOS_GUIDE.md - l'ho scritta col sangue")
        print("="*60)
    else:
        print(f"\n💥 Fallito: {result.get('error')}")
        print("Controlla connessione internet, GitHub API a volte ha limiti")
        sys.exit(1)

if __name__ == "__main__":
    main()
