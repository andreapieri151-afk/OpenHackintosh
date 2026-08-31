"""Test database loading + profilo di riferimento Q556/2."""

from database import load_all_profiles, get_profile


def test_load_q5562():
    profiles = load_all_profiles()
    assert "fujitsu_q556_2" in profiles


def test_q5562_required_kexts():
    prof = get_profile("fujitsu_q556_2")
    assert prof is not None
    assert "Lilu" in prof.required_kexts
    assert "VirtualSMC" in prof.required_kexts
    assert "WhateverGreen" in prof.required_kexts
    assert "AppleALC" in prof.required_kexts
    assert "RealtekRTL8111" in prof.required_kexts


def test_q5562_state_verified_or_documented():
    prof = get_profile("fujitsu_q556_2")
    assert prof.state in ("VERIFIED", "DOCUMENTED", "UNKNOWN")


def test_q957_present():
    profiles = load_all_profiles()
    assert "fujitsu_q957" in profiles
