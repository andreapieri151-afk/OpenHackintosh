"""
Schema del Sources Manifest (v1).

Il sources manifest e' il "database delle fonti": per OGNI file che finisce
nella EFI dichiara:

- COS'E'            (kind: efi_binary | kext | aml | generated)
- DOVE VA           (target: percorso relativo dentro la EFI o nell'output)
- DA DOVE ARRIVA    (source: github_release | github_raw | url | generated)
- COME SI VALIDA    (min_size, sha256 opzionale)
- SE E' OBBLIGATORIO (required) e a quale gruppo opzionale appartiene

Regole dure:
- nessun field inventato: i campi sconosciuti sono errori, non warnings;
- target sempre relativi e senza ".." (niente path traversal);
- provenance: "default" = fonte canonica non ancora confermata dal
  maintainer; "verified" = fonte confermata/verificata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

MANIFEST_VERSION = 1

KINDS = ("efi_binary", "kext", "aml", "generated")
SOURCE_TYPES = ("github_release", "github_raw", "url", "generated")
PROVENANCE = ("default", "verified")
SCOPES = ("efi", "output")
OPTIONAL_GROUPS = (
    "wifi",
    "bluetooth",
    "nvme",
    "restrict_events",
    "optional_drivers",
    "usb_mapping",
)
GENERATORS = ("config.plist", "readme", "provenance", "usb_map")

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

#: Suffisso atteso per target in base al kind (coerenza interna del manifest).
KIND_TARGET_SUFFIX = {
    "efi_binary": ".efi",
    "kext": ".kext",
    "aml": ".aml",
}


@dataclass
class SourceSpec:
    """Da dove arriva un componente."""
    type: str
    # github_release
    repo: str = ""
    tag: str = "latest"           # "latest" oppure una versione fissata (es. "1.0.8")
    asset: str = ""               # pattern fnmatch sul nome asset (es. "OpenCore-*-RELEASE.zip")
    path_in_archive: str = ""     # path/glob dentro lo zip (solo file singoli)
    # github_raw
    ref: str = ""                 # branch/tag/commit per raw.githubusercontent.com
    path: str = ""                # path nel repo
    # url
    url: str = ""
    # generated
    generator: str = ""           # config.plist | readme | provenance

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v not in ("", None)}

    def summary(self) -> str:
        """Descrizione breve e leggibile della fonte."""
        if self.type == "github_release":
            tag = "@" + self.tag if self.tag and self.tag != "latest" else "@latest"
            return f"github:{self.repo}{tag} :: {self.asset or '*'}"
        if self.type == "github_raw":
            return f"raw:{self.repo}@{self.ref}/{self.path}"
        if self.type == "url":
            return self.url
        return f"generated:{self.generator}"


@dataclass
class ComponentSpec:
    """Un file della EFI: cosa e', dove va, da dove arriva."""
    id: str
    kind: str
    required: bool
    target: str                       # relativo a EFI/ (scope=efi) o all'output (scope=output)
    source: SourceSpec
    scope: str = "efi"                # efi | output
    min_size: int = 0
    sha256: str = ""                  # pin opzionale (solo file singoli, no kext)
    optional_group: str = ""          # gruppo opzionale (vedi OPTIONAL_GROUPS)
    provenance: str = "default"       # default | verified
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "required": self.required,
            "scope": self.scope,
            "target": self.target,
            "source": self.source.to_dict(),
            "min_size": self.min_size,
            "sha256": self.sha256,
            "optional_group": self.optional_group,
            "provenance": self.provenance,
            "notes": self.notes,
        }


@dataclass
class SourcesManifest:
    manifest_version: int
    profile_id: str
    name: str = ""
    description: str = ""
    components: List[ComponentSpec] = field(default_factory=list)

    def required_components(self) -> List[ComponentSpec]:
        return [c for c in self.components if c.required]

    def optional_components(self) -> List[ComponentSpec]:
        return [c for c in self.components if not c.required]

    def by_id(self) -> Dict[str, ComponentSpec]:
        return {c.id: c for c in self.components}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "profile_id": self.profile_id,
            "name": self.name,
            "description": self.description,
            "components": [c.to_dict() for c in self.components],
        }


# ---------------------------------------------------------------------------
# Validazione
# ---------------------------------------------------------------------------

def _validate_source(raw: Any, ctx: str) -> tuple:
    """Restituisce (SourceSpec | None, errori)."""
    errors: List[str] = []
    if not isinstance(raw, dict):
        return None, [f"{ctx}: 'source' deve essere un oggetto"]

    known = {"type", "repo", "tag", "asset", "path_in_archive", "ref", "path", "url", "generator"}
    unknown = set(raw) - known
    if unknown:
        errors.append(f"{ctx}.source: campi sconosciuti: {sorted(unknown)}")

    stype = raw.get("type", "")
    if stype not in SOURCE_TYPES:
        errors.append(f"{ctx}.source: type invalido o mancante: {stype!r} (validi: {', '.join(SOURCE_TYPES)})")
        return None, errors

    spec = SourceSpec(
        type=stype,
        repo=str(raw.get("repo", "")),
        tag=str(raw.get("tag", "latest")),
        asset=str(raw.get("asset", "")),
        path_in_archive=str(raw.get("path_in_archive", "")),
        ref=str(raw.get("ref", "")),
        path=str(raw.get("path", "")),
        url=str(raw.get("url", "")),
        generator=str(raw.get("generator", "")),
    )

    if stype == "github_release":
        if not spec.repo or "/" not in spec.repo:
            errors.append(f"{ctx}.source: repo GitHub mancante/invalido: {spec.repo!r}")
        if "debug" in spec.asset.lower():
            errors.append(
                f"{ctx}.source: gli asset DEBUG sono vietati nel manifest "
                f"(solo RELEASE ufficiali): {spec.asset!r}"
            )
    elif stype == "github_raw":
        if not spec.repo or "/" not in spec.repo:
            errors.append(f"{ctx}.source: repo GitHub mancante/invalido: {spec.repo!r}")
        if not spec.ref:
            errors.append(f"{ctx}.source: 'ref' richiesto per github_raw")
        if not spec.path:
            errors.append(f"{ctx}.source: 'path' richiesto per github_raw")
    elif stype == "url":
        if not spec.url.startswith(("http://", "https://")):
            errors.append(f"{ctx}.source: url invalido: {spec.url!r}")
    elif stype == "generated":
        if spec.generator not in GENERATORS:
            errors.append(f"{ctx}.source: generator invalido: {spec.generator!r} (validi: {', '.join(GENERATORS)})")

    return spec, errors


def _validate_component(raw: Any, idx: int) -> tuple:
    """Restituisce (ComponentSpec | None, errori)."""
    ctx = f"components[{idx}]"
    errors: List[str] = []
    if not isinstance(raw, dict):
        return None, [f"{ctx}: deve essere un oggetto"]

    known = {
        "id", "kind", "required", "target", "source", "scope",
        "min_size", "sha256", "optional_group", "provenance", "notes",
    }
    unknown = set(raw) - known
    if unknown:
        errors.append(f"{ctx}: campi sconosciuti: {sorted(unknown)}")

    cid = str(raw.get("id", "")).strip()
    if not cid or not re.match(r"^[a-z0-9_]+$", cid):
        errors.append(f"{ctx}: id mancante/invalido: {cid!r} (solo minuscole, cifre, underscore)")

    kind = raw.get("kind", "")
    if kind not in KINDS:
        errors.append(f"{ctx}: kind invalido: {kind!r} (validi: {', '.join(KINDS)})")

    required = raw.get("required")
    if not isinstance(required, bool):
        errors.append(f"{ctx}: 'required' deve essere true/false")
        required = False

    target = str(raw.get("target", "")).strip().lstrip("/")
    if not target:
        errors.append(f"{ctx}: target mancante")
    elif ".." in target.split("/"):
        errors.append(f"{ctx}: target con path traversal non permesso: {target!r}")

    suffix = KIND_TARGET_SUFFIX.get(kind)
    if suffix and target and not target.endswith(suffix):
        errors.append(f"{ctx}: target {target!r} deve terminare con {suffix!r} (kind={kind})")

    scope = raw.get("scope", "efi")
    if scope not in SCOPES:
        errors.append(f"{ctx}: scope invalido: {scope!r} (validi: {', '.join(SCOPES)})")

    min_size = raw.get("min_size", 0)
    if not isinstance(min_size, int) or isinstance(min_size, bool) or min_size < 0:
        errors.append(f"{ctx}: min_size deve essere un intero >= 0")
        min_size = 0

    sha256 = str(raw.get("sha256", "")).lower()
    if sha256:
        if not _SHA256_RE.match(sha256):
            errors.append(f"{ctx}: sha256 non e' un hash esadecimale a 64 caratteri")
        if kind == "kext":
            errors.append(f"{ctx}: sha256 non supportato per i kext (bundle multi-file)")

    optional_group = str(raw.get("optional_group", ""))
    if optional_group and optional_group not in OPTIONAL_GROUPS:
        errors.append(f"{ctx}: optional_group invalido: {optional_group!r} (validi: {', '.join(OPTIONAL_GROUPS)})")
    if not required and not optional_group:
        errors.append(f"{ctx}: un componente opzionale deve dichiarare optional_group")

    provenance = str(raw.get("provenance", "default"))
    if provenance not in PROVENANCE:
        errors.append(f"{ctx}: provenance invalido: {provenance!r} (validi: {', '.join(PROVENANCE)})")

    source, source_errors = _validate_source(raw.get("source"), ctx)
    errors.extend(source_errors)

    # Coerenza kind <-> source
    if source and kind == "generated" and source.type != "generated":
        errors.append(f"{ctx}: kind 'generated' richiede source.type 'generated'")
    if source and kind != "generated" and source.type == "generated":
        errors.append(f"{ctx}: source 'generated' non valida per kind {kind!r}")
    if source and kind == "kext" and source.type not in ("github_release", "url"):
        errors.append(f"{ctx}: i kext si estraggono da un archivio (github_release/url)")
    if source and kind == "efi_binary" and source.type == "github_raw":
        errors.append(f"{ctx}: efi_binary da github_raw non supportato (usa un archivio o url diretto)")

    if errors:
        return None, errors

    return ComponentSpec(
        id=cid,
        kind=kind,
        required=required,
        target=target,
        source=source,
        scope=scope,
        min_size=min_size,
        sha256=sha256,
        optional_group=optional_group,
        provenance=provenance,
        notes=str(raw.get("notes", "")),
    ), []


def validate_manifest_dict(raw: Any) -> tuple:
    """Valida il dizionario grezzo del manifest. Restituisce (SourcesManifest | None, errori)."""
    errors: List[str] = []
    if not isinstance(raw, dict):
        return None, ["il manifest deve essere un oggetto JSON"]

    version = raw.get("manifest_version")
    if version != MANIFEST_VERSION:
        errors.append(f"manifest_version deve essere {MANIFEST_VERSION}, trovato {version!r}")

    profile_id = str(raw.get("profile_id", "")).strip()
    if not profile_id:
        errors.append("profile_id mancante")

    known_top = {"manifest_version", "profile_id", "name", "description", "components"}
    unknown_top = set(raw) - known_top
    if unknown_top:
        errors.append(f"campi sconosciuti nel manifest: {sorted(unknown_top)}")

    raw_components = raw.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        errors.append("'components' deve essere una lista non vuota")
        raw_components = []

    components: List[ComponentSpec] = []
    for idx, rc in enumerate(raw_components):
        comp, comp_errors = _validate_component(rc, idx)
        errors.extend(comp_errors)
        if comp is not None:
            components.append(comp)

    seen: set = set()
    for comp in components:
        if comp.id in seen:
            errors.append(f"id duplicato: {comp.id!r}")
        seen.add(comp.id)

    targets = {}
    for comp in components:
        key = (comp.scope, comp.target)
        if key in targets:
            errors.append(f"target duplicato: {comp.target!r} (componenti {targets[key]!r} e {comp.id!r})")
        targets.setdefault(key, comp.id)

    if errors:
        return None, errors

    return SourcesManifest(
        manifest_version=MANIFEST_VERSION,
        profile_id=profile_id,
        name=str(raw.get("name", "")),
        description=str(raw.get("description", "")),
        components=components,
    ), []
