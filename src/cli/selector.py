"""
Componente generico di selezione da terminale (menu interattivo).

Questo modulo contiene TUTTA la logica del selettore usato dalla CLI:

* lettura tastiera a basso livello (raw byte da file descriptor, non
  ``sys.stdin.read`` bufferizzato);
* decodifica delle sequenze di escape (frecce in modalita' "normal" ``ESC [ A``
  e in modalita' "application" ``ESC O A``, Home/End/PageUp/PageDown, Shift+Tab);
* macchina a stati pura (:class:`SelectorState`) che traduce i tasti in azioni
  ed e' completamente testabile senza un TTY;
* supporto ai numeri multi-cifra (``10``, ``11``, ... senza limiti) con
  disambiguazione a timeout o con Enter;
* fallback line-based per stdin non interattivo (pipe, CI, ``echo 2 | ...``).

Il componente e' generico: non conosce le singole voci di menu ne' le azioni
associate. Funziona con un numero qualsiasi di opzioni.
"""

from __future__ import annotations

import codecs
import os
import select as _select
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

# --------------------------------------------------------------------------
# Token dei tasti
# --------------------------------------------------------------------------

KEY_UP = "UP"
KEY_DOWN = "DOWN"
KEY_LEFT = "LEFT"
KEY_RIGHT = "RIGHT"
KEY_HOME = "HOME"
KEY_END = "END"
KEY_PGUP = "PGUP"
KEY_PGDN = "PGDN"
KEY_ENTER = "ENTER"
KEY_ESC = "ESC"
KEY_BACKSPACE = "BACKSPACE"
KEY_TAB = "TAB"
KEY_CTRL_C = "CTRL_C"
KEY_CTRL_D = "CTRL_D"
KEY_UNKNOWN = "UNKNOWN"

ESC = "\x1b"

#: Sequenze di escape complete -> token.
#: Sono incluse sia le sequenze CSI (``ESC [``) sia quelle SS3 (``ESC O``),
#: perche' il Terminale di macOS (e ``screen``/``tmux``) inviano ``ESC O A``
#: quando il "keypad application mode" e' attivo.
ESCAPE_SEQUENCES: Dict[str, str] = {
    "\x1b[A": KEY_UP,
    "\x1b[B": KEY_DOWN,
    "\x1b[C": KEY_RIGHT,
    "\x1b[D": KEY_LEFT,
    "\x1bOA": KEY_UP,
    "\x1bOB": KEY_DOWN,
    "\x1bOC": KEY_RIGHT,
    "\x1bOD": KEY_LEFT,
    "\x1b[H": KEY_HOME,
    "\x1b[F": KEY_END,
    "\x1bOH": KEY_HOME,
    "\x1bOF": KEY_END,
    "\x1b[1~": KEY_HOME,
    "\x1b[7~": KEY_HOME,
    "\x1b[4~": KEY_END,
    "\x1b[8~": KEY_END,
    "\x1b[5~": KEY_PGUP,
    "\x1b[6~": KEY_PGDN,
    "\x1b[Z": KEY_UP,       # Shift+Tab
    "\x1bOM": KEY_ENTER,    # Enter del tastierino numerico
    "\x1b[3~": KEY_BACKSPACE,  # Canc
}

#: Caratteri singoli -> token.
CONTROL_KEYS: Dict[str, str] = {
    "\r": KEY_ENTER,
    "\n": KEY_ENTER,
    "\x7f": KEY_BACKSPACE,
    "\x08": KEY_BACKSPACE,
    "\t": KEY_TAB,
    "\x03": KEY_CTRL_C,
    "\x04": KEY_CTRL_D,
    ESC: KEY_ESC,
}

#: Parole che annullano la selezione nel fallback line-based.
CANCEL_WORDS = {"q", "quit", "exit", "esc", "cancel", "annulla", "x"}


def decode_key(data: str) -> str:
    """Traduce una sequenza grezza di tastiera in un token normalizzato.

    Funzione pura: utile per i test e per riusare il decoder altrove.
    """
    if not data:
        return KEY_UNKNOWN
    if data in ESCAPE_SEQUENCES:
        return ESCAPE_SEQUENCES[data]
    if len(data) == 1:
        if data in CONTROL_KEYS:
            return CONTROL_KEYS[data]
        if data.isprintable():
            return data
        return KEY_UNKNOWN
    if data.startswith(ESC):
        # Sequenza di escape sconosciuta: NON deve essere interpretata come
        # testo, altrimenti "ESC O B" verrebbe letto come la lettera "B".
        return KEY_UNKNOWN
    return KEY_UNKNOWN


# --------------------------------------------------------------------------
# Lettura tastiera
# --------------------------------------------------------------------------


class KeyReader:
    """Lettore di tasti da un TTY, in modalita' *cbreak*.

    Perche' cbreak e non raw:

    * ``tty.setraw`` disabilita ISIG, quindi Ctrl+C non genera piu' SIGINT e il
      menu diventa impossibile da interrompere;
    * ``tty.setraw`` disabilita anche OPOST, quindi ogni ``\\n`` stampato non
      viene tradotto in CRLF e il menu appare "a scala".

    In cbreak i tasti arrivano immediatamente (niente line buffering) ma il
    terminale resta utilizzabile.
    """

    #: Attesa massima per completare una sequenza di escape.
    escape_timeout = 0.08

    def __init__(self, fd: Optional[int] = None) -> None:
        self.fd = fd if fd is not None else sys.stdin.fileno()
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._pending: List[str] = []
        self._saved = None
        self._raw_log: List[str] = []

    # -- context manager ---------------------------------------------------
    def __enter__(self) -> "KeyReader":
        try:
            import termios
            import tty

            self._saved = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        except Exception:  # pragma: no cover - dipende dalla piattaforma
            self._saved = None
        return self

    def __exit__(self, *exc) -> None:
        self.restore()

    def restore(self) -> None:
        if self._saved is None:
            return
        try:
            import termios

            termios.tcsetattr(self.fd, termios.TCSADRAIN, self._saved)
        except Exception:  # pragma: no cover
            pass
        finally:
            self._saved = None

    # -- lettura -----------------------------------------------------------
    def _wait(self, timeout: Optional[float]) -> bool:
        try:
            ready, _, _ = _select.select([self.fd], [], [], timeout)
        except Exception:  # pragma: no cover - fd non selezionabile
            return True
        return bool(ready)

    def _read_char(self, timeout: Optional[float]) -> Optional[str]:
        """Legge un singolo carattere (gestendo UTF-8 multi-byte)."""
        if self._pending:
            return self._pending.pop(0)
        while True:
            if timeout is not None and not self._wait(timeout):
                return None
            try:
                chunk = os.read(self.fd, 1024)
            except (OSError, InterruptedError):
                return None
            if not chunk:
                return None
            text = self._decoder.decode(chunk)
            if not text:
                # byte UTF-8 incompleto: continua a leggere
                timeout = self.escape_timeout if timeout is None else timeout
                continue
            self._pending.extend(list(text))
            return self._pending.pop(0)

    def read_key(self, timeout: Optional[float] = None) -> Optional[str]:
        """Restituisce il prossimo token, oppure ``None`` allo scadere del timeout."""
        ch = self._read_char(timeout)
        if ch is None:
            return None
        if ch != ESC:
            return decode_key(ch)

        # ESC: puo' essere il tasto ESC oppure l'inizio di una sequenza.
        nxt = self._read_char(self.escape_timeout)
        if nxt is None:
            return KEY_ESC
        if nxt not in ("[", "O"):
            # ESC + carattere (Alt+tasto): riprogramma il carattere e segnala ESC.
            self._pending.insert(0, nxt)
            return KEY_ESC

        seq = ESC + nxt
        while True:
            c = self._read_char(self.escape_timeout)
            if c is None:
                break
            seq += c
            # Il byte finale di una sequenza CSI/SS3 sta in 0x40..0x7E.
            if "\x40" <= c <= "\x7e":
                break
            if len(seq) > 12:  # pragma: no cover - sequenza malformata
                break
        return decode_key(seq)


# --------------------------------------------------------------------------
# Macchina a stati del selettore (pura, testabile senza TTY)
# --------------------------------------------------------------------------

PENDING = "pending"
SELECTED = "selected"
CANCELLED = "cancelled"
INVALID = "invalid"
INTERRUPTED = "interrupted"


@dataclass
class KeyResult:
    """Esito dell'elaborazione di un tasto."""

    status: str = PENDING
    index: Optional[int] = None
    message: str = ""
    #: True se il selettore sta aspettando altre cifre (numero ambiguo).
    awaiting_digits: bool = False

    @property
    def done(self) -> bool:
        return self.status in (SELECTED, CANCELLED, INTERRUPTED)


@dataclass
class SelectorState:
    """Stato del menu: indice evidenziato + buffer delle cifre digitate.

    Regole di selezione numerica (generiche, valide per N opzioni qualsiasi):

    * le opzioni sono numerate ``1..N``;
    * ogni cifra viene accodata al buffer;
    * se il numero nel buffer e' l'UNICO candidato possibile -> selezione
      immediata (es. ``3`` con 10 opzioni, oppure ``9`` con 10 opzioni);
    * se il numero e' valido ma e' anche prefisso di altri numeri validi
      (es. ``1`` con 10+ opzioni) -> si attende un'altra cifra, Enter o il
      timeout (:meth:`flush`);
    * se il buffer non corrisponde a nessuna opzione si riparte dall'ultima
      cifra digitata (es. ``9`` poi ``5`` con 10 opzioni seleziona la 5).
    """

    count: int
    index: int = 0
    digits: str = field(default="")
    wrap: bool = True

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError("Il selettore richiede almeno una opzione")
        self.index = max(0, min(self.index, self.count - 1))

    # -- helper ------------------------------------------------------------
    @property
    def max_digits(self) -> int:
        return len(str(self.count))

    def candidates(self, prefix: str) -> List[int]:
        """Numeri di opzione (1-based) che iniziano con ``prefix``."""
        if not prefix:
            return list(range(1, self.count + 1))
        return [n for n in range(1, self.count + 1) if str(n).startswith(prefix)]

    def move(self, delta: int) -> None:
        self.digits = ""
        if self.wrap:
            self.index = (self.index + delta) % self.count
        else:
            self.index = max(0, min(self.index + delta, self.count - 1))

    def _highlight(self, number: int) -> None:
        if 1 <= number <= self.count:
            self.index = number - 1

    # -- input -------------------------------------------------------------
    def press_digit(self, digit: str) -> KeyResult:
        candidate_buffer = self.digits + digit
        if not self.candidates(candidate_buffer):
            # Il buffer accumulato non porta a nulla: riparti dalla cifra nuova.
            candidate_buffer = digit
            if not self.candidates(candidate_buffer):
                self.digits = ""
                return KeyResult(
                    INVALID,
                    message=f"Opzione non valida. Scegli un numero tra 1 e {self.count}.",
                )

        self.digits = candidate_buffer
        value = int(candidate_buffer)
        options = self.candidates(candidate_buffer)
        self._highlight(value)

        if options == [value]:
            # Nessun numero piu' lungo inizia con questo prefisso: conferma subito.
            self.digits = ""
            return KeyResult(SELECTED, index=value - 1)

        # Numero valido ma prefisso di altri (es. "1" -> 1, 10, 11...).
        return KeyResult(PENDING, awaiting_digits=True, message=candidate_buffer)

    def press_enter(self) -> KeyResult:
        if self.digits:
            value = int(self.digits)
            self.digits = ""
            if 1 <= value <= self.count:
                self._highlight(value)
                return KeyResult(SELECTED, index=value - 1)
            return KeyResult(
                INVALID,
                message=f"Opzione non valida. Scegli un numero tra 1 e {self.count}.",
            )
        return KeyResult(SELECTED, index=self.index)

    def press_backspace(self) -> KeyResult:
        if self.digits:
            self.digits = self.digits[:-1]
            if self.digits:
                self._highlight(int(self.digits))
            return KeyResult(PENDING, awaiting_digits=bool(self.digits), message=self.digits)
        return KeyResult(PENDING)

    def flush(self) -> KeyResult:
        """Conferma il numero in attesa (chiamata allo scadere del timeout)."""
        if not self.digits:
            return KeyResult(PENDING)
        value = int(self.digits)
        self.digits = ""
        if 1 <= value <= self.count:
            self._highlight(value)
            return KeyResult(SELECTED, index=value - 1)
        return KeyResult(
            INVALID,
            message=f"Opzione non valida. Scegli un numero tra 1 e {self.count}.",
        )

    def feed(self, key: Optional[str]) -> KeyResult:
        """Elabora un token restituito da :meth:`KeyReader.read_key`."""
        if key is None:
            return self.flush()
        if key == KEY_ENTER:
            return self.press_enter()
        if key in (KEY_UP,):
            self.move(-1)
            return KeyResult(PENDING)
        if key in (KEY_DOWN, KEY_TAB):
            self.move(1)
            return KeyResult(PENDING)
        if key == KEY_HOME or key == KEY_PGUP:
            self.digits = ""
            self.index = 0
            return KeyResult(PENDING)
        if key == KEY_END or key == KEY_PGDN:
            self.digits = ""
            self.index = self.count - 1
            return KeyResult(PENDING)
        if key == KEY_BACKSPACE:
            return self.press_backspace()
        if key == KEY_ESC:
            self.digits = ""
            return KeyResult(CANCELLED, message="Selezione annullata.")
        if key == KEY_CTRL_C:
            return KeyResult(INTERRUPTED, message="Interrotto.")
        if key == KEY_CTRL_D:
            return KeyResult(CANCELLED, message="Selezione annullata.")
        if len(key) == 1 and key.isdigit():
            return self.press_digit(key)
        if len(key) == 1 and key.lower() in ("q",):
            self.digits = ""
            return KeyResult(CANCELLED, message="Selezione annullata.")
        if key in (KEY_LEFT, KEY_RIGHT, KEY_UNKNOWN) or key == " ":
            return KeyResult(PENDING)
        return KeyResult(
            INVALID,
            message=f"Input non valido: '{key}'. Usa le frecce oppure un numero tra 1 e {self.count}.",
        )


# --------------------------------------------------------------------------
# Fallback line-based (stdin non interattivo)
# --------------------------------------------------------------------------


def parse_line_selection(raw: str, items: Sequence[dict]) -> KeyResult:
    """Interpreta una riga di testo come selezione di menu.

    Accetta: numeri (anche multi-cifra), ``q``/``quit``/``exit``, oppure il
    nome (o un prefisso non ambiguo) dell'etichetta.
    """
    count = len(items)
    text = (raw or "").strip()
    if not text:
        return KeyResult(PENDING, message="")

    lowered = text.lower()

    # Accetta anche forme come "[10]" o "10." o "#10".
    cleaned = lowered.strip("[]().#> \t")
    if cleaned.isdigit():
        value = int(cleaned)
        if 1 <= value <= count:
            return KeyResult(SELECTED, index=value - 1)
        return KeyResult(
            INVALID,
            message=f"Opzione non valida: '{text}'. Scegli un numero tra 1 e {count}.",
        )

    # Match esatto per etichetta / action: ha la precedenza sulle parole di
    # annullamento (un menu con la voce "Exit" deve poter essere selezionato).
    exact = [
        i
        for i, item in enumerate(items)
        if str(item.get("label", "")).lower() == cleaned
        or str(item.get("action", "")).lower() == cleaned
    ]
    if len(exact) == 1:
        return KeyResult(SELECTED, index=exact[0])

    if lowered in CANCEL_WORDS or cleaned in CANCEL_WORDS:
        return KeyResult(CANCELLED, message="Selezione annullata.")

    partial = [
        i
        for i, item in enumerate(items)
        if str(item.get("label", "")).lower().startswith(cleaned)
        or str(item.get("action", "")).lower().startswith(cleaned)
    ]
    if len(partial) == 1:
        return KeyResult(SELECTED, index=partial[0])

    return KeyResult(
        INVALID,
        message=f"Opzione non valida: '{text}'. Scegli un numero tra 1 e {count}.",
    )


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def render_menu(
    items: Sequence[dict],
    index: int,
    digits: str = "",
    use_ansi: bool = True,
    marker: str = "\u276f",
) -> List[str]:
    """Costruisce le righe del menu (senza stamparle)."""
    count = len(items)
    width = max((len(str(i.get("label", ""))) for i in items), default=0)
    num_width = len(str(count))
    lines: List[str] = []
    for i, item in enumerate(items):
        label = str(item.get("label", ""))
        active = i == index
        cursor = marker if active else " "
        number = f"[{str(i + 1).rjust(num_width)}]"
        line = f" {cursor} {label.ljust(width)}   {number}"
        if active and use_ansi:
            line = f"\033[1;36m{line}\033[0m"
        lines.append(line)
    if digits:
        lines.append(f"   Numero: {digits}_")
    return lines


def _clear_lines(count: int, stream) -> None:
    """Riporta il cursore all'inizio del blocco menu, cancellando le righe."""
    for _ in range(count):
        stream.write("\033[1A\033[2K")
    stream.write("\r")


# --------------------------------------------------------------------------
# Loop principale del selettore
# --------------------------------------------------------------------------

#: Tempo di attesa per capire se dopo "1" arrivera' uno "0" (opzione 10).
DIGIT_TIMEOUT = 0.8


def is_interactive(stdin=None, stdout=None) -> bool:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    try:
        if not (stdin.isatty() and stdout.isatty()):
            return False
        stdin.fileno()
    except Exception:
        return False
    if os.environ.get("OPENHACKINTOSH_NO_TTY"):
        return False
    return True


def supports_ansi(stdout=None) -> bool:
    stdout = stdout or sys.stdout
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM", "") in ("dumb", ""):
        return False
    try:
        return bool(stdout.isatty())
    except Exception:
        return False


def select_interactive(
    items: Sequence[dict],
    title: str,
    prompt: str,
    index: int = 0,
    stdout=None,
    reader: Optional[KeyReader] = None,
    digit_timeout: float = DIGIT_TIMEOUT,
) -> Optional[int]:
    """Menu interattivo su TTY. Ritorna l'indice scelto o ``None`` se annullato."""
    stdout = stdout or sys.stdout
    state = SelectorState(count=len(items), index=index)
    ansi = supports_ansi(stdout)
    drawn = 0
    message = ""

    owns_reader = reader is None
    reader = reader or KeyReader()
    if owns_reader:
        reader.__enter__()

    if title:
        stdout.write(title + "\n")
    try:
        while True:
            lines = render_menu(items, state.index, state.digits, use_ansi=ansi)
            if message:
                lines.append(message)
            lines.append(prompt)

            if drawn and ansi:
                _clear_lines(drawn, stdout)
            stdout.write("\n".join(lines) + "\n")
            stdout.flush()
            drawn = len(lines)
            message = ""

            timeout = digit_timeout if state.digits else None
            key = reader.read_key(timeout=timeout)
            result = state.feed(key)

            if result.status == SELECTED:
                return result.index
            if result.status == CANCELLED:
                return None
            if result.status == INTERRUPTED:
                raise KeyboardInterrupt
            if result.status == INVALID:
                message = result.message
    finally:
        if owns_reader:
            reader.restore()
        stdout.write("\n")
        stdout.flush()


def select_line_based(
    items: Sequence[dict],
    title: str,
    prompt: str,
    stdin=None,
    stdout=None,
    max_attempts: int = 50,
) -> Optional[int]:
    """Fallback per stdin non interattivo: menu numerato + ``input()``."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    count = len(items)

    if title:
        stdout.write(title + "\n")
    for line in render_menu(items, index=-1, use_ansi=False, marker=" "):
        stdout.write(line + "\n")
    stdout.write(prompt + "\n")
    stdout.flush()

    for _ in range(max_attempts):
        stdout.write("> ")
        stdout.flush()
        try:
            raw = stdin.readline()
        except (EOFError, KeyboardInterrupt):
            return None
        if raw == "":  # EOF
            return None
        result = parse_line_selection(raw, items)
        if result.status == SELECTED:
            return result.index
        if result.status == CANCELLED:
            return None
        if result.status == INVALID:
            stdout.write(result.message + "\n")
        else:
            stdout.write(f"Inserisci un numero tra 1 e {count} (oppure 'q' per uscire).\n")
        stdout.flush()
    return None


def select(
    items: Sequence[dict],
    title: str = "What would you like to do?",
    prompt: str = "Use arrows or numbers (1-N), Enter to confirm, ESC/q to cancel.",
    index: int = 0,
    stdin=None,
    stdout=None,
) -> Optional[int]:
    """Punto di ingresso generico del selettore.

    Sceglie automaticamente la modalita' interattiva (TTY) o quella
    line-based (pipe/CI). Ritorna l'indice selezionato oppure ``None``.
    """
    if not items:
        raise ValueError("Nessuna opzione da selezionare")
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout

    prompt = prompt.replace("1-N", f"1-{len(items)}")

    if is_interactive(stdin, stdout):
        try:
            return select_interactive(items, title, prompt, index=index, stdout=stdout)
        except KeyboardInterrupt:
            stdout.write("\n")
            return None
        except (OSError, ValueError):
            # TTY non utilizzabile: degrada al fallback invece di crashare.
            pass
    return select_line_based(items, title, prompt, stdin=stdin, stdout=stdout)
