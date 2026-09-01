"""
Matching hardware rilevato <-> profilo database.

E' un matcher deterministico basato su regole + Hardware ID. Non usa mai
inferenze da testo libero per affermare una compatibilita'.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import re
from hardware.detection import UNKNOWN
from hardware.identification import HardwareIdentity
from database.loader import HardwareProfile


MATCH_EXACT = "EXACT_MATCH"
MATCH_CLOSE = "CLOSE_MATCH"
MATCH_PARTIAL = "PARTIAL_MATCH"
MATCH_NONE = "NO_MATCH"


@dataclass
class MatchResult:
    profile: Optional[HardwareProfile]
    score: int
    matched_fields: List[str] = None
    reasons: List[str] = None

    def __init__(self, profile: Optional[HardwareProfile], score: int,
                 matched_fields: Optional[List[str]] = None,
                 reasons: Optional[List[str]] = None):
        self.profile = profile
        self.score = score
        self.matched_fields = matched_fields or []
        self.reasons = reasons or []

    @property
    def matched(self) -> bool:
        return self.profile is not None and self.score >= MIN_SCORE

    @property
    def match_type(self) -> str:
        """Classificazione del match: EXACT/CLOSE/PARTIAL/NO_MATCH.

        Non e' inventata: deriva da campi realmente matchati e score.
        PARTIAL = evidenza debole (vendor/cpu/famiglia) ma non abbastanza per
        selezionare il profilo. NO_MATCH = nessuna evidenza.
        """
        if not self.profile:
            return MATCH_PARTIAL if self.score > 0 else MATCH_NONE
        fields = set(self.matched_fields)
        # Corrispondenza esatta su modello/board della macchina rilevata.
        if "model" in fields or "board" in fields:
            if self.score >= 3 or ("model" in fields and "board" in fields):
                return MATCH_EXACT
            if "board" in fields or "model" in fields:
                return MATCH_CLOSE
        if self.score >= MIN_SCORE:
            return MATCH_CLOSE
        if self.score > 0:
            return MATCH_PARTIAL
        return MATCH_NONE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matched": self.matched,
            "match_type": self.match_type,
            "score": self.score,
            "matched_fields": self.matched_fields,
            "reasons": self.reasons,
            "profile_id": self.profile.id if self.profile else None,
        }


MIN_SCORE = 2


def _contains(needle: str, hay: Optional[str]) -> bool:
    if not needle or not hay:
        return False
    needle = needle.lower().strip()
    hay = hay.lower().strip()
    if needle in (UNKNOWN.lower(), "unknown / not detected"):
        return False
    return needle in hay or any(word in hay for word in needle.split()) if needle else False


def _model_match(alias: str, model: Optional[str]) -> bool:
    if not alias or not model:
        return False
    a = alias.lower().strip()
    m = model.lower().strip()
    # match esatto/parziale del modello per intero, non di singole parole generiche
    if a in m or m in a:
        return True
    # token distintivi (contengono cifre) presenti nel modello rilevato
    tokens = [t for t in re.split(r"[\s/]+", a) if any(ch.isdigit() for ch in t)]
    return any(t in m for t in tokens)


def _board_match(aliases: List[str], board: Optional[str]) -> bool:
    if not board:
        return False
    b = board.lower().strip()
    return any(str(a).lower().strip() == b for a in aliases if str(a).strip())


def _id_match(req_ids: List[str], actual_id: str) -> bool:
    if not req_ids or not actual_id:
        return False
    actual = actual_id.lower()
    return any(req.lower() in actual for req in req_ids)


def match_profile(identity: HardwareIdentity, profiles: Dict[str, HardwareProfile]) -> MatchResult:
    """
    Restituisce il profilo piu' simile.

    Punteggio:
        3 -> modello/alias corrispondenza forte
        2 -> board o Hardware ID corrispondenza
        1 -> brand / famiglia hardware parziale
        0 -> nessuna evidenza
    """
    best: Optional[MatchResult] = None

    for profile in profiles.values():
        score = 0
        matched: List[str] = []
        reasons: List[str] = []

        # 1. modello o alias forte (match sull'intero modello o token distintivo)
        for alias in [_titleish(profile.model)] + list(profile.aliases):
            if _model_match(alias, identity.model):
                score = max(score, 3)
                matched.append("model")
                reasons.append(f"Modello '{identity.model}' corrisponde a '{profile.name}'")
                break

        # 2. board (match esatto, per evitare falsi positivi tipo D3403-U vs D3403-U2)
        board_aliases = list(profile.board.get("aliases", [])) + [str(profile.board.get("name", ""))]
        if _board_match(board_aliases, identity.board):
            score = max(score, 2)
            matched.append("board")
            reasons.append(f"Board '{identity.board}' corrisponde a '{profile.board.get('name', '')}'")

        # 3. Hardware ID: GPU/audio/ethernet
        hardware_ids = (
            list(profile.gpu.get("ids", []))
            + list(profile.audio.get("ids", []))
            + list(profile.ethernet.get("ids", []))
            + list(profile.wifi.get("ids", []))
        )
        actual_ids = [identity.gpu_id, identity.audio_id, identity.ethernet_id, identity.wifi_id]
        for actual in actual_ids:
            if _id_match(hardware_ids, actual):
                score = max(score, 2)
                matched.append("hardware_id")
                reasons.append(f"Hardware ID '{actual}' presente nel profilo")
                break

        # 4. vendor / famiglia
        if identity.manufacturer and _contains(profile.manufacturer, identity.manufacturer):
            score = max(score, 1)
            matched.append("manufacturer")
            reasons.append(f"Vendor '{identity.manufacturer}' corrisponde a '{profile.manufacturer}'")

        if profile.cpu.get("generations") and identity.cpu and any(
            _contains(gen, identity.cpu) for gen in profile.cpu.get("generations", [])
        ):
            score = max(score, 1)
            if "cpu" not in matched:
                matched.append("cpu")
                reasons.append(f"CPU '{identity.cpu}' coerente con {profile.cpu.get('generations')}")

        result = MatchResult(profile, score, matched, reasons)
        if best is None or score > best.score or (score == best.score and profile.verified and not best.profile.verified):
            best = result

    if best is None or best.profile is None:
        return MatchResult(None, 0, [], ["Nessun profilo corrispondente trovato"])

    if best.score < MIN_SCORE:
        return MatchResult(None, best.score, best.matched_fields,
                           ["Corrispondenza troppo debole: " + ", ".join(best.matched_fields)])

    return best


def _titleish(text: str) -> str:
    return text if text else ""
