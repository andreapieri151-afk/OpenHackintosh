"""Test CLI: comando `sources` e flag --engine manifest di `generate`."""

import json

from cli.main import build_parser, main


def test_sources_list(capsys):
    code = main(["sources", "list"])
    assert code == 0
    out = capsys.readouterr().out
    assert "fujitsu_q556_2" in out
    assert "VALID" in out


def test_sources_list_json(capsys):
    code = main(["sources", "list", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    profiles = [row["profile"] for row in data["manifests"]]
    assert "fujitsu_q556_2" in profiles


def test_sources_show(capsys):
    code = main(["sources", "show", "--profile", "fujitsu_q556_2"])
    assert code == 0
    out = capsys.readouterr().out
    assert "opencore" in out and "lilu" in out
    assert "acidanthera/OpenCorePkg" in out


def test_sources_show_json(capsys):
    code = main(["sources", "show", "--profile", "fujitsu_q556_2", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["profile"] == "fujitsu_q556_2"
    ids = {c["id"] for c in data["manifest"]["components"]}
    assert "opencore" in ids and "config_plist" in ids


def test_sources_check_ok(capsys):
    code = main(["sources", "check", "--profile", "fujitsu_q556_2"])
    assert code == 0
    assert "OK" in capsys.readouterr().out


def test_sources_check_json_ok(capsys):
    code = main(["sources", "check", "--profile", "fujitsu_q556_2", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    assert data["problems"] == []


def test_sources_show_missing_profile(capsys):
    code = main(["sources", "show", "--profile", "non_esiste", "--json"])
    assert code != 0


def test_generate_parser_accepts_manifest_engine():
    parser = build_parser()
    args = parser.parse_args(["generate", "--engine", "manifest", "--profile", "fujitsu_q556_2"])
    assert args.engine == "manifest"
    args2 = parser.parse_args(["generate", "--manifest", "x/sources.json"])
    assert args2.manifest == "x/sources.json"


def test_generate_parser_default_engine_manifest():
    """Dalla 2.0.2 il motore di default e' il sources engine."""
    parser = build_parser()
    args = parser.parse_args(["generate"])
    assert args.engine == "manifest"
    assert args.manifest is None


def test_resolve_engine_manifest_for_q556():
    from cli.commands.generate import _resolve_engine

    parser = build_parser()
    args = parser.parse_args(["generate", "--profile", "fujitsu_q556_2"])
    assert _resolve_engine(args, "fujitsu_q556_2") == "manifest"


def test_resolve_engine_fallback_legacy_without_manifest():
    """Profilo senza sources manifest (es. q957) -> fallback legacy, mai crash."""
    from cli.commands.generate import _resolve_engine

    parser = build_parser()
    args = parser.parse_args(["generate", "--profile", "fujitsu_q957"])
    assert _resolve_engine(args, "fujitsu_q957") == "legacy"


def test_resolve_engine_explicit_legacy():
    from cli.commands.generate import _resolve_engine

    parser = build_parser()
    args = parser.parse_args(["generate", "--engine", "legacy"])
    assert _resolve_engine(args, "fujitsu_q556_2") == "legacy"


def test_resolve_engine_explicit_manifest_path_wins():
    from cli.commands.generate import _resolve_engine

    parser = build_parser()
    args = parser.parse_args(["generate", "--manifest", "x/sources.json",
                              "--engine", "legacy"])
    assert _resolve_engine(args, "fujitsu_q957") == "manifest"
