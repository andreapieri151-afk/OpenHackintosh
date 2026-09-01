"""Test di riferimento per Fujitsu Esprimo Q556/2."""

from database import get_profile, match_profile, load_all_profiles
from compatibility import CompatibilityEngine
from hardware.identification import HardwareIdentity


def test_q556_reference_profile_full():
    prof = get_profile("fujitsu_q556_2")
    assert prof is not None
    assert prof.state == "VERIFIED"
    assert prof.manufacturer == "Fujitsu"
    assert "RealtekRTL8111" in prof.required_kexts
    assert prof.required_drivers == ["HfsPlus", "OpenRuntime"]
    assert "SSDT-PLUG-DRTNIA" in prof.required_ssdts
    assert "SSDT-EC-USBX-DESKTOP" in prof.required_ssdts
    assert "SSDT-AWAC" not in prof.required_ssdts
    assert "SSDT-RHUB" not in prof.required_ssdts


def test_q556_reference_compatibility():
    identity = HardwareIdentity(
        manufacturer="Fujitsu",
        model="Esprimo Q556/2",
        board="D3403-U",
        cpu="Intel Core i5-6500T",
        gpu="Intel HD Graphics 530",
        gpu_id="8086:1912",
        audio="Realtek ALC671",
        audio_id="10ec:0267",
        ethernet="Realtek RTL8111",
        ethernet_id="10ec:8168",
    )
    prof = get_profile("fujitsu_q556_2")
    result = CompatibilityEngine({prof.id: prof}).analyze(identity=identity)
    assert result.profile.id == "fujitsu_q556_2"
    assert result.overall.value == "compatible"
