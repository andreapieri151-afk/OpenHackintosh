"""Test della fase Hardware Detection / Identification / Diagnosis.

Usa SOLO fixture hardware sintetiche (mai spacciate per hardware reale).
Copre: detection completa/parziale/sconosciuta, snapshot, match
(EXACT/CLOSE/PARTIAL/NO), component unknown, compatibility result,
Q556/2, JSON e gestione errori.
"""

from hardware import (
    HardwareInfo,
    detected,
    deduced,
    unknown,
    not_available,
    capture,
    STATUS_DETECTED,
    STATUS_INFERRED,
    STATUS_NOT_DETECTED,
    STATUS_NOT_AVAILABLE,
)
from hardware.identification import identify
from hardware.detection import _infer_cpu_generation, detect_all
from hardware.identification import HardwareIdentity
from database import (
    load_all_profiles, match_profile,
    MATCH_EXACT, MATCH_NONE, MATCH_PARTIAL,
)
from cli.commands.diagnose import build_diagnosis_payload


def _q556_info() -> HardwareInfo:
    """Hardware sintetico che riproduce il profilo Q556/2 (dati di test, non reali)."""
    return HardwareInfo(
        platform={
            "system": detected("Linux"),
            "uefi_mode": deduced("UEFI"),
        },
        dmi={
            "system_vendor": detected("Fujitsu"),
            "product_name": detected("ESPRIMO Q556/2"),
            "product_version": unknown(),
            "board_vendor": detected("Fujitsu"),
            "board_name": detected("D3403-U"),
            "board_version": unknown(),
            "bios_vendor": detected("American Megatrends"),
            "bios_version": detected("V1.0"),
            "bios_date": detected("01/01/2020"),
        },
        cpu={
            "model": detected("Intel Core i5-6500T"),
            "vendor": detected("GenuineIntel"),
            "architecture": detected("x86_64"),
            "generation": deduced("Skylake (6th Gen)"),
            "cores": detected("4"),
            "threads": detected("4"),
        },
        gpu={
            "gpu": detected("Intel Corporation HD Graphics 530 [8086:1912]"),
            "gpu_id": detected("8086:1912"),
            "gpu_vendor": detected("Intel"),
            "gpu_model": detected("Intel Corporation HD Graphics 530"),
            "gpu_vendor_id": detected("8086"),
            "gpu_device_id": detected("1912"),
            "gpu_pci": detected("00:02.0"),
            "gpu_type": deduced("integrated"),
            "gpu_vram": unknown(),
        },
        audio={
            "audio": detected("Realtek ALC671 [10ec:0267]"),
            "audio_id": detected("10ec:0267"),
            "audio_vendor": detected("Realtek"),
            "audio_model": detected("Realtek ALC671"),
            "audio_vendor_id": detected("10ec"),
            "audio_device_id": detected("0267"),
            "audio_pci": detected("00:1f.3"),
        },
        ethernet={
            "ethernet": detected("Realtek RTL8111/8168 PCIe [10ec:8168]"),
            "ethernet_id": detected("10ec:8168"),
            "ethernet_vendor": detected("Realtek"),
            "ethernet_model": detected("Realtek RTL8111/8168 PCIe"),
            "ethernet_vendor_id": detected("10ec"),
            "ethernet_device_id": detected("8168"),
            "ethernet_pci": detected("00:1f.6"),
        },
        storage={
            "storage": detected("sda (128 GB)"),
            "sata_controllers": detected("Intel H110 SATA [8086:a102]"),
            "nvme_controllers": unknown(),
        },
        acpi={
            "acpi_table_list": detected(["DSDT", "FACP", "SSDT"]),
            "dsdt_present": detected("present"),
        },
    )


def _unknown_info() -> HardwareInfo:
    return HardwareInfo()


def test_detected_value_status_semantics():
    assert detected("x").to_dict()["status"] == STATUS_DETECTED
    assert deduced("y").to_dict()["status"] == STATUS_INFERRED
    assert unknown().to_dict()["value"] is None
    assert unknown().to_dict()["status"] == STATUS_NOT_DETECTED
    na = not_available("not available")
    assert na.to_dict()["status"] == STATUS_NOT_AVAILABLE
    assert na.to_dict()["value"] == "not available"


def test_cpu_generation_inference_safe():
    assert _infer_cpu_generation("Intel Core i5-6500T") == "Skylake (6th Gen)"
    assert _infer_cpu_generation("Intel Core i5-7500T") == "Kaby Lake (7th Gen)"
    assert _infer_cpu_generation("AMD Ryzen 9") == ""


def test_snapshot_exact_q556():
    snap = capture(info=_q556_info(), profiles=load_all_profiles())
    assert snap.match_type == MATCH_EXACT
    assert snap.profile is not None
    assert snap.profile.id == "fujitsu_q556_2"
    assert snap.result is not None


def test_snapshot_no_match_unknown():
    snap = capture(info=_unknown_info(), profiles=load_all_profiles())
    assert snap.match_type == MATCH_NONE
    assert snap.profile is None
    assert snap.result.profile is None


def test_diagnosis_payload_unknown_is_null_not_invented():
    snap = capture(info=_unknown_info(), profiles=load_all_profiles())
    payload = build_diagnosis_payload(snap)
    assert payload["system"]["manufacturer"]["value"] is None
    assert payload["system"]["manufacturer"]["status"] == "NOT_DETECTED"
    assert payload["compatibility"]["status"] in ("unknown", "partial", "unsupported")
    wifi = [c for c in payload["compatibility"]["components"] if c["name"] == "Wi-Fi"][0]
    assert wifi["status"] == "unknown"
    assert "Hardware not detected" in wifi["evidence"]
    assert "incompatible" not in wifi["status"]


def test_diagnosis_payload_q556_evidence():
    snap = capture(info=_q556_info(), profiles=load_all_profiles())
    payload = build_diagnosis_payload(snap)
    components = {c["name"]: c for c in payload["compatibility"]["components"]}
    assert components["GPU"]["status"] == "ok"
    assert components["GPU"]["evidence"]
    assert any("Database" in e for e in components["GPU"]["evidence"])
    assert payload["database"]["match"] == "EXACT_MATCH"


def test_match_profile_close_and_none():
    profiles = load_all_profiles()
    close = capture(info=_q556_info(), profiles=profiles)
    assert close.match_type in ("EXACT_MATCH", "CLOSE_MATCH")

    none_identity = HardwareIdentity(
        manufacturer="Asus",
        model="CustomBoard999",
        board="Z999",
        cpu="AMD Ryzen 9",
    )
    none = match_profile(none_identity, profiles)
    assert none.match_type == MATCH_NONE


def test_partial_match_weak_evidence_never_exact():
    partial_identity = HardwareIdentity(
        manufacturer="Fujitsu",
        model="Unknown / Not detected",
        board="Unknown / Not detected",
        cpu="Unknown / Not detected",
    )
    result = match_profile(partial_identity, load_all_profiles())
    assert result.profile is None
    assert result.score < 2
    assert result.match_type == MATCH_PARTIAL


def test_error_handling_one_section_failure_continues(monkeypatch):
    import hardware.detection as hw

    def boom():
        raise RuntimeError("simulated gpu detection failure")

    monkeypatch.setattr(hw, "detect_gpu", boom)
    info = detect_all()
    # La diagnosi non si ferma: cpu esiste, gpu risulta non rilevata e l'errore è tracciato.
    assert info.cpu
    assert info.gpu
    assert any("gpu" in e for e in info.detection_errors)


def test_identify_normalizes_unknown():
    identity = identify(_unknown_info())
    assert identity.manufacturer == "Unknown / Not detected"
    assert identity.cpu == "Unknown / Not detected"


def test_unknown_component_never_become_verified():
    snap = capture(info=_unknown_info(), profiles=load_all_profiles())
    assert snap.result.overall.value != "compatible"
