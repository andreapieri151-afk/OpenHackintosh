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

Tu scegli il tuo PC, clicchi un bottone, lui fa tutto:

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

**Fujitsu Esprimo Q957** - Simile al Q556/2
- Board D3403-U2/D3600, Q270, Intel I219 LAN
- Stessa EFI, cambia solo kext LAN (IntelMausi invece di Realtek)

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

- Scegli il tuo hardware da una lista
- Scegli macOS target
- Clicchi e ti fa EFI vera con download ufficiali
- Non devi più cercare kext a mano

Un po' come OpCore-Simplify ma più semplice, più umano, con GUI bella e con focus su mini PC (che sono i migliori per Hackintosh secondo me - piccoli, silenziosi, consumano poco).

---

## Come si usa? (3 modi)

### 1. Doppio click su macOS (il più facile)

Scarica release, scompatta, doppio click su `FujitsuEFI.command` (lo rinominerò in OpenHackintosh.command presto). Se mancano dipendenze te le installa da solo.

### 2. GUI Python

```bash
git clone https://github.com/andreapieri151-afk/OpenHackintosh.git
cd OpenHackintosh
pip install -r requirements.txt
python3 main.py
```

Scegli PC, macOS (Ventura consigliato per Q556/2), SMBIOS (iMac18,1 per iniziare), audio layout (11 di solito va), clicchi "Crea EFI vera, non finta". Vedi log live e ZIP finale.

### 3. Terminale (per chi si sente hacker)

```bash
# Vedi cosa supporta ora
python3 src/cli.py --list-profiles

# EFI base Q556/2 Ventura
python3 src/cli.py --profile Q556/2 --macos "Ventura 13.x" --smbios iMac18,1

# EFI Sonoma con WiFi Intel
python3 src/cli.py --profile Q556/2 --macos "Sonoma 14.x" --smbios iMacPro1,1 --wifi --bluetooth

# Per Q957
python3 src/cli.py --profile Q957 --macos "Ventura 13.x"
```

### 4. Web (Linux o per fare il figo)

```bash
python3 app.py
# http://localhost:5000
```

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
- [x] GUI decente
- [x] CLI e Web Dashboard
- [x] Supporto Q556/2 e Q957
- [x] Rinominato OpenHackintosh (da tool singolo a universale)
- [x] README più umano
- [ ] **Nuovi dispositivi nei prossimi giorni** (Q558, Q958, Lenovo Tiny, HP Mini, Dell Micro)
- [ ] macserial nativo per seriali più furbi
- [ ] USB mapping automatico
- [ ] Creazione chiavetta installer automatica
- [ ] Supporto più hardware generico (framework già pronto)

---

## Come contribuire

Se vuoi aggiungere il tuo PC, è facile:

1. Apri `src/efi_builder/hardware.py`
2. Aggiungi profilo tipo:

```python
MIO_PC = HardwareProfile(
    name="Lenovo ThinkCentre M720q",
    board="... ",
    lan_kext="IntelMausi.kext",
    ...
)
PROFILES["M720q"] = MIO_PC
```

3. Fai PR con modello, board, LAN, audio, CPU

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
