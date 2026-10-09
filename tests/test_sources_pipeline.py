"""
Sources engine v1: pipeline end-to-end OFFLINE.

Usa InMemoryFetcher con binari sintetici MA formalmente validi (PE/COFF,
Mach-O, firma AML) per provare che l'algoritmo:
- assembla la EFI completa a partire dal manifest;
- genera config.plist e README con provenance;
- passa il final audit e produce lo ZIP;
- FALLISCE (mai EFI parziale/finta) se un componente obbligatorio manca,
  e' vuoto, ha magic sbagliato, contiene placeholder o sgarra lo sha256.
"""

from __future__ import annotations

import io
import json
import struct
import zipfile

import pytest

from database import load_all_profiles
from sources import (
    InMemoryFetcher,
    check_against_profile,
    load_manifest_for_profile,
    run_manifest_pipeline,
    validate_manifest_dict,
)
from sources.schema import SourceSpec


# ---------------------------------------------------------------------------
# Binari sintetici validi
# ---------------------------------------------------------------------------

def make_pe(size: int = 512) -> bytes:
    """Binario PE/COFF minimale: DOS header MZ + firma PE\\0\\0 a e_lfanew."""
    data = bytearray(size)
    data[0:2] = b"MZ"
    e_lfanew = 0x80
    struct.pack_into("<I", data, 0x3C, e_lfanew)
    data[e_lfanew:e_lfanew + 4] = b"PE\x00\x00"
    return bytes(data)


def make_macho(size: int = 512) -> bytes:
    return b"\xcf\xfa\xed\xfe" + b"\x00" * (size - 4)


def make_aml(size: int = 600) -> bytes:
    return b"SSDT" + b"\x00" * (size - 4)


def make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


KEXT_PLIST = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<plist version="1.0"><dict>'
    "<key>CFBundleIdentifier</key><string>test.kext</string>"
    "<key>CFBundleExecutable</key><string>Bin</string>"
    "</dict></plist>"
).encode()


def make_kext_zip(prefix: str, bundle: str, executable: bytes = None) -> bytes:
    executable = make_macho() if executable is None else executable
    return make_zip({
        f"{prefix}/{bundle}/Contents/Info.plist": KEXT_PLIST,
        f"{prefix}/{bundle}/Contents/MacOS/Bin": executable,
    })


# ---------------------------------------------------------------------------
# Manifest di test (costruito via schema, stesse regole di quelli reali)
# ---------------------------------------------------------------------------

OC_REPO = "test/OpenCorePkg"
OC_ASSET = "OpenCore-*-RELEASE.zip"


def _gh_release(repo, asset, path_in_archive=""):
    src = {"type": "github_release", "repo": repo, "tag": "latest", "asset": asset}
    if path_in_archive:
        src["path_in_archive"] = path_in_archive
    return src


def build_manifest_dict():
    return {
        "manifest_version": 1,
        "profile_id": "fujitsu_q556_2",
        "name": "Test manifest",
        "components": [
            {"id": "opencore", "kind": "efi_binary", "required": True,
             "target": "OC/OpenCore.efi",
             "source": _gh_release(OC_REPO, OC_ASSET, "X64/EFI/OC/OpenCore.efi")},
            {"id": "bootx64", "kind": "efi_binary", "required": True,
             "target": "BOOT/BOOTx64.efi",
             "source": _gh_release(OC_REPO, OC_ASSET, "X64/EFI/BOOT/BOOTx64.efi")},
            {"id": "hfsplus", "kind": "efi_binary", "required": True,
             "target": "OC/Drivers/HfsPlus.efi",
             "source": _gh_release(OC_REPO, OC_ASSET, "X64/EFI/OC/Drivers/HfsPlus.efi")},
            {"id": "openruntime", "kind": "efi_binary", "required": True,
             "target": "OC/Drivers/OpenRuntime.efi",
             "source": _gh_release(OC_REPO, OC_ASSET, "X64/EFI/OC/Drivers/OpenRuntime.efi")},
            {"id": "lilu", "kind": "kext", "required": True,
             "target": "OC/Kexts/Lilu.kext",
             "source": _gh_release("test/Lilu", "Lilu-*-RELEASE.zip")},
            {"id": "virtualsmc", "kind": "kext", "required": True,
             "target": "OC/Kexts/VirtualSMC.kext",
             "source": _gh_release("test/VirtualSMC", "VirtualSMC-*-RELEASE.zip")},
            {"id": "whatevergreen", "kind": "kext", "required": True,
             "target": "OC/Kexts/WhateverGreen.kext",
             "source": _gh_release("test/WhateverGreen", "WhateverGreen-*-RELEASE.zip")},
            {"id": "applealc", "kind": "kext", "required": True,
             "target": "OC/Kexts/AppleALC.kext",
             "source": _gh_release("test/AppleALC", "AppleALC-*-RELEASE.zip")},
            {"id": "realtekrtl8111", "kind": "kext", "required": True,
             "target": "OC/Kexts/RealtekRTL8111.kext",
             "source": _gh_release("test/RTL8111", "*.zip")},
            {"id": "ssdt_plug", "kind": "aml", "required": True,
             "target": "OC/ACPI/SSDT-PLUG-DRTNIA.aml",
             "source": {"type": "github_raw", "repo": "test/acpi", "ref": "master",
                        "path": "extra-files/compiled/SSDT-PLUG-DRTNIA.aml"}},
            {"id": "ssdt_ec_usbx", "kind": "aml", "required": True,
             "target": "OC/ACPI/SSDT-EC-USBX-DESKTOP.aml",
             "source": {"type": "github_raw", "repo": "test/acpi", "ref": "master",
                        "path": "extra-files/compiled/SSDT-EC-USBX-DESKTOP.aml"}},
            {"id": "config_plist", "kind": "generated", "required": True,
             "target": "OC/config.plist",
             "source": {"type": "generated", "generator": "config.plist"}},
            {"id": "nvmefix", "kind": "kext", "required": False,
             "optional_group": "nvme",
             "target": "OC/Kexts/NVMeFix.kext",
             "source": _gh_release("test/NVMeFix", "NVMeFix-*-RELEASE.zip")},
        ],
    }


def build_manifest():
    manifest, errors = validate_manifest_dict(build_manifest_dict())
    assert errors == [], errors
    return manifest


OC_ZIP = make_zip({
    "X64/EFI/OC/OpenCore.efi": make_pe(),
    "X64/EFI/BOOT/BOOTx64.efi": make_pe(),
    "X64/EFI/OC/Drivers/HfsPlus.efi": make_pe(),
    "X64/EFI/OC/Drivers/OpenRuntime.efi": make_pe(),
})


def build_fetcher(manifest, fetcher=None) -> InMemoryFetcher:
    """Registra nel fetcher tutto cio' che il manifest dichiara di scaricare."""
    fetcher = fetcher or InMemoryFetcher()
    for comp in manifest.components:
        src = comp.source
        if comp.kind in ("efi_binary", "kext"):
            if src.repo == OC_REPO:
                fetcher.register_archive(src, OC_ZIP)
            else:
                bundle = comp.target.split("/")[-1]
                fetcher.register_archive(src, make_kext_zip(f"{bundle}-1.0-RELEASE", bundle))
        elif comp.kind == "aml":
            fetcher.register_bytes(src, make_aml())
    return fetcher


def profile():
    return load_all_profiles()["fujitsu_q556_2"]


def run(tmp_path, manifest=None, fetcher=None, **kwargs):
    manifest = manifest or build_manifest()
    fetcher = fetcher or build_fetcher(manifest)
    out = tmp_path / "out"
    return run_manifest_pipeline(
        manifest=manifest,
        profile=profile(),
        output_dir=out,
        fetcher=fetcher,
        log=lambda msg: None,
        **kwargs,
    ), out


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_full_build_valid(tmp_path):
    result, out = run(tmp_path)
    assert result["success"] is True
    assert result["efi_status"] == "VALID"
    assert result["engine"] == "sources.v1"

    efi = out / "EFI"
    for rel in [
        "BOOT/BOOTx64.efi",
        "OC/OpenCore.efi",
        "OC/config.plist",
        "OC/Drivers/HfsPlus.efi",
        "OC/Drivers/OpenRuntime.efi",
        "OC/Kexts/Lilu.kext/Contents/MacOS/Bin",
        "OC/Kexts/VirtualSMC.kext/Contents/Info.plist",
        "OC/Kexts/WhateverGreen.kext/Contents/MacOS/Bin",
        "OC/Kexts/AppleALC.kext/Contents/MacOS/Bin",
        "OC/Kexts/RealtekRTL8111.kext/Contents/MacOS/Bin",
        "OC/ACPI/SSDT-PLUG-DRTNIA.aml",
        "OC/ACPI/SSDT-EC-USBX-DESKTOP.aml",
    ]:
        assert (efi / rel).exists(), f"manca {rel}"
        if not rel.endswith("/"):
            assert (efi / rel).stat().st_size > 0, f"vuoto: {rel}"

    # ZIP creato e contiene la EFI
    zip_path = out / "EFI_FUJITSU_Q556_2.zip"
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert "EFI/OC/OpenCore.efi" in names
    assert "EFI/OC/config.plist" in names
    assert "README_EFI.txt" in names

    # config.plist e' plist valido
    import plistlib
    config = plistlib.loads((efi / "OC" / "config.plist").read_bytes())
    assert "Kernel" in config and "UEFI" in config and "PlatformInfo" in config

    # Provenance ledger: ogni componente reale ha sha256 e fonte
    for comp in result["components"]:
        if comp["status"] == "OK":
            assert comp["sha256"], comp
            assert comp["source_url"], comp


def test_optional_not_included_by_default(tmp_path):
    result, out = run(tmp_path)
    ids = {c["component_id"]: c for c in result["components"]}
    assert "nvmefix" not in ids
    assert not (out / "EFI" / "OC" / "Kexts" / "NVMeFix.kext").exists()


def test_optional_included_on_flag(tmp_path):
    result, out = run(tmp_path, include_nvme=True)
    ids = {c["component_id"]: c for c in result["components"]}
    assert ids["nvmefix"]["status"] == "OK"
    assert (out / "EFI" / "OC" / "Kexts" / "NVMeFix.kext").exists()


def test_optional_failure_does_not_block(tmp_path):
    manifest = build_manifest()
    # NVMeFix richiesto ma archivio non disponibile -> opzionale scartato, build VALID
    fetcher2 = InMemoryFetcher()
    for comp in manifest.components:
        if comp.id == "nvmefix":
            continue
        src = comp.source
        if comp.kind in ("efi_binary", "kext"):
            if src.repo == OC_REPO:
                fetcher2.register_archive(src, OC_ZIP)
            else:
                bundle = comp.target.split("/")[-1]
                fetcher2.register_archive(src, make_kext_zip(f"{bundle}-1.0-RELEASE", bundle))
        elif comp.kind == "aml":
            fetcher2.register_bytes(src, make_aml())

    out_dir = tmp_path / "out_opt"
    result = run_manifest_pipeline(
        manifest=manifest, profile=profile(), output_dir=out_dir,
        fetcher=fetcher2, include_nvme=True, log=lambda m: None,
    )
    assert result["success"] is True
    assert result["efi_status"] == "VALID"
    ids = {c["component_id"]: c for c in result["components"]}
    assert ids["nvmefix"]["status"] == "SKIPPED"


# ---------------------------------------------------------------------------
# Fallimenti: nessun file finto, mai
# ---------------------------------------------------------------------------

def test_missing_required_archive_fails(tmp_path):
    manifest = build_manifest()
    fetcher = build_fetcher(manifest)
    # Rimuove l'archivio OpenCore: componente obbligatorio non scaricabile.
    from sources.fetcher import source_cache_name
    oc_src = manifest.by_id()["opencore"].source
    fetcher.archives.pop(source_cache_name(oc_src), None)

    result, out = run(tmp_path, manifest=manifest, fetcher=fetcher)
    assert result["success"] is False
    assert result["efi_status"] == "FAILED"
    assert "opencore" in result["error"]
    # Nessuno ZIP in giro
    assert not list(out.glob("*.zip"))


def test_zero_byte_kext_binary_fails(tmp_path):
    manifest = build_manifest()
    fetcher = InMemoryFetcher()
    for comp in manifest.components:
        src = comp.source
        if comp.kind in ("efi_binary", "kext"):
            if src.repo == OC_REPO:
                fetcher.register_archive(src, OC_ZIP)
            elif comp.id == "lilu":
                # Eseguibile del kext a 0 byte: il caso "Lilu finto" della 1.0.0
                fetcher.register_archive(src, make_kext_zip("Lilu-1.0-RELEASE", "Lilu.kext", executable=b""))
            else:
                bundle = comp.target.split("/")[-1]
                fetcher.register_archive(src, make_kext_zip(f"{bundle}-1.0-RELEASE", bundle))
        elif comp.kind == "aml":
            fetcher.register_bytes(src, make_aml())

    result, out = run(tmp_path, manifest=manifest, fetcher=fetcher)
    assert result["success"] is False
    assert result["efi_status"] == "FAILED"
    assert "lilu" in result["error"]
    assert not list(out.glob("*.zip"))


def test_kext_missing_from_archive_fails(tmp_path):
    manifest = build_manifest()
    fetcher = InMemoryFetcher()
    for comp in manifest.components:
        src = comp.source
        if comp.kind in ("efi_binary", "kext"):
            if src.repo == OC_REPO:
                fetcher.register_archive(src, OC_ZIP)
            elif comp.id == "applealc":
                # Lo zip non contiene il bundle richiesto
                fetcher.register_archive(src, make_zip({"README.txt": b"niente kext qui"}))
            else:
                bundle = comp.target.split("/")[-1]
                fetcher.register_archive(src, make_kext_zip(f"{bundle}-1.0-RELEASE", bundle))
        elif comp.kind == "aml":
            fetcher.register_bytes(src, make_aml())

    result, out = run(tmp_path, manifest=manifest, fetcher=fetcher)
    assert result["success"] is False
    assert "applealc" in result["error"]


def test_wrong_magic_efi_binary_fails(tmp_path):
    manifest = build_manifest()
    fetcher = InMemoryFetcher()
    bad_oc_zip = make_zip({
        "X64/EFI/OC/OpenCore.efi": b"questo non e' un PE/COFF" * 10,
        "X64/EFI/BOOT/BOOTx64.efi": make_pe(),
        "X64/EFI/OC/Drivers/HfsPlus.efi": make_pe(),
        "X64/EFI/OC/Drivers/OpenRuntime.efi": make_pe(),
    })
    for comp in manifest.components:
        src = comp.source
        if comp.kind in ("efi_binary", "kext"):
            if src.repo == OC_REPO:
                fetcher.register_archive(src, bad_oc_zip)
            else:
                bundle = comp.target.split("/")[-1]
                fetcher.register_archive(src, make_kext_zip(f"{bundle}-1.0-RELEASE", bundle))
        elif comp.kind == "aml":
            fetcher.register_bytes(src, make_aml())

    result, out = run(tmp_path, manifest=manifest, fetcher=fetcher)
    assert result["success"] is False
    assert "opencore" in result["error"]
    assert any("PE" in c["reason"].upper() for c in result["components"] if c["component_id"] == "opencore")


def test_placeholder_aml_fails(tmp_path):
    manifest = build_manifest()
    fetcher = build_fetcher(manifest)
    # SSDT con firma valida ma contenuto placeholder -> rilevato
    src = manifest.by_id()["ssdt_plug"].source
    fetcher.register_bytes(src, b"SSDT" + b"placeholder finto" * 20)

    result, out = run(tmp_path, manifest=manifest, fetcher=fetcher)
    assert result["success"] is False
    assert "ssdt_plug" in result["error"]


def test_min_size_violation_fails(tmp_path):
    raw = build_manifest_dict()
    for comp in raw["components"]:
        if comp["id"] == "openruntime":
            comp["min_size"] = 10_000_000
    manifest, errors = validate_manifest_dict(raw)
    assert errors == []
    result, out = run(tmp_path, manifest=manifest)
    assert result["success"] is False
    assert "openruntime" in result["error"]
    assert "min_size" in result["error"]


def test_sha256_pin_mismatch_fails(tmp_path):
    raw = build_manifest_dict()
    for comp in raw["components"]:
        if comp["id"] == "ssdt_plug":
            comp["sha256"] = "0" * 64
    manifest, errors = validate_manifest_dict(raw)
    assert errors == []
    result, out = run(tmp_path, manifest=manifest)
    assert result["success"] is False
    assert "ssdt_plug" in result["error"]
    assert "sha256" in result["error"].lower()


def test_sha256_pin_match_passes(tmp_path):
    import hashlib

    aml = make_aml()
    raw = build_manifest_dict()
    for comp in raw["components"]:
        if comp["id"] == "ssdt_plug":
            comp["sha256"] = hashlib.sha256(aml).hexdigest()
    manifest, errors = validate_manifest_dict(raw)
    assert errors == []

    fetcher = build_fetcher(manifest)
    src = manifest.by_id()["ssdt_plug"].source
    fetcher.register_bytes(src, aml)

    result, out = run(tmp_path, manifest=manifest, fetcher=fetcher)
    assert result["success"] is True


def test_corrupt_zip_fails_cleanly(tmp_path):
    manifest = build_manifest()
    fetcher = build_fetcher(manifest)
    from sources.fetcher import source_cache_name
    oc_src = manifest.by_id()["opencore"].source
    fetcher.archives[source_cache_name(oc_src)] = b"non sono uno zip"

    result, out = run(tmp_path, manifest=manifest, fetcher=fetcher)
    assert result["success"] is False
    assert result["efi_status"] == "FAILED"


def test_inconsistent_manifest_rejected_before_fetch(tmp_path):
    manifest = build_manifest()
    manifest.components = [c for c in manifest.components if c.id != "lilu"]
    fetcher = build_fetcher(manifest)

    out = tmp_path / "out"
    result = run_manifest_pipeline(
        manifest=manifest, profile=profile(), output_dir=out,
        fetcher=fetcher, log=lambda m: None,
    )
    assert result["success"] is False
    assert "incoerente" in result["error"].lower()
    assert fetcher.calls == []  # nessuna chiamata di rete


# ---------------------------------------------------------------------------
# Manifest REALE del Q556/2, build offline con fonti finte
# ---------------------------------------------------------------------------

def test_real_manifest_offline_build(tmp_path):
    manifest = load_manifest_for_profile("fujitsu_q556_2")
    assert check_against_profile(manifest, profile()) == []

    # PE sintetici abbastanza grandi per i min_size realistici del manifest vero.
    big_oc_zip = make_zip({
        "X64/EFI/OC/OpenCore.efi": make_pe(60_000),
        "X64/EFI/BOOT/BOOTx64.efi": make_pe(60_000),
        "X64/EFI/OC/Drivers/HfsPlus.efi": make_pe(60_000),
        "X64/EFI/OC/Drivers/OpenRuntime.efi": make_pe(60_000),
        "X64/EFI/OC/Drivers/OpenCanopy.efi": make_pe(60_000),
        "X64/EFI/OC/Drivers/ResetNvramEntry.efi": make_pe(60_000),
    })

    fetcher = InMemoryFetcher()
    for comp in manifest.components:
        src = comp.source
        if comp.kind == "efi_binary":
            fetcher.register_archive(src, big_oc_zip)
        elif comp.kind == "kext":
            bundle = comp.target.split("/")[-1]
            fetcher.register_archive(src, make_kext_zip(f"{bundle}-1.0-RELEASE", bundle))
        elif comp.kind == "aml":
            fetcher.register_bytes(src, make_aml())

    out = tmp_path / "real"
    result = run_manifest_pipeline(
        manifest=manifest, profile=profile(), output_dir=out,
        fetcher=fetcher, log=lambda m: None,
    )
    assert result["success"] is True, result.get("error")
    assert result["efi_status"] == "VALID"

    names = set()
    with zipfile.ZipFile(out / "EFI_FUJITSU_Q556_2.zip") as zf:
        names = set(zf.namelist())
    assert "EFI/OC/OpenCore.efi" in names
    assert "EFI/BOOT/BOOTx64.efi" in names
    assert "EFI/OC/Kexts/Lilu.kext/Contents/MacOS/Bin" in names
    assert "EFI/OC/ACPI/SSDT-PLUG-DRTNIA.aml" in names

    readme = (out / "README_EFI.txt").read_text(encoding="utf-8")
    assert "acidanthera/OpenCorePkg" in readme
    assert "Componenti e fonti" in readme


def test_real_manifest_json_serializable(tmp_path):
    """Il report della pipeline deve essere serializzabile (per --json)."""
    manifest = load_manifest_for_profile("fujitsu_q556_2")
    big_oc_zip = make_zip({
        "X64/EFI/OC/OpenCore.efi": make_pe(60_000),
        "X64/EFI/BOOT/BOOTx64.efi": make_pe(60_000),
        "X64/EFI/OC/Drivers/HfsPlus.efi": make_pe(60_000),
        "X64/EFI/OC/Drivers/OpenRuntime.efi": make_pe(60_000),
    })
    fetcher = InMemoryFetcher()
    for comp in manifest.components:
        src = comp.source
        if comp.kind == "efi_binary":
            fetcher.register_archive(src, big_oc_zip)
        elif comp.kind == "kext":
            bundle = comp.target.split("/")[-1]
            fetcher.register_archive(src, make_kext_zip(f"{bundle}-1.0-RELEASE", bundle))
        elif comp.kind == "aml":
            fetcher.register_bytes(src, make_aml())

    out = tmp_path / "json"
    result = run_manifest_pipeline(
        manifest=manifest, profile=profile(), output_dir=out,
        fetcher=fetcher, log=lambda m: None,
    )
    serialized = json.dumps(result)
    assert "sources.v1" in serialized


# ---------------------------------------------------------------------------
# GitHubFetcher (senza rete: API/download via monkeypatch)
# ---------------------------------------------------------------------------

def test_github_fetcher_archive_download(tmp_path, monkeypatch):
    from sources.fetcher import GitHubFetcher
    from efi_builder import downloader

    fetcher = GitHubFetcher(tmp_path / "work", cache_dir=tmp_path / "cache",
                            log=lambda m: None)
    monkeypatch.setattr(
        fetcher, "_get_release",
        lambda repo, tag: {"assets": [
            {"name": "OpenCore-1.0.8-RELEASE.zip", "browser_download_url": "https://example.invalid/oc.zip"},
            {"name": "OpenCore-1.0.8-DEBUG.zip", "browser_download_url": "https://example.invalid/dbg.zip"},
        ]},
    )

    def fake_download(url, dest, progress=None, name="file"):
        from pathlib import Path
        Path(dest).write_bytes(OC_ZIP)
        return True

    monkeypatch.setattr(downloader, "download_file", fake_download)

    src = SourceSpec(type="github_release", repo="acidanthera/OpenCorePkg",
                     asset="OpenCore-*-RELEASE.zip")
    path = fetcher.fetch_archive(src)
    assert zipfile.is_zipfile(path)
    assert path.name == "OpenCore-1.0.8-RELEASE.zip"

    # Secondo fetch: cache hit, nessun nuovo download
    calls = []
    monkeypatch.setattr(downloader, "download_file",
                        lambda *a, **k: calls.append(a) or True)
    path2 = fetcher.fetch_archive(src)
    assert path2 == path
    assert calls == []


def test_github_fetcher_no_matching_asset(tmp_path, monkeypatch):
    from sources.fetcher import FetchError, GitHubFetcher

    fetcher = GitHubFetcher(tmp_path / "work", cache_dir=tmp_path / "cache",
                            log=lambda m: None)
    monkeypatch.setattr(fetcher, "_get_release",
                        lambda repo, tag: {"assets": [{"name": "altro.txt",
                                                        "browser_download_url": "x"}]})
    src = SourceSpec(type="github_release", repo="a/b", asset="OpenCore-*-RELEASE.zip")
    with pytest.raises(FetchError):
        fetcher.fetch_archive(src)


def test_github_fetcher_release_not_found(tmp_path, monkeypatch):
    from sources.fetcher import FetchError, GitHubFetcher

    fetcher = GitHubFetcher(tmp_path / "work", cache_dir=tmp_path / "cache",
                            log=lambda m: None)
    monkeypatch.setattr(fetcher, "_get_release", lambda repo, tag: None)
    src = SourceSpec(type="github_release", repo="a/b", asset="*.zip")
    with pytest.raises(FetchError):
        fetcher.fetch_archive(src)


def test_github_fetcher_corrupt_zip_invalidates_cache(tmp_path, monkeypatch):
    from sources.fetcher import FetchError, GitHubFetcher
    from efi_builder import downloader

    fetcher = GitHubFetcher(tmp_path / "work", cache_dir=tmp_path / "cache",
                            log=lambda m: None)
    monkeypatch.setattr(fetcher, "_get_release",
                        lambda repo, tag: {"assets": [
                            {"name": "oc.zip", "browser_download_url": "https://example.invalid/oc.zip"}]})

    attempts = {"n": 0}

    def fake_download(url, dest, progress=None, name="file"):
        attempts["n"] += 1
        from pathlib import Path
        Path(dest).write_bytes(b"corrotto, non uno zip")
        return True

    monkeypatch.setattr(downloader, "download_file", fake_download)
    src = SourceSpec(type="github_release", repo="a/b", asset="oc.zip")
    with pytest.raises(FetchError):
        fetcher.fetch_archive(src)
    assert attempts["n"] == 2  # due tentativi, cache invalidata ogni volta
