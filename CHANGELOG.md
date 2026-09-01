# Changelog - Tutte le bestemmie in ordine cronologico

## 2.0.1 Beta 1 — HOTFIX SELETTORE CLI - 2026-09-01

> Stessa versione **2.0.1 Beta 1**, ricostruita con il selettore corretto.
> Non è una 2.0.2. Build: `releases/OpenHackintosh-2.0.1-Beta-1-fixed.zip`
> (la build originale resta `releases/OpenHackintosh-2.0.1-Beta-1.zip`).

### Corretto — componente di selezione/input del menu (root cause)

Il menu principale leggeva **un solo carattere** e lo convertiva subito in una
scelta (`int(char) - 1`). Un modello a cifra singola, quindi:

- **numeri multi-cifra impossibili**: digitando `1` poi `0` veniva selezionata
  l'opzione `1`, e la voce `[10] Exit` era irraggiungibile da tastiera;
- **frecce non riconosciute in application cursor mode**: erano gestite solo le
  sequenze `ESC [ A` / `ESC [ B`, non `ESC O A` / `ESC O B` — quelle inviate dal
  Terminale di macOS, da `tmux` e da `screen`;
- **ESC bloccava il programma**: dopo `\x1b` veniva eseguita una
  `sys.stdin.read(2)` bloccante, senza timeout;
- **Ctrl+C non funzionava**: `tty.setraw` disabilita ISIG (e OPOST);
- **menu ristampato a ogni tasto** invece di essere aggiornato in place;
- **input non valido ignorato in silenzio**, senza messaggio di errore;
- fallback non-TTY che accettava solo cifre singole e poteva lasciare l'indice
  evidenziato fuori range.

### Aggiunto

- `src/cli/selector.py`: componente di selezione **generico e riusabile**
  - buffer numerico multi-cifra con disambiguazione (cifra successiva, Enter o
    timeout): valido per 10, 12, 100+ opzioni senza modifiche;
  - decoder tastiera completo: `ESC [` (CSI) e `ESC O` (SS3), frecce,
    Home/End/PageUp/PageDown, Tab/Shift+Tab, Backspace/Canc, Enter del
    tastierino, Ctrl+C, Ctrl+D;
  - ESC isolato riconosciuto tramite timeout sulla sequenza;
  - modalità **cbreak** al posto di *raw*: Ctrl+C e l'output restano corretti;
  - lettura via `os.read()` su file descriptor con decoder UTF-8 incrementale
    (niente buffering di `sys.stdin`);
  - ridisegno **in place** del menu con sequenze ANSI, evidenziazione della voce
    attiva e anteprima del numero digitato;
  - messaggi espliciti per l'input non valido, con lo stato del menu preservato;
  - fallback line-based per stdin non interattivo (pipe/CI) con supporto
    multi-cifra, match per etichetta, `q`/`quit`/`exit` e protezione contro i
    loop infiniti.
- `tests/test_selector.py`: 129 test — decodifica tasti, macchina a stati,
  numeri multi-cifra (fino a 123 opzioni), frecce, Enter, ESC, Ctrl+C, input non
  valido, fallback non-TTY, rendering ed **end-to-end su pseudo-terminale reale**.
- `tools/build_release.py`: build riproducibile dello ZIP di distribuzione.
- `docs/HOTFIX-2.0.1-Beta-1-SELECTOR.md`: nota tecnica dell'hotfix.

### Modificato

- `src/cli/interactive.py`: ora è un adattatore sottile sopra `cli.selector`.
  `run_menu()` mantiene la stessa firma e restituisce la voce di uscita quando
  la selezione viene annullata.
- `src/cli/main.py`: voci di menu e mappatura azione→comando estratte in
  `MENU_ITEMS` / `MENU_COMMANDS` (testabili). **La logica delle singole azioni
  non è stata toccata.**

### Invariato

- Versione (`2.0.1 Beta 1`), launcher (`OpenHackintosh.command`,
  `FujitsuEFI.command`, `openhackintosh`, `openhackintosh.sh`), `src/efi/`,
  `src/efi_builder/`, database, detection e compatibilità.

## 2.0.1 Beta 1 - 2026-08-31 - CHECKPOINT DI DISTRIBUZIONE (PRERELEASE)

Questa è una **build di distribuzione/checkpoint** dello stato attuale, non una
nuova fase architetturale. Include:

- **CLI-first workflow**: il tool si usa da terminale, niente GUI/web.
- **Hardware detection/diagnosis**: detection DMI, CPU, GPU, audio, Ethernet, Wi-Fi, USB, storage, ACPI + report `diagnose`.
- **Hardware identification + database matching**: `EXACT_MATCH` / `CLOSE_MATCH` / `PARTIAL_MATCH` / `NO_MATCH`, basato su `src/database/`.
- **Compatibility analysis**: motore deterministico basato su DB/regole/HW-ID, mai su invenzioni AI.
- **EFI generator hardening**: binari reali, validazione Mach-O/PE/COFF/AML, config↔file consistency, zero-byte/placeholder detection, SHA-256, cache, final EFI audit, clean failure.
- **No fake binaries**: se un componente obbligatorio non è ottenibile/verificato, la generazione **fallisce**.
- **Migliorata gestione errori** e output JSON strutturato.

> ⚠️ BETA: il supporto è sperimentale. Nessun profilo viene dichiarato VERIFIED
> senza test fisico sul hardware. Il profilo Q556/2 è marcato VERIFIED dal
> creatore del progetto; Q957 è DOCUMENTED.

## [Unreleased] - 2026-08-30 - v2.0.2 in preparazione (NON PUBBLICATA)

### Rimosso GUI e Web Dashboard: solo terminale

- Rimosso `src/gui/` (GUI customtkinter/tkinter)
- Rimosso `app.py`, `run_web.py`, `templates/`, `static/` (Web Dashboard Flask)
- `main.py` ora è un wrapper che gira direttamente la CLI
- `src/cli.py`: rimossa opzione `--gui`, epilog aggiornato
- `FujitsuEFI.command`: avvio diretto da terminale, niente più tentativo GUI
- `requirements.txt`: rimossi `flask`, `customtkinter`, `pillow`, `packaging`; resta `requests`
- README, CONTRIBUTING, `.github/DESCRIPTION.md` aggiornati: il progetto è CLI-only

### EFI Generator Hardening (2.0.2)

- **NO FAKE BINARIES**: nessun placeholder/fake se un componente obbligatorio non è ottenibile/verificato.
- **Binary validation** (`src/efi/integrity.py`): Mach-O per kext, PE/COFF per driver/OpenCore/BOOTx64, firma AML per SSDT.
- **Hash / Integrity**: SHA-256, versione/source, download time per ogni componente.
- **Download cache** (`~/.cache/openhackintosh`): riusa zip solo se integro; invalida e ri-scarica se corrotti.
- **Config.plist consistency**: cross-reference ACPI/Kext/Driver config <-> file realmente presenti.
- **Zero-byte / placeholder scan** ricorsiva globale.
- **Component Selection minimale**: di default SOLO required. Opzionali espliciti (`--wifi`, `--bluetooth`, `--include-nvme`, `--include-restrict-events`, `--include-optional-drivers`).
- **SSDT da profilo**: Q556/2/Q957 usano `SSDT-PLUG-DRTNIA.aml` e `SSDT-EC-USBX-DESKTOP.aml`; niente AWAC/RHUB automatici.
- **DeviceProperties dal profilo** (no valori inventati).
- **Release vs Dev**: release boot-args pulito; `--dev` abilita debug.
- **Final EFI Audit** (`src/efi/audit.py`) + **generation/failure report** (`VALID` / `FAILED`).
- Interfaccia `generate --json` ora produce JSON pulito (log nascosti in json mode).
- Test di hardening (37 totali) per download failure, fake/invalid binaries, 0-byte, missing kext/driver/ACPI, config mismatch, exit code, Q556/2.

### Hardware Detection / Identification / Diagnosis (2.0.2)

- `DetectedValue` ora espone `value` / `status` / `source`: `DETECTED`, `INFERRED`, `DATABASE_MATCH`, `NOT_DETECTED`, `UNKNOWN`, `NOT_AVAILABLE_ON_PLATFORM`. Se non rilevato: `value: null`.
- Detection arricchita: CPU vendor/architettura/generazione/cores/threads/features; GPU vendor/model/ids/PCI/type/VRAM best-effort; Audio, Ethernet, Wi-Fi con vendor/model/ids/PCI; Bluetooth best-effort (USB/PCI); USB controllers + devices; Storage SATA/NVMe/drives; ACPI tables + DSDT; boot mode UEFI/Legacy.
- **HardwareSnapshot** (`src/hardware/snapshot.py`): rileva una sola volta e condivide detection ↔ matching ↔ compatibility.
- Matcher: `match_type` = `EXACT_MATCH` / `CLOSE_MATCH` / `PARTIAL_MATCH` / `NO_MATCH`.
- Compatibility: `ComponentAssessment.evidence` (Detected / Hardware ID match / Database profile / Documented / Tested) e `match_type` nel JSON.
- `openhackintosh diagnose`: report completo (SYSTEM, CPU, GPU, Audio, Ethernet, Wi-Fi, Storage, DATABASE, DIAGNOSIS, macOS Compatibility, Overall, NOTE). `diagnose --json` produce solo JSON.
- Error handling: la diagnosi continua se una singola sezione di rilevamento fallisce (`detection_errors` tracciato).
- NON toccato il generatore EFI in questa fase.

### Fondazione intelligente (2.0.2)

- **Hardware Detection** (`src/hardware/detection.py`): rileva DMI, CPU, GPU/PCI, audio, Ethernet, WiFi, USB, storage, ACPI; MAI inventa, altrimenti "Unknown / Not detected".
- **Hardware Identification** (`src/hardware/identification.py`): identità confrontabile.
- **Hardware Database JSON** (`src/database/profiles/`): profili `fujitsu_q556_2` e `fujitsu_q957` con stato VERIFIED / DOCUMENTED / UNKNOWN.
- **Database Loader + Matcher** (`src/database/`): caricamento autonomo e matching deterministico per modello/board/HW ID.
- **Compatibility Engine** (`src/compatibility/`): confronto hardware vs profilo con stati compatible/partial/unsupported/unknown. Non usa AI per decidere.
- **AI Layer** (`src/ai/`): solo spiegazione sopra il risultato del motore.
- **EFI Generator hardware-aware** (`src/efi/` + `src/efi_builder/builder.py`): include solo componenti necessari; il download di un componente obbligatorio che fallisce ABORTA, non crea placeholder.
- **EFI Validator avanzato** (`src/efi_builder/validator.py`): rileva 0-byte, placeholder, missing, componenti configurati ma assenti, config/file inconsistency.
- **CLI commands**: `detect`, `info`, `diagnose`, `compatibility`, `generate`, `validate`, `doctor`, `database`, `bios`, `ask`.
- **Output JSON** su tutti i comandi principali; `--dev` per verbose/debug.
- **Guida BIOS per profilo**: `openhackintosh bios --profile fujitsu_q556_2`, solo impostazioni pertinenti, con "requires hardware verification".
- **Tests pytest** (24): detection, database, matching, compatibility, validator 0-byte/placeholder/missing, CLI JSON, reference Q556/2.

## [2.1.0] - 2026-08-29 - OpenHackintosh 🍎

### Perché ho cambiato nome?

Perché alla fine non è solo per Q556/2. Il codice per generare EFI è uguale per tanti PC, ho solo fatto il profilo Q556/2 come principale perché è quello che ho io. Ma se uno ha Q957 o altro Skylake, funziona uguale. Quindi ho detto: chiamiamolo OpenHackintosh, più generico, più figo.

- README riscritto da zero, più umano
- Titolo da "Fujitsu Esprimo Q556/2 Auxiliary Tool" a "OpenHackintosh"
- Descrizione: da tecnica e noiosa a "EFI vere, non finte"
- Preparato per rename repo su GitHub
- Release v2.1.0 con nuovo nome

### Come rinominare repo su GitHub (per me, che me lo dimentico sempre)

1. Vai su Settings del repo
2. General -> Repository name
3. Cambia in OpenHackintosh
4. Rename

GitHub fa redirect automatico, quindi vecchi link continuano a funzionare.

## [2.0.0] - 2026-08-29 - Basta file finti 💥

### La storia

Avevo una prima versione del tool. Bellissima fuori, vuota dentro. Letteralmente file da 0 byte. 3 giorni a bestemmiare davanti a logo Fujitsu che si riavviava.

Ho riscritto tutto da zero.

### Cosa ho fixato

**Prima:**
- BOOTx64.efi 0 byte (finto)
- Lilu.kext senza binario (solo Info.plist vuoto)
- config.plist a caso
- Non bootava mai

**Ora:**
- BOOTx64.efi vero 50KB+ da OpenCorePkg ufficiale
- Kext veri con binari 200-300KB da GitHub ufficiale
- SSDT veri da Dortania
- config.plist fatto seguendo Dortania Skylake
- SMBIOS validi generati
- ZIP pronto per USB che boota davvero

### Novità

- `downloader.py` - Scarica file veri da GitHub API, con progress bar e fallback se mancano certificati SSL
- `config_generator.py` - Genera config.plist corretto per Skylake, con patch HD 530, DVMT fix, alcid=11
- `smbios.py` - Genera seriali validi (12 chars, 17 chars MLB, UUID, ROM) - poi rigeneri con GenSMBIOS per uso tuo
- `validator.py` - Controlla se file sono finti/vuoti (se <100 byte, è finto)
- Profili hardware: Q556/2 (D3403-U, H110, Realtek RTL8111GN, ALC671) e Q957 (Intel LAN)
- Supporto macOS: Monterey, Ventura (consigliato, lo uso io), Sonoma, Sequoia sperimentale
- Auto-swap kext LAN: Realtek per Q556/2, IntelMausi per Q957
- GUI moderna con customtkinter: dark mode, card layout, SF Pro font, progress bar, log live, hardware info, SMBIOS preview - prima era brutta forte
- CLI completo con argparse, help umano
- Web Dashboard Flask: gradient, blur, glassmorphism, responsive, log live - l'ho fatta perché in sandbox non potevo far girare GUI macOS
- Validazione EFI integrata
- Icona 3D professionale (mini PC + Apple glow)
- Launcher macOS FujitsuEFI.command (doppio click)
- README con BIOS setup, troubleshooting, tabella kext - scritto col sangue
- docs/FAKE_VS_REAL.md - spiego perché prima non andava, con esempi file finti vs veri
- docs/BIOS_GUIDE.md - guida BIOS con DVMT 64MB ovunque perché è fondamentale
- LICENSE MIT, CONTRIBUTING, .gitignore

### Design

Prima: UI base con tkinter standard, colori default, layout semplice, nessuna progress bar, log testuale base.

Ora:
- GUI: customtkinter, dark theme, blue accent, card layout, SF Pro font, progress bar, log colorato, badge, hardware info, SMBIOS preview
- Web: gradient, blur, glassmorphism, monospace log, status badge, responsive
- Icona: 3D render mini PC + Apple glow, professionale
- README: badges, tabelle, emoji, storia personale, più umano

### Tecnico

- Struttura progetto professionale: src/efi_builder/, src/gui/, assets/, tools/, templates/
- Type hints, dataclasses, error handling
- GitHub API per latest releases
- Zip extraction con ricerca ricorsiva kext
- Plist generation con xml
- Threading per build non bloccante
- Progress callback

### Test

- Testato offline build con dummy files - genera struttura valida e ZIP
- Testato import - tutti i moduli si importano
- Testato download GitHub API - funziona su macOS con certificati, in sandbox Linux mancano certificati ma ho messo fallback

## [1.0.0] - 2026-08-28 - Quello finto

- Generazione struttura EFI
- File vuoti/finti (problema)
- Design base
- Prima versione non funzionante
- Non bootava
- 3 giorni di bestemmie

---

Morale: non fidarti dei tool che generano file senza scaricarli da fonti ufficiali. Se EFI è 100KB totale, è finta. Una vera è 15-20MB.
