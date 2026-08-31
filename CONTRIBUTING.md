# Come contribuire - Senza troppi formalismi

Ciao! Se vuoi dare una mano a OpenHackintosh, sei il benvenuto. Non serve essere un genio di Hackintosh, basta avere voglia.

## Come iniziare (veloce)

```bash
git clone https://github.com/andreapieri151-afk/OpenHackintosh.git
cd OpenHackintosh
pip install -r requirements.txt
python3 src/cli.py --list-profiles
```

Il tool gira da terminale. `main.py` è solo un wrapper che delega alla CLI.

## Cosa puoi fare

### 1. Aggiungere il tuo PC

Se hai un Fujitsu diverso da Q556/2 o un altro mini PC Skylake/Kaby Lake, aggiungi il profilo.

Apri `src/efi_builder/hardware.py` e aggiungi:

```python
MIO_PC = HardwareProfile(
    name="Il mio PC figo",
    board="D1234",
    chipset="Intel H110",
    cpu_generations=["Skylake"],
    igpu="HD 530",
    lan_chip="Realtek RTL8111",
    lan_kext="RealtekRTL8111.kext",
    audio_codec="ALC671",
    audio_layout_ids=[11,13,15],
    usb_ports={"USB2": 2, "USB3": 4},
    smbios_recommended=["iMac18,1"],
    notes="DVMT 64MB necessario"
)

PROFILES["MioPC"] = MIO_PC
```

Poi fai PR. Se funziona, lo aggiungo.

### 2. Aggiungere kext

Se manca un kext che ti serve, aggiungilo in `KEXTS` in `hardware.py`:

```python
KEXTS["MioKext"] = {
    "repo": "utente/repo-github",
    "required": False,
    "description": "A cosa serve",
    "bundle": "MioKext.kext"
}
```

Il downloader lo scaricherà da GitHub release.

### 3. Migliorare la CLI

La CLI è in `src/cli/` (package). Se hai idee per renderla più chiara, con più opzioni o con output migliore, fai pure. La release 2.0.2 è solo terminale, quindi la CLI è la faccia principale del tool.

### 4. Fixare bug

Se trovi bug, apri issue con:
- Che PC hai
- Che macOS vuoi
- Log del tool (copia incolla)
- Cosa ti aspettavi vs cosa è successo

### 5. Scrivere guide

Se hai risolto un problema strano con Q556/2, scrivi una guida in `docs/`. Io ho scritto BIOS_GUIDE.md e FAKE_VS_REAL.md con sangue, se ne hai altre ben vengano.

## Struttura progetto (così non ti perdi)

```
src/efi_builder/
  hardware.py       -> Profili PC (legacy), kext, driver, SSDT
  downloader.py     -> Scarica file veri da GitHub (quello che fixa i file finti)
  config_generator.py -> Genera config.plist per Skylake
  smbios.py         -> Genera seriali a caso
  builder.py        -> Mette tutto insieme e fa ZIP (hardware-aware)
  validator.py      -> Validazione EFI avanzata (placeholder/missing/0-byte)

src/hardware/       -> Hardware detection + identification
src/database/       -> Profili JSON (hardware_profiles/), loader, matcher
src/compatibility/  -> Compatibility Engine (deterministico, non AI)
src/efi/            -> Selezione componenti + generator hardware-aware
src/ai/             -> Layer di spiegazione sopra il Compatibility Engine
src/cli/            -> CLI: commands/, interactive UI, output JSON/testo

main.py             -> Wrapper che gira la CLI (entry point terminal)
```

## Regole (poche)

- **File veri, non finti**: Se aggiungi qualcosa, scaricalo da fonte ufficiale, non creare placeholder vuoti. Ho già dato con i file finti.
- **Testa prima di fare PR**: Lancia `python3 src/cli.py --help` e vedi se non crasha.
- **Scrivi umano**: Nei log, nei messaggi, nei commenti, scrivi come parleresti a un amico, non come un manuale tecnico. Tipo "Sto scaricando OpenCore vero..." non "Downloading OpenCore...".
- **Non rompere Q556/2**: Se aggiungi roba per altri PC, assicurati che Q556/2 continui a funzionare. È il profilo principale, quello che ho io.

## PR

1. Forka
2. Branch: `feature/mia-idea-figa`
3. Fai modifiche
4. Testa che non rompa tutto
5. Commit con messaggio che si capisce: "Aggiunto profilo Q558" non "fix"
6. Apri PR con descrizione: cosa hai fatto, perché, testato su che hardware

Non serve essere perfetti, se c'è qualcosa da sistemare te lo dico nella PR.

## Cose che vorrei fare (se hai tempo)

- [ ] macserial nativo per seriali più furbi (ora sono a caso ma formato giusto)
- [ ] USB mapping automatico (ora devi farlo a mano con USBToolBox)
- [ ] OCAT integration
- [ ] Auto-update kexts
- [ ] Creazione chiavetta installer automatica (createinstallmedia wrapper)
- [ ] Supporto più hardware generico (se mi mandate profili)
- [ ] Traduzione EN/DE oltre IT (ora è mezzo IT mezzo EN, lo so)

Se ne fai una, sei un mito.

## Domande?

Apri issue su GitHub, rispondo quando ho tempo (di solito sera).

Oppure leggi README, c'è già tanta roba.

Grazie! ❤️

Andrea - quello che ha bestemmiato 3 giorni davanti a un Fujitsu che non bootava
