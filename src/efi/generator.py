"""
EFI Generator hardware-aware.

Flusso:
    Hardware -> Profilo -> ComponentSelection -> EFIBuilder -> EFI.

Il generatore NON include componenti extra: usa solo quelli del profilo
(required + optional scelti esplicitamente).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from database import HardwareProfile
from efi_builder.builder import EFIBuilder
from .selection import ComponentSelection, select_components


def build_efi(
    profile: HardwareProfile,
    output_dir: Path,
    smbios_model: str,
    audio_layout: int,
    macos_version: str,
    include_wifi: bool = False,
    include_bluetooth: bool = False,
    generate_zip: bool = True,
    strict: bool = True,
) -> Dict:
    selection = select_components(
        profile,
        include_wifi=include_wifi,
        include_bluetooth=include_bluetooth,
        include_nvme=True,
        include_restrict_events=True,
        include_usb_toolbox=False,
    )

    builder = EFIBuilder(output_dir)
    result = builder.build(
        profile_name=profile.id,
        smbios_model=smbios_model,
        audio_layout=audio_layout,
        macos_version=macos_version,
        include_wifi=include_wifi,
        include_bluetooth=include_bluetooth,
        generate_zip=generate_zip,
        selection=selection,
        strict=strict,
    )
    result["selection"] = selection.to_dict()
    return result
