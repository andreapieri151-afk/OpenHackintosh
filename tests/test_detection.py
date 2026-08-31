"""Test detection: mai eccezioni, mai inventare componenti."""

from datetime import date

from hardware import detect_all, HardwareInfo, UNKNOWN, unknown, detected
from hardware.detection import parse_lspci
from hardware.identification import identify


def test_detect_all_no_throw():
    info = detect_all()
    assert isinstance(info, HardwareInfo)
    assert isinstance(info.to_dict(), dict)


def test_detect_does_not_invent():
    info = detect_all()
    # Ogni valore deve essere valido; se non rilevato -> value=None + status NOT_DETECTED.
    allowed_status = ("DETECTED", "INFERRED", "DATABASE_MATCH", "NOT_DETECTED",
                      "UNKNOWN", "NOT_AVAILABLE_ON_PLATFORM")
    allowed_source = ("detected", "deduced", "database", "unknown", "platform")
    for section in info.to_dict().values():
        for val in section.values():
            if val.get("status") == "NOT_DETECTED":
                assert val.get("value") is None
            else:
                assert isinstance(val.get("value"), (str, int, list))
                assert val.get("value") != ""
            assert val.get("status") in allowed_status
            assert val.get("source") in allowed_source


def test_parse_lspci():
    sample = (
        "00:02.0 VGA compatible controller [0300]: Intel Corporation HD Graphics 530 [8086:1912] (rev 06)\n"
        "00:1f.6 Ethernet controller [0200]: Realtek Semiconductor Co., Ltd. RTL8111/8168/8411 PCI Express Gigabit Ethernet Controller [10ec:8168] (rev 0c)\n"
    )
    devices = parse_lspci(sample)
    assert len(devices) == 2
    assert devices[0]["id"] == "8086:1912"
    assert devices[1]["id"] == "10ec:8168"


def test_identity_unknowns_are_strings():
    info = HardwareInfo()
    identity = identify(info)
    assert identity.model == UNKNOWN
    assert identity.cpu == UNKNOWN
