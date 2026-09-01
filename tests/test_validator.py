"""Test EFI validator: 0-byte, placeholder, missing, config consistency, binari reali vs fake."""

import plistlib
import struct
from pathlib import Path

from efi_builder.validator import validate_efi


def _pe_bytes() -> bytes:
    """Header PE/COFF minimale per i test del validator (non descrive un bootloader reale)."""
    e_lfanew = 0x40
    data = bytearray(e_lfanew + 8)
    data[0:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, e_lfanew)
    data[e_lfanew:e_lfanew + 4] = b"PE\x00\x00"
    return bytes(data) + b"\x00" * 200


def _macho_bytes() -> bytes:
    return b"\xcf\xfa\xed\xfe" + b"\x00" * 200


def _aml_bytes() -> bytes:
    return b"SSDT" + b"\x00" * 500


def _make_efi(tmp_path: Path, with_empty_aml=False, with_missing_kext=False,
              fake_binaries=False, fake_aml=False, fake_kext=False) -> Path:
    efi = tmp_path / "EFI"
    (efi / "BOOT").mkdir(parents=True)
    (efi / "OC" / "Kexts").mkdir(parents=True)
    (efi / "OC" / "Drivers").mkdir(parents=True)
    (efi / "OC" / "ACPI").mkdir(parents=True)

    boot = b"\x00" * 200 if fake_binaries else _pe_bytes()
    (efi / "BOOT" / "BOOTx64.efi").write_bytes(boot)
    (efi / "OC" / "OpenCore.efi").write_bytes(boot)

    config = {
        "ACPI": {"Add": [{"Path": "SSDT-PLUG.aml", "Enabled": True}]},
        "Kernel": {"Add": [{"BundlePath": "Lilu.kext", "ExecutablePath": "Contents/MacOS/Lilu", "Enabled": True}]},
        "UEFI": {"Drivers": [{"Path": "HfsPlus.efi", "Enabled": True}]},
        "PlatformInfo": {"Generic": {"SystemSerialNumber": "C02TEST12345"}},
    }
    with open(efi / "OC" / "config.plist", "wb") as f:
        plistlib.dump(config, f)

    if with_empty_aml:
        (efi / "OC" / "ACPI" / "SSDT-PLUG.aml").write_bytes(b"")
    elif fake_aml:
        (efi / "OC" / "ACPI" / "SSDT-PLUG.aml").write_bytes(b"FAKE AML CONTENT" * 40)
    else:
        (efi / "OC" / "ACPI" / "SSDT-PLUG.aml").write_bytes(_aml_bytes())

    if not with_missing_kext:
        lilu = efi / "OC" / "Kexts" / "Lilu.kext" / "Contents"
        (lilu / "MacOS").mkdir(parents=True)
        with open(lilu / "Info.plist", "wb") as f:
            plistlib.dump({"CFBundleIdentifier": "as.vit9696.Lilu", "CFBundleExecutable": "Lilu"}, f)
        exec_bytes = b"\x00" * 200 if fake_kext else _macho_bytes()
        (lilu / "MacOS" / "Lilu").write_bytes(exec_bytes)

    (efi / "OC" / "Drivers" / "HfsPlus.efi").write_bytes(boot)
    return efi


def test_valid_efi_ready(tmp_path):
    efi = _make_efi(tmp_path)
    res = validate_efi(efi)
    assert res["ready"] is True
    assert res["valid"] is True


def test_fake_binary_not_ready(tmp_path):
    efi = _make_efi(tmp_path, fake_binaries=True)
    res = validate_efi(efi)
    assert res["ready"] is False
    assert res["states"]["INVALID"] >= 1


def test_fake_aml_not_ready(tmp_path):
    efi = _make_efi(tmp_path, fake_aml=True)
    res = validate_efi(efi)
    assert res["ready"] is False
    assert res["states"]["INVALID"] >= 1


def test_fake_kext_not_ready(tmp_path):
    efi = _make_efi(tmp_path, fake_kext=True)
    res = validate_efi(efi)
    assert res["ready"] is False
    assert res["states"]["INVALID"] >= 1


def test_empty_aml_not_ready(tmp_path):
    efi = _make_efi(tmp_path, with_empty_aml=True)
    res = validate_efi(efi)
    assert res["ready"] is False
    assert res["states"]["PLACEHOLDER"] >= 1


def test_missing_kext_not_ready(tmp_path):
    efi = _make_efi(tmp_path, with_missing_kext=True)
    res = validate_efi(efi)
    assert res["ready"] is False
    assert res["states"]["MISSING"] >= 1


def test_missing_config_file(tmp_path):
    efi = tmp_path / "EFI2"
    (efi / "BOOT").mkdir(parents=True)
    (efi / "OC").mkdir(parents=True)
    (efi / "BOOT" / "BOOTx64.efi").write_bytes(_pe_bytes())
    res = validate_efi(efi)
    assert res["valid"] is False
    assert res["ready"] is False
