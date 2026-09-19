"""Provider di detection per Windows (OpenHackintosh 2.0.1 Stable).

Esattamente le stesse regole del provider Linux:

- Non inventiamo mai un componente;
- un dato non disponibile -> ``unknown()`` (NOT_DETECTED, value=null);
- distinguiamo sempre DETECTED / INFERRED (deduced) / NOT_AVAILABLE_ON_PLATFORM.

Come funziona
-------------
Una sola invocazione di PowerShell (batched) raccoglie, via CIM, tutto il
necessario: DMI (computer system + baseboard + BIOS), CPU, device PnP
(PCI e USB, con VEN/DEV o VID/PID), dischi, schede di rete e firmware type.
L'output e' JSON; le funzioni ``parse_*`` sono PURE e testabili con fixture,
senza Windows e senza PowerShell.

Perché PowerShell CIM e non ``wmic``: wmic e' deprecato e rimosso dalle build
recenti di Windows 11. ``Get-CimInstance`` funziona su Windows 10/11 stock
(PowerShell 5.1, sempre presente) senza privilegi di amministratore.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from utils.platforms import PLATFORM_WINDOWS, current_platform

from .detection import (
    PCI_VENDOR_NAMES,
    DetectedValue,
    _infer_cpu_generation,
    _pci_vendor_name,
    deduced,
    detected,
    not_available,
    unknown,
)

# Timeout unico per l'intera raccolta batched. Get-CimInstance su Win32_PnPEntity
# puo' richiedere alcuni secondi su macchine lente: restiamo conservativi.
PS_TIMEOUT = 90


# ---------------------------------------------------------------------------
# Esecuzione PowerShell
# ---------------------------------------------------------------------------


def _powershell_bin() -> Optional[str]:
    """powershell.exe (5.1, sempre presente su Win10/11) o pwsh (7+) se installato."""
    for candidate in ("powershell", "pwsh"):
        path = shutil.which(candidate)
        if path:
            return candidate
    return None


def powershell_available() -> bool:
    return current_platform() == PLATFORM_WINDOWS and _powershell_bin() is not None


# Script unico: un solo processo PowerShell per tutta la detection.
# ConvertTo-Json escapinga i non-ASCII come \uXXXX, quindi il parse e' sicuro
# indipendentemente dal codepage della console.
_PS_SCRIPT = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$out = [ordered]@{}
$out.computerSystem = Get-CimInstance Win32_ComputerSystem |
    Select-Object -First 1 Manufacturer,Model,SystemFamily
$out.baseBoard = Get-CimInstance Win32_BaseBoard |
    Select-Object -First 1 Manufacturer,Product,Version,SerialNumber
$out.bios = Get-CimInstance Win32_BIOS |
    Select-Object -First 1 Manufacturer,SMBIOSBIOSVersion,ReleaseDate
$out.cpu = Get-CimInstance Win32_Processor |
    Select-Object -First 1 Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed
try {
    $out.pnp = @(
        Get-CimInstance Win32_PnPEntity |
        Where-Object { $_.DeviceID -match '^(PCI|USB)\\' } |
        Select-Object Name,PNPClass,DeviceID
    )
} catch { $out.pnp = @() }
try {
    $out.disks = @(Get-CimInstance Win32_DiskDrive | Select-Object Model,Size)
} catch { $out.disks = @() }
try {
    $out.netAdapters = @(
        Get-NetAdapter -ErrorAction Stop | Select-Object Name,InterfaceDescription
    )
} catch { $out.netAdapters = @() }
$out.firmwareType = $null
try {
    $out.firmwareType = (
        Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control' `
            -Name PEFirmwareType -ErrorAction Stop
    ).PEFirmwareType
} catch {}
$out | ConvertTo-Json -Depth 4 -Compress
"""


def run_powershell(script: str = _PS_SCRIPT, timeout: int = PS_TIMEOUT) -> Optional[Dict[str, Any]]:
    """Esegue lo script e restituisce il dict JSON. Mai eccezioni: None se fallisce."""
    if current_platform() != PLATFORM_WINDOWS:
        return None
    shell = _powershell_bin()
    if not shell:
        return None
    cmd = [
        shell,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-Command", script,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return None
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return None
    try:
        data = json.loads(proc.stdout)
    except (ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# Parsing (puro, testabile con fixture)
# ---------------------------------------------------------------------------

#: PCI\VEN_8086&DEV_9D70&...  oppure  USB\VID_046D&PID_C52B&...
PnpIdRE = re.compile(
    r"(?:PCI\\VEN_|USB\\VID_)([0-9A-Fa-f]{4})&(?:DEV|PID)_([0-9A-Fa-f]{4})",
    re.IGNORECASE,
)


def parse_ids(device_path: str) -> Dict[str, str]:
    """Estrae vendor/device id dal DeviceID PnP. Id in formato "xxxx:xxxx"."""
    match = PnpIdRE.search(device_path or "")
    if not match:
        return {"vendor_id": "", "device_id": "", "id": ""}
    vendor = match.group(1).lower()
    device = match.group(2).lower()
    return {"vendor_id": vendor, "device_id": device, "id": f"{vendor}:{device}"}


def classify_pnp_device(name: str, pnp_class: str, device_path: str) -> str:
    """Classificazione hardware dal nome/classe PnP. Mai inventata:

    - "display"  GPU;            - "audio"    controller audio HDA;
    - "wifi"     NIC wireless;   - "ethernet" NIC cablata;
    - "usb_ctrl" host controller USB;  - "usb_dev" altri device USB;
    - "bluetooth" radio Bluetooth (di solito su bus USB);
    - "sata" / "nvme" controller storage; - "other" il resto.
    """
    cls = (pnp_class or "").strip().lower()
    lname = (name or "").strip().lower()

    if cls == "display":
        return "display"
    if cls in ("media", "sound", "hdaudio"):
        if "audio" in lname or "sound" in lname or cls == "hdaudio":
            return "audio"
        return "other"
    if cls == "bluetooth":
        return "bluetooth"
    if cls == "net":
        if any(t in lname for t in ("wi-fi", "wifi", "wireless", "802.11", "wlan")):
            return "wifi"
        return "ethernet"
    if cls in ("usb",):
        if any(t in lname for t in ("host controller", "controller host", "xhci", "ehci", "extensible")):
            return "usb_ctrl"
        return "usb_dev"
    if cls in ("scsiadapter", "hdc", "sdhost"):
        if "nvme" in lname or "nvm express" in lname:
            return "nvme"
        if any(t in lname for t in ("sata", "ahci", "raid")):
            return "sata"
        return "other"
    # Classi mancanti ma nome esplicito (PNPClass e' spesso vuota).
    if not cls:
        if "bluetooth" in lname and "v-enumerat" not in lname and "enumerator" not in lname:
            return "bluetooth"
    return "other"


def parse_pnp_devices(devices: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Raggruppa i device PnP nelle stesse categorie usate da lspci su Linux.

    Le voci replicate volutamente lo stesso schema di ``parse_lspci`` cosi' che
    ``_component_fields`` e tutto il resto della detection funzionino identici.
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    if not isinstance(devices, list):
        devices = [devices] if devices else []
    for raw in devices:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("Name") or "").strip()
        cls = str(raw.get("PNPClass") or "").strip()
        device_path = str(raw.get("DeviceID") or "").strip()
        kind = classify_pnp_device(name, cls, device_path)
        if kind == "other":
            continue
        ids = parse_ids(device_path)
        entry = {
            "slot": device_path,
            "name": name,
            "class_code": cls.lower(),
            "class": kind,
            "description": name,
            "vendor_id": ids["vendor_id"],
            "device_id": ids["device_id"],
            "id": ids["id"],
            "revision": "",
        }
        grouped.setdefault(kind, []).append(entry)
    return grouped


def _first(obj: Any) -> Dict[str, Any]:
    """ConvertTo-Json puo' restituire un oggetto singolo o una lista."""
    if isinstance(obj, list):
        return obj[0] if obj else {}
    return obj if isinstance(obj, dict) else {}


def parse_bios_date(value: Any) -> str:
    """Data BIOS in forma leggibile (best effort, mai inventata)."""
    if value in (None, ""):
        return ""
    text = str(value)
    if text.startswith("/Date("):  # formato legacy PS 5.1: /Date(1631664000000)/
        digits = re.sub(r"\D", "", text)
        if digits:
            try:
                import datetime as _dt

                ts = int(digits[:10] if len(digits) > 10 else digits)
                return _dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            except (ValueError, OverflowError, OSError):
                return ""
        return ""
    return text[:10] if len(text) >= 10 else text


# ---------------------------------------------------------------------------
# Cache della raccolta (una sola PowerShell per run)
# ---------------------------------------------------------------------------

_WINDOWS_CACHE: Optional[Dict[str, Any]] = None


def _clear_windows_cache() -> None:
    """Svuota la cache (test o detection fresca richiesta esplicita)."""
    global _WINDOWS_CACHE
    _WINDOWS_CACHE = None


def windows_data() -> Dict[str, Any]:
    """Dati grezzi raccolti (cached). Vuoto se non su Windows / PS assente."""
    global _WINDOWS_CACHE
    if _WINDOWS_CACHE is not None:
        return _WINDOWS_CACHE
    data = run_powershell() or {}
    _WINDOWS_CACHE = data
    return data


# ---------------------------------------------------------------------------
# Sezioni di detection (stesso contratto di hardware.detection)
# ---------------------------------------------------------------------------


def _pci_grouped_windows() -> Dict[str, List[Dict[str, Any]]]:
    return parse_pnp_devices(windows_data().get("pnp") or [])


def component_windows(kind: str, prefix: str) -> Dict[str, DetectedValue]:
    """Primo device PnP di una categoria, come campi DetectedValue (come _component_fields)."""
    grouped = _pci_grouped_windows()
    entries = grouped.get(kind, [])
    if not entries:
        return {prefix: unknown(), f"{prefix}_id": unknown()}
    dev = entries[0]
    ids = dev.get("id") or ""
    label = f"{dev.get('description', '')} [{ids}]" if ids else dev.get("description", "")
    out = {
        prefix: detected(label) if label else unknown(),
        f"{prefix}_id": detected(ids) if ids else unknown(),
        f"{prefix}_vendor": detected(_pci_vendor_name(dev.get("vendor_id", "")))
        if dev.get("vendor_id") else unknown(),
        f"{prefix}_model": detected(dev.get("description", "")) if dev.get("description") else unknown(),
        f"{prefix}_vendor_id": detected(dev.get("vendor_id")) if dev.get("vendor_id") else unknown(),
        f"{prefix}_device_id": detected(dev.get("device_id")) if dev.get("device_id") else unknown(),
        f"{prefix}_pci": detected(dev.get("slot")) if dev.get("slot") else unknown(),
    }
    return out


def detect_dmi_windows() -> Dict[str, DetectedValue]:
    data = windows_data()
    cs = _first(data.get("computerSystem"))
    bb = _first(data.get("baseBoard"))
    bios = _first(data.get("bios"))
    out = {
        "system_vendor": detected(cs.get("Manufacturer", "")) if cs.get("Manufacturer") else unknown(),
        "product_name": detected(cs.get("Model", "")) if cs.get("Model") else unknown(),
        "product_version": detected(cs.get("SystemFamily", "")) if cs.get("SystemFamily") else unknown(),
        "board_vendor": detected(bb.get("Manufacturer", "")) if bb.get("Manufacturer") else unknown(),
        "board_name": detected(bb.get("Product", "")) if bb.get("Product") else unknown(),
        "board_version": detected(bb.get("Version", "")) if bb.get("Version") else unknown(),
        "bios_vendor": detected(bios.get("Manufacturer", "")) if bios.get("Manufacturer") else unknown(),
        "bios_version": detected(bios.get("SMBIOSBIOSVersion", ""))
        if bios.get("SMBIOSBIOSVersion") else unknown(),
        "bios_date": detected(parse_bios_date(bios.get("ReleaseDate")))
        if parse_bios_date(bios.get("ReleaseDate")) else unknown(),
    }
    return out


def detect_cpu_windows() -> Dict[str, DetectedValue]:
    import os
    import platform as _platform

    cpu = _first(windows_data().get("cpu"))
    name = str(cpu.get("Name") or "").strip()
    manufacturer = str(cpu.get("Manufacturer") or "").strip()
    cores = cpu.get("NumberOfCores")
    threads = cpu.get("NumberOfLogicalProcessors")
    mhz = cpu.get("MaxClockSpeed")

    info: Dict[str, DetectedValue] = {}
    info["processor"] = detected(name) if name else unknown()
    info["architecture"] = detected(_platform.machine()) if _platform.machine() else unknown()
    info["model"] = detected(name) if name else unknown()
    info["vendor"] = detected(manufacturer) if manufacturer else unknown()
    info["frequency_mhz"] = detected(str(mhz)) if mhz else unknown()

    if cores:
        info["cores"] = detected(str(cores))
    elif os.cpu_count():
        info["cores"] = deduced(str(os.cpu_count()))
    else:
        info["cores"] = unknown()
    if threads:
        info["threads"] = detected(str(threads))
    elif os.cpu_count():
        info["threads"] = deduced(str(os.cpu_count()))
    else:
        info["threads"] = unknown()

    # Generazione: stessa inferenza sicura del provider Linux.
    generation = _infer_cpu_generation(name)
    info["generation"] = deduced(generation) if generation else unknown()

    # Feature flags CPU: non esposti in modo affidabile via CIM -> onesti.
    info["features"] = unknown()
    info["feature_list"] = unknown()
    return info


def detect_gpu_windows() -> Dict[str, DetectedValue]:
    grouped = _pci_grouped_windows()
    displays = grouped.get("display", [])
    if not displays:
        return {"gpu": unknown(), "gpu_id": unknown()}
    primary = displays[0]
    out = component_windows("display", "gpu")
    # Tipo iGPU/dGPU: stessa inferenza logica del provider Linux.
    vendor_id = (primary.get("vendor_id") or "").lower()
    if vendor_id == "8086":
        out["gpu_type"] = deduced("integrated")
    elif vendor_id in ("1002", "10de"):
        out["gpu_type"] = deduced("discrete")
    else:
        out["gpu_type"] = unknown()
    # VRAM non esposta in modo affidabile via CIM per iGPU: NOT rilevato.
    out["gpu_vram"] = unknown()
    return out


def detect_usb_windows() -> Dict[str, DetectedValue]:
    grouped = _pci_grouped_windows()
    controllers = grouped.get("usb_ctrl", [])
    devices = grouped.get("usb_dev", [])
    out: Dict[str, DetectedValue] = {}
    if controllers:
        names = ", ".join(
            f"{d['description']} [{d['id']}]" if d.get("id") else d["description"]
            for d in controllers
        )
        out["usb_controllers"] = detected(names)
        out["usb_controller_list"] = detected(controllers)
    else:
        out["usb_controllers"] = unknown()
        out["usb_controller_list"] = unknown()
    if devices:
        listings = []
        for dev in devices:
            listings.append(
                {
                    "bus": "",
                    "device": "",
                    "vendor_id": dev.get("vendor_id", ""),
                    "device_id": dev.get("device_id", ""),
                    "id": dev.get("id", ""),
                    "description": dev.get("description", ""),
                    "vendor_name": PCI_VENDOR_NAMES.get(dev.get("vendor_id", ""), ""),
                }
            )
        out["usb_devices"] = detected(listings)
        out["usb_count"] = detected(len(listings))
    else:
        out["usb_devices"] = unknown()
        out["usb_count"] = unknown()
    return out


def detect_bluetooth_windows() -> Dict[str, DetectedValue]:
    fields = component_windows("bluetooth", "bluetooth")
    fields.setdefault("bluetooth_vendor", unknown())
    fields.setdefault("bluetooth_vendor_id", unknown())
    fields.setdefault("bluetooth_device_id", unknown())
    return fields


def detect_sata_nvme_windows() -> Dict[str, DetectedValue]:
    grouped = _pci_grouped_windows()
    sata = grouped.get("sata", [])
    nvme = grouped.get("nvme", [])

    def join(entries: List[Dict[str, Any]]) -> str:
        return ", ".join(
            f"{d['description']} [{d['id']}]" if d.get("id") else d["description"]
            for d in entries
        )

    return {
        "sata_controllers": detected(join(sata)) if sata else unknown(),
        "nvme_controllers": detected(join(nvme)) if nvme else unknown(),
    }


def detect_storage_windows() -> Dict[str, DetectedValue]:
    disks = windows_data().get("disks") or []
    if not isinstance(disks, list):
        disks = [disks] if disks else []
    entries: List[str] = []
    for disk in disks:
        if not isinstance(disk, dict):
            continue
        model = str(disk.get("Model") or "").strip()
        size = disk.get("Size")
        try:
            gb = int(size) // (1024 ** 3)
        except (TypeError, ValueError):
            gb = 0
        if model:
            entries.append(f"{model} ({gb} GB)" if gb else model)
    return {
        "storage": detected(", ".join(entries)) if entries else unknown(),
        "storage_count": detected(len(entries)) if entries else unknown(),
    }


def detect_net_interfaces_windows() -> Dict[str, DetectedValue]:
    adapters = windows_data().get("netAdapters") or []
    if not isinstance(adapters, list):
        adapters = [adapters] if adapters else []
    names = [
        str(a.get("Name") or "").strip()
        for a in adapters
        if isinstance(a, dict) and str(a.get("Name") or "").strip()
    ]
    return {"net_interfaces": detected(", ".join(names)) if names else unknown()}


def detect_uefi_windows() -> DetectedValue:
    """UEFI vs Legacy da PEFirmwareType (registry, usato anche da setupapi).

    INFERRED (deduced): e' una chiave di registry, non una lettura diretta
    del firmware. Mai marcata DETECTED.
    """
    fw_type = windows_data().get("firmwareType")
    try:
        fw_type = int(fw_type)
    except (TypeError, ValueError):
        return unknown()
    if fw_type == 2:
        return deduced("UEFI")
    if fw_type == 1:
        return deduced("Legacy BIOS")
    return unknown()


def detect_acpi_windows() -> Dict[str, DetectedValue]:
    reason = "ACPI table enumeration not available via CIM on Windows"
    return {
        "acpi_tables": not_available(reason),
        "acpi_table_list": not_available(reason),
        "dsdt_present": not_available(reason),
    }
