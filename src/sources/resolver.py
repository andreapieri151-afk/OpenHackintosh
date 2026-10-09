"""
Resolver: trasforma un ComponentSpec del manifest in un file reale su disco.

Passi per ogni componente:
1. FETCH   -> il fetcher ottiene l'archivio o il file dalla fonte dichiarata;
2. EXTRACT -> per archivi: estrazione del file/bundle esatto dichiarato;
3. VERIFY  -> validazione binaria (PE/COFF, Mach-O/kext, firma AML), min_size,
              sha256 pin se presente;
4. PLACE   -> scrittura nel target esatto del manifest.

Se un componente obbligatorio non supera un passaggio -> FAILED (mai file
finti, mai fallback silenziosi).
"""

from __future__ import annotations

import fnmatch
import hashlib
import io
import shutil
import zipfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

from efi.integrity import sha256_file, validate_aml_file, validate_efi_binary, validate_kext

from .fetcher import FetchError, source_cache_name
from .schema import ComponentSpec

#: Esiti della materializzazione.
OK = "OK"
FAILED = "FAILED"
SKIPPED = "SKIPPED"           # opzionale non richiesto dai flag
GENERATED = "GENERATED"       # prodotto dal motore (config.plist, readme...)


@dataclass
class MaterializedComponent:
    component_id: str
    kind: str
    target: str
    scope: str
    status: str = FAILED
    reason: str = ""
    path: str = ""
    size: int = 0
    sha256: str = ""
    source_url: str = ""
    provenance: str = "default"
    required: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def _extract_member(zf: zipfile.ZipFile, member: str) -> bytes:
    with zf.open(member) as fh:
        return fh.read()


def _find_single_file(zf: zipfile.ZipFile, pattern: str) -> Optional[str]:
    """Trova il primo file nell'archivio che matcha il pattern dichiarato."""
    names = [n for n in zf.namelist() if not n.endswith("/")]
    for name in names:
        if fnmatch.fnmatch(name, pattern):
            return name
    # Tolleranza al prefisso variabile (es. zip con cartella versione davanti).
    base = pattern.split("/")[-1]
    for name in names:
        if fnmatch.fnmatch(name.split("/")[-1], base):
            return name
    return None


def _extract_kext_bundle(zf: zipfile.ZipFile, bundle_name: str, dest_dir: Path) -> bool:
    """Estrae un bundle .kext dall'archivio, cercandolo a qualsiasi profondita'."""
    marker = f"{bundle_name}/"
    members = [n for n in zf.namelist() if marker in n]
    if not members:
        return False

    # Radice del bundle: tutto cio' che precede (e include) "<bundle_name>/".
    first = members[0]
    root = first[: first.index(marker) + len(marker)]

    target_bundle = dest_dir / bundle_name
    if target_bundle.exists():
        shutil.rmtree(target_bundle)

    for member in members:
        rel = member[len(root):]
        if not rel:
            continue
        dest = target_bundle / rel
        if member.endswith("/"):
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)

    return (target_bundle / "Contents" / "Info.plist").exists()


def materialize_component(component: ComponentSpec, fetcher, output_dir: Path,
                          efi_root: Path, context: Optional[dict] = None) -> MaterializedComponent:
    """Materializza UN componente. Non lancia eccezioni: lo stato sta nell'esito."""
    result = MaterializedComponent(
        component_id=component.id,
        kind=component.kind,
        target=component.target,
        scope=component.scope,
        required=component.required,
        provenance=component.provenance,
    )

    base = efi_root if component.scope == "efi" else Path(output_dir)
    dest = base / component.target

    if component.kind == "generated":
        result.status = GENERATED
        result.reason = "prodotto dal motore (non scaricato)"
        return result

    try:
        if component.kind in ("efi_binary", "kext"):
            archive_path = fetcher.fetch_archive(component.source, context)
            result.source_url = component.source.summary()
            with zipfile.ZipFile(archive_path) as zf:
                if component.kind == "efi_binary":
                    pattern = component.source.path_in_archive or ("*/" + dest.name)
                    member = _find_single_file(zf, pattern)
                    if not member:
                        result.reason = f"file non trovato nell'archivio: {pattern!r}"
                        return result
                    data = _extract_member(zf, member)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)
                else:  # kext
                    bundle_name = dest.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if not _extract_kext_bundle(zf, bundle_name, dest.parent):
                        result.reason = f"bundle {bundle_name} non trovato nell'archivio"
                        return result

        elif component.kind == "aml":
            data, url = fetcher.fetch_bytes(component.source, context)
            result.source_url = url
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)

        else:  # gia' filtrato dallo schema, difesa in profondita'
            result.reason = f"kind non gestito dal resolver: {component.kind}"
            return result

    except FetchError as exc:
        result.reason = f"fetch fallito: {exc}"
        return result
    except zipfile.BadZipFile:
        result.reason = "archivio corrotto (zip invalido)"
        return result
    except Exception as exc:  # errore inatteso: mai crashare la pipeline
        result.reason = f"errore inatteso: {exc}"
        return result

    # ---- Verifica binaria reale (NO FAKE BINARIES) ----
    if component.kind == "efi_binary":
        check = validate_efi_binary(dest)
    elif component.kind == "kext":
        check = validate_kext(dest)
    else:
        check = validate_aml_file(dest)

    if not check.ok:
        result.reason = f"validazione binaria fallita: {check.reason}"
        return result

    if dest.is_file():
        result.size = dest.stat().st_size
        result.sha256 = sha256_file(dest)
        result.path = str(dest)
    else:  # bundle kext: hash dell'eseguibile dentro il bundle
        executables = list((dest / "Contents" / "MacOS").iterdir()) if (dest / "Contents" / "MacOS").exists() else []
        if executables:
            result.size = executables[0].stat().st_size
            result.sha256 = sha256_file(executables[0])
        result.path = str(dest)

    if component.min_size and result.size < component.min_size:
        result.reason = f"file troppo piccolo: {result.size} < min_size {component.min_size}"
        return result

    if component.sha256 and result.sha256 != component.sha256:
        result.reason = f"sha256 mismatch: atteso {component.sha256}, ottenuto {result.sha256}"
        return result

    result.status = OK
    return result
