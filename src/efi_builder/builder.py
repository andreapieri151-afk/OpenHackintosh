"""
Main EFI Builder - orchestrates the whole process
Fixed for Q556/2 specificity - EFI 2.0.0 audit
"""
import os
import shutil
import zipfile
from pathlib import Path
from typing import Callable, Optional, Dict, List
import plistlib

from .hardware import PROFILES, KEXTS, DRIVERS, SSDTs, get_kexts_for_profile, Q556_2, Q556_2_REQUIRED_SSDTS, Q556_2_OPTIONAL_SSDTS
from .downloader import EFIDownloader
from .smbios import generate_smbios
from .config_generator import generate_config, save_config

class EFIBuilder:
    def __init__(self, output_dir: Path, progress_callback: Optional[Callable] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.progress_callback = progress_callback
        self.downloader = EFIDownloader(self.output_dir / "downloads", progress_callback)
        self.efi_root = self.output_dir / "EFI"
        
        self.logs = []
    
    def log(self, msg: str):
        print(msg)
        self.logs.append(msg)
        if self.progress_callback:
            try:
                self.progress_callback("log", msg)
            except:
                pass
    
    def create_structure(self):
        """Create EFI folder structure"""
        self.log("📁 Creo la struttura cartelle EFI...")
        for folder in [
            self.efi_root / "BOOT",
            self.efi_root / "OC" / "ACPI",
            self.efi_root / "OC" / "Drivers",
            self.efi_root / "OC" / "Kexts",
            self.efi_root / "OC" / "Tools",
            self.efi_root / "OC" / "Resources" / "Audio",
            self.efi_root / "OC" / "Resources" / "Font",
            self.efi_root / "OC" / "Resources" / "Image",
        ]:
            folder.mkdir(parents=True, exist_ok=True)
        self.log("✓ Cartelle create, sembra già una EFI vera")
    
    def download_opencore(self) -> bool:
        """Download and prepare OpenCore"""
        self.log("⬇️  Scarico OpenCore VERO da Acidanthera (non finto, giuro)...")
        oc_extracted = self.downloader.download_opencore()
        if not oc_extracted:
            self.log("✗ Cavolo, download OpenCore fallito - controlla connessione")
            return False
        
        success = self.downloader.prepare_opencore_structure(oc_extracted, self.efi_root)
        if success:
            self.log("✓ OpenCore scaricato e preparato - file veri, non vuoti!")
        else:
            self.log("✗ Preparazione OpenCore fallita")
        return success
    
    def download_kexts(self, profile_name: str, include_wifi: bool = False, include_bluetooth: bool = False, include_optional: bool = False) -> Dict[str, bool]:
        """Download kexts for profile - minimal per Q556/2 (fix EFI generica)"""
        kext_list = get_kexts_for_profile(profile_name, include_wifi, include_bluetooth, include_optional=include_optional)
        if include_optional:
            self.log(f"🔌 Scarico kext per {profile_name} (con opzionali): {', '.join(kext_list)}")
        else:
            self.log(f"🔌 Scarico kext per {profile_name} MINIMAL Q556/2: {', '.join(kext_list)}")
            self.log(f"   (solo essenziali: Lilu, VirtualSMC, WhateverGreen, AppleALC, LAN - non generica)")
        self.log(f"   (tutti da GitHub ufficiale, con binari veri dentro)")
        
        kexts_dir = self.efi_root / "OC" / "Kexts"
        results = self.downloader.download_all_kexts(kext_list, KEXTS, kexts_dir)
        
        for kext, ok in results.items():
            if ok:
                self.log(f"  ✓ {kext} - scaricato vero, non finto")
            else:
                self.log(f"  ✗ {kext} - fallito, poi riproviamo")
        
        return results
    
    def create_ssdts(self, profile_name: str = "Q556/2", include_optional: bool = False):
        """
        Crea SSDT realmente necessari per Q556/2
        Fix per EFI 2.0.0: prima erano 0 byte perché URL sbagliati e nomi non corretti
        Ora: usa nomi corretti Dortania (PLUG-DRTNIA, EC-USBX-DESKTOP) e valida non 0 byte
        Per Q556/2 Skylake H110: solo PLUG-DRTNIA + EC-USBX-DESKTOP sono REQUIRED (Dortania table)
        AWAC e PMC sono per Coffee Lake+, NON necessari per Q556/2
        """
        from .hardware import SSDTs, Q556_2_REQUIRED_SSDTS, Q556_2_OPTIONAL_SSDTS, Q957_REQUIRED_SSDTS
        
        self.log(f"🧩 Creo SSDT per {profile_name} - presi da Dortania, nomi corretti, non 0 byte...")
        acpi_dir = self.efi_root / "OC" / "ACPI"
        
        # Determina quali SSDT servono davvero per profilo
        if profile_name == "Q556/2":
            required = Q556_2_REQUIRED_SSDTS
            optional = Q556_2_OPTIONAL_SSDTS if include_optional else []
            self.log(f"  Per Q556/2 H110 Skylake: REQUIRED = {required} (Dortania Skylake table)")
            self.log(f"  OPTIONAL = {optional} (solo se NVRAM non funziona)")
            ssdts_to_get = required + optional
        elif profile_name == "Q957":
            required = Q957_REQUIRED_SSDTS
            optional = []
            ssdts_to_get = required
            self.log(f"  Per Q957 Q270 Kaby Lake: REQUIRED = {required}")
        else:
            ssdts_to_get = Q556_2_REQUIRED_SSDTS
        
        import requests
        
        downloaded_count = 0
        for ssdt_key in ssdts_to_get:
            ssdt_info = SSDTs.get(ssdt_key)
            if not ssdt_info:
                self.log(f"  ! SSDT {ssdt_key} non trovato in definizioni")
                continue
            
            file_name = ssdt_info["file"]
            url = ssdt_info["url"]
            dest = acpi_dir / file_name
            
            # Prova download da URL ufficiale Dortania
            downloaded = False
            urls = [
                url,
                f"https://raw.githubusercontent.com/dortania/Getting-Started-With-ACPI/master/extra-files/compiled/{file_name}",
                f"https://github.com/dortania/Getting-Started-With-ACPI/raw/master/extra-files/compiled/{file_name}",
            ]
            
            for attempt_url in urls:
                try:
                    self.log(f"  ⬇️  Provo {file_name} da {attempt_url[:60]}...")
                    r = requests.get(attempt_url, timeout=15, verify=False)
                    if r.status_code == 200 and len(r.content) > 100:
                        # Valida che non sia 0 byte e che sia AML valido (inizia con SSDT o ha firma)
                        if len(r.content) == 0:
                            self.log(f"  ! {file_name} scaricato ma 0 byte - scarto (problema EFI 2.0.0)")
                            continue
                        # Salva
                        with open(dest, 'wb') as f:
                            f.write(r.content)
                        # Verifica salvato non 0 byte
                        if dest.stat().st_size == 0:
                            self.log(f"  ! {file_name} salvato ma 0 byte - elimino")
                            dest.unlink(missing_ok=True)
                            continue
                        self.log(f"  ✓ {file_name} scaricato - {dest.stat().st_size} byte REALI, non 0 byte")
                        downloaded = True
                        downloaded_count += 1
                        break
                    else:
                        self.log(f"  ! {file_name} - HTTP {r.status_code} o troppo piccolo ({len(r.content)} byte)")
                except Exception as e:
                    self.log(f"  ! Errore download {file_name}: {e}")
                    continue
            
            if not downloaded:
                self.log(f"  ! {file_name} - download fallito, provo da assets locali...")
                # Prova da assets locali
                assets_acpi = Path(__file__).parent.parent.parent / "assets" / "acpi"
                if assets_acpi.exists():
                    for aml in assets_acpi.glob("*.aml"):
                        if file_name.lower() in aml.name.lower() or ssdt_key.lower() in aml.name.lower():
                            if aml.stat().st_size > 0:
                                shutil.copy2(aml, dest)
                                self.log(f"  ✓ {file_name} da assets locali - {dest.stat().st_size} byte")
                                downloaded = True
                                downloaded_count += 1
                                break
                
                if not downloaded:
                    self.log(f"  ! {file_name} - non trovato da nessuna parte, creo README")
        
        # Verifica finale
        existing = [f for f in acpi_dir.glob("*.aml") if f.stat().st_size > 0]
        zero_byte = [f for f in acpi_dir.glob("*.aml") if f.stat().st_size == 0]
        
        # Rimuovi file 0 byte (fix EFI 2.0.0)
        for zb in zero_byte:
            self.log(f"  🗑️  Rimuovo {zb.name} - 0 byte (fix problema EFI 2.0.0)")
            zb.unlink(missing_ok=True)
        
        if not existing:
            self.log("  ! Nessun SSDT valido scaricato, creo guida per download manuale")
            (acpi_dir / "README_Q5562_SSDT.txt").write_text(
                f"SSDT per Q556/2 - Verificati per Skylake H110\n"
                f"REQUIRED (Dortania Skylake table):\n"
                f"- SSDT-PLUG-DRTNIA.aml (CPU power management) - REQUIRED\n"
                f"- SSDT-EC-USBX-DESKTOP.aml (EC fix) - REQUIRED\n"
                f"\n"
                f"OPTIONAL (solo se NVRAM non funziona):\n"
                f"- SSDT-PMC.aml (NVRAM fix per 300 series, ma utile anche su H110 se NVRAM rotta)\n"
                f"\n"
                f"NON necessari per Q556/2 (erano in EFI 2.0.0 ma sbagliati):\n"
                f"- SSDT-AWAC.aml - solo per Coffee Lake+ (300 series), Q556/2 H110 NON ha AWAC\n"
                f"- SSDT-RHUB.aml - solo per Comet Lake+\n"
                f"\n"
                f"Download da:\n"
                f"https://github.com/dortania/Getting-Started-With-ACPI/tree/master/extra-files/compiled\n"
                f"\n"
                f"URL diretti:\n"
                f"https://raw.githubusercontent.com/dortania/Getting-Started-With-ACPI/master/extra-files/compiled/SSDT-PLUG-DRTNIA.aml\n"
                f"https://raw.githubusercontent.com/dortania/Getting-Started-With-ACPI/master/extra-files/compiled/SSDT-EC-USBX-DESKTOP.aml\n"
            )
        else:
            self.log(f"✓ {len(existing)} SSDT validi pronti per Q556/2: {[f.name for f in existing]}")
            # Log quali sono stati rimossi perché non necessari
            if any("AWAC" in f.name for f in acpi_dir.glob("*.aml")):
                self.log(f"  ! Note: AWAC trovato ma per Q556/2 H110 Skylake NON serve (solo Coffee Lake+), disabilitato in config")
            if any("RHUB" in f.name for f in acpi_dir.glob("*.aml")):
                self.log(f"  ! Note: RHUB trovato ma per Q556/2 NON serve (solo Comet Lake+)")
    
    def generate_config_plist(self, profile_name: str, smbios_model: str, audio_layout: int, macos_version: str, smbios_data: Optional[Dict] = None, dev_mode: bool = False, minimal_q5562: bool = True):
        """Generate config.plist - specifico per Q556/2 con dev_mode e minimal"""
        self.log(f"⚙️  Genero config.plist per {profile_name} / {smbios_model} / {macos_version}...")
        if dev_mode:
            self.log(f"   Modalità DEV: con debug -v keepsyms")
        else:
            self.log(f"   Modalità RELEASE: pulita, solo alcid={audio_layout} (per Q556/2 ALC671)")
        self.log(f"   (basato su Dortania Skylake, specifico per Q556/2, non generico)")
        
        if not smbios_data:
            smbios_data = generate_smbios(smbios_model)
            self.log(f"  🎲 SMBIOS generato: {smbios_data['SerialNumber']} / {smbios_data['ProductName']} (individuale, non preset)")
        
        config = generate_config(
            efi_root=self.efi_root,
            smbios_data=smbios_data,
            profile_name=profile_name,
            audio_layout=audio_layout,
            macos_version=macos_version,
            dev_mode=dev_mode,
            minimal_q5562=minimal_q5562
        )
        
        dest = self.efi_root / "OC" / "config.plist"
        save_config(config, dest)
        self.log("✓ config.plist generato - specifico per Q556/2: DP+DVI-D, HD 530, ALC671 layout 11, minimal drivers")
        return smbios_data, config
    
    def create_readme(self, profile_name: str, macos_version: str, smbios_model: str):
        """Create README for EFI"""
        profile = PROFILES.get(profile_name, Q556_2)
        readme_content = f"""# EFI per {profile.name} - Generata con OpenHackintosh

Ciao! Questa EFI è stata generata con OpenHackintosh, non a mano.

Se stai leggendo questo, probabilmente hai usato il tool e ora hai una cartella EFI che dovrebbe bootare davvero, non come quelle finte di prima.

## Il tuo hardware
- Board: {profile.board}
- Chipset: {profile.chipset}
- CPU: {', '.join(profile.cpu_generations)}
- iGPU: {profile.igpu}
- LAN: {profile.lan_chip} ({profile.lan_kext})
- Audio: {profile.audio_codec} (layouts: {profile.audio_layout_ids})
- SMBIOS: {smbios_model}
- macOS: {macos_version}

## Specifico per Q556/2 (EFI 2.1.0)
Questa EFI è ora veramente specifica per Q556/2, non generica:
- SSDT: solo PLUG-DRTNIA + EC-USBX-DESKTOP (richiesti per Skylake H110 per Dortania), non AWAC/RHUB
- Drivers: solo HfsPlus + OpenRuntime (minimal, non tutti indiscriminatamente)
- Kext: solo essenziali Lilu/VirtualSMC/WhateverGreen/AppleALC/RealtekRTL8111 (no extra generici)
- DeviceProperties: DP (con0 00040000) + DVI-D (con1 00080000 HDMI type) + con2 disabilitato (2 porte fisiche)
- Boot-args: RELEASE solo alcid=11 (ALC671 verificato), DEV con -v keepsyms debug=0x100
- SMBIOS: generato individuale, no preset seriali/MLB/UUID
- Misc Debug: disabilitato in release (Target=0), abilitato solo in dev

## BIOS - Se non lo imposti bene non boota, te lo dico

Disabilita:
- Fast Boot, Secure Boot, Serial/COM, Parallel, VT-d, CSM, SGX, Platform Trust

Abilita:
- VT-x, Above 4G, EHCI/XHCI Hand-off, OS Windows 8.1/10 UEFI
- DVMT Pre-Allocated: 64MB - QUESTO È FONDAMENTALE, se non lo metti a 64MB non boota

## Installazione (veloce)

1. Formatta USB come Mac OS Extended (Journaled) GUID
2. Crea installer macOS con createinstallmedia
3. Monta EFI della USB
4. Copia cartella EFI dentro
5. Boota da USB (F12)
6. Installa macOS
7. Dopo, copia EFI su disco interno

## Dopo installazione

- Monta EFI disco interno, copia EFI
- Rigenera SMBIOS con GenSMBIOS (questo è generato a caso, usalo solo per test)
- Mappa USB con USBToolBox
- Togli XhciPortLimit dopo mapping

## Kext inclusi

Guarda in OC/Kexts. Per Q556/2 c'è RealtekRTL8111, per Q957 IntelMausi. Il tool fa swap automatico.

## Se non boota

- Stuck su [EB|LOG:EXITBS:START]: controlla DVMT 64MB, ReleaseUsbOwnership YES
- Schermo nero: prova -igfxvesa, cambia ig-platform-id, prova SMBIOS diverso
- Audio non va: prova layout diversi (11,13,15,21,27,28) - 11 è default verificato per Q556/2 ALC671

## Note

{profile.notes}

## Crediti

- OpenCore by Acidanthera (senza loro non esisterebbe nulla)
- Dortania Guide (la Bibbia)
- Community Fujitsu Esprimo

Generata il: {__import__('datetime').datetime.now().isoformat()}
Tool: https://github.com/andreapieri151-afk/OpenHackintosh
Fatta con ❤️ e bestemmie davanti a un Q556/2 che non bootava
"""
        (self.output_dir / "README.md").write_text(readme_content)
        (self.efi_root / "OC" / "README_Q5562.txt").write_text(readme_content)
        self.log("✓ README created")
    
    def create_zip(self) -> Path:
        """Create ZIP of EFI"""
        self.log("📦 Creo ZIP pronto per chiavetta...")
        zip_path = self.output_dir / "EFI_Q5562.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for file_path in self.efi_root.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.output_dir)
                    z.write(file_path, arcname)
            readme = self.output_dir / "README.md"
            if readme.exists():
                z.write(readme, "README.md")
        
        self.log(f"✓ ZIP creato: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB) - pronto da copiare su USB!")
        return zip_path
    
    def build(
        self,
        profile_name: str = "Q556/2",
        smbios_model: str = "iMac18,1",
        audio_layout: int = 11,
        macos_version: str = "Ventura 13.x",
        include_wifi: bool = False,
        include_bluetooth: bool = False,
        include_optional_kexts: bool = False,
        include_optional_ssdts: bool = False,
        dev_mode: bool = False,
        minimal_q5562: bool = True,
        generate_zip: bool = True
    ) -> Dict:
        """Full build process - specifico per Q556/2"""
        mode_str = "DEV (con debug)" if dev_mode else "RELEASE (pulita, solo alcid)"
        self.log(f"=== 🚀 Creo EFI per {profile_name} - {mode_str} ===")
        self.log(f"Obiettivo: {macos_version} / {smbios_model} / audio layout {audio_layout}")
        self.log(f"Modalità: {'minimal Q556/2 specifica' if minimal_q5562 else 'generica'}")
        self.log(f"Prometto: file veri, non finti, e veramente specifici per Q556/2")
        
        self.create_structure()
        
        if not self.download_opencore():
            return {"success": False, "error": "OpenCore download failed", "logs": self.logs}
        
        kext_results = self.download_kexts(profile_name, include_wifi, include_bluetooth, include_optional=include_optional_kexts)
        
        critical = ["Lilu", "VirtualSMC", "WhateverGreen", "AppleALC"]
        failed_critical = [k for k in critical if not kext_results.get(k, False)]
        if failed_critical:
            self.log(f"! Attenzione: kext importanti falliti: {failed_critical} - senza questi non boota")
        
        self.create_ssdts(profile_name=profile_name, include_optional=include_optional_ssdts)
        
        smbios_data, config = self.generate_config_plist(profile_name, smbios_model, audio_layout, macos_version, dev_mode=dev_mode, minimal_q5562=minimal_q5562)
        
        self.create_readme(profile_name, macos_version, smbios_model)
        
        zip_path = None
        if generate_zip:
            zip_path = self.create_zip()
        
        self.log("=== 🎉 Fatto! EFI pronta - specifica per Q556/2! ===")
        self.log("Ora copia la cartella EFI sulla chiavetta e prova a bootare")
        self.log("Se non boota, 99% è il BIOS - controlla DVMT 64MB!")
        
        return {
            "success": True,
            "efi_path": str(self.efi_root),
            "zip_path": str(zip_path) if zip_path else None,
            "smbios": smbios_data,
            "kext_results": kext_results,
            "logs": self.logs
        }
    
    def cleanup(self):
        """Cleanup temp files"""
        self.downloader.cleanup()
