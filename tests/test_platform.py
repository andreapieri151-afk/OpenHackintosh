"""Test dei moduli di piattaforma (utils.platforms, utils.console) e dei fix
di portabilita' in efi_builder (slug profilo per i nomi dei file)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from efi_builder import builder  # noqa: E402
from utils import console, platforms  # noqa: E402


class TestCurrentPlatform:
    def test_linux(self, monkeypatch):
        monkeypatch.setattr(platforms.platform, "system", lambda: "Linux")
        monkeypatch.setattr(platforms.os, "name", "posix")
        assert platforms.current_platform() == "linux"
        assert platforms.is_linux()
        assert not platforms.is_windows()

    def test_windows(self, monkeypatch):
        monkeypatch.setattr(platforms.platform, "system", lambda: "Windows")
        monkeypatch.setattr(platforms.os, "name", "nt")
        assert platforms.current_platform() == "windows"
        assert platforms.is_windows()

    def test_macos(self, monkeypatch):
        monkeypatch.setattr(platforms.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(platforms.os, "name", "posix")
        assert platforms.current_platform() == "macos"
        assert platforms.is_macos()


class TestCacheDir:
    def test_override_env_vince(self, monkeypatch, tmp_path):
        monkeypatch.setenv("OPENHACKINTOSH_CACHE", str(tmp_path / "custom"))
        assert platforms.default_cache_dir() == tmp_path / "custom"

    def test_windows_usa_localappdata(self, monkeypatch, tmp_path):
        monkeypatch.delenv("OPENHACKINTOSH_CACHE", raising=False)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        monkeypatch.setattr(platforms, "is_windows", lambda: True)
        assert platforms.default_cache_dir() == tmp_path / "OpenHackintosh" / "Cache"

    def test_linux_usa_home_cache(self, monkeypatch, tmp_path):
        monkeypatch.delenv("OPENHACKINTOSH_CACHE", raising=False)
        monkeypatch.setattr(platforms, "is_windows", lambda: False)
        monkeypatch.setattr(platforms.Path, "home", classmethod(lambda cls: tmp_path))
        assert platforms.default_cache_dir() == tmp_path / ".cache" / "openhackintosh"


class TestProfileSlug:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("fujitsu_q556_2", "FUJITSU_Q556_2"),
            ("fujitsu_q957", "FUJITSU_Q957"),
            ("Q556/2", "Q556_2"),
            ("Q556\\2", "Q556_2"),
            ("lenovo m720q", "LENOVO_M720Q"),
            ("", "UNKNOWN"),
        ],
    )
    def test_slug(self, name, expected):
        assert builder._profile_slug(name) == expected


class _FakeStream:
    def __init__(self, tty):
        self._tty = tty
        self.reconfigured = None

    def isatty(self):
        return self._tty

    def reconfigure(self, **kw):
        self.reconfigured = kw


class TestConsole:
    def test_setup_console_idempotente(self, monkeypatch):
        out = _FakeStream(True)
        monkeypatch.setattr(console.sys, "stdout", out)
        monkeypatch.setattr(console.sys, "stderr", _FakeStream(True))
        monkeypatch.setattr(console, "_ready", False)
        console.setup_console()
        console.setup_console()  # seconda chiamata: no-op
        assert out.reconfigured == {"encoding": "utf-8", "errors": "replace"}

    def test_ansi_no_color(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setattr(console, "is_windows", lambda: False)
        assert not console.ansi_supported(_FakeStream(True))

    def test_ansi_richiede_tty(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setattr(console, "is_windows", lambda: False)
        monkeypatch.delenv("TERM", raising=False)
        assert not console.ansi_supported(_FakeStream(False))
        assert console.ansi_supported(_FakeStream(True))

    def test_ansi_windows_richiede_vt(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setattr(console, "is_windows", lambda: True)
        monkeypatch.setattr(console, "enable_windows_vt_mode", lambda: False)
        assert not console.ansi_supported(_FakeStream(True))
        monkeypatch.setattr(console, "enable_windows_vt_mode", lambda: True)
        assert console.ansi_supported(_FakeStream(True))
