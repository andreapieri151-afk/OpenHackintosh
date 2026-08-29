# OpenHackintosh 🍎💻

> *"Basta EFI finte che non bootano nemmeno a pagarle"*

Ciao! Sono Andrea, e questo è **OpenHackintosh** - il tool che avrei voluto avere quando ho iniziato a smanettare con il mio Fujitsu Esprimo Q556/2.

### La storia (veloce, promesso)

Allora, avevo questo mini PC Fujitsu Q556/2 - carino, piccolo, silenzioso, perfetto per farci un Hackintosh. Provo con un tool generato con Google AI Studio... struttura EFI bellissima, cartelle perfette, tutto ordinato. Peccato che dentro i file fossero **vuoti**. Letteralmente 0 byte. Oppure con dentro scritto "fake efi file". 

Risultato? Tre giorni a bestemmiare davanti a un logo Fujitsu che si riavviava all'infinito. 

Così ho detto: basta. Lo riscrivo da zero, ma **per bene**. Con file veri, scaricati da GitHub ufficiale, non fuffa.

E ora è qui. E si chiama OpenHackintosh perché alla fine funziona anche per altri PC, non solo il mio Q556/2.

---

## Cosa fa, in pratica?

Tu clicchi un bottone, lui fa tutto:

1. **Scarica OpenCore vero** da Acidanthera (non un file di testo rinominato .efi)
2. **Scarica i kext veri** - Lilu, VirtualSMC, WhateverGreen, AppleALC... con i binari dentro, non solo l'Info.plist vuoto
3. **Scarica gli SSDT veri** da Dortania (quelli che ti fanno funzionare CPU, USB, NVRAM)
4. **Ti genera il config.plist giusto** per Skylake, non uno a caso copiato da internet
5. **Ti inventa un SMBIOS credibile** (serial, MLB, UUID, ROM) - poi tu lo rigeneri con GenSMBIOS per i fatti tuoi
6. **Ti fa lo ZIP** pronto da buttare nella EFI della chiavetta

Fine. Non devi andare a cercare kext su 10 siti diversi, non devi impazzire con ProperTree per ore.

### Prima vs Ora

| Prima (tool AI Studio) | Ora (OpenHackintosh) |
|---|---|
| BOOTx64.efi 0 byte | BOOTx64.efi 50KB+ vero |
| Lilu.kext senza binario | Lilu.kext con binario 245KB |
| config.plist a caso | config.plist per Skylake fatto bene |
| Non boota mai | Boota (se imposti il BIOS giusto) |

---

## Per chi è?

- Hai un **Fujitsu Esprimo Q556/2** (D3403-U, H110, Realtek LAN, ALC671) - sei a casa, è nato per te
- Hai un **Q957** (simile ma con Intel LAN) - funziona uguale, cambia solo un kext
- Hai un altro Skylake/Kaby Lake e vuoi provare - il framework c'è, puoi aggiungere il tuo profilo

Io l'ho testato sul mio Q556/2 con i3-6100T e HD 530. Ventura gira una meraviglia. Sonoma con iMacPro1,1 pure.

---

## Come si usa? (3 modi)

### 1. Doppio click su macOS (il più facile)

Scarica la release, scompatta, doppio click su `FujitsuEFI.command`. Se non hai le dipendenze te le installa da solo. Ti si apre una finestra bella, dark mode, con tutto.

### 2. GUI Python

```bash
git clone https://github.com/andreapieri151-afk/OpenHackintosh.git
cd OpenHackintosh
pip install -r requirements.txt
python3 main.py
```

Ti si apre la GUI: scegli Q556/2 o Q957, scegli macOS (Ventura consigliato), SMBIOS (iMac18,1 per iniziare), layout audio (11 di solito va), e clicchi "Genera EFI Reale". Vedi i log in tempo reale, la progress bar, e alla fine ti dice dove ha messo lo ZIP.

### 3. Da terminale (per chi si sente hacker)

```bash
# Vedi cosa supporta
python3 src/cli.py --list-profiles

# Build base
python3 src/cli.py --profile Q556/2 --macos "Ventura 13.x" --smbios iMac18,1

# Build cattivo per Sonoma con WiFi Intel
python3 src/cli.py --profile Q556/2 --macos "Sonoma 14.x" --smbios iMacPro1,1 --wifi --bluetooth
```

### 4. Web (se sei su Linux o vuoi fare il figo)

```bash
python3 app.py
# vai su http://localhost:5000
```

Interfaccia web carina, tutta nera e blu, con log live. L'ho messa perché in sandbox non potevo far girare la GUI macOS.

---

## Il BIOS, croce e delizia del Q556/2

Ascolta, questa parte è importante, se la sbagli non boota manco con l'EFI di Cristo.

**Entra nel BIOS con F2** all'avvio.

**Disabilita questa roba:**
- Fast Boot
- Secure Boot (sta in Security)
- Serial Port, Parallel Port
- VT-d (oppure lasciala ma il config ha già DisableIoMapper YES)
- CSM - mettilo su Disabled, vogliamo solo UEFI
- Intel SGX, Platform Trust

**Abilita:**
- VT-x (virtualization)
- Above 4G decoding (se c'è)
- EHCI/XHCI Hand-off
- OS Type: Windows 8.1/10 UEFI
- **DVMT Pre-Allocated: 64MB - QUESTO È FONDAMENTALE**

Se non trovi DVMT 64MB (succede, Fujitsu blocca il BIOS), il tool ti mette già una patch nel config, ma se puoi modda il BIOS o cerca su bios-mods.com. Altrimenti kernel panic assicurato con HD 530.

**CFG Lock:** Se lo trovi, disabilitalo. Se non lo trovi, lascia stare - il tool mette AppleXcpmCfgLock YES e funziona lo stesso.

Se incasini tutto: spegni, stacca la spina, apri il case (2 viti), trova il jumper del BIOS vicino alla batteria, spostalo 10 secondi, rimettilo. O togli la batteria 10 minuti. Torna tutto default.

Guida completa in `docs/BIOS_GUIDE.md` - l'ho scritta con sangue.

---

## Cosa c'è dentro l'EFI che genera?

```
EFI/
├── BOOT/BOOTx64.efi (quello vero, non finto)
└── OC/
    ├── ACPI/ -> SSDT-PLUG, EC-USBX, AWAC, PMC (veri, presi da Dortania)
    ├── Drivers/ -> HfsPlus, OpenRuntime, OpenCanopy (veri)
    ├── Kexts/ -> Lilu, VirtualSMC, WhateverGreen, AppleALC, RealtekRTL8111 (veri, con binari)
    ├── OpenCore.efi (vero, 1MB+)
    └── config.plist (fatto seguendo Dortania Skylake, non a caso)
```

Il config ha già:
- Lilu per primo (obbligatorio)
- ig-platform-id giusto per HD 530 (00001219) o 630 (00001259)
- boot-args con alcid=11 (per ALC671)
- ReleaseUsbOwnership YES (fix per quel maledetto EXITBS:START)
- SMBIOS generato

---

## Problemi comuni (che ho avuto pure io)

**Stuck su [EB|LOG:EXITBS:START]** -> 99% è DVMT non a 64MB. Controlla BIOS. Poi controlla che ReleaseUsbOwnership sia YES (lo è già nel config del tool).

**Schermo nero** -> Prova -igfxvesa nei boot-args, o cambia SMBIOS, o controlla cavo DP/DVI. Il Q556/2 non ha HDMI nativo, serve adattatore DP->HDMI attivo.

**Audio non va** -> Prova layout diversi: 11, 13, 15, 21, 27, 28. Io con 11 ho risolto, ma ogni scheda è un mondo.

**LAN non va** -> Q556/2 usa RealtekRTL8111, Q957 usa IntelMausi. Il tool lo fa già in automatico se scegli il profilo giusto.

**USB non vanno** -> Mappa le porte con USBToolBox, poi togli XhciPortLimit. Lo so, è una palla, ma va fatto.

---

## Kext inclusi

- **Lilu** - il boss, serve per tutti gli altri
- **VirtualSMC** - finge di essere un Mac vero
- **WhateverGreen** - sistema la grafica
- **AppleALC** - audio ALC671
- **RealtekRTL8111** - LAN per Q556/2 (o IntelMausi per Q957)
- **NVMeFix, RestrictEvents** - utili, non obbligatori
- **Intel WiFi/Bluetooth** - opzionali, se hai scheda Intel

Tutti scaricati da GitHub ufficiale, non da siti strani.

---

## Perché OpenHackintosh e non più Q556/2 Tool?

Perché alla fine il codice per generare EFI è lo stesso per tanti PC. Ho fatto il profilo Q556/2 come principale perché è quello che ho, ma il framework è lì - puoi aggiungere il tuo hardware in `src/efi_builder/hardware.py` e funziona.

L'idea è: un tool che fa una cosa sola ma la fa bene, con file veri, senza fuffa.

---

## Roadmap (cose che voglio fare quando ho tempo)

- [x] Fix file finti -> file veri
- [x] GUI decente (prima era brutta forte)
- [x] CLI e Web Dashboard
- [x] Supporto Q957
- [x] Rinominato OpenHackintosh
- [ ] Integrazione macserial per seriali più furbi
- [ ] USB mapping automatico (ora lo devi fare a mano)
- [ ] Creazione chiavetta installer automatica
- [ ] Supporto più hardware (se mi mandate i vostri profili)

Se vuoi contribuire, apri una issue o una PR. Non mordo.

---

## Crediti

- **Acidanthera** per OpenCore e i kext (senza di loro non esisterebbe nulla)
- **Dortania** per la guida che è la Bibbia dell'Hackintosh
- **Mieze** per RealtekRTL8111
- **OpenIntelWireless** per WiFi/BT Intel
- La community di hackintosh-forum.de e Reddit r/hackintosh - ho copiato un sacco da loro

---

## Disclaimer (quello noioso ma necessario)

- Questo è per studio/test. Genera SMBIOS casuali, poi rigenerali con GenSMBIOS per uso personale.
- Non condividere EFI con seriali generati.
- Hackintosh viola EULA macOS - usalo solo se hai una licenza macOS vera.
- Non sono responsabile se bricki tutto. Fai backup.
- MIT License - fai quello che vuoi ma non rompere.

---

## Supporto

Se non ti funziona:
1. Leggi `docs/FAKE_VS_REAL.md` - spiego perché prima non andava
2. Leggi `docs/BIOS_GUIDE.md` - 90% dei problemi è lì
3. Controlla i log del tool - scarica file veri, non finti
4. Apri una issue su GitHub, ma metti i log e che hardware hai

---

Fatto con ❤️ e tante bestemmie davanti a un Fujitsu che non bootava.

**Prima:** EFI con file vuoti che non bootano nemmeno se preghi  
**Ora:** EFI veri che bootano (se imposti il BIOS come si deve)

*OpenHackintosh - Da un Q556/2 frustrato a tool per tutti*
