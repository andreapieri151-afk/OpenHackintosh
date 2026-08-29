# Changelog

## [2.0.0] - 2026-08-29 - REAL FILES EDITION

### 🚀 Major Rewrite - Fixed Fake Files Issue

#### Problema Risolto
- **Prima (v1.0 - Google AI Studio)**: Tool generava struttura EFI ma file erano vuoti/quasi finti, non bootabili
- **Ora (v2.0)**: Tool scarica file REALI da GitHub ufficiale, EFI funzionante

#### Aggiunto
- **Downloader reale** (`downloader.py`): Scarica OpenCorePkg da Acidanthera releases ufficiali
- **Kext reali**: Lilu, VirtualSMC, WhateverGreen, AppleALC, RealtekRTL8111, IntelMausi, etc da repo ufficiali
- **SSDT reali**: PLUG, EC-USBX, AWAC, PMC da Dortania
- **Config.plist generator** corretto basato su Dortania Skylake Desktop guide
- **SMBIOS generator** con seriali validi (formato corretto 12/17 chars, UUID, ROM)
- **Validator** per controllare EFI (detect file finti/vuoti)
- **GUI moderna** per macOS con customtkinter (design curato, dark mode, progress bar, log live)
- **CLI completo** con argparse, supporto profili Q556/2 e Q957
- **Web Dashboard** con Flask, design macOS-like, preview live, per sandbox e Linux
- **Hardware profiles** dettagliati per Q556/2 (D3403-U, H110, Realtek RTL8111GN, ALC671) e Q957
- **Supporto macOS**: Monterey, Ventura, Sonoma, Sequoia (sperimentale)
- **Auto swap kext LAN**: RealtekRTL8111 per Q556/2, IntelMausi per Q957
- **README completo** con BIOS setup, troubleshooting, tabella kext
- **Icona** professionale
- **Launcher macOS** FujitsuEFI.command (double-click)
- **ZIP export** pronto per USB
- **Documentazione** BIOS, troubleshooting, credits

#### Design Migliorato
- Prima: design base, poco curato (Google AI Studio)
- Ora: 
  - GUI con customtkinter, dark theme, blue accent, card layout, SF Pro font
  - Web Dashboard con gradient, blur, progress bar, log monospace, status badge
  - Icona 3D con mini PC + Apple logo glow
  - README con badges, tabelle, emoji, struttura chiara

#### Tecnico
- Struttura progetto professionale: src/efi_builder/, src/gui/, assets/, tools/, templates/
- Type hints, dataclasses, error handling
- GitHub API per latest releases
- Zip extraction con ricerca ricorsiva kext
- Plist generation con xml
- Threading per build non bloccante
- Progress callback

## [1.0.0] - 2026-08-28 - Initial (Fake Files)

- Generazione struttura EFI
- File vuoti/finti (problema)
- Design base
- Creato con Google AI Studio
