"""Test matching hardware <-> database."""

from database import load_all_profiles, match_profile
from hardware.identification import HardwareIdentity


def _q556_identity():
    return HardwareIdentity(
        manufacturer="Fujitsu",
        model="Esprimo Q556/2",
        board="D3403-U",
        board_vendor="Fujitsu",
        cpu="Intel Core i5-6500T",
        gpu="Intel Corporation HD Graphics 530",
        gpu_id="8086:1912",
        audio="Realtek ALC671",
        audio_id="10ec:0267",
        ethernet="Realtek RTL8111",
        ethernet_id="10ec:8168",
    )


def test_match_q556():
    profiles = load_all_profiles()
    result = match_profile(_q556_identity(), profiles)
    assert result.profile is not None
    assert result.profile.id == "fujitsu_q556_2"
    assert result.score >= 2


def test_match_q957():
    profiles = load_all_profiles()
    identity = HardwareIdentity(
        manufacturer="Fujitsu",
        model="Esprimo Q957",
        board="D3403-U2",
        cpu="Intel Core i5-7500T",
        gpu="Intel HD Graphics 630",
        gpu_id="8086:5912",
        ethernet="Intel I219-LM",
        ethernet_id="8086:15b8",
    )
    result = match_profile(identity, profiles)
    assert result.profile is not None
    assert result.profile.id == "fujitsu_q957"
    assert result.score >= 2


def test_match_unknown_returns_none():
    profiles = load_all_profiles()
    identity = HardwareIdentity(
        manufacturer="Asus",
        model="CustomBoard999",
        board="Z999",
        cpu="AMD Ryzen 9",
    )
    result = match_profile(identity, profiles)
    assert result.profile is None or result.score < 2
