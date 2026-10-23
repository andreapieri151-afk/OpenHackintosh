"""
Test dei fix della 2.0.3 (release di correzione):

1. menu interattivo: dopo ogni comando torna al menu (loop fino a "Exit");
2. hfsplus: OpenCorePkg 1.0.8 non include piu' HfsPlus.efi — il manifest
   dichiara una lista di path candidati e il resolver usa il primo che
   esiste; se nessuno esiste l'errore elenca i driver presenti;
3. UX menu: la selezione mostra un feedback visibile ("✔ N. Label") anche
   in modalita' raw, dove i tasti non hanno eco.
"""

from __future__ import annotations

import io
import sys

import cli.main  # noqa: F401  (garantisce il caricamento del modulo)
import pytest

# NB: "cli/__init__.py" fa `from .main import main`, quindi l'attributo
# `cli.main` e' la FUNZIONE: il modulo si recupera da sys.modules.
cli_main_mod = sys.modules["cli.main"]
from cli.main import _pause_before_menu, interactive_main
from cli.output import Out
from sources import InMemoryFetcher, run_manifest_pipeline, validate_manifest_dict

from test_sources_pipeline import (
    OC_ASSET,
    OC_REPO,
    build_manifest_dict,
    make_aml,
    make_kext_zip,
    make_pe,
    make_zip,
    profile,
)


# ---------------------------------------------------------------------------
# Fix 2 — hfsplus: path_in_archive come lista di candidati
# ---------------------------------------------------------------------------

def _hfsplus_candidates() -> dict:
    return {
        "type": "github_release",
        "repo": OC_REPO,
        "tag": "latest",
        "asset": OC_ASSET,
        "path_in_archive": [
            "X64/EFI/OC/Drivers/HfsPlus.efi",
            "X64/EFI/OC/Drivers/OpenHfsPlus.efi",
            "X64/EFI/OC/Drivers/HfsPlusLegacy.efi",
        ],
    }


def _validate_source(raw: dict):
    """Valida un singolo blocco source dentro un manifest minimale."""
    manifest = {
        "manifest_version": 1,
        "profile_id": "fujitsu_q556_2",
        "name": "t",
        "components": [
            {
                "id": "hfsplus",
                "kind": "efi_binary",
                "required": True,
                "target": "OC/Drivers/HfsPlus.efi",
                "source": raw,
            }
        ],
    }
    spec, errors = validate_manifest_dict(manifest)
    if errors:
        return None, errors
    return spec.components[0].source, []


def test_schema_accepts_path_in_archive_list():
    src, errors = _validate_source(_hfsplus_candidates())
    assert errors == []
    assert src.path_in_archive == [
        "X64/EFI/OC/Drivers/HfsPlus.efi",
        "X64/EFI/OC/Drivers/OpenHfsPlus.efi",
        "X64/EFI/OC/Drivers/HfsPlusLegacy.efi",
    ]
    # to_dict conserva la lista
    assert isinstance(src.to_dict()["path_in_archive"], list)


def test_schema_accepts_path_in_archive_string():
    raw = dict(_hfsplus_candidates())
    raw["path_in_archive"] = "X64/EFI/OC/Drivers/HfsPlus.efi"
    src, errors = _validate_source(raw)
    assert errors == []
    assert src.path_in_archive == ["X64/EFI/OC/Drivers/HfsPlus.efi"]


def test_schema_rejects_invalid_path_in_archive_list():
    raw = dict(_hfsplus_candidates())
    raw["path_in_archive"] = [123]
    _, errors = _validate_source(raw)
    assert any("path_in_archive" in e for e in errors)


def _manifest_with_openhfsplus_only():
    """Manifest di test dove l'archivio OC ha SOLO OpenHfsPlus.efi (come 1.0.8)."""
    d = build_manifest_dict()
    for comp in d["components"]:
        if comp["id"] == "hfsplus":
            comp["source"] = _hfsplus_candidates()
    manifest, errors = validate_manifest_dict(d)
    assert errors == [], errors
    return manifest


def _fetcher_with_oc_zip(manifest, oc_zip: bytes) -> InMemoryFetcher:
    fetcher = InMemoryFetcher()
    for comp in manifest.components:
        src = comp.source
        if comp.kind in ("efi_binary", "kext"):
            if src.repo == OC_REPO:
                fetcher.register_archive(src, oc_zip)
            else:
                bundle = comp.target.split("/")[-1]
                fetcher.register_archive(src, make_kext_zip(f"{bundle}-1.0-RELEASE", bundle))
        elif comp.kind == "aml":
            fetcher.register_bytes(src, make_aml())
    return fetcher


OC_ZIP_NO_HFS = make_zip({
    "X64/EFI/OC/OpenCore.efi": make_pe(),
    "X64/EFI/BOOT/BOOTx64.efi": make_pe(),
    # HfsPlus.efi assente: OpenCorePkg 1.0.8 spedisce OpenHfsPlus.efi
    "X64/EFI/OC/Drivers/OpenHfsPlus.efi": make_pe(),
    "X64/EFI/OC/Drivers/OpenRuntime.efi": make_pe(),
})


def _run_pipeline(tmp_path, manifest, fetcher):
    out = tmp_path / "out"
    return run_manifest_pipeline(
        manifest=manifest,
        profile=profile(),
        output_dir=out,
        fetcher=fetcher,
        log=lambda msg: None,
    ), out


def test_hfsplus_fallback_picks_openhfsplus(tmp_path):
    """Scenario reale 1.0.8: niente HfsPlus.efi -> usa OpenHfsPlus.efi."""
    manifest = _manifest_with_openhfsplus_only()
    fetcher = _fetcher_with_oc_zip(manifest, OC_ZIP_NO_HFS)
    result, out = _run_pipeline(tmp_path, manifest, fetcher)
    assert result["success"] is True, result
    assert result["efi_status"] == "VALID"

    placed = out / "EFI" / "OC" / "Drivers" / "HfsPlus.efi"
    assert placed.exists(), "il driver HFS+ deve essere comunque materializzato"
    assert placed.stat().st_size > 0

    ids = {c["component_id"]: c for c in result["components"]}
    assert ids["hfsplus"]["status"] == "OK"
    # La provenienza deve dire da quale file dell'archivio arriva davvero
    assert "OpenHfsPlus" in ids["hfsplus"]["resolved"]


def test_hfsplus_prefers_exact_when_present(tmp_path):
    """Se HfsPlus.efi esiste ancora nell'archivio, vince il path esatto."""
    oc_zip = make_zip({
        "X64/EFI/OC/OpenCore.efi": make_pe(),
        "X64/EFI/BOOT/BOOTx64.efi": make_pe(),
        "X64/EFI/OC/Drivers/HfsPlus.efi": make_pe(),
        "X64/EFI/OC/Drivers/OpenHfsPlus.efi": make_pe(),
        "X64/EFI/OC/Drivers/OpenRuntime.efi": make_pe(),
    })
    manifest = _manifest_with_openhfsplus_only()
    fetcher = _fetcher_with_oc_zip(manifest, oc_zip)
    result, out = _run_pipeline(tmp_path, manifest, fetcher)
    assert result["success"] is True, result
    ids = {c["component_id"]: c for c in result["components"]}
    assert ids["hfsplus"]["resolved"].endswith("HfsPlus.efi")
    assert "OpenHfsPlus" not in ids["hfsplus"]["resolved"]


def test_hfsplus_missing_everywhere_shows_drivers_in_error(tmp_path):
    """Nessun candidato esiste -> FAILED con elenco dei driver nell'archivio."""
    oc_zip = make_zip({
        "X64/EFI/OC/OpenCore.efi": make_pe(),
        "X64/EFI/BOOT/BOOTx64.efi": make_pe(),
        "X64/EFI/OC/Drivers/OpenRuntime.efi": make_pe(),
    })
    manifest = _manifest_with_openhfsplus_only()
    fetcher = _fetcher_with_oc_zip(manifest, oc_zip)
    result, out = _run_pipeline(tmp_path, manifest, fetcher)
    assert result["success"] is False
    ids = {c["component_id"]: c for c in result["components"]}
    hfs = ids["hfsplus"]
    assert hfs["status"] == "FAILED"
    assert "non trovato nell'archivio" in hfs["reason"]
    # Diagnosi utile: l'errore elenca i driver presenti
    assert "OpenRuntime.efi" in hfs["reason"]


# ---------------------------------------------------------------------------
# Fix 1 — il menu torna al menu principale dopo ogni comando
# ---------------------------------------------------------------------------

def test_interactive_main_loops_until_exit(monkeypatch):
    """Dopo un comando il menu viene ridisegnato, finche' non si sceglie Exit."""
    choices = iter([
        {"label": "Doctor", "action": "doctor"},
        {"label": "Exit", "action": "exit"},
    ])
    calls = []

    monkeypatch.setattr(cli_main_mod, "run_menu", lambda items: next(choices))
    monkeypatch.setattr(cli_main_mod, "_pause_before_menu", lambda: True)

    def fake_run_command(args, parser, out):
        calls.append(args.command)
        return 0

    monkeypatch.setattr(cli_main_mod, "run_command", fake_run_command)

    interactive_main(Out(json_output=False, dev=False))

    assert calls == ["doctor"], "un solo comando eseguito prima dell'Exit"


def test_interactive_main_multiple_commands_then_exit(monkeypatch):
    choices = iter([
        {"label": "View database", "action": "database"},
        {"label": "Doctor", "action": "doctor"},
        {"label": "Exit", "action": "exit"},
    ])
    calls = []
    monkeypatch.setattr(cli_main_mod, "run_menu", lambda items: next(choices))
    monkeypatch.setattr(cli_main_mod, "_pause_before_menu", lambda: True)
    monkeypatch.setattr(
        cli_main_mod, "run_command",
        lambda args, parser, out: calls.append(args.command) or 0,
    )
    interactive_main(Out(json_output=False, dev=False))
    assert calls == ["database", "doctor"]


def test_interactive_main_q_at_pause_exits(monkeypatch):
    """Se l'utente preme q alla pausa, il loop termina senza altri comandi."""
    choices = iter([
        {"label": "Doctor", "action": "doctor"},
        {"label": "Exit", "action": "exit"},
    ])
    calls = []
    monkeypatch.setattr(cli_main_mod, "run_menu", lambda items: next(choices))
    monkeypatch.setattr(cli_main_mod, "_pause_before_menu", lambda: False)
    monkeypatch.setattr(
        cli_main_mod, "run_command",
        lambda args, parser, out: calls.append(args.command) or 0,
    )
    interactive_main(Out(json_output=False, dev=False))
    assert calls == ["doctor"]


def test_pause_is_noop_on_non_tty():
    """Pipe/CI: nessuna pausa, il loop non deve bloccarsi."""
    assert _pause_before_menu() is True


def test_interactive_main_pipe_doctor_then_exit(monkeypatch, capsys):
    """`echo '8\\n10' | openhackintosh`: doctor, poi menu, poi Exit (EOF-safe)."""
    monkeypatch.setattr("sys.stdin", io.StringIO("8\n10\n"))
    interactive_main(Out(json_output=False, dev=False))
    captured = capsys.readouterr()
    assert "Doctor" in captured.out or "doctor" in captured.out


def test_interactive_main_ctrl_c_during_command_returns_to_menu(monkeypatch):
    choices = iter([
        {"label": "Generate EFI", "action": "generate"},
        {"label": "Exit", "action": "exit"},
    ])
    monkeypatch.setattr(cli_main_mod, "run_menu", lambda items: next(choices))
    monkeypatch.setattr(cli_main_mod, "_pause_before_menu", lambda: True)

    def boom(args, parser, out):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli_main_mod, "run_command", boom)
    # Non deve propagare KeyboardInterrupt: torna al menu e poi esce con Exit.
    interactive_main(Out(json_output=False, dev=False))


# ---------------------------------------------------------------------------
# Fix 3 — feedback visibile della selezione
# ---------------------------------------------------------------------------

class _FakeReader:
    """Reader di test: restituisce i token in coda."""

    def __init__(self, keys):
        self.keys = list(keys)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def restore(self):
        pass

    def read_key(self, timeout=None):
        if self.keys:
            return self.keys.pop(0)
        return None


def test_selection_shows_visible_feedback(monkeypatch):
    """Anche senza eco dei tasti, la scelta mostra '✔ N. Label'."""
    monkeypatch.setattr("cli.selector.time.sleep", lambda s: None)
    from cli import selector as sel

    items = [
        {"label": "Uno", "action": "one"},
        {"label": "Due", "action": "two"},
        {"label": "Tre", "action": "three"},
    ]
    out = io.StringIO()
    reader = _FakeReader(["3"])
    idx = sel.select_interactive(items, "T", "P", stdout=out, reader=reader)
    assert idx == 2
    text = out.getvalue()
    assert "\u2714" in text, "riga di conferma mancante"
    assert "Tre" in text, "la label scelta deve essere visibile"


def test_selection_feedback_on_enter(monkeypatch):
    monkeypatch.setattr("cli.selector.time.sleep", lambda s: None)
    from cli import selector as sel

    items = [{"label": "Uno", "action": "one"}, {"label": "Due", "action": "two"}]
    out = io.StringIO()
    reader = _FakeReader([sel.KEY_DOWN, sel.KEY_ENTER])
    idx = sel.select_interactive(items, "T", "P", stdout=out, reader=reader)
    assert idx == 1
    assert "\u2714" in out.getvalue()
    assert "Due" in out.getvalue()
