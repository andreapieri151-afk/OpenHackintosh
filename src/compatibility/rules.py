"""
Regole di compatibilita'. Sono deterministiche e basate su:
- profilo database;
- hardware rilevato;
- Hardware ID documentati;
- stato di verifica del profilo.

Non inventa mai compatibilita': in caso di dati insufficienti -> UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

from hardware.detection import UNKNOWN
from hardware.identification import HardwareIdentity
from database.loader import HardwareProfile
from database.matcher import MatchResult


class ComponentStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"
    MISSING = "missing"


class OverallStatus(str, Enum):
    COMPATIBLE = "compatible"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


STATUS_ICON = {
    OverallStatus.COMPATIBLE: "green",
    OverallStatus.PARTIAL: "yellow",
    OverallStatus.UNSUPPORTED: "red",
    OverallStatus.UNKNOWN: "gray",
}


@dataclass
class ComponentAssessment:
    name: str
    detected: str = UNKNOWN
    expected: str = ""
    status: ComponentStatus = ComponentStatus.UNKNOWN
    detail: str = ""
    optional: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CompatibilityResult:
    profile: Optional[HardwareProfile] = None
    match: Optional[MatchResult] = None
    overall: OverallStatus = OverallStatus.UNKNOWN
    components: List[ComponentAssessment] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    unknown_components: List[str] = field(default_factory=list)

    @property
    def requires_hardware_testing(self) -> bool:
        return bool(self.profile and self.profile.requires_hardware_testing)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile.to_dict() if self.profile else None,
            "matching": {
                "score": self.match.score if self.match else 0,
                "matched_fields": self.match.matched_fields if self.match else [],
                "reasons": self.match.reasons if self.match else [],
            },
            "overall": self.overall.value,
            "status_icon": STATUS_ICON[self.overall],
            "components": [c.to_dict() for c in self.components],
            "notes": self.notes,
            "unknown_components": self.unknown_components,
            "requires_hardware_testing": bool(self.profile and self.profile.requires_hardware_testing),
        }


def _has(actual: str) -> bool:
    return bool(actual) and actual.lower() not in (UNKNOWN.lower(), "unknown / not detected")


def _cpu_matches(expected: str, detected: str) -> bool:
    """Rule basata sulla generazione, non su text matching generico."""
    if not _has(detected) or not expected:
        return False
    expected_l = expected.lower()
    detected_l = detected.lower()
    if "skylake" in expected_l and "skylake" in detected_l:
        return True
    if "kaby" in expected_l and "kaby" in detected_l:
        return True
    # Inferenza limitata dal model number reale rilevato: 6xxx -> Skylake, 7xxx -> Kaby
    import re
    match = re.search(r"\b(\d{4})\w*\b", detected)
    if match:
        family = match.group(1)[0]
        if family == "6" and "6" in expected_l:
            return True
        if family == "7" and "7" in expected_l:
            return True
    return False


def assess_component(name: str, detected_value: str, expected: str) -> ComponentAssessment:
    if not _has(detected_value):
        return ComponentAssessment(
            name=name,
            detected=UNKNOWN,
            expected=expected,
            status=ComponentStatus.UNKNOWN,
            detail="Non rilevato. Require real hardware testing.",
        )
    if not expected:
        return ComponentAssessment(
            name=name,
            detected=detected_value,
            expected=expected,
            status=ComponentStatus.OK,
            detail="Rilevato, profilo non specifica dettagli.",
        )
    found = detected_value.lower()
    exp = expected.lower()
    if exp in found or found in exp or all(word in found for word in exp.split()):
        return ComponentAssessment(
            name=name,
            detected=detected_value,
            expected=expected,
            status=ComponentStatus.OK,
            detail="Il componente rientra nel profilo.",
        )
    return ComponentAssessment(
        name=name,
        detected=detected_value,
        expected=expected,
        status=ComponentStatus.PARTIAL,
        detail="Presente ma non esattamente atteso dal profilo.",
    )


def evaluate(identity: HardwareIdentity, profile: Optional[HardwareProfile],
             match: Optional[MatchResult]) -> CompatibilityResult:
    components: List[ComponentAssessment] = []

    cpu_expected = get_profile_cpu(profile)
    if cpu_expected and _cpu_matches(cpu_expected, identity.cpu):
        components.append(ComponentAssessment(
            name="CPU",
            detected=identity.cpu,
            expected=cpu_expected,
            status=ComponentStatus.OK,
            detail="CPU coerente con la generazione attesa dal profilo.",
        ))
    else:
        components.append(assess_component("CPU", identity.cpu, cpu_expected))
    components.append(assess_component("GPU", identity.gpu, get_profile_gpu(profile)))
    components.append(assess_component("Audio", identity.audio, get_profile_audio(profile)))
    components.append(assess_component("Ethernet", identity.ethernet, get_profile_ethernet(profile)))
    wifi_assessment = assess_component("Wi-Fi", identity.wifi, get_profile_wifi(profile))
    wifi_assessment.optional = True
    components.append(wifi_assessment)

    unknown_components = [c.name for c in components
                          if c.status == ComponentStatus.UNKNOWN and not c.optional]
    partial = [c for c in components
               if c.status == ComponentStatus.PARTIAL and not c.optional]
    optional_unknown = [c.name for c in components
                        if c.status == ComponentStatus.UNKNOWN and c.optional]

    notes: List[str] = []
    if not profile:
        notes.append("Nessun profilo corrispondente. Non e' possibile affermare nessuna compatibilita'.")
        overall = OverallStatus.UNKNOWN
    elif profile.state == "UNSUPPORTED":
        notes.append("Profilo marcato UNSUPPORTED. Non procedere con la generazione.")
        overall = OverallStatus.UNSUPPORTED
    elif profile.state == "UNKNOWN":
        notes.append("Profilo con stato UNKNOWN. Richiede verifica su hardware reale.")
        overall = OverallStatus.UNKNOWN
    else:
        if partial:
            overall = OverallStatus.PARTIAL
            notes.append("Alcuni componenti differiscono dal profilo: compatibilita' parziale.")
        elif unknown_components:
            overall = OverallStatus.PARTIAL
            notes.append("Alcuni componenti obbligatori non rilevati: compatibilita' parziale.")
        else:
            overall = OverallStatus.COMPATIBLE
            notes.append("Hardware coerente con il profilo selezionato.")

        if profile.requires_hardware_testing:
            notes.append("Il profilo non e' VERIFIED: richiede test su hardware reale.")
            if overall == OverallStatus.COMPATIBLE:
                overall = OverallStatus.UNKNOWN

    if unknown_components:
        notes.append(
            "Componenti obbligatori non rilevati: " + ", ".join(unknown_components) +
            ". Non considerare il risultato definitivo senza dati reali."
        )
    if optional_unknown:
        notes.append(
            "Componenti opzionali non rilevati (non influenzano il verdetto): "
            + ", ".join(optional_unknown)
        )

    return CompatibilityResult(
        profile=profile,
        match=match,
        overall=overall,
        components=components,
        notes=notes,
        unknown_components=unknown_components + optional_unknown,
    )


def get_profile_cpu(profile: Optional[HardwareProfile]) -> str:
    if not profile:
        return ""
    gens = profile.cpu.get("generations", [])
    return ", ".join(gens) if gens else ""


def get_profile_gpu(profile: Optional[HardwareProfile]) -> str:
    if not profile:
        return ""
    return str(profile.gpu.get("igpu", ""))


def get_profile_audio(profile: Optional[HardwareProfile]) -> str:
    if not profile:
        return ""
    return str(profile.audio.get("codec", ""))


def get_profile_ethernet(profile: Optional[HardwareProfile]) -> str:
    if not profile:
        return ""
    return str(profile.ethernet.get("chip", ""))


def get_profile_wifi(profile: Optional[HardwareProfile]) -> str:
    if not profile:
        return ""
    return str(profile.wifi.get("hardware", ""))
