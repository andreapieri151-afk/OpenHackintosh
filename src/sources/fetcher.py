"""
Fetcher: scarica archivi/file dichiarati nel sources manifest.

Due implementazioni:
- GitHubFetcher: produzione. GitHub Releases API + raw.githubusercontent.com,
  cache su disco, fallback SSL, invalidazione cache se lo zip e' corrotto.
- InMemoryFetcher: test/offline. Serve bytes registrati in memoria.

Il fetcher e' l'UNICO punto di contatto con la rete dell'intero motore:
resolver e pipeline sono puri e testabili senza rete.
"""

from __future__ import annotations

import fnmatch
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from .schema import SourceSpec


class FetchError(RuntimeError):
    """Impossibile ottenere il componente dalla fonte dichiarata."""


def source_cache_name(source: SourceSpec) -> str:
    """Nome stabile per la cache/lookup di un archivio."""
    if source.type == "github_release":
        repo = source.repo.replace("/", "__")
        asset = source.asset or "any.zip"
        tag = source.tag or "latest"
        return f"{repo}__{tag}__{asset}".replace("*", "any").replace("?", "_")
    if source.type == "url":
        return source.url.split("/")[-1] or "download.bin"
    return "archive.bin"


def pick_asset(assets: list, pattern: str) -> Optional[dict]:
    """Sceglie l'asset di una release GitHub con fnmatch sul nome.

    pattern vuoto -> primo .zip; nessun match -> None (MAI fallback silenziosi
    su asset diversi da quelli dichiarati nel manifest).
    """
    if not assets:
        return None
    if pattern:
        for asset in assets:
            if fnmatch.fnmatch(asset.get("name", ""), pattern):
                return asset
        return None
    for asset in assets:
        if asset.get("name", "").endswith(".zip"):
            return asset
    return assets[0] if assets else None


class InMemoryFetcher:
    """Fetcher per test: archivi e file registrati in memoria.

    Le chiavi sono prodotte da ``source_cache_name`` (per gli archivi) e da
    ``bytes_key`` (per i file singoli).
    """

    def __init__(self, work_dir: Optional[Path] = None):
        import tempfile
        self.archives: Dict[str, bytes] = {}
        self.files: Dict[str, bytes] = {}
        self._tmp = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="oh-inmem-"))
        self._tmp.mkdir(parents=True, exist_ok=True)
        self.calls: list = []

    @staticmethod
    def bytes_key(source: SourceSpec) -> str:
        if source.type == "github_raw":
            return f"raw:{source.repo}@{source.ref}/{source.path}"
        return source.url

    def register_archive(self, source: SourceSpec, data: bytes) -> None:
        self.archives[source_cache_name(source)] = data

    def register_bytes(self, source: SourceSpec, data: bytes) -> None:
        self.files[self.bytes_key(source)] = data

    def fetch_archive(self, source: SourceSpec) -> Path:
        self.calls.append(("archive", source_cache_name(source)))
        data = self.archives.get(source_cache_name(source))
        if data is None:
            raise FetchError(f"archivio non disponibile: {source.summary()}")
        if not zipfile.is_zipfile(io.BytesIO(data)):
            raise FetchError(f"archivio corrotto (non e' uno zip): {source.summary()}")
        dest = self._tmp / source_cache_name(source)
        dest.write_bytes(data)
        return dest

    def fetch_bytes(self, source: SourceSpec) -> Tuple[bytes, str]:
        key = self.bytes_key(source)
        self.calls.append(("bytes", key))
        data = self.files.get(key)
        if data is None:
            raise FetchError(f"file non disponibile: {source.summary()}")
        return data, key


class GitHubFetcher:
    """Fetcher reale: GitHub Releases + raw.githubusercontent.com.

    Riutilizza la rete di ``efi_builder.downloader`` (requests con fallback
    SSL e cache). Nessuna logica di validazione qui: quella spetta al resolver.
    """

    def __init__(self, work_dir: Path, cache_dir: Optional[Path] = None,
                 log: Optional[Callable[[str], None]] = None):
        from utils.platforms import default_cache_dir

        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = Path(cache_dir) if cache_dir else default_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log = log or print

    # -- GitHub API ---------------------------------------------------------

    def _get_release(self, repo: str, tag: str) -> Optional[dict]:
        from efi_builder import downloader

        if not tag or tag == "latest":
            return downloader.get_latest_release(repo)

        requests = downloader._requests()
        url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
        for verify in (True, False):
            try:
                r = requests.get(url, headers=downloader.HEADERS, timeout=15, verify=verify)
                if r.status_code == 200:
                    return r.json()
                if verify:
                    continue
                self.log(f"GitHub API error for {repo}@{tag}: {r.status_code}")
                return None
            except Exception as exc:
                if verify:
                    continue
                self.log(f"Error fetching {repo}@{tag}: {exc}")
                return None
        return None

    # -- Interfaccia Fetcher -------------------------------------------------

    def fetch_archive(self, source: SourceSpec) -> Path:
        if source.type != "github_release":
            raise FetchError(f"fetch_archive supporta solo github_release, non {source.type!r}")

        release = self._get_release(source.repo, source.tag)
        if not release:
            raise FetchError(f"release non trovata: {source.repo} ({source.tag})")

        asset = pick_asset(release.get("assets", []), source.asset)
        if not asset:
            raise FetchError(
                f"nessun asset corrisponde al pattern {source.asset!r} in {source.repo}"
            )

        cache_name = asset["name"]
        url = asset["browser_download_url"]
        dest = self.cache_dir / cache_name

        for attempt in (0, 1):
            if dest.exists() and dest.stat().st_size > 0 and zipfile.is_zipfile(dest):
                self.log(f"Cache hit: {dest}")
                return dest

            from efi_builder.downloader import download_file

            if dest.exists():
                dest.unlink(missing_ok=True)
            if not download_file(url, dest, None, cache_name):
                raise FetchError(f"download fallito: {url}")
            if zipfile.is_zipfile(dest):
                return dest
            self.log(f"Zip corrotto (tentativo {attempt + 1}), invalido la cache e riscarico")

        raise FetchError(f"archivio corrotto dopo 2 tentativi: {url}")

    def fetch_bytes(self, source: SourceSpec) -> Tuple[bytes, str]:
        if source.type == "github_raw":
            url = f"https://raw.githubusercontent.com/{source.repo}/{source.ref}/{source.path}"
        elif source.type == "url":
            url = source.url
        else:
            raise FetchError(f"fetch_bytes supporta github_raw/url, non {source.type!r}")

        from efi_builder import downloader

        requests = downloader._requests()
        last_error: Optional[Exception] = None
        for verify in (True, False):
            try:
                r = requests.get(url, headers=downloader.HEADERS, timeout=30, verify=verify)
                if r.status_code == 200:
                    return r.content, url
                last_error = FetchError(f"HTTP {r.status_code} per {url}")
            except Exception as exc:
                last_error = exc
        raise FetchError(f"download fallito: {url} ({last_error})")
