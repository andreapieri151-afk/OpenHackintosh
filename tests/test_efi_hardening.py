"""Test EFI Generator hardening: download failure, fake/binar, missing, audit, Q556/2."""

import json
import plistlib
import struct
import sys
from pathlib import Path

from cli.main import main
from database import get_profile, load_all_profiles
from efi.audit import final_audit
from efi.integrity import validate_aml_file, validate_efi_binary, validate_kext
from efi.selection import select_components


def _pe_bytes() -> bytes:
    e = 0x40
    d = bytearray(e + 8)
    d[0:2] = b"MZ"
    struct.pack_into("<I", d, 0x3C, e)
    d[e:e + 4] = b"PE\x00\x00"
    return bytes(d) + b"\x00" * 128


def _macho() -> bytes:
    return b"\xcf\xfa\xed\xfe" + b"\x00" * 128


def _aml() -> bytes:
    return b"SSDT" + b"\x00" * 128


REQUIRED_KEXTS = ["Lilu", "VirtualSMC", "WhateverGreen", "AppleALC", "RealtekRTL8111"]


def _add_kext(efi: Path, name: str, bundle_id: str, exec_name: str) -> None:
    kext = efi / "OC" / "Kexts" / f"{name}.kext"
    (kext / "Contents" / "MacOS").mkdir(parents=True)
    with open(kext / "Contents" / "Info.plist", "wb") as f:
        plistlib.dump({
            "CFBundleIdentifier": bundle_id,
            "CFBundleExecutable": exec_name,
            "CFBundleName": exec_name,
        }, f)
    (kext / "Contents" / "MacOS" / exec_name).write_bytes(_macho())


def _make_valid_efi(tmp: Path) -> Path:
    efi = tmp / "EFI"
    (efi / "BOOT").mkdir(parents=True)
    (efi / "OC" / "Kexts").mkdir(parents=True)
    (efi / "OC" / "Drivers").mkdir(parents=True)
    (efi / "OC" / "ACPI").mkdir(parents=True)

    (efi / "BOOT" / "BOOTx64.efi").write_bytes(_pe_bytes())
    (efi / "OC" / "OpenCore.efi").write_bytes(_pe_bytes())
    (efi / "OC" / "Drivers" / "HfsPlus.efi").write_bytes(_pe_bytes())
    (efi / "OC" / "Drivers" / "OpenRuntime.efi").write_bytes(_pe_bytes())
    (efi / "OC" / "ACPI" / "SSDT-PLUG-DRTNIA.aml").write_bytes(_aml())
    (efi / "OC" / "ACPI" / "SSDT-EC-USBX-DESKTOP.aml").write_bytes(_aml())

    _add_kext(efi, "Lilu", "as.vit9696.Lilu", "Lilu")
    _add_kext(efi, "VirtualSMC", "org.acidanthera.VirtualSMC", "VirtualSMC")
    _add_kext(efi, "WhateverGreen", "as.vit9696.WhateverGreen", "WhateverGreen")
    _add_kext(efi, "AppleALC", "as.vit9696.AppleALC", "AppleALC")
    _add_kext(efi, "RealtekRTL8111", "com.retek.Rtl8111", "RealtekRTL8111")

    config = {
        "ACPI": {"Add": [
            {"Path": "SSDT-PLUG-DRTNIA.aml", "Enabled": True},
            {"Path": "SSDT-EC-USBX-DESKTOP.aml", "Enabled": True},
        ]},
        "Kernel": {"Add": [
            {"BundlePath": f"{k}.kext", "ExecutablePath": f"Contents/MacOS/{k}", "Enabled": True}
            for k in REQUIRED_KEXTS
        ]},
        "UEFI": {"Drivers": [
            {"Path": "HfsPlus.efi", "Enabled": True},
            {"Path": "OpenRuntime.efi", "Enabled": True},
        ]},
        "PlatformInfo": {"Generic": {"SystemSerialNumber": "C02TEST12345"}},
    }
    with open(efi / "OC" / "config.plist", "wb") as f:
        plistlib.dump(config, f)
    return efi


def test_integrity_binary_pe():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.efi"
        p.write_bytes(_pe_bytes())
        assert validate_efi_binary(p).ok
        p.write_bytes(b"not a pe")
        assert not validate_efi_binary(p).ok


def test_integrity_aml():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.aml"
        p.write_bytes(_aml())
        assert validate_aml_file(p).ok
        p.write_bytes(b"0byte")
        assert not validate_aml_file(p).ok


def test_q556_selection_minimal():
    prof = get_profile("fujitsu_q556_2")
    sel = select_components(prof)
    assert sel.required_kexts == ["Lilu", "VirtualSMC", "WhateverGreen", "AppleALC", "RealtekRTL8111"]
    assert "NVMeFix" not in sel.optional_kexts
    assert "RestrictEvents" not in sel.optional_kexts
    assert sel.required_drivers == ["HfsPlus", "OpenRuntime"]
    assert sel.required_ssdts == ["SSDT-PLUG-DRTNIA", "SSDT-EC-USBX-DESKTOP"]


def test_q556_audit_valid(tmp_path):
    efi = _make_valid_efi(tmp_path)
    prof = get_profile("fujitsu_q556_2")
    sel = select_components(prof)
    audit = final_audit(efi, prof, sel)
    assert audit["status"] == "VALID"


def test_q556_audit_missing_acpi(tmp_path):
    efi = _make_valid_efi(tmp_path)
    (efi / "OC" / "ACPI" / "SSDT-PLUG-DRTNIA.aml").unlink()
    prof = get_profile("fujitsu_q556_2")
    sel = select_components(prof)
    audit = final_audit(efi, prof, sel)
    assert audit["status"] == "FAILED"
    assert any("AML invalid" in e for e in audit["errors"])


def test_q556_audit_missing_driver(tmp_path):
    efi = _make_valid_efi(tmp_path)
    (efi / "OC" / "Drivers" / "OpenRuntime.efi").unlink()
    prof = get_profile("fujitsu_q556_2")
    sel = select_components(prof)
    audit = final_audit(efi, prof, sel)
    assert audit["status"] == "FAILED"


def test_q556_audit_config_reference_mismatch(tmp_path):
    efi = _make_valid_efi(tmp_path)
    # Rimuovi kext ma lascia il riferimento in config
    import shutil
    shutil.rmtree(efi / "OC" / "Kexts" / "Lilu.kext")
    prof = get_profile("fujitsu_q556_2")
    sel = select_components(prof)
    audit = final_audit(efi, prof, sel)
    assert audit["status"] == "FAILED"
    assert any("Kext invalid" in e for e in audit["errors"])


def test_generate_failure_exit_code(tmp_path, capsys):
    code = main(["generate", "--profile", "nonexistent", "--output", "output/EFI",
                 "--no-zip", "--json"])
    assert code != 0
    data = json.loads(capsys.readouterr().out)
    assert data.get("ok") is False


def test_download_failure_aborts(tmp_path, monkeypatch):
    """Se il download fallisce, la generazione NON deve proseguire né simulare successo."""
    import efi_builder.downloader as dl
    from efi.generator import build_efi
    prof = get_profile("fujitsu_q556_2")
    monkeypatch.setattr(dl.EFIDownloader, "download_opencore", lambda self: None)
    monkeypatch.setattr(dl, "get_latest_release", lambda _: None)
    result = build_efi(
        profile=prof,
        output_dir=tmp_path / "out",
        smbios_model="iMac18,1",
        audio_layout=11,
        macos_version="Ventura 13.x",
        generate_zip=False,
        silent=True,
    )
    assert result.get("success") is False
    assert result.get("efi_status") == "FAILED"


def test_database_has_q556():
    profs = load_all_profiles()
    assert "fujitsu_q556_2" in profs
