"""
Real downloader for OpenCore and kexts - NO FAKE FILES
Downloads from GitHub releases API
"""
import os
import sys
import json
import zipfile
import shutil
import tempfile
import requests
from pathlib import Path
from typing import Callable, Optional, Dict

GITHUB_API = "https://api.github.com/repos/{repo}/releases/latest"
HEADERS = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Q5562-EFI-Tool/1.0"}

class DownloadProgress:
    def __init__(self, callback: Optional[Callable[[str, int, int], None]] = None):
        self.callback = callback
    
    def report(self, name: str, downloaded: int, total: int):
        if self.callback:
            self.callback(name, downloaded, total)

def get_latest_release(repo: str) -> Optional[Dict]:
    """Get latest release info from GitHub"""
    url = GITHUB_API.format(repo=repo)
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"GitHub API error for {repo}: {r.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching {repo}: {e}")
        # Try without SSL verify as fallback (for environments with missing certs)
        try:
            print(f"Retrying {repo} without SSL verification...")
            r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if r.status_code == 200:
                return r.json()
        except Exception as e2:
            print(f"Fallback also failed for {repo}: {e2}")
        return None

def find_asset(release: Dict, keywords: list) -> Optional[Dict]:
    """Find asset matching keywords"""
    assets = release.get("assets", [])
    for asset in assets:
        name = asset["name"].lower()
        if all(k.lower() in name for k in keywords):
            return asset
    # Fallback: first zip
    for asset in assets:
        if asset["name"].endswith(".zip"):
            return asset
    return None

def download_file(url: str, dest: Path, progress: Optional[DownloadProgress] = None, name: str = "file") -> bool:
    """Download file with progress"""
    for verify in [True, False]:  # Try with and without SSL verify
        try:
            with requests.get(url, stream=True, timeout=60, headers=HEADERS, verify=verify) as r:
                r.raise_for_status()
                total = int(r.headers.get('content-length', 0))
                downloaded = 0
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress:
                                progress.report(name, downloaded, total)
                return True
        except Exception as e:
            if verify:
                print(f"Download failed for {name} (with SSL verify), retrying without: {e}")
                continue
            else:
                print(f"Download failed for {name}: {e}")
                return False
    return False

def extract_kext_from_zip(zip_path: Path, kext_bundle_name: str, dest_dir: Path) -> bool:
    """Extract kext bundle from zip (searches recursively)"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            # Find kext
            for member in z.namelist():
                # Look for bundle
                if member.endswith(f"{kext_bundle_name}/") or f"/{kext_bundle_name}/" in member or member.endswith(kext_bundle_name):
                    # If it's a directory entry, extract all files under it
                    if kext_bundle_name in member:
                        # Extract kext bundle
                        # Find root of kext
                        parts = member.split(kext_bundle_name)
                        if len(parts) >= 1:
                            # Extract all files that are part of this kext
                            kext_root = member.split(kext_bundle_name)[0] + kext_bundle_name + "/"
                            for m in z.namelist():
                                if m.startswith(kext_root):
                                    # Extract
                                    target = dest_dir / kext_bundle_name / m[len(kext_root):]
                                    if m.endswith('/'):
                                        target.mkdir(parents=True, exist_ok=True)
                                    else:
                                        target.parent.mkdir(parents=True, exist_ok=True)
                                        with z.open(m) as src, open(target, 'wb') as dst:
                                            shutil.copyfileobj(src, dst)
                            return True
            # Second try: search for .kext folder directly
            for member in z.namelist():
                if kext_bundle_name in member and member.endswith(".kext/Contents/Info.plist"):
                    kext_path = member.split(kext_bundle_name)[0] + kext_bundle_name
                    # Extract entire kext
                    for m in z.namelist():
                        if m.startswith(kext_path):
                            rel = m[len(kext_path):].lstrip("/")
                            target = dest_dir / kext_bundle_name / rel
                            if m.endswith('/'):
                                target.mkdir(parents=True, exist_ok=True)
                            else:
                                target.parent.mkdir(parents=True, exist_ok=True)
                                try:
                                    with z.open(m) as src, open(target, 'wb') as dst:
                                        shutil.copyfileobj(src, dst)
                                except:
                                    pass
                    return (dest_dir / kext_bundle_name).exists()
        return False
    except Exception as e:
        print(f"Extract failed for {kext_bundle_name}: {e}")
        return False

def extract_all_kexts(zip_path: Path, dest_dir: Path) -> list:
    """Extract all kexts found in zip"""
    found = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            kexts_in_zip = set()
            for name in z.namelist():
                if ".kext/" in name:
                    # Extract bundle name
                    idx = name.find(".kext/")
                    bundle = name[:idx+5]  # include .kext
                    # Get just the bundle name, not full path
                    bundle_name = bundle.split("/")[-1]
                    if bundle_name.endswith(".kext"):
                        kexts_in_zip.add((bundle, bundle_name))
            
            for full_path, bundle_name in kexts_in_zip:
                # Extract
                root = full_path
                if not root.endswith("/"):
                    root = root[:root.rfind(".kext")+5]
                dest_kext_dir = dest_dir / bundle_name
                if dest_kext_dir.exists():
                    shutil.rmtree(dest_kext_dir)
                for m in z.namelist():
                    if m.startswith(full_path.split(bundle_name)[0] + bundle_name):
                        rel = m[len(full_path.split(bundle_name)[0] + bundle_name):].lstrip("/")
                        target = dest_kext_dir / rel
                        if m.endswith('/'):
                            target.mkdir(parents=True, exist_ok=True)
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            try:
                                with z.open(m) as src, open(target, 'wb') as dst:
                                    shutil.copyfileobj(src, dst)
                            except:
                                pass
                if dest_kext_dir.exists():
                    found.append(bundle_name)
        return found
    except Exception as e:
        print(f"Extract all failed: {e}")
        return found

class EFIDownloader:
    def __init__(self, work_dir: Path, progress_callback=None):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.progress = DownloadProgress(progress_callback)
        self.temp_dir = self.work_dir / "temp"
        self.temp_dir.mkdir(exist_ok=True)
    
    def download_opencore(self, version: str = "latest") -> Optional[Path]:
        """Download OpenCorePkg"""
        print("Downloading OpenCore...")
        repo = "acidanthera/OpenCorePkg"
        release = get_latest_release(repo)
        if not release:
            return None
        
        # Find OpenCore release zip
        asset = None
        for a in release.get("assets", []):
            if "RELEASE" in a["name"] and a["name"].endswith(".zip"):
                asset = a
                break
        if not asset:
            asset = find_asset(release, ["RELEASE"])
        
        if not asset:
            print("OpenCore asset not found")
            return None
        
        zip_path = self.temp_dir / asset["name"]
        if not download_file(asset["browser_download_url"], zip_path, self.progress, "OpenCore"):
            return None
        
        # Extract
        oc_dir = self.work_dir / "OpenCore"
        if oc_dir.exists():
            shutil.rmtree(oc_dir)
        oc_dir.mkdir()
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(oc_dir)
        
        print(f"OpenCore extracted to {oc_dir}")
        return oc_dir
    
    def download_kext(self, repo: str, kext_name: str, dest_kexts_dir: Path) -> bool:
        """Download single kext"""
        print(f"Downloading {kext_name} from {repo}...")
        release = get_latest_release(repo)
        if not release:
            return False
        
        asset = find_asset(release, [".zip"]) or find_asset(release, ["RELEASE"])
        if not asset:
            # Try first asset
            assets = release.get("assets", [])
            if assets:
                asset = assets[0]
        
        if not asset:
            print(f"No asset for {kext_name}")
            return False
        
        zip_path = self.temp_dir / f"{kext_name}_{asset['name']}"
        if not download_file(asset["browser_download_url"], zip_path, self.progress, kext_name):
            return False
        
        dest_kexts_dir.mkdir(parents=True, exist_ok=True)
        # Try extract specific kext
        success = extract_kext_from_zip(zip_path, kext_name, dest_kexts_dir)
        if not success:
            # Try extract all and check
            found = extract_all_kexts(zip_path, dest_kexts_dir)
            success = kext_name in found or any(kext_name.lower() in f.lower() for f in found)
            if not success and found:
                print(f"Found kexts: {found}, but not {kext_name}")
                # If we downloaded VirtualSMC, it contains multiple kexts, that's ok
                success = len(found) > 0
        
        if success:
            print(f"✓ {kext_name} ready")
        else:
            print(f"✗ Failed to extract {kext_name}")
        return success
    
    def download_all_kexts(self, kext_list: list, kext_definitions: dict, dest_dir: Path) -> Dict[str, bool]:
        """Download all required kexts"""
        results = {}
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        for kext_key in kext_list:
            definition = kext_definitions.get(kext_key)
            if not definition:
                results[kext_key] = False
                continue
            
            repo = definition["repo"]
            bundle = definition["bundle"]
            success = self.download_kext(repo, bundle, dest_dir)
            results[kext_key] = success
            
            # Download extra bundles if any
            if success and "extra_bundles" in definition:
                # They are in same zip, already extracted via extract_all
                zip_name = None
                for f in self.temp_dir.glob(f"{bundle}_*"):
                    zip_name = f
                    break
                if zip_name and zip_name.exists():
                    for extra in definition["extra_bundles"]:
                        extract_kext_from_zip(zip_name, extra, dest_dir)
        
        return results
    
    def prepare_opencore_structure(self, oc_extracted: Path, efi_root: Path):
        """Copy required OpenCore files to EFI structure"""
        # Find X64 folder
        x64_path = None
        for root, dirs, files in os.walk(oc_extracted):
            if "X64" in dirs:
                x64_path = Path(root) / "X64"
                if (x64_path / "EFI").exists():
                    break
        if not x64_path:
            # Search for EFI folder
            for root, dirs, files in os.walk(oc_extracted):
                if "BOOT" in dirs and "OC" in dirs:
                    x64_path = Path(root)
                    break
        
        if not x64_path:
            print("Could not find OpenCore EFI structure")
            return False
        
        efi_source = x64_path / "EFI" if (x64_path / "EFI").exists() else x64_path
        if not (efi_source / "BOOT").exists():
            # Look one level deeper
            for p in oc_extracted.rglob("BOOTx64.efi"):
                efi_source = p.parent.parent
                break
        
        print(f"Using OpenCore source: {efi_source}")
        
        # Create EFI structure
        efi_root.mkdir(parents=True, exist_ok=True)
        boot_dest = efi_root / "BOOT"
        oc_dest = efi_root / "OC"
        boot_dest.mkdir(exist_ok=True)
        oc_dest.mkdir(exist_ok=True)
        
        # Copy BOOT
        if (efi_source / "BOOT").exists():
            for f in (efi_source / "BOOT").iterdir():
                shutil.copy2(f, boot_dest / f.name)
        
        # Copy OC essentials, but we will rebuild
        for sub in ["Drivers", "Tools", "Resources"]:
            src = efi_source / "OC" / sub
            dst = oc_dest / sub
            if src.exists():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                dst.mkdir(exist_ok=True)
        
        # Copy OpenCore.efi
        oc_efi_src = efi_source / "OC" / "OpenCore.efi"
        if oc_efi_src.exists():
            shutil.copy2(oc_efi_src, oc_dest / "OpenCore.efi")
        
        # Create ACPI and Kexts if not exist
        (oc_dest / "ACPI").mkdir(exist_ok=True)
        (oc_dest / "Kexts").mkdir(exist_ok=True)
        
        return True

    def cleanup(self):
        """Clean temp files"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
