# BIOS Guide per Fujitsu Esprimo Q556/2 Hackintosh

## Accesso BIOS

- Premi `F2` all'avvio (logo Fujitsu)
- Oppure `F12` per boot menu

## Versione BIOS

- Tipo: AMI Aptio V
- Aggiorna all'ultima versione da Fujitsu support
- Versione consigliata: V5.0.0.11 o superiore

## Impostazioni CRITICHE

### 1. DVMT Pre-Allocated (FONDAMENTALE)

**Percorso**: Advanced → Graphics Configuration → DVMT Pre-Allocated

**Imposta a**: **64MB** (o 128MB)

**Perché**: macOS richiede minimo 64MB per HD 530. Se imposti 32MB, kernel panic.

**Se non trovi l'opzione**:
- Il tool applica già patch framebuffer (stolenmem 19MB, fbmem 9MB)
- Ma meglio moddare BIOS o usare setup_var:
  ```
  setup_var 0xXXX 0x2  # Dove XXX è offset DVMT (varia per versione BIOS)
  ```
- Cerca su bios-mods.com per Q556/2 DVMT unlock

### 2. Disabilita (Security → o Advanced)

- **Fast Boot**: Disabled
- **Secure Boot**: Disabled (in Security → Secure Boot Configuration)
- **Intel SGX**: Disabled
- **Intel Platform Trust**: Disabled
- **Serial Port**: Disabled (Advanced → Super IO)
- **Parallel Port**: Disabled se presente
- **VT-d**: Disabled (o lascia Enabled ma imposta DisableIoMapper YES in config.plist - già fatto dal tool)
- **CSM**: Disabled (Boot → CSM → Disabled) - IMPORTANTE per UEFI boot puro

### 3. Abilita

- **VT-x**: Enabled (Advanced → CPU Configuration → Intel Virtualization Technology)
- **Above 4G decoding**: Enabled (Advanced → PCI Subsystem Settings) - Se non c'è, lascia Disabled e usa boot-arg npci=0x2000
- **EHCI/XHCI Hand-off**: Enabled (Advanced → USB Configuration)
- **OS Type**: Windows 8.1/10 UEFI Mode (Boot → OS Type)
- **DVMT Total**: MAX (Graphics Configuration)
- **Boot Mode**: UEFI only (non Legacy)

### 4. Boot Order

- **Boot → Boot Option #1**: USB (per installazione)
- Dopo installazione: imposta SSD/HDD con OpenCore come primo

## Impostazioni Consigliate Complete

```
Advanced:
  CPU Configuration:
    Intel Virtualization Technology: Enabled
    VT-d: Disabled
    CFG Lock: Disabled (se presente, altrimenti lascia - gestito da AppleXcpmCfgLock YES)
  Graphics Configuration:
    Primary Display: IGFX (se usi iGPU HD 530)
    DVMT Pre-Allocated: 64MB
    DVMT Total: MAX
  USB Configuration:
    XHCI Hand-off: Enabled
    EHCI Hand-off: Enabled
    Legacy USB Support: Enabled
  Super IO:
    Serial Port: Disabled

Security:
  Secure Boot: Disabled
  Intel SGX: Disabled
  Intel Platform Trust: Disabled

Boot:
  Boot Mode: UEFI
  Fast Boot: Disabled
  CSM: Disabled
  OS Type: Windows 8.1/10 UEFI
  PXE Boot: Disabled (opzionale)
```

## CFG Lock

### Cos'è
MSR 0xE2 write protection. Se Enabled, macOS non può scrivere su MSR e serve patch.

### Come disabilitare su Q556/2

**Opzione 1**: Se opzione presente in BIOS (raro su Fujitsu)
- Advanced → CPU Configuration → CFG Lock → Disabled

**Opzione 2**: Via setup_var (consigliato)
1. Crea USB con EFI Shell (da OpenCorePkg → Tools)
2. Boota in EFI Shell
3. Trova offset CFG Lock:
   ```
   setup_var 0x4ED 0x0  # Esempio, offset varia
   ```
   Per trovare offset corretto:
   - Dump BIOS con AFU o CH341A programmer
   - Apri con AMIBCP o UEFITool
   - Cerca CFG Lock

4. Oppure usa tool CFGLock.efi incluso in OpenCore:
   - Metti CFGLock.efi in EFI/OC/Tools
   - Abilita in config.plist → Misc → Tools
   - Boota da OpenCore → seleziona CFGLock.efi → disabilita

**Opzione 3**: Lascia Enabled e usa quirk (già fatto dal tool)
- Tool imposta `AppleXcpmCfgLock: YES` e `AppleCpuPmCfgLock: YES`
- Funziona ma non ottimale per power management

**Verifica**:
```
# In macOS, verifica se CFG Lock disabilitato
# Se disabilitato, puoi mettere AppleXcpmCfgLock: NO
```

## BIOS Modding (Avanzato)

Se vuoi sbloccare opzioni nascoste:

1. **Dump BIOS**:
   - Usa CH341A programmer + SOIC8 clip
   - Oppure AFUWIN / AFUDOS (rischio brick)

2. **Modifica con AMIBCP**:
   - Apri dump in AMIBCP 5.02
   - Sblocca opzioni nascoste
   - Salva

3. **Flash**:
   - Con programmer (sicuro)
   - Oppure con AFU (rischio)

**Attenzione**: Rischio brick! Fai backup e usa programmer.

## Reset BIOS

Se qualcosa va storto:

1. Spegni PC, stacca alimentazione
2. Apri case (2 viti dietro)
3. Trova jumper BIOS (vicino batteria CMOS)
4. Sposta jumper da 1-2 a 2-3 per 10 sec
5. Rimetti a 1-2
6. Oppure rimuovi batteria CMOS per 10 minuti

Oppure:
- Tieni premuto power button 30 sec senza alimentazione

## Note Q556/2 Specifiche

- **RAM**: 2 slot SO-DIMM DDR4, max 32GB, dual channel. Usa 2 banchi uguali per performance
- **Storage**: 1x M.2 SATA/NVMe (controlla), 1x 2.5" SATA, 2x SATA III totali
- **LAN**: Realtek RTL8111GN - funziona con RealtekRTL8111.kext
- **Audio**: ALC671 - layout 11 consigliato, prova 13,15,21 se non va
- **USB**: 2x USB 2.0 rear, 4x USB 3.0 (2 front, 2 rear) - mappa con USBToolBox
- **Video**: DP + DVI-D, no HDMI nativo (usa adattatore DP->HDMI attivo se serve)
- **WiFi/BT**: Opzionale M.2 2230, se Intel usa AirportItlwm + IntelBluetoothFirmware

## Dopo BIOS Setup

1. Crea USB installer macOS con createinstallmedia
2. Usa questo tool per generare EFI
3. Copia EFI su EFI partition USB
4. Boota da USB (F12 → USB)
5. Installa macOS
6. Dopo install, copia EFI su SSD interno
7. Mappa USB, genera SMBIOS unico, etc

## Troubleshooting BIOS

### Non entra in BIOS (F2 non funziona)
- Prova F1, DEL, ESC
- Rimuovi HDD/SSD, boota senza - a volte entra
- Reset CMOS

### Stuck su logo Fujitsu dopo modifiche
- Reset CMOS con jumper
- Rimuovi RAM, boota, rimetti
- Prova con 1 banco RAM solo

### DVMT non trovabile
- Normale su BIOS Fujitsu locked
- Usa patch framebuffer (già nel config del tool)
- Oppure mod BIOS
