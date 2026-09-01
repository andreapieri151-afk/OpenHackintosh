"""
Test del componente generico di selezione (menu interattivo della CLI).

Copre:
* decodifica tastiera (frecce normal/application mode, Enter, ESC, Backspace,
  Home/End, Ctrl+C);
* macchina a stati del selettore (numeri singoli e MULTI-CIFRA);
* validazione input non valido;
* fallback line-based per stdin non interattivo;
* end-to-end su pseudo-terminale reale (comportamento Terminale macOS);
* raggiungibilita' di TUTTE le voci del menu principale.
"""

from __future__ import annotations

import io
import os
import sys
import time

import pytest

from cli import selector as sel
from cli.interactive import run_menu
from cli.main import MENU_COMMANDS, MENU_ITEMS


def make_items(n: int):
    items = [{"label": f"Opt{i}", "action": f"a{i}"} for i in range(1, n)]
    items.append({"label": "Exit", "action": "exit"})
    return items


# ---------------------------------------------------------------------------
# 1. Decodifica tastiera
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("\x1b[A", sel.KEY_UP),
        ("\x1b[B", sel.KEY_DOWN),
        ("\x1b[C", sel.KEY_RIGHT),
        ("\x1b[D", sel.KEY_LEFT),
        # application cursor mode: usato dal Terminale macOS / tmux / screen
        ("\x1bOA", sel.KEY_UP),
        ("\x1bOB", sel.KEY_DOWN),
        ("\x1bOC", sel.KEY_RIGHT),
        ("\x1bOD", sel.KEY_LEFT),
        ("\x1b[H", sel.KEY_HOME),
        ("\x1b[F", sel.KEY_END),
        ("\x1b[1~", sel.KEY_HOME),
        ("\x1b[4~", sel.KEY_END),
        ("\x1b[5~", sel.KEY_PGUP),
        ("\x1b[6~", sel.KEY_PGDN),
        ("\x1bOM", sel.KEY_ENTER),
        ("\r", sel.KEY_ENTER),
        ("\n", sel.KEY_ENTER),
        ("\x1b", sel.KEY_ESC),
        ("\x7f", sel.KEY_BACKSPACE),
        ("\x08", sel.KEY_BACKSPACE),
        ("\t", sel.KEY_TAB),
        ("\x03", sel.KEY_CTRL_C),
        ("\x04", sel.KEY_CTRL_D),
        ("1", "1"),
        ("0", "0"),
        ("q", "q"),
    ],
)
def test_decode_key(raw, expected):
    assert sel.decode_key(raw) == expected


def test_unknown_escape_is_not_read_as_text():
    """Regressione: 'ESC O B' non deve mai diventare la lettera 'B'."""
    assert sel.decode_key("\x1b[200~") == sel.KEY_UNKNOWN
    assert sel.decode_key("\x1bX") == sel.KEY_UNKNOWN


# ---------------------------------------------------------------------------
# 2. Macchina a stati: numeri singoli
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("digit", list("23456789"))
def test_single_digit_selects_immediately_with_10_items(digit):
    """Con 10 opzioni, 2..9 non sono prefissi di nulla: selezione immediata."""
    state = sel.SelectorState(count=10)
    res = state.press_digit(digit)
    assert res.status == sel.SELECTED
    assert res.index == int(digit) - 1


def test_digit_one_is_ambiguous_with_ten_items():
    state = sel.SelectorState(count=10)
    res = state.press_digit("1")
    assert res.status == sel.PENDING
    assert res.awaiting_digits is True
    # l'elemento evidenziato segue comunque il numero digitato
    assert state.index == 0


def test_digit_one_is_immediate_with_nine_items():
    state = sel.SelectorState(count=9)
    res = state.press_digit("1")
    assert res.status == sel.SELECTED
    assert res.index == 0


# ---------------------------------------------------------------------------
# 3. Macchina a stati: numeri MULTI-CIFRA (il bug originale)
# ---------------------------------------------------------------------------


def test_option_ten_is_reachable():
    """BUG 2.0.1 Beta 1: digitare '1','0' selezionava l'opzione 1."""
    state = sel.SelectorState(count=10)
    assert state.press_digit("1").status == sel.PENDING
    res = state.press_digit("0")
    assert res.status == sel.SELECTED
    assert res.index == 9


def test_option_ten_with_enter():
    state = sel.SelectorState(count=10)
    state.press_digit("1")
    state.press_digit("0")  # gia' selezionato, ma verifichiamo anche via Enter
    state = sel.SelectorState(count=12)
    state.press_digit("1")
    res = state.press_enter()
    assert res.status == sel.SELECTED
    assert res.index == 0


def test_pending_digit_committed_on_timeout():
    """'1' + timeout (flush) -> opzione 1."""
    state = sel.SelectorState(count=10)
    state.press_digit("1")
    res = state.flush()
    assert res.status == sel.SELECTED
    assert res.index == 0


@pytest.mark.parametrize("number", [1, 2, 9, 10, 11, 12])
def test_multi_digit_up_to_twelve(number):
    state = sel.SelectorState(count=12)
    result = None
    for ch in str(number):
        result = state.press_digit(ch)
    if result.status == sel.PENDING:
        result = state.flush()
    assert result.status == sel.SELECTED
    assert result.index == number - 1


@pytest.mark.parametrize("number", [1, 7, 10, 42, 99, 100, 123])
def test_multi_digit_three_digits(number):
    """Il selettore e' generico: funziona anche con 123 opzioni."""
    state = sel.SelectorState(count=123)
    result = None
    for ch in str(number):
        result = state.press_digit(ch)
    if result.status == sel.PENDING:
        result = state.flush()
    assert result.status == sel.SELECTED
    assert result.index == number - 1


def test_backspace_edits_the_number():
    state = sel.SelectorState(count=20)
    state.press_digit("1")
    state.press_backspace()
    assert state.digits == ""
    res = state.press_digit("3")
    assert res.status == sel.SELECTED
    assert res.index == 2


def test_buffer_restarts_when_no_candidate():
    """'9' poi '5' con 10 opzioni: '95' impossibile -> vale l'ultima cifra."""
    state = sel.SelectorState(count=20)
    state.press_digit("1")  # ambiguo (1, 10..19)
    res = state.press_digit("9")  # 19 valido
    assert res.status == sel.SELECTED and res.index == 18

    state = sel.SelectorState(count=20)
    state.press_digit("2")  # ambiguo (2, 20)
    res = state.press_digit("5")  # "25" impossibile -> riparte da "5"
    assert res.status == sel.SELECTED and res.index == 4


# ---------------------------------------------------------------------------
# 4. Frecce, Enter, Home/End, ESC, input non valido
# ---------------------------------------------------------------------------


def test_arrows_move_and_wrap():
    state = sel.SelectorState(count=10)
    state.feed(sel.KEY_DOWN)
    state.feed(sel.KEY_DOWN)
    assert state.index == 2
    state.feed(sel.KEY_UP)
    assert state.index == 1
    state.index = 0
    state.feed(sel.KEY_UP)
    assert state.index == 9  # wrap in alto
    state.feed(sel.KEY_DOWN)
    assert state.index == 0  # wrap in basso


def test_enter_selects_highlighted_item():
    state = sel.SelectorState(count=10)
    state.feed(sel.KEY_DOWN)
    res = state.feed(sel.KEY_ENTER)
    assert res.status == sel.SELECTED and res.index == 1


def test_home_and_end():
    state = sel.SelectorState(count=10)
    state.feed(sel.KEY_END)
    assert state.index == 9
    state.feed(sel.KEY_HOME)
    assert state.index == 0


def test_escape_cancels():
    state = sel.SelectorState(count=10)
    res = state.feed(sel.KEY_ESC)
    assert res.status == sel.CANCELLED


def test_ctrl_c_interrupts():
    state = sel.SelectorState(count=10)
    assert state.feed(sel.KEY_CTRL_C).status == sel.INTERRUPTED


def test_q_cancels():
    state = sel.SelectorState(count=10)
    assert state.feed("q").status == sel.CANCELLED


def test_invalid_characters_are_reported_not_swallowed():
    state = sel.SelectorState(count=10)
    res = state.feed("z")
    assert res.status == sel.INVALID
    assert "1 e 10" in res.message
    # lo stato resta usabile
    assert state.feed("4").status == sel.SELECTED


def test_zero_is_invalid():
    state = sel.SelectorState(count=10)
    res = state.press_digit("0")
    assert res.status == sel.INVALID
    assert state.digits == ""


def test_arrow_clears_pending_digits():
    state = sel.SelectorState(count=10)
    state.press_digit("1")
    state.feed(sel.KEY_DOWN)
    assert state.digits == ""


def test_unknown_escape_does_nothing():
    state = sel.SelectorState(count=10)
    res = state.feed(sel.KEY_UNKNOWN)
    assert res.status == sel.PENDING


def test_state_requires_items():
    with pytest.raises(ValueError):
        sel.SelectorState(count=0)


# ---------------------------------------------------------------------------
# 5. Fallback line-based (non-TTY)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1", 0),
        ("2\n", 1),
        (" 10 \n", 9),
        ("[10]", 9),
        ("10.", 9),
        ("exit", 9),
        ("Generate EFI", 1),
        ("doctor", 7),
    ],
)
def test_parse_line_selection_valid(raw, expected):
    res = sel.parse_line_selection(raw, MENU_ITEMS)
    assert res.status == sel.SELECTED
    assert res.index == expected


@pytest.mark.parametrize("raw", ["0", "11", "999", "abc", "-1"])
def test_parse_line_selection_invalid(raw):
    res = sel.parse_line_selection(raw, MENU_ITEMS)
    assert res.status == sel.INVALID


@pytest.mark.parametrize("raw", ["q", "quit", "QUIT", "cancel", "annulla"])
def test_parse_line_selection_cancel(raw):
    assert sel.parse_line_selection(raw, MENU_ITEMS).status == sel.CANCELLED


def test_select_line_based_multi_digit():
    out = io.StringIO()
    idx = sel.select_line_based(MENU_ITEMS, "T", "P", stdin=io.StringIO("10\n"), stdout=out)
    assert idx == 9


def test_select_line_based_retries_after_invalid():
    out = io.StringIO()
    idx = sel.select_line_based(
        MENU_ITEMS, "T", "P", stdin=io.StringIO("abc\n0\n99\n\n3\n"), stdout=out
    )
    assert idx == 2
    assert "Opzione non valida" in out.getvalue()


def test_select_line_based_eof_returns_none():
    out = io.StringIO()
    assert sel.select_line_based(MENU_ITEMS, "T", "P", stdin=io.StringIO(""), stdout=out) is None


def test_select_line_based_does_not_loop_forever():
    """Uno stdin che restituisce sempre spazzatura non deve bloccare la CLI."""
    class Garbage:
        def readline(self):
            return "???\n"

    out = io.StringIO()
    assert sel.select_line_based(MENU_ITEMS, "T", "P", stdin=Garbage(), stdout=out,
                                 max_attempts=5) is None


def test_select_uses_line_mode_when_not_a_tty():
    out = io.StringIO()
    idx = sel.select(MENU_ITEMS, stdin=io.StringIO("10\n"), stdout=out)
    assert idx == 9
    assert "1-10" in out.getvalue()


# ---------------------------------------------------------------------------
# 6. Rendering
# ---------------------------------------------------------------------------


def test_render_menu_numbers_all_items():
    lines = sel.render_menu(MENU_ITEMS, index=0, use_ansi=False)
    assert len(lines) == len(MENU_ITEMS)
    for i, line in enumerate(lines, start=1):
        assert f"[{str(i).rjust(2)}]" in line
    assert "[10]" in lines[-1]


def test_render_menu_shows_digit_buffer():
    lines = sel.render_menu(MENU_ITEMS, index=0, digits="1", use_ansi=False)
    assert lines[-1].strip() == "Numero: 1_"


def test_render_menu_aligns_long_labels():
    items = [{"label": "x" * 60, "action": "a"}, {"label": "b", "action": "b"}]
    lines = sel.render_menu(items, index=0, use_ansi=False)
    assert lines[0].index("[1]") == lines[1].index("[2]")


# ---------------------------------------------------------------------------
# 7. run_menu / menu principale
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("number", range(1, len(MENU_ITEMS) + 1))
def test_every_menu_entry_is_reachable_by_number(number, monkeypatch):
    """Tutte le voci [1]..[10] del menu principale sono selezionabili."""
    monkeypatch.setattr(sel, "select", lambda *a, **k: number - 1)
    monkeypatch.setattr("cli.interactive.select", lambda *a, **k: number - 1)
    chosen = run_menu([dict(i) for i in MENU_ITEMS])
    assert chosen["action"] == MENU_ITEMS[number - 1]["action"]


def test_every_menu_action_maps_to_a_command():
    for item in MENU_ITEMS:
        action = item["action"]
        if action == "exit":
            continue
        assert action in MENU_COMMANDS, f"azione '{action}' senza comando"


def test_run_menu_cancel_returns_exit_entry(monkeypatch):
    monkeypatch.setattr("cli.interactive.select", lambda *a, **k: None)
    chosen = run_menu([dict(i) for i in MENU_ITEMS])
    assert chosen["action"] == "exit"


def test_run_menu_requires_items():
    with pytest.raises(ValueError):
        run_menu([])


def test_menu_has_ten_entries_including_multi_digit():
    assert len(MENU_ITEMS) == 10
    assert MENU_ITEMS[9]["action"] == "exit"


# ---------------------------------------------------------------------------
# 8. End-to-end su pseudo-terminale reale (Terminale macOS / Linux)
# ---------------------------------------------------------------------------

pty = pytest.importorskip("pty") if os.name == "posix" else None

PTY_DRIVER = r"""
import sys
sys.path.insert(0, {src!r})
from cli.interactive import run_menu
n = int(sys.argv[1])
items = [{{"label": "Opt%d" % i, "action": "a%d" % i}} for i in range(1, n)]
items.append({{"label": "Exit", "action": "exit"}})
choice = run_menu(items)
sys.stdout.write("\r\nRESULT=" + choice["action"] + "\r\n")
sys.stdout.flush()
"""


def _run_in_pty(keys, count=10, timeout=10.0, key_delay=0.2):
    import select as _select
    import pty as _pty

    src = str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src")
    code = PTY_DRIVER.format(src=src)
    pid, fd = _pty.fork()
    if pid == 0:  # pragma: no cover - processo figlio
        os.environ["TERM"] = "xterm-256color"
        os.execv(sys.executable, [sys.executable, "-c", code, str(count)])

    buf = b""
    try:
        time.sleep(0.8)
        for key in keys:
            if isinstance(key, float):
                time.sleep(key)
                continue
            os.write(fd, key)
            time.sleep(key_delay)
            while _select.select([fd], [], [], 0.02)[0]:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                buf += chunk
        deadline = time.time() + timeout
        while time.time() < deadline and b"RESULT=" not in buf:
            if _select.select([fd], [], [], 0.2)[0]:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                buf += chunk
    finally:
        try:
            os.kill(pid, 9)
            os.waitpid(pid, 0)
        except Exception:
            pass
        os.close(fd)

    text = buf.decode(errors="replace")
    for line in text.splitlines():
        if "RESULT=" in line:
            return line.split("RESULT=")[1].strip(), text
    return None, text


pytestmark_pty = pytest.mark.skipif(
    os.name != "posix" or not hasattr(os, "openpty"),
    reason="richiede uno pseudo-terminale POSIX",
)


@pytestmark_pty
@pytest.mark.parametrize(
    "keys,expected,count",
    [
        ([b"3"], "a3", 10),
        ([b"9"], "a9", 10),
        # BUG originale: '1','0' selezionava l'opzione 1 invece della 10
        ([b"1", b"0"], "exit", 10),
        ([b"1", b"0", b"\r"], "exit", 10),
        ([b"10\r"], "exit", 10),
        ([b"1", 1.2], "a1", 10),
        ([b"1", b"\r"], "a1", 10),
        # frecce standard
        ([b"\x1b[B", b"\x1b[B", b"\r"], "a3", 10),
        ([b"\x1b[A", b"\r"], "exit", 10),
        # frecce in application cursor mode (Terminale macOS / tmux)
        ([b"\x1bOB", b"\r"], "a2", 10),
        ([b"\x1bOA", b"\r"], "exit", 10),
        # ESC isolato: prima bloccava il programma per sempre
        ([b"\x1b"], "exit", 10),
        ([b"q"], "exit", 10),
        # input non valido -> il menu resta usabile
        ([b"z", b"4"], "a4", 10),
        ([b"0", b"5"], "a5", 10),
        # Home / End / Tab / Backspace
        ([b"\x1b[F", b"\r"], "exit", 10),
        ([b"\x1b[H", b"\r"], "a1", 10),
        ([b"\t", b"\t", b"\r"], "a3", 10),
        ([b"1", b"\x7f", b"3"], "a3", 10),
        # menu con 12 voci: 11 e 12 raggiungibili
        ([b"1", b"1"], "a11", 12),
        ([b"1", b"2"], "exit", 12),
        ([b"1", 1.2], "a1", 12),
    ],
)
def test_pty_end_to_end(keys, expected, count):
    got, text = _run_in_pty(keys, count=count)
    assert got == expected, f"atteso {expected!r}, ottenuto {got!r}\n---\n{text[-1500:]}"


@pytestmark_pty
def test_pty_menu_is_redrawn_in_place():
    """Le frecce aggiornano il menu, non ne stampano una copia dopo l'altra."""
    got, text = _run_in_pty([b"\x1b[B", b"\r"])
    assert got == "a2"
    assert "\x1b[2K" in text  # cancellazione riga = redraw in place
    assert text.count("Opt1") <= 3
