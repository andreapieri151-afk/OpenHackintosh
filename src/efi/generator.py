"""
EFI Generator hardware-aware e hardening.

Flusso:
    Hardware -> Profilo -> ComponentSelection -> EFIBuilder -> Final Audit -> EFI.

Il generatore NON include componenti extra: usa solo quelli del profilo
(required + optional scelti esplicitamente). Prima di dichiarare successo
esegue sempre un final EFI audit (binari, zero-byte, placeholder,
config consistency, required components, integrità).
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
from typing import Dict, Optional

from database import HardwareProfile
from efi_builder.builder import EFIBuilder
from efi.selection import ComponentSelection, select_components
from efi.audit import final_audit


def build_efi(
    profile: HardwareProfile,
    output_dir: Path,
    smbios_model: str,
    audio_layout: int,
    macos_version: str,
    include_wifi: bool = False,
    include_bluetooth: bool = False,
    include_nvme: bool = False,
    include_restrict_events: bool = False,
    include_optional_drivers: bool = False,
    generate_zip: bool = True,
    strict: bool = True,
    dev: bool = False,
    silent: bool = False,
) -> Dict:
    selection = select_components(
        profile,
        include_wifi=include_wifi,
        include_bluetooth=include_bluetooth,
        include_nvme=include_nvme,
        include_restrict_events=include_restrict_events,
        include_usb_toolbox=False,
        include_optional_drivers=include_optional_drivers,
    )

    builder = EFIBuilder(output_dir)
    build_kwargs = dict(
        profile_name=profile.id,
        smbios_model=smbios_model,
        audio_layout=audio_layout,
        macos_version=macos_version,
        include_wifi=include_wifi,
        include_bluetooth=include_bluetooth,
        generate_zip=generate_zip,
        selection=selection,
        strict=strict,
        dev=dev,
        device_properties=profile.device_properties,
    )
    if silent:
        # Output JSON pulito: nessun log testuale su stdout durante la build.
        with contextlib.redirect_stdout(io.StringIO()):
            result = builder.build(**build_kwargs)
    else:
        result = builder.build(**build_kwargs)
    result["selection"] = selection.to_dict()

    # Final EFI audit: solo se la build ha prodotto un EFI e solo se TUTTO passa
    # dichiariamo successo.
    if result.get("success") and result.get("efi_path"):
        audit = final_audit(Path(result["efi_path"]), profile, selection)
        result["generation_report"] = audit
        result["efi_status"] = audit["status"]
        if not audit["ready"]:
            result["success"] = False
            result["error"] = "EFI generation aborted. Final audit failed: " + "; ".join(audit["errors"])
    else:
        result["generation_report"] = {
            "status": "FAILED",
            "profile": profile.name,
            "state": profile.state,
            "checks": {},
            "acpi": [],
            "drivers": [],
            "kexts": [],
            "errors": [result.get("error", "Build failed before final audit")],
        }
        result["efi_status"] = "FAILED"

    return result
