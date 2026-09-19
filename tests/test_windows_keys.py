"""Test del lettore tasti Windows (msvcrt) e della selezione multipiattaforma.

Anche qui niente Windows richiesto: msvcrt viene simulato con un modulo fake
iniettato in sys.modules. Il decoder (funzione pura) viene testato a parte.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cli import selector  # noqa: E402


# ---------------------------------------------------------------------------
# Decoder puro
# ---------------------------------------------------------------------------


class TestDecodeWindowsExtended:
    @pytest.mark.parametrize(
        "code,expected",
        [
            ("H", selector.KEY_UP),
            ("P", selector.KEY_DOWN),
            ("K", selector.KEY_LEFT),
            ("M", selector.KEY_RIGHT),
            ("G", selector.KEY_HOME),
            ("O", selector.KEY_END),
            ("I", selector.KEY_PGUP),
            ("Q", selector.KEY_PGDN),
            ("S", selector.KEY_BACKSPACE),
            ("R", selector.KEY_UNKNOWN),   # Insert: ignorato
            ("?", selector.KEY_UNKNOWN),
            (None, selector.KEY_UNKNOWN),
            ("", selector.KEY_UNKNOWN),
        ],
    )
    def test_mapping(self, code, expected):
        assert selector.decode_windows_extended(code) == expected


# ---------------------------------------------------------------------------
# WindowsKeyReader con msvcrt simulato
# ---------------------------------------------------------------------------


class FakeMsvcrt:
    """Simula msvcrt: coda di tasti, kbhit() e getwch()."""

    def __init__(self, keys):
        self.queue = list(keys)

    def kbhit(self):
        return bool(self.queue)

    def getwch(self):
        if not self.queue:
            raise EOFError
        return self.queue.pop(0)


@pytest.fixture
def fake_msvcrt(monkeypatch):
    state = {"module": None}

    def install(keys):
        fake = FakeMsvcrt(keys)
        module = types.ModuleType("msvcrt")
        module.kbhit = fake.kbhit
        module.getwch = fake.getwch
        monkeypatch.setitem(sys.modules, "msvcrt", module)
        state["module"] = module
        return fake

    return install


class TestWindowsKeyReader:
    def _reader(self, fake_msvcrt, keys):
        fake_msvcrt(keys)
        return selector.WindowsKeyReader()

    def test_frecce(self, fake_msvcrt):
        reader = self._reader(fake_msvcrt, ["\xe0", "H", "\xe0", "P"])
        assert reader.read_key() == selector.KEY_UP
        assert reader.read_key() == selector.KEY_DOWN

    def test_doppio_prefisso(self, fake_msvcrt):
        # alcune console mandano \xe0 poi \x00 prima del codice vero
        reader = self._reader(fake_msvcrt, ["\xe0", "\x00", "K"])
        assert reader.read_key() == selector.KEY_LEFT

    def test_home_end_pgup_pgdn_canc(self, fake_msvcrt):
        reader = self._reader(
            fake_msvcrt,
            ["\xe0", "G", "\xe0", "O", "\xe0", "I", "\xe0", "Q", "\xe0", "S"],
        )
        assert reader.read_key() == selector.KEY_HOME
        assert reader.read_key() == selector.KEY_END
        assert reader.read_key() == selector.KEY_PGUP
        assert reader.read_key() == selector.KEY_PGDN
        assert reader.read_key() == selector.KEY_BACKSPACE

    def test_tasti_semplici(self, fake_msvcrt):
        reader = self._reader(fake_msvcrt, ["1", "\r", "\x1b", "q", "\x03", "\x08"])
        assert reader.read_key() == "1"
        assert reader.read_key() == selector.KEY_ENTER
        assert reader.read_key() == selector.KEY_ESC
        assert reader.read_key() == "q"
        assert reader.read_key() == selector.KEY_CTRL_C
        assert reader.read_key() == selector.KEY_BACKSPACE

    def test_timeout_nessun_tasto(self, fake_msvcrt):
        reader = self._reader(fake_msvcrt, [])
        assert reader.read_key(timeout=0.05) is None

    def test_timeout_poi_tasto(self, fake_msvcrt):
        reader = self._reader(fake_msvcrt, ["a"])
        assert reader.read_key(timeout=0.5) == "a"

    def test_context_manager(self, fake_msvcrt):
        reader = self._reader(fake_msvcrt, ["\xe0", "H"])
        with reader:
            assert reader.read_key() == selector.KEY_UP
        reader.restore()  # no-op, ma non deve esplodere

    def test_stesso_contratto_del_loop(self, fake_msvcrt):
        """Il selettore (macchina a stati) non deve accorgersi della piattaforma."""
        fake_msvcrt(["\xe0", "P", "\r"])
        state = selector.SelectorState(count=10)
        reader = selector.WindowsKeyReader()
        r1 = state.feed(reader.read_key())     # freccia GIU': evidenzia voce 2
        assert r1.status == selector.PENDING
        assert state.index == 1
        r2 = state.feed(reader.read_key())     # Enter: conferma la voce 2
        assert r2.status == selector.SELECTED
        assert r2.index == 1


# ---------------------------------------------------------------------------
# make_key_reader: la scelta dipende dalla piattaforma
# ---------------------------------------------------------------------------


class TestMakeKeyReader:
    def test_reader_custom_vince(self):
        fake = object()
        assert selector.make_key_reader(fake) is fake

    def test_posix_di_default(self, monkeypatch):
        # KeyReader() reale richiederebbe uno stdin POSIX: qui testiamo solo
        # la SCELTA della classe, quindi lo sostituiamo con un fake.
        class FakePosixReader:
            pass

        monkeypatch.setattr(selector.os, "name", "posix")
        monkeypatch.setattr(selector, "KeyReader", FakePosixReader)
        reader = selector.make_key_reader()
        assert isinstance(reader, FakePosixReader)

    def test_windows_quando_nt(self, monkeypatch):
        monkeypatch.setattr(selector.os, "name", "nt")
        reader = selector.make_key_reader()
        assert isinstance(reader, selector.WindowsKeyReader)
