"""
Loader del sources manifest + consistency check contro il profilo hardware.

Il manifest vive accanto ai profili:

    src/database/sources/<profile_id>/sources.json

Coerenza richiesta (pena: errore, mai silenzio):
- ogni kext/driver/SSDT REQUIRED del profilo ha un componente required nel manifest;
- config.plist e' sempre generato dal motore (componente 'generated');
- target unici, nessun path traversal.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from database import HardwareProfile
from efi.selection import DRIVER_FILES, KEXT_BUNDLES

from .schema import SourcesManifest, validate_manifest_dict

#: Radice dei sources manifest (src/database/sources).
SOURCES_ROOT = Path(__file__).resolve().parents[1] / "database" / "sources"


class ManifestError(RuntimeError):
    """Manifest assente, malformato o incoerente con il profilo."""


def manifest_path_for(profile_id: str, root: Optional[Path] = None) -> Path:
    base = Path(root) if root else SOURCES_ROOT
    return base / profile_id / "sources.json"


def load_manifest(path: Path) -> SourcesManifest:
    path = Path(path)
    if not path.exists():
        raise ManifestError(f"Sources manifest non trovato: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Sources manifest non e' JSON valido ({path}): {exc}") from exc

    manifest, errors = validate_manifest_dict(raw)
    if errors:
        raise ManifestError(
            f"Sources manifest invalido ({path}):\n  - " + "\n  - ".join(errors)
        )
    return manifest


def load_manifest_for_profile(profile_id: str, root: Optional[Path] = None) -> SourcesManifest:
    return load_manifest(manifest_path_for(profile_id, root))


def available_manifests(root: Optional[Path] = None) -> List[str]:
    """ID dei profili che hanno un sources manifest."""
    base = Path(root) if root else SOURCES_ROOT
    if not base.is_dir():
        return []
    out = []
    for child in sorted(base.iterdir()):
        if child.is_dir() and (child / "sources.json").is_file():
            out.append(child.name)
    return out


def check_against_profile(manifest: SourcesManifest, profile: HardwareProfile) -> List[str]:
    """Verifica che il manifest copra tutto cio' che il profilo dichiara REQUIRED.

    Restituisce una lista di problemi (vuota = coerente).
    """
    problems: List[str] = []

    if manifest.profile_id != profile.id:
        problems.append(
            f"il manifest e' per il profilo {manifest.profile_id!r} ma il profilo caricato e' {profile.id!r}"
        )

    kext_targets = {
        c.target.split("/")[-1]
        for c in manifest.components
        if c.kind == "kext" and c.required
    }
    for logical in profile.required_kexts:
        bundle = KEXT_BUNDLES.get(logical, logical + ".kext")
        if bundle not in kext_targets:
            problems.append(f"kext richiesto dal profilo mancante nel manifest: {logical} ({bundle})")

    driver_targets = {
        c.target.split("/")[-1]
        for c in manifest.components
        if c.kind == "efi_binary" and c.required and c.target.startswith("OC/Drivers/")
    }
    for logical in profile.required_drivers:
        fname = DRIVER_FILES.get(logical, logical + ".efi")
        if fname not in driver_targets:
            problems.append(f"driver richiesto dal profilo mancante nel manifest: {logical} ({fname})")

    aml_targets = {
        c.target.split("/")[-1]
        for c in manifest.components
        if c.kind == "aml" and c.required
    }
    for ssdt in profile.required_ssdts:
        if f"{ssdt}.aml" not in aml_targets:
            problems.append(f"SSDT richiesto dal profilo mancante nel manifest: {ssdt}.aml")

    has_config = any(
        c.kind == "generated" and c.source.generator == "config.plist" and c.scope == "efi"
        for c in manifest.components
    )
    if not has_config:
        problems.append("manca il componente generated per OC/config.plist")

    has_booter = any(
        c.kind == "efi_binary" and c.required and c.scope == "efi"
        and c.target == "BOOT/BOOTx64.efi"
        for c in manifest.components
    )
    if not has_booter:
        problems.append("manca BOOT/BOOTx64.efi (required)")

    has_opencore = any(
        c.kind == "efi_binary" and c.required and c.target == "OC/OpenCore.efi"
        for c in manifest.components
    )
    if not has_opencore:
        problems.append("manca OC/OpenCore.efi (required)")

    return problems
