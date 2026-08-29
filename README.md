# Fujitsu Esprimo Q556/2 - Auxiliary Hackintosh Tool

![Status](https://img.shields.io/badge/Status-Real%20Files-success)
![OpenCore](https://img.shields.io/badge/OpenCore-1.0.1+-blue)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)
![Hardware](https://img.shields.io/badge/Hardware-Q556%2F2%20%7C%20Q957-orange)

Tool ausiliario che **automatizza tutta la procedura di Hackintosh** per Fujitsu Esprimo Q556/2 e Q957, generando automaticamente cartelle EFI **REALI e funzionanti** (non finte/vuote).

> **Problema risolto**: I tool precedenti generavano la struttura EFI ma i file erano vuoti/quasi finti. Questo tool scarica file REALI da GitHub ufficiale (Acidanthera, Dortania, etc).

## ✨ Caratteristiche

### ✅ File Reali, Non Finti
- **OpenCorePkg** ufficiale scaricato da `acidanthera/OpenCorePkg` releases
- **Kext REALI**: Lilu, VirtualSMC, WhateverGreen, AppleALC, RealtekRTL8111, IntelMausi, etc
- **SSDT REALI**: PLUG, EC-USBX, AWAC, PMC scaricati da Dortania
- **Config.plist** generato correttamente seguendo la guida Dortania Skylake Desktop

### 🎯 Supporto Hardware Specifico Q556/2
- **Board**: D3403-U
- **Chipset**: Intel H110
- **CPU**: Intel 6th Gen Skylake (i3/i5/i7-6xxxT) e 7th Gen Kaby Lake
- **iGPU**: Intel HD 530 / 630 (con patch framebuffer corretta)
- **LAN**: Realtek RTL8111GN (Q556/2) / Intel I219 (Q957)
- **Audio**: Realtek ALC671 (layout-id 11, 13, 15, 21, 27, 28)
- **BIOS**: AMI Aptio V - con guida per impostazioni critiche

### 🚀 Funzionalità
- Generazione EFI one-click
- SMBIOS automatico (iMac17,1, iMac18,1, Macmini8,1, iMacPro1,1)
- Supporto macOS: Monterey, Ventura, Sonoma, Sequoia (sperimentale)
- Validazione EFI integrata
- Export ZIP pronto per USB
- GUI moderna per macOS (customtkinter) + CLI + Web Dashboard
- Supporto Q556/2 e Q957 (swap automatico kext LAN)

## 📸 Screenshot

La GUI moderna mostra:
- Selezione hardware Q556/2 vs Q957
- Versione macOS target
- SMBIOS e Audio layout
- Opzioni WiFi/Bluetooth Intel
- Log in tempo reale
- Preview SMBIOS
- Progress bar

## 🛠️ Installazione

### Requisiti
- Python 3.9+
- macOS (per GUI nativa) o Linux/Windows (per CLI/Web)

### Setup
```bash
git clone https://github.com/andreapieri151-afk/Fujistu-esprimo-q556-2-auxiliarty-tool
cd Fujistu-esprimo-q556-2-auxiliarty-tool

# Installa dipendenze
pip install -r requirements.txt

# Opzionale: per GUI migliore su macOS
pip install customtkinter pillow
```

## 💻 Utilizzo

### GUI (macOS - consigliato)
```bash
python main.py
# oppure
python src/gui/app.py
```

### Web Dashboard (per preview / Linux)
```bash
python app.py
# Apri http://localhost:5000
```

### CLI
```bash
# Lista profili
python src/cli.py --list-profiles

# Build base per Q556/2 Ventura
python src/cli.py --profile Q556/2 --macos "Ventura 13.x" --smbios iMac18,1

# Build completo con WiFi/Bluetooth per Sonoma
python src/cli.py --profile Q556/2 --macos "Sonoma 14.x" --smbios iMacPro1,1 --wifi --bluetooth

# Build per Q957
python src/cli.py --profile Q957 --macos "Ventura 13.x" --smbios iMac18,1

# Specifica output custom
python src/cli.py --output ~/Desktop/MiaEFI --audio-layout 13
```

## 📁 Struttura EFI Generata

```
EFI/
├── BOOT/
│   └── BOOTx64.efi (REALE da OpenCorePkg)
└── OC/
    ├── ACPI/
    │   ├── SSDT-PLUG.aml (REALE)
    │   ├── SSDT-EC-USBX.aml (REALE)
    │   ├── SSDT-AWAC.aml (REALE)
    │   └── SSDT-PMC.aml (REALE - per NVRAM H110)
    ├── Drivers/
    │   ├── HfsPlus.efi (REALE)
    │   ├── OpenRuntime.efi (REALE)
    │   ├── OpenCanopy.efi (REALE)
    │   └── ResetNvramEntry.efi
    ├── Kexts/
    │   ├── Lilu.kext (REALE)
    │   ├── VirtualSMC.kext (REALE)
    │   ├── SMCProcessor.kext
    │   ├── SMCSuperIO.kext
    │   ├── WhateverGreen.kext (REALE)
    │   ├── AppleALC.kext (REALE)
    │   ├── RealtekRTL8111.kext (per Q556/2 - REALE)
    │   ├── IntelMausi.kext (per Q957 - REALE)
    │   ├── NVMeFix.kext
    │   └── RestrictEvents.kext
    ├── Tools/
    ├── Resources/
    ├── OpenCore.efi (REALE)
    └── config.plist (GENERATO CORRETTAMENTE per Skylake)
```

## ⚙️ Config.plist - Dettagli Tecnici

Basato su **Dortania Skylake Desktop Guide**:

### ACPI
- SSDT-PLUG, SSDT-EC-USBX, SSDT-AWAC, SSDT-PMC aggiunti automaticamente

### Booter Quirks
- AvoidRuntimeDefrag: YES
- EnableSafeModeSlide: YES
- EnableWriteUnprotector: YES
- ProvideCustomSlide: YES
- RebuildAppleMemoryMap: YES
- SetupVirtualMap: YES

### DeviceProperties
- PciRoot(0x0)/Pci(0x2,0x0) con:
  - AAPL,ig-platform-id: 00001219 (Skylake) / 00001259 (Kaby)
  - framebuffer-patch-enable, stolenmem, fbmem
  - DVMT fix se BIOS non ha 64MB

### Kernel
- Lilu first (obbligatorio)
- AppleXcpmCfgLock: YES (per CFG Lock non disabilitato)
- DisableIoMapper: YES
- XhciPortLimit: NO (per Ventura+)

### NVRAM
- boot-args: `-v keepsyms=1 debug=0x100 alcid=11`
- csr-active-config: 00000000
- prev-lang:kbd: en-US:0

### PlatformInfo
- Automatic: YES
- Genera SMBIOS validi con serial, MLB, UUID, ROM

### UEFI
- ConnectDrivers: YES
- Drivers: HfsPlus, OpenRuntime, OpenCanopy
- ReleaseUsbOwnership: YES (fix per [EB|LOG:EXITBS:START])

## 🔧 BIOS Setup (CRITICO per Q556/2)

### Disabilita:
- Fast Boot
- Secure Boot
- Serial/COM Port
- Parallel Port
- VT-d (può essere disabilitata se DisableIoMapper YES)
- CSM
- Intel SGX
- Intel Platform Trust

### Abilita:
- VT-x
- Above 4G decoding
- EHCI/XHCI Hand-off
- OS type: Windows 8.1/10 UEFI Mode
- **DVMT Pre-Allocated: 64MB** (CRITICO - se non disponibile, serve patch)
- DVMT Total: MAX

> Se non trovi DVMT 64MB, il tool applica già framebuffer patch, ma è consigliato moddare BIOS o usare min-stolen patch.

## 🐛 Troubleshooting

### Stuck su [EB|LOG:EXITBS:START]
- Verifica DVMT 64MB
- Controlla ReleaseUsbOwnership = YES
- EnableSafeModeSlide = YES
- ProvideCustomSlide = YES
- Prova a disabilitare Above 4G e aggiungere npci=0x2000

### Schermo nero / No display
- Prova boot-arg `-igfxvesa`
- Cambia ig-platform-id
- Prova SMBIOS diverso
- Verifica cavo DisplayPort/DVI

### Audio non funziona
- Prova layout-id diversi: 11, 13, 15, 21, 27, 28
- Usa alcid=XX in boot-args
- Verifica AppleALC caricato

### LAN non funziona
- Q556/2: deve usare RealtekRTL8111.kext
- Q957: deve usare IntelMausi.kext
- Il tool fa swap automatico in base al profilo

### USB non funzionano
- Mappa porte con USBToolBox
- Dopo mapping, rimuovi XhciPortLimit e USBInjectAll

## 📦 Kext Inclusi

| Kext | Repo | Descrizione | Obbligatorio |
|------|------|-------------|--------------|
| Lilu | acidanthera/Lilu | Patch engine | ✅ |
| VirtualSMC | acidanthera/VirtualSMC | SMC emulation | ✅ |
| WhateverGreen | acidanthera/WhateverGreen | Graphics fix | ✅ |
| AppleALC | acidanthera/AppleALC | Audio | ✅ |
| RealtekRTL8111 | Mieze/RTL8111 | LAN Q556/2 | Q556/2 |
| IntelMausi | acidanthera/IntelMausi | LAN Q957 | Q957 |
| NVMeFix | acidanthera/NVMeFix | NVMe power | No |
| RestrictEvents | acidanthera/RestrictEvents | Block updates | No |
| IntelBluetooth | OpenIntelWireless | BT Intel | Opzionale |
| AirportItlwm | OpenIntelWireless | WiFi Intel | Opzionale |

## 🔄 Differenze Q556/2 vs Q957

| Feature | Q556/2 | Q957 |
|---------|--------|------|
| LAN Chip | Realtek RTL8111GN | Intel I219-LM |
| Kext LAN | RealtekRTL8111.kext | IntelMausi.kext |
| Board | D3403-U | D3403-U2 / D3600 |
| CPU | 6th Gen Skylake | 7th Gen Kaby Lake |
| Stessa EFI? | Sì, basta swap kext LAN | Sì, basta swap kext LAN |

Il tool gestisce automaticamente lo swap.

## 🚧 Roadmap

- [x] Downloader REALI (no fake)
- [x] Config.plist corretto per Skylake
- [x] SMBIOS generator
- [x] GUI moderna macOS
- [x] CLI completo
- [x] Web Dashboard
- [x] Validazione EFI
- [ ] Integrazione macserial nativo
- [ ] USB mapping automatico
- [ ] OCAT integration
- [ ] Auto-update kexts
- [ ] Creazione installer USB automatica

## 🤝 Crediti

- **OpenCore** by Acidanthera
- **Dortania Guide** - https://dortania.github.io/OpenCore-Install-Guide/
- **OpCore-Simplify** - ispirazione per downloader
- **Fujitsu Esprimo Community** - hackintosh-forum.de, Reddit r/hackintosh
- **Kext Authors**: Acidanthera, Mieze, OpenIntelWireless

## ⚠️ Disclaimer

Questo tool è per scopi educativi e di test. 
- Genera SMBIOS casuali - rigenera con GenSMBIOS per uso personale
- Non distribuire EFI con seriali generati
- Hackintosh viola EULA macOS - usalo solo se hai licenza macOS
- L'autore non è responsabile per danni hardware/software

## 📄 Licenza

MIT License - Vedi LICENSE file

## 🆘 Supporto

- Apri issue su GitHub
- Leggi Dortania guide prima
- Controlla log del tool - scarica file REALI, non finti

---

**Made with ❤️ for Fujitsu Esprimo Q556/2 community**

> Prima: EFI con file vuoti/finti che non bootano
> Ora: EFI REALI con download ufficiali che funzionano
