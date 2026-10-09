"""
Sources manifest: schema, loader e coerenza con il profilo hardware.
"""

from __future__ import annotations

import copy
import json

import pytest

from database import load_all_profiles
from sources import (
    ManifestError,
    available_manifests,
    check_against_profile,
    load_manifest,
    load_manifest_for_profile,
    manifest_path_for,
    validate_manifest_dict,
)
from sources.fetcher import pick_asset
from sources.schema import SourceSpec


# ---------------------------------------------------------------------------
# Fixture: manifest minimo valido
# ---------------------------------------------------------------------------

def _comp(cid, kind="efi_binary", target=None, required=True, source=None, **extra):
    comp = {
        "id": cid,
        "kind": kind,
        "required": required,
        "target": target or f"OC/{cid}.efi",
        "source": source or {
            "type": "github_release",
            "repo": "test/repo",
            "asset": "test.zip",
            "path_in_archive": f"X64/{cid}.efi",
        },
    }
    if not required and "optional_group" not in extra:
        extra.setdefault("optional_group", "nvme")
    comp.update(extra)
    return comp


def valid_manifest_dict():
    return {
        "manifest_version": 1,
        "profile_id": "test_profile",
        "components": [
            _comp("opencore", target="OC/OpenCore.efi"),
            _comp("bootx64", target="BOOT/BOOTx64.efi"),
            _comp(
                "lilu", kind="kext", target="OC/Kexts/Lilu.kext",
                source={"type": "github_release", "repo": "test/lilu", "asset": "*.zip"},
            ),
            _comp(
                "ssdt", kind="aml", target="OC/ACPI/SSDT-X.aml",
                source={"type": "github_raw", "repo": "test/acpi", "ref": "master", "path": "SSDT-X.aml"},
            ),
            _comp("config", kind="generated", target="OC/config.plist",
                  source={"type": "generated", "generator": "config.plist"}),
        ],
    }


# ---------------------------------------------------------------------------
# Schema: manifest validi
# ---------------------------------------------------------------------------

def test_valid_manifest_passes():
    manifest, errors = validate_manifest_dict(valid_manifest_dict())
    assert errors == []
    assert manifest is not None
    assert manifest.profile_id == "test_profile"
    assert len(manifest.components) == 5
    assert manifest.by_id()["lilu"].kind == "kext"


def test_component_source_summary():
    rel = SourceSpec(type="github_release", repo="a/b", asset="X-*.zip")
    assert "a/b" in rel.summary()
    raw = SourceSpec(type="github_raw", repo="a/b", ref="master", path="f.aml")
    assert "raw:a/b@master/f.aml" == raw.summary()


# ---------------------------------------------------------------------------
# Schema: errori
# ---------------------------------------------------------------------------

def test_wrong_manifest_version():
    raw = valid_manifest_dict()
    raw["manifest_version"] = 99
    _, errors = validate_manifest_dict(raw)
    assert any("manifest_version" in e for e in errors)


def test_missing_profile_id():
    raw = valid_manifest_dict()
    del raw["profile_id"]
    _, errors = validate_manifest_dict(raw)
    assert any("profile_id" in e for e in errors)


def test_unknown_top_level_field():
    raw = valid_manifest_dict()
    raw["intruso"] = True
    _, errors = validate_manifest_dict(raw)
    assert any("intruso" in e for e in errors)


def test_empty_components():
    raw = valid_manifest_dict()
    raw["components"] = []
    _, errors = validate_manifest_dict(raw)
    assert any("components" in e for e in errors)


def test_duplicate_id():
    raw = valid_manifest_dict()
    raw["components"].append(_comp("opencore", target="OC/Other.efi"))
    _, errors = validate_manifest_dict(raw)
    assert any("duplicato" in e and "opencore" in e for e in errors)


def test_duplicate_target():
    raw = valid_manifest_dict()
    raw["components"].append(_comp("altro", target="OC/OpenCore.efi"))
    _, errors = validate_manifest_dict(raw)
    assert any("target duplicato" in e for e in errors)


def test_path_traversal_rejected():
    raw = valid_manifest_dict()
    raw["components"][0]["target"] = "../fuori.efi"
    _, errors = validate_manifest_dict(raw)
    assert any("traversal" in e for e in errors)


def test_target_suffix_must_match_kind():
    raw = valid_manifest_dict()
    raw["components"][2]["target"] = "OC/Kexts/Lilu.efi"  # kext ma suffisso .efi
    _, errors = validate_manifest_dict(raw)
    assert any(".kext" in e for e in errors)


def test_optional_requires_group():
    raw = valid_manifest_dict()
    bad = _comp("opt", required=False, target="OC/Kexts/Opt.kext", kind="kext",
                source={"type": "github_release", "repo": "a/b", "asset": "*.zip"})
    bad.pop("optional_group")
    raw["components"].append(bad)
    _, errors = validate_manifest_dict(raw)
    assert any("optional_group" in e for e in errors)


def test_invalid_optional_group():
    raw = valid_manifest_dict()
    raw["components"].append(_comp("opt", required=False, target="OC/opt.efi", optional_group="nonsense"))
    _, errors = validate_manifest_dict(raw)
    assert any("optional_group invalido" in e for e in errors)


def test_sha256_must_be_hex64():
    raw = valid_manifest_dict()
    raw["components"][0]["sha256"] = "zzzz"
    _, errors = validate_manifest_dict(raw)
    assert any("sha256" in e for e in errors)


def test_sha256_not_allowed_on_kext():
    raw = valid_manifest_dict()
    raw["components"][2]["sha256"] = "0" * 64
    _, errors = validate_manifest_dict(raw)
    assert any("kext" in e for e in errors)


def test_invalid_source_type():
    raw = valid_manifest_dict()
    raw["components"][0]["source"] = {"type": "ftp", "url": "ftp://x"}
    _, errors = validate_manifest_dict(raw)
    assert any("type invalido" in e for e in errors)


def test_github_raw_requires_ref_and_path():
    raw = valid_manifest_dict()
    raw["components"][3]["source"] = {"type": "github_raw", "repo": "a/b"}
    _, errors = validate_manifest_dict(raw)
    assert any("'ref'" in e for e in errors)
    assert any("'path'" in e for e in errors)


def test_generated_kind_requires_generated_source():
    raw = valid_manifest_dict()
    raw["components"][4]["source"] = {"type": "url", "url": "https://x.it/f"}
    _, errors = validate_manifest_dict(raw)
    assert any("generated" in e for e in errors)


def test_kext_cannot_come_from_github_raw():
    raw = valid_manifest_dict()
    raw["components"][2]["source"] = {"type": "github_raw", "repo": "a/b", "ref": "m", "path": "p"}
    _, errors = validate_manifest_dict(raw)
    assert any("archivio" in e for e in errors)


def test_min_size_must_be_int():
    raw = valid_manifest_dict()
    raw["components"][0]["min_size"] = "grande"
    _, errors = validate_manifest_dict(raw)
    assert any("min_size" in e for e in errors)


def test_debug_asset_pattern_rejected():
    """Regola 2.0.2: mai build DEBUG nel manifest, solo RELEASE ufficiali."""
    raw = valid_manifest_dict()
    raw["components"][0]["source"]["asset"] = "OpenCore-*-DEBUG.zip"
    _, errors = validate_manifest_dict(raw)
    assert any("DEBUG" in e for e in errors)


def test_release_asset_pattern_allowed():
    raw = valid_manifest_dict()
    raw["components"][0]["source"]["asset"] = "OpenCore-*-RELEASE.zip"
    manifest, errors = validate_manifest_dict(raw)
    assert errors == []
    assert manifest is not None


# ---------------------------------------------------------------------------
# Loader + manifest reale del Q556/2
# ---------------------------------------------------------------------------

def test_available_manifests_include_q556():
    assert "fujitsu_q556_2" in available_manifests()


def test_q556_manifest_loads():
    manifest = load_manifest_for_profile("fujitsu_q556_2")
    assert manifest.profile_id == "fujitsu_q556_2"
    ids = {c.id for c in manifest.components}
    for expected in ("opencore", "bootx64", "lilu", "virtualsmc", "whatevergreen",
                     "applealc", "realtekrtl8111", "ssdt_plug", "ssdt_ec_usbx",
                     "config_plist"):
        assert expected in ids, f"manca {expected}"


def test_q556_manifest_covers_profile():
    manifest = load_manifest_for_profile("fujitsu_q556_2")
    profile = load_all_profiles()["fujitsu_q556_2"]
    assert check_against_profile(manifest, profile) == []


def test_q556_manifest_unique_targets():
    manifest = load_manifest_for_profile("fujitsu_q556_2")
    targets = [(c.scope, c.target) for c in manifest.components]
    assert len(targets) == len(set(targets))


def test_q556_required_components_have_sources():
    manifest = load_manifest_for_profile("fujitsu_q556_2")
    for comp in manifest.required_components():
        assert comp.source.type, f"{comp.id} senza fonte"
        assert comp.target, f"{comp.id} senza target"


def test_load_missing_manifest_raises(tmp_path):
    with pytest.raises(ManifestError):
        load_manifest(tmp_path / "non_esiste.json")


def test_load_invalid_json_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{non valido", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(path)


def test_load_invalid_manifest_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"manifest_version": 1}), encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(path)


def test_manifest_path_for_respects_root(tmp_path):
    p = manifest_path_for("x", tmp_path)
    assert p == tmp_path / "x" / "sources.json"


# ---------------------------------------------------------------------------
# Coerenza: manifest incompleto -> problemi
# ---------------------------------------------------------------------------

def _q556_profile():
    return load_all_profiles()["fujitsu_q556_2"]


def test_inconsistency_missing_lilu():
    manifest = load_manifest_for_profile("fujitsu_q556_2")
    manifest.components = [c for c in manifest.components if c.id != "lilu"]
    problems = check_against_profile(manifest, _q556_profile())
    assert any("Lilu" in p for p in problems)


def test_inconsistency_missing_config_plist():
    manifest = load_manifest_for_profile("fujitsu_q556_2")
    manifest.components = [c for c in manifest.components if c.source.generator != "config.plist"]
    problems = check_against_profile(manifest, _q556_profile())
    assert any("config.plist" in p for p in problems)


def test_inconsistency_wrong_profile_id():
    manifest = load_manifest_for_profile("fujitsu_q556_2")
    manifest.profile_id = "altro"
    problems = check_against_profile(manifest, _q556_profile())
    assert any("profilo" in p for p in problems)


def test_inconsistency_missing_booter():
    manifest = load_manifest_for_profile("fujitsu_q556_2")
    manifest.components = [c for c in manifest.components if c.target != "BOOT/BOOTx64.efi"]
    problems = check_against_profile(manifest, _q556_profile())
    assert any("BOOTx64" in p for p in problems)


# ---------------------------------------------------------------------------
# pick_asset (selezione asset dalle release GitHub)
# ---------------------------------------------------------------------------

def test_pick_asset_pattern_match():
    assets = [{"name": "OpenCore-1.0.8-RELEASE.zip"}, {"name": "OpenCore-1.0.8-DEBUG.zip"}]
    assert pick_asset(assets, "OpenCore-*-RELEASE.zip")["name"] == "OpenCore-1.0.8-RELEASE.zip"


def test_pick_asset_no_match_returns_none():
    assets = [{"name": "OpenCore-1.0.8-DEBUG.zip"}]
    assert pick_asset(assets, "OpenCore-*-RELEASE.zip") is None


def test_pick_asset_empty_pattern_first_zip():
    assets = [{"name": "a.txt"}, {"name": "b.zip"}]
    assert pick_asset(assets, "")["name"] == "b.zip"


def test_pick_asset_empty_list():
    assert pick_asset([], "*.zip") is None


# ---------------------------------------------------------------------------
# Template nei pattern asset ({macos})
# ---------------------------------------------------------------------------

def test_resolve_asset_pattern_plain():
    from sources.fetcher import resolve_asset_pattern

    assert resolve_asset_pattern("X-*-RELEASE.zip", None) == "X-*-RELEASE.zip"
    assert resolve_asset_pattern("X-*-RELEASE.zip", {"macos": "Ventura"}) == "X-*-RELEASE.zip"


def test_resolve_asset_pattern_template():
    from sources.fetcher import resolve_asset_pattern

    pattern = "AirportItlwm_*_stable_{macos}.kext.zip"
    assert resolve_asset_pattern(pattern, {"macos": "Ventura"}) == \
        "AirportItlwm_*_stable_Ventura.kext.zip"


def test_resolve_asset_pattern_missing_context():
    from sources.fetcher import FetchError, resolve_asset_pattern

    with pytest.raises(FetchError):
        resolve_asset_pattern("X_{macos}.zip", None)
    with pytest.raises(FetchError):
        resolve_asset_pattern("X_{macos}.zip", {})


def test_macos_asset_variant_mapping():
    from sources.pipeline import macos_asset_variant

    assert macos_asset_variant("Ventura 13.x") == "Ventura"
    assert macos_asset_variant("Monterey 12.x") == "Monterey"
    assert macos_asset_variant("Sonoma 14.x") == "Sonoma14.4"
    assert macos_asset_variant("Big Sur 11.x") == "BigSur"
    assert macos_asset_variant("Sequoia 15.x") is None
    assert macos_asset_variant("Windows") is None
