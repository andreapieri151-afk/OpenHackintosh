"""Test CLI commands e output JSON."""

import json
import sys

import pytest

from cli.main import main


def test_detect_json(capsys):
    code = main(["detect", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["mode"] == "detect"
    assert "hardware" in data
    assert "identity" in data


def test_database_list_json(capsys):
    code = main(["database", "list", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert "fujitsu_q556_2" in data["profiles"]


def test_diagnose_json(capsys):
    code = main(["diagnose", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["mode"] == "diagnose"
    assert "computer" in data
    assert data["overall"] in ("compatible", "partial", "unsupported", "unknown")


def test_database_show_missing_nonzero(capsys):
    code = main(["database", "show", "does_not_exist", "--json"])
    assert code != 0
    data = json.loads(capsys.readouterr().out)
    assert data.get("ok") is False
