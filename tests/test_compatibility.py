"""Test Compatibility Engine."""

from compatibility import CompatibilityEngine, OverallStatus
from database import load_all_profiles
from hardware.identification import HardwareIdentity


def _engine():
    return CompatibilityEngine(load_all_profiles())


def test_q556_compatible():
    identity = HardwareIdentity(
        manufacturer="Fujitsu",
        model="Esprimo Q556/2",
        board="D3403-U",
        cpu="Intel Core i5-6500T",
        gpu="Intel HD Graphics 530",
        gpu_id="8086:1912",
        audio="Realtek ALC671",
        ethernet="Realtek RTL8111",
        ethernet_id="10ec:8168",
    )
    result = _engine().analyze(identity=identity)
    assert result.profile is not None
    # Verificato dal creatore; se tutti i campi coincidono -> compatible (o unknown solo se non testato)
    assert result.overall == OverallStatus.COMPATIBLE
    assert all(c.status.value != "unknown" or c.optional for c in result.components)


def test_unknown_never_compatible():
    identity = HardwareIdentity(manufacturer="Unknown", model="Unknown", board="Unknown", cpu="Unknown")
    result = _engine().analyze(identity=identity)
    assert result.overall != OverallStatus.COMPATIBLE


def test_partial_on_mismatch():
    identity = HardwareIdentity(
        manufacturer="Fujitsu",
        model="Esprimo Q556/2",
        board="D3403-U",
        cpu="Intel Core i5-6500T",
        gpu="Intel HD Graphics 530",
        gpu_id="8086:1912",
        audio="Some Different Audio",
        ethernet="Realtek RTL8111",
        ethernet_id="10ec:8168",
    )
    result = _engine().analyze(identity=identity)
    # Presenta almeno un partial o unknown, MAI compatible se c'e' mismatch
    assert result.overall != OverallStatus.COMPATIBLE
