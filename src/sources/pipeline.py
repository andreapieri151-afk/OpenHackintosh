"""
Sources engine (v1): il motore di generazione dichiarativo.

    Sources Manifest  ->  FETCH  ->  VERIFY  ->  ASSEMBLE  ->  AUDIT  ->  ZIP

Differenze rispetto al builder legacy:
- i file e le fonti non sono hardcoded nel codice: stanno nel sources manifest
  (src/database/sources/<profilo>/sources.json);
- ogni componente materiale porta con se' provenienza, sha256 e dimensione
  (provenance ledger);
- il fetcher e' iniettabile: la stessa pipeline gira con rete reale
  (GitHubFetcher) o offline nei test (InMemoryFetcher).

Regola sempre valida: se un componente REQUIRED fallisce, la generazione
FALLISCE. Nessun file finto, nessuna EFI parziale dichiarata buona.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Callable, Dict, List, Optional

from database import HardwareProfile
from efi.audit import final_audit
from efi.selection import ComponentSelection, DRIVER_FILES, KEXT_BUNDLES
from efi_builder.config_generator import generate_config, save_config
from efi_builder.smbios import generate_smbios

from .loader import ManifestError, check_against_profile
from .resolver import (
    FAILED,
    GENERATED,
    OK,
    SKIPPED,
    MaterializedComponent,
    materialize_component,
)
from .schema import SourcesManifest

#: Mappa flag CLI -> optional_group del manifest.
FLAG_TO_GROUP = {
    "include_wifi": "wifi",
    "include_bluetooth": "bluetooth",
    "include_nvme": "nvme",
    "include_restrict_events": "restrict_events",
    "include_optional_drivers": "optional_drivers",
    "include_usb_mapping": "usb_mapping",
}


def _profile_slug(profile_name: str) -> str:
    import re

    slug = re.sub(r"[^A-Za-z0-9]+", "_", str(profile_name)).strip("_").upper()
    return slug or "UNKNOWN"


def _select_components(manifest: SourcesManifest, flags: Dict[str, bool]) -> List:
    """Quali componenti del manifest entrano in questa build."""
    enabled_groups = {group for flag, group in FLAG_TO_GROUP.items() if flags.get(flag)}
    chosen = []
    for comp in manifest.components:
        if comp.required:
            chosen.append(comp)
        elif comp.optional_group in enabled_groups:
            chosen.append(comp)
    return chosen


def _build_selection(manifest: SourcesManifest, included_ids: set) -> ComponentSelection:
    """ComponentSelection per l'audit, derivata dai componenti inclusi."""
    bundle_to_logical = {v: k for k, v in KEXT_BUNDLES.items()}
    file_to_logical = {v: k for k, v in DRIVER_FILES.items()}

    sel = ComponentSelection()
    for comp in manifest.components:
        if comp.id not in included_ids:
            continue
        name = comp.target.split("/")[-1]
        if comp.kind == "kext":
            sel.required_kexts.append(bundle_to_logical.get(name, name.removesuffix(".kext")))
        elif comp.kind == "efi_binary" and comp.target.startswith("OC/Drivers/"):
            sel.required_drivers.append(file_to_logical.get(name, name.removesuffix(".efi")))
        elif comp.kind == "aml":
            sel.required_ssdts.append(name.removesuffix(".aml"))
    return sel


def _create_structure(efi_root: Path) -> None:
    for folder in [
        efi_root / "BOOT",
        efi_root / "OC" / "ACPI",
        efi_root / "OC" / "Drivers",
        efi_root / "OC" / "Kexts",
        efi_root / "OC" / "Tools",
        efi_root / "OC" / "Resources" / "Audio",
        efi_root / "OC" / "Resources" / "Font",
        efi_root / "OC" / "Resources" / "Image",
    ]:
        folder.mkdir(parents=True, exist_ok=True)


def _generated_readme(profile: HardwareProfile, macos_version: str, smbios_model: str,
                      components: List[MaterializedComponent]) -> str:
    lines = [
        f"# EFI per {profile.name} — generata con OpenHackintosh (sources engine)",
        "",
        f"macOS target: {macos_version} — SMBIOS: {smbios_model}",
        "",
        "## Componenti e fonti",
        "",
        "| Componente | Target | Fonte | Stato | SHA-256 (file/binario) |",
        "|---|---|---|---|---|",
    ]
    for comp in components:
        sha = comp.sha256[:16] + "…" if comp.sha256 else "-"
        lines.append(f"| {comp.component_id} | {comp.target} | {comp.source_url or 'generato'} | {comp.status} | `{sha}` |")
    lines += [
        "",
        "Provenance: 'verified' = fonte confermata dal maintainer; 'default' = fonte canonica ufficiale.",
        "Se questa EFI non boota: controlla il BIOS (DVMT 64MB!) — leggi docs/BIOS_GUIDE.md.",
        "",
    ]
    return "\n".join(lines)


def run_manifest_pipeline(
    manifest: SourcesManifest,
    profile: HardwareProfile,
    output_dir: Path,
    fetcher,
    smbios_model: str = "iMac18,1",
    audio_layout: int = 11,
    macos_version: str = "Ventura 13.x",
    include_wifi: bool = False,
    include_bluetooth: bool = False,
    include_nvme: bool = False,
    include_restrict_events: bool = False,
    include_optional_drivers: bool = False,
    generate_zip: bool = True,
    dev: bool = False,
    log: Optional[Callable[[str], None]] = None,
) -> Dict:
    """Genera la EFI completa a partire dal sources manifest."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    efi_root = out / "EFI"
    say = log or print

    # 0. Coerenza manifest <-> profilo (prima di toccare la rete).
    problems = check_against_profile(manifest, profile)
    if problems:
        return {
            "success": False,
            "ok": False,
            "engine": "sources.v1",
            "error": "Manifest incoerente con il profilo: " + "; ".join(problems),
            "efi_status": "FAILED",
            "components": [],
        }

    # 1. Struttura cartelle.
    _create_structure(efi_root)
    say(f"=== Sources engine v1: creo EFI per {profile.id} ===")

    flags = dict(
        include_wifi=include_wifi,
        include_bluetooth=include_bluetooth,
        include_nvme=include_nvme,
        include_restrict_events=include_restrict_events,
        include_optional_drivers=include_optional_drivers,
    )
    chosen = _select_components(manifest, flags)

    # 2. Materializzazione di ogni componente dichiarato.
    materialized: List[MaterializedComponent] = []
    failed_required: List[str] = []
    for comp in chosen:
        if comp.kind == "generated":
            materialized.append(MaterializedComponent(
                component_id=comp.id, kind=comp.kind, target=comp.target,
                scope=comp.scope, status=GENERATED, required=comp.required,
                provenance=comp.provenance,
            ))
            continue
        say(f"  -> {comp.id} ({comp.target})")
        result = materialize_component(comp, fetcher, out, efi_root)
        if result.status == OK:
            say(f"     OK  [{result.size} bytes, sha256 {result.sha256[:12]}…]" if result.sha256 else "     OK")
        elif comp.required:
            say(f"     FAIL {result.reason}")
            failed_required.append(f"{comp.id}: {result.reason}")
        else:
            say(f"     SKIP (opzionale): {result.reason}")
            result.status = SKIPPED
            result.reason = f"opzionale scartato: {result.reason}"
        materialized.append(result)

    if failed_required:
        return {
            "success": False,
            "ok": False,
            "engine": "sources.v1",
            "error": "Componenti obbligatori non disponibili/invalidi: " + "; ".join(failed_required),
            "efi_status": "FAILED",
            "components": [m.to_dict() for m in materialized],
        }

    # 3. Componenti generati dal motore (config.plist, README, provenance).
    smbios_data = generate_smbios(smbios_model)
    config = generate_config(
        efi_root=efi_root,
        smbios_data=smbios_data,
        profile_name=profile.id,
        audio_layout=audio_layout,
        macos_version=macos_version,
        device_properties=profile.device_properties,
        dev=dev,
    )
    save_config(config, efi_root / "OC" / "config.plist")
    say("  -> OC/config.plist (generato)")

    readme = _generated_readme(profile, macos_version, smbios_model, materialized)
    (out / "README_EFI.txt").write_text(readme, encoding="utf-8")

    # 4. Audit finale (binari, zero-byte, placeholder, config consistency).
    included_ids = {m.component_id for m in materialized if m.status in (OK, GENERATED)}
    selection = _build_selection(manifest, included_ids)
    audit = final_audit(efi_root, profile, selection)

    if not audit["ready"]:
        return {
            "success": False,
            "ok": False,
            "engine": "sources.v1",
            "error": "Final audit failed: " + "; ".join(audit["errors"]),
            "efi_status": "FAILED",
            "generation_report": audit,
            "components": [m.to_dict() for m in materialized],
        }

    # 5. ZIP.
    zip_path = None
    if generate_zip:
        slug = _profile_slug(profile.id)
        zip_path = out / f"EFI_{slug}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for path in sorted(efi_root.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(out))
            readme_path = out / "README_EFI.txt"
            zf.write(readme_path, readme_path.relative_to(out))
        say(f"  -> ZIP: {zip_path}")

    say("EFI STATUS: VALID (sources engine v1)")
    return {
        "success": True,
        "ok": True,
        "engine": "sources.v1",
        "profile": profile.id,
        "efi_path": str(efi_root),
        "zip_path": str(zip_path) if zip_path else None,
        "smbios": smbios_data,
        "efi_status": "VALID",
        "generation_report": audit,
        "components": [m.to_dict() for m in materialized],
        "selection": selection.to_dict(),
    }
