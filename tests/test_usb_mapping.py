"""
USB mapping automatico (2.0.2): model, detection sysfs, builder inject-kext,
validazione inject-kext e integrazione end-to-end nel sources engine.
"""

from __future__ import annotations

import plistlib
from pathlib import Path

import pytest

from database import load_all_profiles
from efi.integrity import validate_inject_kext
from efi_builder.validator import _kext_state
from sources import InMemoryFetcher, load_manifest_for_profile, run_manifest_pipeline
from usb_mapping import (
    UsbController,
    UsbPort,
    build_usb_map_plist,
    detect_usb_controllers_linux,
    save_usb_map_kext,
)
from usb_mapping.detect import _pci_slot_from_address


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_controller(ports=6, pci_id="8086:a12f", slot="0:20:0"):
    return UsbController(
        pci_id=pci_id,
        pci_slot=slot,
        ports=[UsbPort(name=f"PRT{i:02d}", index=i) for i in range(1, ports + 1)],
    )


def build_fake_sysfs(root: Path, ports=6, pci_class="0x0c0330",
                     vendor="0x8086", device="0xa12f") -> Path:
    """Albero sysfs finto: un controller XHCI con root hub da N porti."""
    dev = root / "bus" / "pci" / "devices" / "0000:00:14.0"
    dev.mkdir(parents=True)
    (dev / "class").write_text(pci_class + "\n")
    (dev / "vendor").write_text(vendor + "\n")
    (dev / "device").write_text(device + "\n")

    hub = root / "devices" / "pci0000:00" / "0000:00:14.0" / "usb1" / "1-0:1.0"
    hub.mkdir(parents=True)
    for i in range(1, ports + 1):
        (hub / f"usb1-port{i}").mkdir()
    return root


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def test_controller_personality_format():
    ctrl = make_controller(ports=4)
    pers = ctrl.personality()
    assert pers["IOClass"] == "AppleUSBHostMergeProperties"
    assert pers["CFBundleIdentifier"] == "com.apple.driver.AppleUSBHostMergeProperties"
    assert pers["IOProviderClass"] == "AppleUSBXHCIPCI"
    assert pers["IOParentMatch"]["IOPropertyMatch"]["pcidebug"] == "0:20:0"

    merge = pers["IOProviderMergeProperties"]
    assert merge["port-count"] == (4).to_bytes(4, "little")
    assert set(merge["ports"]) == {"PRT01", "PRT02", "PRT03", "PRT04"}
    assert merge["ports"]["PRT01"]["port"] == (1).to_bytes(4, "little")
    assert merge["ports"]["PRT01"]["UsbConnector"] == 0


def test_controller_port_count_empty():
    ctrl = UsbController(pci_id="8086:a12f", pci_slot="0:20:0")
    assert ctrl.port_count == 0
    assert ctrl.personality()["IOProviderMergeProperties"]["port-count"] == b"\x00" * 4


def test_pci_slot_conversion():
    assert _pci_slot_from_address("0000:00:14.0") == "0:20:0"
    assert _pci_slot_from_address("0000:3a:00.1") == "58:0:1"


# ---------------------------------------------------------------------------
# Detection (sysfs finto)
# ---------------------------------------------------------------------------

def test_detect_xhci_with_ports(tmp_path):
    root = build_fake_sysfs(tmp_path / "sys", ports=6)
    controllers = detect_usb_controllers_linux(root)
    assert len(controllers) == 1
    ctrl = controllers[0]
    assert ctrl.pci_id == "8086:a12f"
    assert ctrl.pci_slot == "0:20:0"
    assert ctrl.port_count == 6
    assert all(p.status == "DETECTED" for p in ctrl.ports)


def test_detect_ignores_non_xhci(tmp_path):
    # EHCI (0x0c0320): non e' il controller che mappiamo
    build_fake_sysfs(tmp_path / "sys", ports=2, pci_class="0x0c0320")
    assert detect_usb_controllers_linux(tmp_path / "sys") == []


def test_detect_missing_sysfs(tmp_path):
    assert detect_usb_controllers_linux(tmp_path / "non_esiste") == []


def test_detect_controller_without_ports(tmp_path):
    root = build_fake_sysfs(tmp_path / "sys", ports=0)
    controllers = detect_usb_controllers_linux(root)
    assert len(controllers) == 1
    assert controllers[0].port_count == 0
    assert controllers[0].status == "DETECTED_NO_PORTS"


# ---------------------------------------------------------------------------
# Builder inject-kext
# ---------------------------------------------------------------------------

def test_build_usb_map_plist(tmp_path):
    plist = build_usb_map_plist([make_controller(ports=4)], "fujitsu_q556_2")
    assert plist["CFBundleIdentifier"] == "com.openhackintosh.usbmap.fujitsu_q556_2"
    assert plist["OSBundleRequired"] == "Root"
    assert len(plist["IOKitPersonalities"]) == 1
    assert plist["com.openhackintosh.status"] == "DRAFT"


def test_save_usb_map_kext_writes_valid_plist(tmp_path):
    bundle = tmp_path / "USBMap_Q5562.kext"
    info = save_usb_map_kext([make_controller(ports=6)], bundle, "fujitsu_q556_2")
    assert info == bundle / "Contents" / "Info.plist"
    with open(info, "rb") as fh:
        data = plistlib.load(fh)
    personality = next(iter(data["IOKitPersonalities"].values()))
    assert personality["IOProviderMergeProperties"]["port-count"] == (6).to_bytes(4, "little")
    # Un inject-kext non ha eseguibile: niente Contents/MacOS
    assert not (bundle / "Contents" / "MacOS").exists()


# ---------------------------------------------------------------------------
# Validazione inject-kext (NO file finti, ma kext senza binario legittimi)
# ---------------------------------------------------------------------------

def test_validate_inject_kext_ok(tmp_path):
    bundle = tmp_path / "USBMap.kext"
    save_usb_map_kext([make_controller(ports=2)], bundle, "test")
    res = validate_inject_kext(bundle)
    assert res.ok, res.reason


def test_validate_inject_kext_no_personalities(tmp_path):
    bundle = tmp_path / "Fake.kext" / "Contents"
    bundle.mkdir(parents=True)
    (bundle / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "x.y"}))
    res = validate_inject_kext(tmp_path / "Fake.kext")
    assert not res.ok
    assert res.reason == "NO_IOKIT_PERSONALITIES"


def test_validate_inject_kext_missing(tmp_path):
    res = validate_inject_kext(tmp_path / "Nope.kext")
    assert not res.ok and res.reason == "MISSING"


def test_validator_accepts_inject_kext(tmp_path):
    bundle = tmp_path / "USBMap.kext"
    save_usb_map_kext([make_controller(ports=2)], bundle, "test")
    assert _kext_state(bundle) == "REAL"


def test_validator_rejects_empty_bundle_as_invalid(tmp_path):
    bundle = tmp_path / "Vuoto.kext" / "Contents"
    bundle.mkdir(parents=True)
    (bundle / "Info.plist").write_text("non un plist" * 10)
    assert _kext_state(tmp_path / "Vuoto.kext") == "INVALID"


# ---------------------------------------------------------------------------
# Integrazione nel sources engine (end-to-end offline)
# ---------------------------------------------------------------------------

# Riusa i binari sintetici dalla suite pipeline.
from test_sources_pipeline import (  # noqa: E402
    make_aml,
    make_kext_zip,
    make_pe,
    make_zip,
)

OC_REPO = "acidanthera/OpenCorePkg"


def _register_real_manifest_sources(fetcher, manifest):
    big_oc_zip = make_zip({
        "X64/EFI/OC/OpenCore.efi": make_pe(60_000),
        "X64/EFI/BOOT/BOOTx64.efi": make_pe(60_000),
        "X64/EFI/OC/Drivers/HfsPlus.efi": make_pe(60_000),
        "X64/EFI/OC/Drivers/OpenRuntime.efi": make_pe(60_000),
    })
    for comp in manifest.components:
        src = comp.source
        if comp.kind == "efi_binary":
            fetcher.register_archive(src, big_oc_zip)
        elif comp.kind == "kext":
            bundle = comp.target.split("/")[-1]
            fetcher.register_archive(src, make_kext_zip(f"{bundle}-1.0-RELEASE", bundle))
        elif comp.kind == "aml":
            fetcher.register_bytes(src, make_aml())


def _profile():
    return load_all_profiles()["fujitsu_q556_2"]


def test_pipeline_generates_usb_map(tmp_path, monkeypatch):
    manifest = load_manifest_for_profile("fujitsu_q556_2")
    fetcher = InMemoryFetcher()
    _register_real_manifest_sources(fetcher, manifest)

    fake = [make_controller(ports=6)]
    monkeypatch.setattr("sources.pipeline.detect_usb_controllers", lambda: fake)

    out = tmp_path / "usb"
    result = run_manifest_pipeline(
        manifest=manifest, profile=_profile(), output_dir=out, fetcher=fetcher,
        include_usb_mapping=True, log=lambda m: None,
    )
    assert result["success"] is True, result.get("error")

    bundle = out / "EFI" / "OC" / "Kexts" / "USBMap_Q5562.kext"
    info = bundle / "Contents" / "Info.plist"
    assert info.exists()
    with open(info, "rb") as fh:
        data = plistlib.load(fh)
    personality = next(iter(data["IOKitPersonalities"].values()))
    assert personality["IOProviderMergeProperties"]["port-count"] == (6).to_bytes(4, "little")

    # La mappa deve finire in config.plist (Kernel/Add) e nello ZIP.
    with open(out / "EFI" / "OC" / "config.plist", "rb") as fh:
        config = plistlib.load(fh)
    bundles = {e["BundlePath"]: e for e in config["Kernel"]["Add"]}
    assert "USBMap_Q5562.kext" in bundles
    assert bundles["USBMap_Q5562.kext"]["ExecutablePath"] == ""  # inject-kext

    import zipfile
    with zipfile.ZipFile(out / "EFI_FUJITSU_Q556_2.zip") as zf:
        assert "EFI/OC/Kexts/USBMap_Q5562.kext/Contents/Info.plist" in zf.namelist()

    # Provenance ledger: componente usb_map presente con stato OK
    ids = {c["component_id"]: c for c in result["components"]}
    assert ids["usb_map"]["status"] == "OK"
    assert "6 porte rilevate" in ids["usb_map"]["source_url"]


def test_pipeline_without_usb_map_flag_skips_component(tmp_path, monkeypatch):
    manifest = load_manifest_for_profile("fujitsu_q556_2")
    fetcher = InMemoryFetcher()
    _register_real_manifest_sources(fetcher, manifest)

    monkeypatch.setattr("sources.pipeline.detect_usb_controllers",
                        lambda: [make_controller(ports=6)])

    out = tmp_path / "nousb"
    result = run_manifest_pipeline(
        manifest=manifest, profile=_profile(), output_dir=out, fetcher=fetcher,
        log=lambda m: None,
    )
    assert result["success"] is True
    ids = {c["component_id"] for c in result["components"]}
    assert "usb_map" not in ids
    assert not (out / "EFI" / "OC" / "Kexts" / "USBMap_Q5562.kext").exists()


def test_pipeline_no_xhci_detected_skips_usb_map(tmp_path, monkeypatch):
    """Nessun controller rilevabile -> componente scartato, EFI comunque VALID.
    La mappa USB non viene MAI inventata."""
    manifest = load_manifest_for_profile("fujitsu_q556_2")
    fetcher = InMemoryFetcher()
    _register_real_manifest_sources(fetcher, manifest)

    monkeypatch.setattr("sources.pipeline.detect_usb_controllers", lambda: [])

    out = tmp_path / "noxhci"
    result = run_manifest_pipeline(
        manifest=manifest, profile=_profile(), output_dir=out, fetcher=fetcher,
        include_usb_mapping=True, log=lambda m: None,
    )
    assert result["success"] is True
    assert result["efi_status"] == "VALID"
    ids = {c["component_id"]: c for c in result["components"]}
    assert ids["usb_map"]["status"] == "SKIPPED"
    assert "mai inventata" in ids["usb_map"]["reason"]
    assert not (out / "EFI" / "OC" / "Kexts" / "USBMap_Q5562.kext").exists()


def test_cli_generate_accepts_usb_map_flag():
    from cli.main import build_parser

    parser = build_parser()
    args = parser.parse_args(["generate", "--usb-map", "--engine", "manifest"])
    assert args.usb_map is True
    args2 = parser.parse_args(["generate"])
    assert args2.usb_map is False
