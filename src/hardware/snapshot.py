"""HardwareSnapshot: raccoglie una sola volta i dati di detection e li passa
a database matching e compatibility engine.

Questo NON è un secondo sistema di rilevamento: è solo il contenitore
immutabile condiviso tra i moduli per evitare ridondanza e mantenere
coerenza tra detection, matching e diagnosi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from hardware.detection import HardwareInfo
from hardware.identification import HardwareIdentity, identify
from database import HardwareProfile, MatchResult, load_all_profiles, match_profile
from compatibility.engine import CompatibilityEngine
from compatibility.rules import CompatibilityResult


@dataclass
class HardwareSnapshot:
    info: HardwareInfo
    identity: HardwareIdentity
    profiles: Dict[str, HardwareProfile] = field(default_factory=dict)
    match: Optional[MatchResult] = None
    result: Optional[CompatibilityResult] = None

    @property
    def profile(self) -> Optional[HardwareProfile]:
        return self.result.profile if self.result else None

    @property
    def match_type(self) -> str:
        return self.match.match_type if self.match else "NO_MATCH"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hardware": self.info.to_dict(),
            "identity": self.identity.to_dict(),
            "match": self.match.to_dict() if self.match else {"match_type": "NO_MATCH"},
            "profile": self.profile.to_dict() if self.profile else None,
            "compatibility": self.result.to_dict() if self.result else None,
        }


def capture(info: Optional[HardwareInfo] = None,
            profiles: Optional[Dict[str, HardwareProfile]] = None) -> HardwareSnapshot:
    """Rileva (o riceve una detection già fatta) e costruisce lo snapshot in un solo passaggio."""
    if info is None:
        from hardware.detection import detect_all
        info = detect_all()
    identity = identify(info)
    profiles = profiles if profiles is not None else load_all_profiles()
    match = match_profile(identity, profiles)
    engine = CompatibilityEngine(profiles)
    result = engine.evaluate_match(identity, match)
    return HardwareSnapshot(info=info, identity=identity, profiles=profiles,
                            match=match, result=result)


def detect_and_capture(profiles: Optional[Dict[str, HardwareProfile]] = None) -> HardwareSnapshot:
    from hardware.detection import detect_all
    return capture(info=detect_all(), profiles=profiles)
