# OpenHackintosh 🍎💻

> *"Basta EFI finte che non bootano nemmeno a pagarle"*

Ciao! Sono Andrea, e questo è **OpenHackintosh** - il tool che crea EFI Hackintosh **vere** che bootano davvero.

### La storia (veloce, promesso)

Avevo un mini PC Fujitsu Esprimo Q556/2 - piccolo, silenzioso, perfetto per Hackintosh. Provo un tool fatto con AI... struttura EFI bellissima, cartelle perfette. Peccato che dentro i file fossero **vuoti**. 0 byte. Oppure con scritto "fake efi file".

Tre giorni a bestemmiare davanti a un logo Fujitsu che si riavviava all'infinito.

Così l'ho riscritto da zero, ma **per bene**. Con file veri scaricati da GitHub ufficiale. E ora funziona. E siccome il codice per generare EFI è uguale per tanti PC, l'ho reso universale. Si chiama OpenHackintosh.

**Ora supporta Q556/2 e Q957, e nei prossimi giorni aggiungerò altri dispositivi** - mini PC, laptop, desktop Skylake/Kaby Lake/Coffee Lake. Se hai un PC e vuoi che lo supporti, apri una issue con il modello e lo aggiungo.

---

## Cosa fa, in pratica?

Tu scrivi un comando da terminale, lui fa tutto:

1. **Scarica OpenCore vero** da Acidanthera (non un file di testo rinominato .efi)
2. **Scarica i kext veri** - Lilu, VirtualSMC, WhateverGreen, AppleALC... con i binari dentro
3. **Scarica gli SSDT veri** da Dortania
4. **Genera config.plist giusto** per il tuo hardware (non uno a caso)
5. **Crea SMBIOS credibile**
6. **Fa ZIP** pronto per USB

Non devi cercare kext su 10 siti, non devi impazzire con ProperTree per ore.

### Prima vs Ora

| Prima (vecchia versione) | Ora (OpenHackintosh) |
|---|---|
| BOOTx64.efi 0 byte | BOOTx64.efi 50KB+ vero |
| Lilu.kext senza binario | Lilu.kext 245KB con binario |
| config.plist a caso | config.plist per il tuo hardware |
| Non boota mai | Boota (se BIOS è giusto) |

---

## 🖥️ Dispositivi supportati (e in arrivo)

### ✅ Già supportati

**Fujitsu Esprimo Q556/2** - Il mio, testato personalmente
- Board D3403-U, H110, i3/i5/i7-6xxxT, HD 530/630, Realtek RTL8111GN, ALC671
- SMBIOS consigliato: iMac18,1
- macOS: Ventura va una meraviglia, Sonoma con iMacPro1,1


### 🚧 In arrivo nei prossimi giorni

Sto lavorando per aggiungere:

- **Fujitsu Esprimo Q558, Q958, Q556, Q956** - Altri mini Esprimo
- **Lenovo ThinkCentre Tiny** (M700, M710, M720, M920) - Molto simili, molto richiesti
- **HP EliteDesk / ProDesk Mini** (G2, G3, G4) - Altri mini PC popolari per Hackintosh
- **Dell OptiPlex Micro** (3040, 3050, 3060, 7040, 7050) - Stessa famiglia
- **Laptop generici Skylake/Kaby Lake** - Con patch batteria, trackpad
- **Desktop custom Skylake/Kaby/Coffee Lake** - Framework generico

Se hai un PC specifico e vuoi che lo aggiunga prima, apri una issue su GitHub con:
- Modello esatto
- Board, chipset, CPU, LAN, audio, GPU
- Se hai già una EFI funzionante (anche parziale) linkala

Li aggiungo in ordine di richiesta.

### 🔮 Visione

L'idea è fare un **tool universale** che non sia legato a un solo PC. Un posto dove:

- Rileva il tuo hardware da solo (se possibile)
- Scegli/identifica il profilo dal database
- Scegli macOS target
- Esegui un comando e ti genera EFI vera con download ufficiali
- Non devi più cercare kext a mano

Un po' come OpCore-Simplify ma più semplice, più umano, con CLI chiara e con focus su mini PC (che sono i migliori per Hackintosh secondo me - piccoli, silenziosi, consumano poco).

---

## Come si usa? (da terminale)

La 2.0.2 è **solo terminale**: ho tolto GUI e Web Dashboard per mantenere il tool semplice, testabile e senza dipendenze inutili.

### 1. Doppio click su macOS (il più facile)

Scarica release, scompatta, doppio click su `FujitsuEFI.command` (lo rinominerò in OpenHackintosh.command presto). Apre il terminale, installa le dipendenze se servono, elenca i profili disponibili.

### 2. Terminale (interfaccia principale)

```bash
git clone https://github.com/andreapieri151-afk/OpenHackintosh.git
cd OpenHackintosh
pip install -r requirements.txt

# Menu interattivo
python3 main.py

# Rileva hardware reale
python3 main.py detect

# Diagnosi completa (hardware + compatibilità + spiegazione)
python3 main.py diagnose

# Controlla compatibilità con il database
python3 main.py compatibility

# Genera EFI hardware-aware
python3 main.py generate

# Valida una EFI già generata
python3 main.py validate output/EFI

# Profili database
python3 main.py database list
python3 main.py database show fujitsu_q556_2

# Output JSON (per script/CI/AI)
python3 main.py diagnose --json
python3 main.py detect --json
```

Tutte le opzioni sono visibili con `python3 main.py --help`.

---

## Il BIOS, croce e delizia del Q556/2

Se sbagli qui non boota manco con EFI di Cristo. Vale per Q556/2 ma simile per altri mini PC.

**F2 all'avvio per entrare nel BIOS.**

**Disabilita:**
- Fast Boot, Secure Boot, Serial Port, Parallel Port, VT-d, CSM, SGX, Platform Trust

**Abilita:**
- VT-x, Above 4G, EHCI/XHCI Hand-off, OS Windows 8.1/10 UEFI, **DVMT 64MB - FONDAMENTALE**

Se non trovi DVMT 64MB (Fujitsu lo nasconde), il tool mette già patch, ma meglio moddare BIOS. Guida completa in `docs/BIOS_GUIDE.md`.

**CFG Lock:** Se lo trovi disabilitalo, altrimenti il tool mette AppleXcpmCfgLock YES e funziona lo stesso.

Se incasini tutto: togli batteria CMOS 10 minuti o sposta jumper BIOS.

---

## Cosa c'è dentro l'EFI?

```
EFI/
├── BOOT/BOOTx64.efi (vero, 50KB+)
└── OC/
    ├── ACPI/ -> SSDT-PLUG, EC-USBX, AWAC, PMC (veri da Dortania)
    ├── Drivers/ -> HfsPlus, OpenRuntime, OpenCanopy (veri)
    ├── Kexts/ -> Lilu, VirtualSMC, WhateverGreen, AppleALC, RealtekRTL8111 (veri con binari)
    ├── OpenCore.efi (vero, 1MB+)
    └── config.plist (fatto bene per il tuo hardware, non a caso)
```

---

## Problemi comuni

**[EB|LOG:EXITBS:START]** -> 99% DVMT non a 64MB. Controlla BIOS.

**Schermo nero** -> Prova -igfxvesa, cambia SMBIOS, controlla cavo DP/DVI. Q556/2 non ha HDMI nativo.

**Audio non va** -> Prova layout 11,13,15,21. Io con 11 ho risolto.

**LAN non va** -> Q556/2 RealtekRTL8111, Q957 IntelMausi. Tool fa swap automatico.

**USB non vanno** -> Mappa con USBToolBox, poi togli XhciPortLimit.

Guida completa in docs/.

---

## Kext inclusi

- **Lilu, VirtualSMC, WhateverGreen, AppleALC** - base, obbligatori
- **RealtekRTL8111 / IntelMausi** - LAN (auto in base a PC)
- **NVMeFix, RestrictEvents** - utili
- **Intel WiFi/BT** - opzionali

Tutti da GitHub ufficiale.

---

## Roadmap

- [x] Fix file finti -> file veri
- [x] CLI chiara e usabile da terminale
- [x] Supporto Q556/2 e Q957
- [x] Rinominato OpenHackintosh (da tool singolo a universale)
- [x] README più umano
- [x] Rimossa GUI e Web Dashboard (v2.0.2: solo terminale)
- [x] Hardware Detection (`hardware/detection.py`)
- [x] Hardware Database JSON (`database/profiles/`)
- [x] Compatibility Engine deterministico (`compatibility/`)
- [x] CLI commands: detect, info, diagnose, compatibility, generate, validate, doctor, database
- [x] Output JSON su tutti i comandi principali
- [x] EFI validator avanzato (0-byte / placeholder / missing / config consistency)
- [x] Test automatici base (pytest)
- [ ] **Nuovi dispositivi nei prossimi giorni** (Q558, Q958, Lenovo Tiny, HP Mini, Dell Micro)
- [ ] macserial nativo per seriali più furbi
- [ ] USB mapping automatico
- [ ] Creazione chiavetta installer automatica
- [ ] Supporto più hardware generico (framework già pronto)

---

## Come contribuire

Se vuoi aggiungere il tuo PC, è facile (2.0.2 usa un database JSON):

1. Crea una cartella in `src/database/profiles/` (es. `lenovo_m720q/`)
2. Aggiungi `profile.json` con: manufacturer, model, board, CPU, GPU, audio, LAN, kext/driver/SSDT, SMBIOS, config e stato:
   - `VERIFIED` (testato davvero)
   - `DOCUMENTED` (da documentazione)
   - `UNSUPPORTED` / `UNKNOWN`
3. Fai PR con modello, board, LAN, audio, CPU e che profilo hai testato davvero.

Non inventare compatibilità: se non è testato su hardware reale, scrivi `DOCUMENTED`, mai `VERIFIED`.

Oppure apri issue con il tuo hardware e lo aggiungo io nei prossimi giorni.

Leggi `CONTRIBUTING.md` - l'ho scritto senza formalismi.

---

## Crediti

- **Acidanthera** per OpenCore e kext
- **Dortania** per la guida (la Bibbia)
- **Mieze, OpenIntelWireless** per kext
- Community hackintosh-forum.de, Reddit r/hackintosh

---

## Disclaimer noioso ma necessario

- Per studio/test. Genera SMBIOS a caso, poi rigenera con GenSMBIOS per uso tuo.
- Non condividere EFI con seriali generati.
- Hackintosh viola EULA macOS - usalo solo se hai licenza macOS.
- Non sono responsabile se bricki tutto. Fai backup.
- MIT License

---

## Supporto

Se non va:
1. Leggi `docs/BIOS_GUIDE.md` - 90% dei problemi è lì
2. Leggi `docs/FAKE_VS_REAL.md` - spiego perché prima non andava
3. Controlla log tool - scarica file veri, non finti
4. Apri issue su GitHub con log e hardware

---

Fatto con ❤️ e tante bestemmie davanti a un Fujitsu che non bootava.

**Prima:** EFI con file vuoti che non bootano nemmeno se preghi  
**Ora:** EFI vere che bootano (se imposti BIOS come si deve)  
**Prossimo:** Supporto per tanti altri mini PC, così non devi più cercare kext a mano

*OpenHackintosh - Da un Q556/2 frustrato a tool universale per tutti*
