"""
Sources engine: database delle fonti + motore di generazione dichiarativo.

    src/sources/schema.py    -> schema e validazione del sources manifest
    src/sources/loader.py    -> caricamento + coerenza con il profilo hardware
    src/sources/fetcher.py   -> download (GitHub reale o in-memory per i test)
    src/sources/resolver.py  -> estrazione + validazione binaria dei componenti
    src/sources/pipeline.py  -> orchestrazione: manifest -> EFI -> audit -> zip
"""

from .schema import (
    MANIFEST_VERSION,
    ComponentSpec,
    SourceSpec,
    SourcesManifest,
    validate_manifest_dict,
)
from .loader import (
    ManifestError,
    available_manifests,
    check_against_profile,
    load_manifest,
    load_manifest_for_profile,
    manifest_path_for,
)
from .fetcher import FetchError, GitHubFetcher, InMemoryFetcher, pick_asset, source_cache_name
from .resolver import (
    FAILED,
    GENERATED,
    OK,
    SKIPPED,
    MaterializedComponent,
    materialize_component,
)
from .pipeline import run_manifest_pipeline

__all__ = [
    "MANIFEST_VERSION",
    "ComponentSpec",
    "SourceSpec",
    "SourcesManifest",
    "validate_manifest_dict",
    "ManifestError",
    "available_manifests",
    "check_against_profile",
    "load_manifest",
    "load_manifest_for_profile",
    "manifest_path_for",
    "FetchError",
    "GitHubFetcher",
    "InMemoryFetcher",
    "pick_asset",
    "source_cache_name",
    "FAILED",
    "GENERATED",
    "OK",
    "SKIPPED",
    "MaterializedComponent",
    "materialize_component",
    "run_manifest_pipeline",
]
