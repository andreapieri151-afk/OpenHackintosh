"""
Compatibility Engine: orchestrazione.

Hardware -> Detection -> Matcher -> Database -> CompatibilityResult.

NON e' un AI: e' deterministico, basato su database e regole.
"""

from __future__ import annotations

from typing import Dict, Optional

from hardware.detection import HardwareInfo
from hardware.identification import HardwareIdentity, identify
from database import HardwareProfile, MatchResult, load_all_profiles, match_profile
from .rules import CompatibilityResult, evaluate


class CompatibilityEngine:
    def __init__(self, profiles: Optional[Dict[str, HardwareProfile]] = None):
        self.profiles = profiles if profiles is not None else load_all_profiles()

    def identify(self, info: HardwareInfo) -> HardwareIdentity:
        return identify(info)

    def match(self, identity: HardwareIdentity) -> MatchResult:
        return match_profile(identity, self.profiles)

    def analyze(self, identity: Optional[HardwareIdentity] = None,
                info: Optional[HardwareInfo] = None) -> CompatibilityResult:
        if info is not None:
            identity = identity or identify(info)
        if identity is None:
            raise ValueError("identity o info richiesto")

        match = self.match(identity)
        return evaluate(identity, match.profile, match)

    def analyze_hardware(self, info: HardwareInfo) -> CompatibilityResult:
        return self.analyze(info=info)

    def add_profile(self, profile: HardwareProfile) -> None:
        self.profiles[profile.id] = profile
