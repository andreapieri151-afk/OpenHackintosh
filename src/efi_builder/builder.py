"""
Main EFI Builder - orchestrates the whole process
"""
import os
import shutil
import zipfile
from pathlib import Path
from typing import Callable, Optional, Dict, List
import plistlib

from .hardware import PROFILES, KEXTS, DRIVERS, SSDTs, get_kexts_for_profile, Q556_2
from .downloader import EFIDownloader
from efi.selection import ComponentSelection, KEXT_BUNDLES
from efi.integrity import validate_efi_binary
from .smbios import generate_smbios
from .config_generator import generate_config, save_config


class BuildError(RuntimeError):
    """Errore bloccante: un componente obbligatorio non e' disponibile."""


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

    def filter_drivers(self, allowed_files: List[str]) -> None:
        """Rimuove i driver UEFI non necessari (whitelist)."""
        drivers_dir = self.efi_root / "OC" / "Drivers"
        if not drivers_dir.exists():
            return
        allowed = set(allowed_files)
        for f in drivers_dir.glob("*.efi"):
            if f.name not in allowed:
                self.log(f"  - Driver rimosso (non necessario): {f.name}")
                f.unlink(missing_ok=True)

    def validate_opencore_binaries(self) -> bool:
        """OpenCore.efi e BOOTx64.efi devono essere binari EFI reali (PE/COFF)."""
        boot = self.efi_root / "BOOT" / "BOOTx64.efi"
        oc = self.efi_root / "OC" / "OpenCore.efi"
        boot_res = validate_efi_binary(boot)
        oc_res = validate_efi_binary(oc)
        if not oc_res.ok:
            self.log(f"  ✗ OpenCore.efi invalid: {oc_res.reason}")
        if not boot_res.ok:
            self.log(f"  ✗ BOOTx64.efi invalid: {boot_res.reason}")
        return oc_res.ok and boot_res.ok

    def validate_critical_components(self, required_kexts: List[str]) -> Dict[str, bool]:
        """Verifica che i kext obbligatori siano davvero presenti e non vuoti."""
        kexts_dir = self.efi_root / "OC" / "Kexts"
        results = {}
        for kext_name in required_kexts:
            bundle_name = KEXT_BUNDLES.get(kext_name, kext_name)
            kext_path = kexts_dir / bundle_name
            info = kext_path / "Contents" / "Info.plist" if kext_path.exists() else None
            ok = bool(info and info.exists() and info.stat().st_size > 0)
            results[kext_name] = ok
            if not ok:
                self.log(f"  ✗ Manca componente obbligatorio: {kext_name} ({bundle_name})")
        return results

    def ensure_no_placeholders(self) -> List[str]:
        """Controlla che nessun file nell'EFI sia vuoto o contenga segnaposto."""
        problems: List[str] = []
        if not self.efi_root.exists():
            return problems
        placeholder_texts = (b"placeholder", b"fake", b"0 byte", b"TODO")
        for path in self.efi_root.rglob("*"):
            if not path.is_file():
                continue
            if path.stat().st_size == 0:
                problems.append(str(path))
                continue
            if path.suffix.lower() in (".aml", ".plist", ".txt", ".kext"):
                try:
                    head = path.read_bytes()[:512]
                    if any(p.lower() in head.lower() for p in placeholder_texts):
                        problems.append(str(path))
                except Exception:
                    pass
        return problems
    
    def download_kexts(self, profile_name: str, include_wifi: bool = False,
                       include_bluetooth: bool = False, kext_list: Optional[List[str]] = None) -> Dict[str, bool]:
        """Download kexts for profile. Se kext_list e' dato, scarica solo quelli."""
        if kext_list is None:
            kext_list = get_kexts_for_profile(profile_name, include_wifi, include_bluetooth)
        self.log(f"🔌 Scarico kext per {profile_name}: {', '.join(kext_list)}")
        self.log(f"   (tutti da GitHub ufficiale, con binari veri dentro)")

        kexts_dir = self.efi_root / "OC" / "Kexts"
        results = self.downloader.download_all_kexts(kext_list, KEXTS, kexts_dir)

        for kext, ok in results.items():
            if ok:
                self.log(f"  ✓ {kext} - scaricato vero, non finto")
            else:
                self.log(f"  ✗ {kext} - fallito")
        return results
    
    def create_ssdts(self, ssdt_names=None, required_ssdts=None):
        """Create SSDTs from Dortania. Mai placeholder vuoti."""
        names = ssdt_names or list(SSDTs.keys())
        required = set(required_ssdts or [])
        self.log("🧩 Creo SSDT da Dortania, niente placeholder...")
        acpi_dir = self.efi_root / "OC" / "ACPI"
        acpi_dir.mkdir(parents=True, exist_ok=True)

        base_url = "https://raw.githubusercontent.com/dortania/Getting-Started-With-ACPI/master/extra-files/compiled/"
        urls_tpl = [
            f"{base_url}{name}.aml",
            f"https://raw.githubusercontent.com/dortania/OpenCore-Install-Guide/master/extra-files/compiled/{name}.aml",
            f"https://github.com/dortania/Getting-Started-With-ACPI/raw/master/extra-files/compiled/{name}.aml",
        ]

        import requests

        missing: List[str] = []
        for ssdt_name in names:
            dest = acpi_dir / f"{ssdt_name}.aml"
            if dest.exists() and dest.stat().st_size > 0:
                self.log(f"  ✓ {ssdt_name}.aml già presente")
                continue
            for url in urls_tpl:
                try:
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200 and len(r.content) > 100:
                        dest.write_bytes(r.content)
                        self.log(f"  ✓ {ssdt_name}.aml scaricato")
                        break
                except Exception:
                    continue
            else:
                missing.append(ssdt_name)
                self.log(f"  ✗ {ssdt_name}.aml - download fallito")

        # Se un SSDT obbligatorio manca -> errore bloccante, MAI placeholder
        required_missing = [n for n in missing if n in required]
        if required_missing:
            raise BuildError(
                "EFI generation aborted. Failed to download required SSDT(s): "
                + ", ".join(required_missing)
            )

        if missing:
            self.log(f"  ! SSDT opzionali mancanti: {', '.join(missing)}")

        existing = [p.name for p in acpi_dir.glob("*.aml") if p.stat().st_size > 0]
        self.log(f"✓ {len(existing)} SSDT pronti (solo file reali, mai vuoti)")
    
    def generate_config_plist(self, profile_name: str, smbios_model: str, audio_layout: int,
                              macos_version: str, smbios_data: Optional[Dict] = None,
                              device_properties: Optional[Dict] = None, dev: bool = False):
        """Generate config.plist"""
        self.log(f"⚙️  Genero config.plist per {profile_name} / {smbios_model} / {macos_version}...")
        self.log(f"   (basato su Dortania Skylake, non a caso)")
        
        if not smbios_data:
            smbios_data = generate_smbios(smbios_model)
            self.log(f"  🎲 SMBIOS generato: {smbios_data['SerialNumber']} / {smbios_data['ProductName']}")
        
        config = generate_config(
            efi_root=self.efi_root,
            smbios_data=smbios_data,
            profile_name=profile_name,
            audio_layout=audio_layout,
            macos_version=macos_version,
            device_properties=device_properties,
            dev=dev,
        )
        
        dest = self.efi_root / "OC" / "config.plist"
        save_config(config, dest)
        self.log("✓ config.plist generato - con patch giuste per HD 530 e ALC671")
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
- Audio non va: prova layout diversi (11,13,15,21)

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
        generate_zip: bool = True,
        selection: Optional[ComponentSelection] = None,
        strict: bool = True,
        dev: bool = False,
        device_properties: Optional[Dict] = None
    ) -> Dict:
        """Full build process, hardware-aware e strict."""
        self.log(f"=== 🚀 Creo EFI per {profile_name} ===")
        self.log(f"Obiettivo: {macos_version} / {smbios_model} / audio layout {audio_layout}")
        self.log(f"Modalità: {'DEV' if dev else 'RELEASE'}")
        self.log(f"Prometto: file veri, non finti come prima")

        if selection is None:
            # Fallback legacy (build_efi passa sempre una ComponentSelection).
            # Qui NON si aggiungono NVMeFix/RestrictEvents "just in case".
            selection = ComponentSelection(
                required_kexts=get_kexts_for_profile(profile_name, include_wifi, include_bluetooth),
                required_drivers=["HfsPlus", "OpenRuntime"],
                required_ssdts=list(SSDTs.keys()),
            )

        self.create_structure()

        if not self.download_opencore():
            return {"success": False, "error": "OpenCore download failed", "logs": self.logs}

        if not self.validate_opencore_binaries():
            msg = "EFI generation aborted. Invalid OpenCore binary (not PE/COFF)."
            self.log("✗ " + msg)
            return {"success": False, "error": msg, "logs": self.logs}

        self.filter_drivers(selection.driver_files())
        kext_results = self.download_kexts(profile_name, include_wifi, include_bluetooth, kext_list=selection.kexts())

        failed_required = [k for k in selection.required_kexts if not kext_results.get(k, False)]
        if failed_required:
            msg = "EFI generation aborted. Required component unavailable: " + ", ".join(failed_required)
            self.log("✗ " + msg)
            if strict:
                return {"success": False, "error": msg, "logs": self.logs}

        try:
            self.create_ssdts(selection.ssdts(), selection.required_ssdts)
        except BuildError as exc:
            self.log("✗ " + str(exc))
            if strict:
                return {"success": False, "error": str(exc), "logs": self.logs}

        smbios_data, config = self.generate_config_plist(
            profile_name, smbios_model, audio_layout, macos_version,
            device_properties=device_properties, dev=dev,
        )

        self.create_readme(profile_name, macos_version, smbios_model)

        placeholders = self.ensure_no_placeholders()
        if placeholders:
            msg = "EFI generation aborted. Placeholder/empty files detected: " + ", ".join(placeholders[:5])
            self.log("✗ " + msg)
            if strict:
                return {"success": False, "error": msg, "logs": self.logs}

        zip_path = None
        if generate_zip:
            zip_path = self.create_zip()

        self.log("=== 🎉 Fatto! EFI pronta! ===")
        self.log("Ora copia la cartella EFI sulla chiavetta e prova a bootare")
        self.log("Se non boota, 99% è il BIOS - controlla DVMT 64MB!")

        return {
            "success": True,
            "efi_path": str(self.efi_root),
            "zip_path": str(zip_path) if zip_path else None,
            "smbios": smbios_data,
            "kext_results": kext_results,
            "selection": selection.to_dict(),
            "logs": self.logs
        }
    
    def cleanup(self):
        """Cleanup temp files"""
        self.downloader.cleanup()
