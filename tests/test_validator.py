"""Test EFI validator: 0-byte, placeholder, missing, config consistency."""

import plistlib
from pathlib import Path

from efi_builder.validator import validate_efi


def _make_efi(tmp_path: Path, with_empty_aml=False, with_missing_kext=False) -> Path:
    efi = tmp_path / "EFI"
    (efi / "BOOT").mkdir(parents=True)
    (efi / "OC" / "Kexts").mkdir(parents=True)
    (efi / "OC" / "Drivers").mkdir(parents=True)
    (efi / "OC" / "ACPI").mkdir(parents=True)

    (efi / "BOOT" / "BOOTx64.efi").write_bytes(b"\x00" * 200)
    (efi / "OC" / "OpenCore.efi").write_bytes(b"\x00" * 200)

    # config con kext fantasma + AML fantasma
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
    else:
        (efi / "OC" / "ACPI" / "SSDT-PLUG.aml").write_bytes(b"\x00" * 500)

    if not with_missing_kext:
        lilu = efi / "OC" / "Kexts" / "Lilu.kext" / "Contents"
        (lilu / "MacOS").mkdir(parents=True)
        with open(lilu / "Info.plist", "wb") as f:
            plistlib.dump({"CFBundleIdentifier": "as.vit9696.Lilu", "CFBundleExecutable": "Lilu"}, f)
        (lilu / "MacOS" / "Lilu").write_bytes(b"\x00" * 200)

    # Driver presente
    (efi / "OC" / "Drivers" / "HfsPlus.efi").write_bytes(b"\x00" * 200)
    return efi


def test_valid_efi_ready(tmp_path):
    efi = _make_efi(tmp_path)
    res = validate_efi(efi)
    assert res["ready"] is True
    assert res["valid"] is True


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
    (efi / "BOOT" / "BOOTx64.efi").write_bytes(b"\x00" * 200)
    res = validate_efi(efi)
    assert res["valid"] is False
    assert res["ready"] is False
