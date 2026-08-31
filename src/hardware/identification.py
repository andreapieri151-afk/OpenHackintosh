"""
Identificazione hardware: da HardwareInfo a un'identità confrontabile.
Non inventa nulla; usa solo i dati rilevati.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Optional

from .detection import HardwareInfo, UNKNOWN, unknown, DetectedValue


@dataclass
class HardwareIdentity:
    manufacturer: str = UNKNOWN
    model: str = UNKNOWN
    board: str = UNKNOWN
    board_vendor: str = UNKNOWN
    bios: str = UNKNOWN
    cpu: str = UNKNOWN
    cpu_vendor: str = UNKNOWN
    gpu: str = UNKNOWN
    gpu_id: str = UNKNOWN
    audio: str = UNKNOWN
    audio_id: str = UNKNOWN
    ethernet: str = UNKNOWN
    ethernet_id: str = UNKNOWN
    wifi: str = UNKNOWN
    wifi_id: str = UNKNOWN

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

    def search_terms(self) -> list[str]:
        """Stringhe per il matching con il database (sempre lowercase)."""
        terms: list[str] = []
        for value in [self.manufacturer, self.model, self.board, self.cpu,
                      self.gpu, self.audio, self.ethernet, self.wifi]:
            v = value.lower().strip()
            if v and v not in (UNKNOWN.lower(), "unknown / not detected"):
                terms.append(v)
        for value in [self.gpu_id, self.audio_id, self.ethernet_id, self.wifi_id]:
            v = value.lower().strip()
            if v and "/" in v:
                terms.append(v)
        return terms


def _first(d: Dict[str, DetectedValue], *keys: str) -> str:
    for key in keys:
        v = d.get(key)
        if v and str(v) != UNKNOWN:
            return str(v)
    return UNKNOWN


def identify(info: HardwareInfo) -> HardwareIdentity:
    return HardwareIdentity(
        manufacturer=_first(info.dmi, "system_vendor"),
        model=_first(info.dmi, "product_name"),
        board=_first(info.dmi, "board_name"),
        board_vendor=_first(info.dmi, "board_vendor"),
        bios=f"{_first(info.dmi, 'bios_vendor')} {_first(info.dmi, 'bios_version')}".strip(),
        cpu=_first(info.cpu, "model"),
        cpu_vendor=_first(info.cpu, "vendor"),
        gpu=_first(info.gpu, "gpu"),
        gpu_id=_first(info.gpu, "gpu_id"),
        audio=_first(info.audio, "audio"),
        audio_id=_first(info.audio, "audio_id"),
        ethernet=_first(info.ethernet, "ethernet"),
        ethernet_id=_first(info.ethernet, "ethernet_id"),
        wifi=_first(info.wifi, "wifi"),
        wifi_id=_first(info.wifi, "wifi_id"),
    )
