# OpenHackintosh 2.0.1 Beta 1 — Hotfix del selettore CLI

Questa build è **la stessa versione 2.0.1 Beta 1**: non è una 2.0.2.
Cambia solo il componente di **selezione/input del menu principale**, che nella
prima build di Beta 1 non interpretava correttamente la tastiera.

## Sintomi della build originale

- digitando `1` seguito da `0` veniva selezionata l'opzione **1**, quindi la
  voce `[10] Exit` era **irraggiungibile** da tastiera;
- le frecce ↑ ↓ non funzionavano quando il terminale è in *application cursor
  mode* (`ESC O A` / `ESC O B`), caso normale nel Terminale di macOS, in `tmux`
  e in `screen`;
- premere **ESC** bloccava il programma per sempre (attesa di due byte che non
  sarebbero mai arrivati);
- **Ctrl+C** non usciva più dal menu (la modalità *raw* disattiva i segnali);
- ogni tasto ristampava una copia completa del menu invece di aggiornarlo,
  dando l'impressione che la selezione non funzionasse;
- caratteri non validi venivano ignorati in silenzio, senza alcun messaggio.

## Causa

Il selettore leggeva un solo carattere e lo trasformava subito in una scelta
(`int(char) - 1`): un modello a **cifra singola**, incompatibile con opzioni a
più cifre. La lettura tastiera usava inoltre `tty.setraw` + `sys.stdin.read(2)`
per le sequenze di escape, senza timeout e senza supporto per le sequenze SS3.

## Correzione

Il selettore è stato riscritto come componente **generico e riusabile**
(`src/cli/selector.py`):

- buffer numerico multi-cifra con disambiguazione (timeout, Enter o cifra
  successiva): funziona con 10, 12, 100 o più opzioni;
- decodifica completa dei tasti: `ESC [` e `ESC O`, Home/End/PageUp/PageDown,
  Tab/Shift+Tab, Backspace, Enter del tastierino;
- ESC isolato riconosciuto tramite timeout, niente più blocchi;
- modalità **cbreak** invece di *raw*: Ctrl+C e l'output del terminale
  restano corretti;
- ridisegno del menu **in place** con sequenze ANSI;
- messaggi espliciti sull'input non valido;
- fallback riga-per-riga (multi-cifra incluso) quando stdin non è un TTY.

Le azioni associate alle voci di menu **non sono state modificate**.

## Come verificare

```bash
./OpenHackintosh.command      # macOS
./openhackintosh              # Linux / macOS
```

Poi provare: `3`, `10`, frecce + Invio, ESC, Ctrl+C, caratteri non validi.
