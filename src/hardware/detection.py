"""
Hardware detection per OpenHackintosh.

Regole rigorose:
- Non inventamo mai un componente.
- Se un dato non è disponibile -> "Unknown / Not detected".
- Distinguiamo sempre:
    DETECTED  -> letto dalla macchina reale
    DEDUCED   -> derivato in modo sicuro da un dato rilevato
    UNKNOWN   -> non disponibile

Supporto:
- Linux (sysfs, lspci, dmi)  -> implementato e testabile in sandbox
- macOS / BSD               -> best effort (non ancora testato su hardware reale)
- Windows                   -> non disponibile in questa release
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


UNKNOWN = "Unknown / Not detected"

# Stati espliciti di un valore hardware. Mai confondere:
# - DETECTED: letto dall'hardware reale;
# - INFERRED: derivato in modo sicuro da un dato rilevato (non inventato);
# - DATABASE_MATCH: valore fornito da un profilo del database (solo dopo match);
# - NOT_DETECTED: non rilevato, value=null;
# - UNKNOWN: informazione insufficiente.
STATUS_DETECTED = "DETECTED"
STATUS_INFERRED = "INFERRED"
STATUS_DATABASE_MATCH = "DATABASE_MATCH"
STATUS_NOT_DETECTED = "NOT_DETECTED"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_NOT_AVAILABLE = "NOT_AVAILABLE_ON_PLATFORM"


@dataclass
class DetectedValue:
    """Valore hardware + provenienza e stato del dato."""

    value: Any = None
    source: str = "unknown"  # detected | deduced | database | unknown
    status: str = STATUS_NOT_DETECTED

    @property
    def display_value(self) -> str:
        if self.value is None:
            return UNKNOWN
        if isinstance(self.value, str) and not self.value.strip():
            return UNKNOWN
        if isinstance(self.value, (list, tuple)):
            return ", ".join(str(v) for v in self.value) if self.value else UNKNOWN
        return str(self.value)

    def to_dict(self) -> Dict[str, Any]:
        raw = self.value
        if raw is None:
            raw = None
        elif isinstance(raw, str) and not raw.strip():
            raw = None
        return {
            "value": raw,
            "status": self.status,
            "source": self.source,
        }

    def __str__(self) -> str:
        return self.display_value


def detected(value: Any) -> DetectedValue:
    if value in (None, "") or (isinstance(value, (list, tuple)) and not value):
        return unknown()
    return DetectedValue(value, "detected", STATUS_DETECTED)


def deduced(value: Any) -> DetectedValue:
    if value in (None, "") or (isinstance(value, (list, tuple)) and not value):
        return unknown()
    return DetectedValue(value, "deduced", STATUS_INFERRED)


def database_match(value: Any) -> DetectedValue:
    if value in (None, "") or (isinstance(value, (list, tuple)) and not value):
        return unknown()
    return DetectedValue(value, "database", STATUS_DATABASE_MATCH)


def unknown() -> DetectedValue:
    return DetectedValue(None, "unknown", STATUS_NOT_DETECTED)


def not_available(reason: str = "") -> DetectedValue:
    """Informazione non simulabile sulla piattaforma corrente (NOT_AVAILABLE_ON_PLATFORM)."""
    value = reason or "Not available on this platform"
    return DetectedValue(value, "platform", STATUS_NOT_AVAILABLE)


def _run(cmd: List[str], timeout: int = 8) -> str:
    """Esegue un comando esterno. Mai fallire: in caso errore -> stringa vuota."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            errors="replace",
        )
        if proc.returncode != 0:
            return ""
        return proc.stdout.strip()
    except Exception:
        return ""


def _read_sysfs(path: str) -> str:
    try:
        text = Path(path).read_text(errors="replace").strip()
        return text
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# DMI / BIOS
# ---------------------------------------------------------------------------

def detect_dmi() -> Dict[str, DetectedValue]:
    """Legge SMBIOS/DMI dove disponibile (Linux)."""
    base = "/sys/class/dmi/id"
    keys = {
        "system_vendor": "system_vendor",
        "product_name": "product_name",
        "product_version": "product_version",
        "board_vendor": "board_vendor",
        "board_name": "board_name",
        "board_version": "board_version",
        "bios_vendor": "bios_vendor",
        "bios_version": "bios_version",
        "bios_date": "bios_date",
    }
    out: Dict[str, DetectedValue] = {}
    for field, path in keys.items():
        raw = _read_sysfs(f"{base}/{path}")
        out[field] = detected(raw) if raw else unknown()
    return out


# ---------------------------------------------------------------------------
# CPU
# ---------------------------------------------------------------------------

def _infer_cpu_generation(model: str) -> str:
    """Solo inferenza sicura dal modello reale; mai inventare.

    Intel desktop/note: i3/i5/i7/i9-XXXX -> prima cifra = generazione.
    6 -> Skylake, 7 -> Kaby Lake, 8/9 -> Coffee Lake. Oltre -> non inferibile.
    """
    if not model or "intel" not in model.lower():
        return ""
    import re
    m = re.search(r"\b(?:i[3579][-\s]?)(\d{4})\w*\b", model)
    if not m:
        return ""
    generation = m.group(1)[0]
    base = int(m.group(1))
    if generation == "6":
        return "Skylake (6th Gen)"
    if generation == "7":
        return "Kaby Lake (7th Gen)"
    if generation in ("8", "9"):
        return "Coffee Lake (8th/9th Gen)"
    if base >= 10000:
        return f"Intel Core (generazione basata su modello, non completamente inferita)"
    return "Intel Core (generation not inferred)"


def detect_cpu() -> Dict[str, DetectedValue]:
    info: Dict[str, DetectedValue] = {}

    # platform.processor()
    p = platform.processor() or platform.machine()
    info["processor"] = detected(p) if p and p not in ("unknown",) else unknown()
    info["architecture"] = detected(platform.machine()) if platform.machine() else unknown()

    # /proc/cpuinfo: model name / vendor + cores/threads/features
    model = ""
    vendor = ""
    mhz = ""
    cores = ""
    threads = ""
    flags: List[str] = []
    try:
        for line in Path("/proc/cpuinfo").read_text(errors="replace").splitlines():
            low = line.lower()
            if low.startswith("model name") and not model:
                model = line.split(":", 1)[1].strip()
            elif low.startswith("vendor_id") and not vendor:
                vendor = line.split(":", 1)[1].strip()
            elif low.startswith("cpu mhz") and not mhz:
                mhz = line.split(":", 1)[1].strip()
            elif low.startswith("cpu cores") and not cores:
                cores = line.split(":", 1)[1].strip()
            elif low.startswith("siblings") and not threads:
                threads = line.split(":", 1)[1].strip()
            elif low.startswith("flags") and not flags:
                flags = line.split(":", 1)[1].split()
    except Exception:
        pass

    info["model"] = detected(model) if model else unknown()
    info["vendor"] = detected(vendor) if vendor else unknown()
    info["frequency_mhz"] = detected(mhz) if mhz else unknown()

    # Cores/threads reali da cpuinfo, fallback razionale su poi os.cpu_count() (dedotto)
    if not cores and os.cpu_count():
        cores = str(os.cpu_count())
        info["cores"] = deduced(cores)
    else:
        info["cores"] = detected(cores) if cores else unknown()
    if not threads and os.cpu_count():
        threads = str(os.cpu_count())
        info["threads"] = deduced(threads)
    else:
        info["threads"] = detected(threads) if threads else unknown()

    # Generazione: INFERRED, mai DETECTED. Se il modello non basta -> NOT_DETECTED.
    generation = _infer_cpu_generation(model)
    info["generation"] = deduced(generation) if generation else unknown()

    # Flags CPU: DETECTED quando leggibili; separate per non appesantire il display.
    info["features"] = detected(flags) if flags else unknown()
    info["feature_list"] = detected(flags) if flags else unknown()
    return info


# ---------------------------------------------------------------------------
# PCI / PCIe
# ---------------------------------------------------------------------------

PCI_RE = re.compile(
    r"^(?P<slot>\S+)\s+"
    r"(?P<name>.*?)\s*"
    r"\[(?P<class>\w{4})\]:\s+"
    r"(?P<desc>.*?)\s*"
    r"\[(?P<vendor>[0-9a-f]{4}):(?P<device>[0-9a-f]{4})\]"
    r"(?:\s*\(rev\s+(?P<rev>[0-9a-f]+)\))?"
    r"\s*$",
    re.IGNORECASE,
)

PCI_CLASS = {
    "0300": "display",
    "0301": "display",
    "0302": "display",
    "0380": "display",
    "0401": "audio",
    "0402": "audio",
    "0403": "audio",
    "0200": "ethernet",
    "0201": "ethernet",
    "0280": "network",
    "0c03": "usb",
    "0106": "sata",
    "0108": "nvme",
    "010802": "nvme",
    "0601": "lpc",
    "0604": "pcie-bridge",
}


def _lspci_bin() -> Optional[str]:
    for candidate in ("lspci", "lspci.nopci"):
        path = shutil.which(candidate)
        if path:
            return candidate
    return None


def parse_lspci(text: str) -> List[Dict[str, Any]]:
    devices: List[Dict[str, Any]] = []
    if not text:
        return devices
    for line in text.splitlines():
        m = PCI_RE.match(line.strip())
        if not m:
            continue
        klass = m.group("class").lower()
        vendor = m.group("vendor").lower()
        device = m.group("device").lower()
        devices.append(
            {
                "slot": m.group("slot"),
                "name": m.group("name").strip(),
                "class_code": klass,
                "class": PCI_CLASS.get(klass, "other"),
                "description": m.group("desc").strip(),
                "vendor_id": vendor,
                "device_id": device,
                "id": f"{vendor}:{device}",
                "revision": m.group("rev") or "",
            }
        )
    return devices


def detect_pci() -> Dict[str, DetectedValue]:
    """Lista PCI/PCIe. Source detected se lspci disponibile altrimenti unknown."""
    grouped = _pci_grouped()
    devices = [d for devices in grouped.values() for d in devices]
    if not devices:
        return {"pci_devices": unknown(), "pci_count": unknown()}
    # Arricchisce ogni device con il nome vendor noto (mai inventato).
    enriched = []
    for dev in devices:
        entry = dict(dev)
        entry["vendor_name"] = _pci_vendor_name(dev["vendor_id"])
        enriched.append(entry)
    return {
        "pci_devices": detected(enriched),
        "pci_count": detected(len(enriched)),
    }


# Mappature sicure di vendor ID noti. Per ID sconosciuti usiamo il fatto
# disponibile "PCI 0xVENDOR" (non inventiamo un nome).
PCI_VENDOR_NAMES = {
    "8086": "Intel",
    "10ec": "Realtek",
    "1002": "AMD/ATI",
    "1022": "AMD",
    "14e4": "Broadcom",
    "8087": "Intel",
    "1a03": "ASPEED",
    "0a12": "Cambridge Silicon Radio",
    "0bda": "Realtek",
    "168c": "Qualcomm Atheros",
}


def _pci_vendor_name(vendor_id: str) -> str:
    return PCI_VENDOR_NAMES.get(vendor_id, f"PCI 0x{vendor_id}")


_PCI_GROUPED_CACHE: Optional[Dict[str, List[Dict[str, Any]]]] = None


def _clear_pci_cache() -> None:
    """Svuota la cache PCI (usata nei test e quando si vuole una detection fresca)."""
    global _PCI_GROUPED_CACHE
    _PCI_GROUPED_CACHE = None


def _pci_grouped() -> Dict[str, List[Dict[str, Any]]]:
    global _PCI_GROUPED_CACHE
    if _PCI_GROUPED_CACHE is not None:
        return _PCI_GROUPED_CACHE
    text = _run([_lspci_bin() or "lspci", "-nn", "-D"])
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for dev in parse_lspci(text):
        grouped.setdefault(dev["class"], []).append(dev)
    _PCI_GROUPED_CACHE = grouped
    return grouped


def _component_fields(dev: Dict[str, Any], prefix: str) -> Dict[str, DetectedValue]:
    """Campi strutturati comuni per un device PCI rilevato."""
    name = _pci_vendor_name(dev["vendor_id"])
    description = dev.get("description", "")
    label = f"{description} [{dev['id']}]"
    field = {
        f"{prefix}": detected(label),
        f"{prefix}_id": detected(dev["id"]),
        f"{prefix}_vendor": detected(name),
        f"{prefix}_model": detected(description),
        f"{prefix}_vendor_id": detected(dev["vendor_id"]),
        f"{prefix}_device_id": detected(dev["device_id"]),
        f"{prefix}_pci": detected(dev.get("slot", "")),
    }
    return field


def detect_gpu() -> Dict[str, DetectedValue]:
    grouped = _pci_grouped()
    displays = grouped.get("display", [])
    if not displays:
        return {"gpu": unknown(), "gpu_id": unknown()}
    primary = displays[0]
    out = _component_fields(primary, "gpu")
    # Tipo iGPU/dGPU: solo inferenza logica, mai DETECTED.
    vendor_id = primary.get("vendor_id", "").lower()
    if vendor_id == "8086":
        out["gpu_type"] = deduced("integrated")
    elif vendor_id in ("1002", "10de"):
        out["gpu_type"] = deduced("discrete")
    else:
        out["gpu_type"] = unknown()
    # VRAM: leggibile solo dove il kernel lo espone (AMD tipicamente). Intel iGPU non lo espone.
    vram = _read_sysfs("/sys/class/drm/card0/device/mem_info_vram_total")
    if vram:
        total_bytes = int(vram) if vram.isdigit() else 0
        out["gpu_vram"] = detected(f"{total_bytes // (1024 ** 3)} GB")
    else:
        out["gpu_vram"] = unknown()
    return out


def detect_audio() -> Dict[str, DetectedValue]:
    grouped = _pci_grouped()
    audio = grouped.get("audio", [])
    if not audio:
        return {"audio": unknown(), "audio_id": unknown()}
    return _component_fields(audio[0], "audio")


def detect_ethernet() -> Dict[str, DetectedValue]:
    grouped = _pci_grouped()
    eth = grouped.get("ethernet", [])
    if not eth:
        return {"ethernet": unknown(), "ethernet_id": unknown()}
    return _component_fields(eth[0], "ethernet")


def detect_wifi() -> Dict[str, DetectedValue]:
    grouped = _pci_grouped()
    net = grouped.get("network", [])
    if not net:
        return {"wifi": unknown(), "wifi_id": unknown()}
    return _component_fields(net[0], "wifi")


def _lsusb_available() -> bool:
    return shutil.which("lsusb") is not None


def detect_usb_devices() -> Dict[str, DetectedValue]:
    """Dispositivi USB da lsusb (best effort Linux). Mai inventare."""
    if not _lsusb_available():
        return {"usb_devices": unknown(), "usb_count": unknown()}
    text = _run(["lsusb"])
    if not text:
        return {"usb_devices": unknown(), "usb_count": unknown()}
    devices: List[Dict[str, Any]] = []
    # Formato: Bus 001 Device 002: ID 8087:0a2b Intel Corp. Bluetooth...
    for line in text.splitlines():
        m = re.search(
            r"Bus\s+(\d+)\s+Device\s+(\d+):\s+ID\s+([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\s+(.*)",
            line.strip(),
        )
        if not m:
            continue
        vid = m.group(3).lower()
        did = m.group(4).lower()
        devices.append({
            "bus": m.group(1),
            "device": m.group(2),
            "vendor_id": vid,
            "device_id": did,
            "id": f"{vid}:{did}",
            "description": m.group(5).strip(),
            "vendor_name": _pci_vendor_name(vid),
        })
    if not devices:
        return {"usb_devices": unknown(), "usb_count": unknown()}
    return {
        "usb_devices": detected(devices),
        "usb_count": detected(len(devices)),
    }


def detect_usb_controllers() -> Dict[str, DetectedValue]:
    grouped = _pci_grouped()
    usb = grouped.get("usb", [])
    out: Dict[str, DetectedValue] = {}
    if not usb:
        out["usb_controllers"] = unknown()
        out["usb_controller_list"] = unknown()
    else:
        names = ", ".join(f"{d['description']} [{d['id']}]" for d in usb)
        out["usb_controllers"] = detected(names)
        out["usb_controller_list"] = detected(usb)
    # Aggiunge anche i device USB reali (best effort) senza fermare nulla.
    try:
        out.update(detect_usb_devices())
    except Exception:
        out["usb_devices"] = unknown()
        out["usb_count"] = unknown()
    return out


def detect_bluetooth() -> Dict[str, DetectedValue]:
    """Bluetooth best effort: USB o PCI con nome Bluetooth. Non inventa nulla."""
    # 1. USB Bluetooth
    if _lsusb_available():
        text = _run(["lsusb"])
        for line in text.splitlines():
            if "bluetooth" in line.lower():
                m = re.search(r"ID\s+([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\s+(.*)", line)
                if m:
                    vid = m.group(1).lower()
                    did = m.group(2).lower()
                    return {
                        "bluetooth": detected(f"{m.group(3).strip()} [{vid}:{did}]"),
                        "bluetooth_id": detected(f"{vid}:{did}"),
                        "bluetooth_vendor": detected(_pci_vendor_name(vid)),
                        "bluetooth_vendor_id": detected(vid),
                        "bluetooth_device_id": detected(did),
                    }
    # 2. PCI Bluetooth
    grouped = _pci_grouped()
    for dev in grouped.get("network", []):
        if "bluetooth" in dev.get("description", "").lower():
            return _component_fields(dev, "bluetooth")
    return {
        "bluetooth": unknown(),
        "bluetooth_id": unknown(),
        "bluetooth_vendor": unknown(),
        "bluetooth_vendor_id": unknown(),
        "bluetooth_device_id": unknown(),
    }


def detect_sata_nvme_controllers() -> Dict[str, DetectedValue]:
    grouped = _pci_grouped()
    sata = grouped.get("sata", [])
    nvme = grouped.get("nvme", [])
    out: Dict[str, DetectedValue] = {}
    out["sata_controllers"] = detected(
        ", ".join(f"{d['description']} [{d['id']}]" for d in sata)
    ) if sata else unknown()
    out["nvme_controllers"] = detected(
        ", ".join(f"{d['description']} [{d['id']}]" for d in nvme)
    ) if nvme else unknown()
    return out


# ---------------------------------------------------------------------------
# Storage, network interfaces
# ---------------------------------------------------------------------------

def detect_storage() -> Dict[str, DetectedValue]:
    disks: List[str] = []
    base = Path("/sys/block")
    try:
        for entry in sorted(base.iterdir()):
            if entry.is_dir() and not entry.name.startswith(("loop", "ram", "sr", "fd")):
                size = _read_sysfs(str(entry / "size"))
                if size:
                    disks.append(f"{entry.name} ({int(size) * 512 // (1024**3)} GB)")
    except Exception:
        pass
    return {
        "storage": detected(", ".join(disks)) if disks else unknown(),
        "storage_count": detected(len(disks)) if disks else unknown(),
    }


def detect_net_interfaces() -> Dict[str, DetectedValue]:
    out = _run(["ip", "-o", "link", "show"])
    if not out:
        return {"net_interfaces": unknown()}
    names = re.findall(r"^\d+:\s+([^:@\s]+)", out, re.M)
    return {"net_interfaces": detected(", ".join(names)) if names else unknown()}


# ---------------------------------------------------------------------------
# ACPI (best effort)
# ---------------------------------------------------------------------------

def detect_acpi() -> Dict[str, DetectedValue]:
    if platform.system().lower() != "linux":
        reason = "ACPI tables via sysfs not available on this platform"
        return {
            "acpi_tables": not_available(reason),
            "acpi_table_list": not_available(reason),
            "dsdt_present": not_available(reason),
        }
    base = Path("/sys/firmware/acpi/tables")
    tables: List[str] = []
    if base.exists():
        try:
            tables = sorted(p.name for p in base.iterdir() if p.is_file())
        except Exception:
            tables = []
    if not tables:
        return {
            "acpi_tables": unknown(),
            "acpi_table_list": unknown(),
            "dsdt_present": unknown(),
        }
    return {
        "acpi_tables": detected(", ".join(tables)),
        "acpi_table_list": detected(tables),
        "dsdt_present": detected("present" if "DSDT" in tables else "absent"),
    }


# ---------------------------------------------------------------------------
# Hardwarinfo aggregato
# ---------------------------------------------------------------------------

@dataclass
class HardwareInfo:
    dmi: Dict[str, DetectedValue] = field(default_factory=dict)
    cpu: Dict[str, DetectedValue] = field(default_factory=dict)
    pci: Dict[str, DetectedValue] = field(default_factory=dict)
    gpu: Dict[str, DetectedValue] = field(default_factory=dict)
    audio: Dict[str, DetectedValue] = field(default_factory=dict)
    ethernet: Dict[str, DetectedValue] = field(default_factory=dict)
    wifi: Dict[str, DetectedValue] = field(default_factory=dict)
    bluetooth: Dict[str, DetectedValue] = field(default_factory=dict)
    usb: Dict[str, DetectedValue] = field(default_factory=dict)
    storage: Dict[str, DetectedValue] = field(default_factory=dict)
    net: Dict[str, DetectedValue] = field(default_factory=dict)
    acpi: Dict[str, DetectedValue] = field(default_factory=dict)
    platform: Dict[str, DetectedValue] = field(default_factory=dict)
    detection_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        def section(d: Dict[str, DetectedValue]) -> Dict[str, Any]:
            return {k: v.to_dict() for k, v in d.items()}

        return {
            "platform": section(self.platform),
            "dmi": section(self.dmi),
            "cpu": section(self.cpu),
            "pci": section(self.pci),
            "gpu": section(self.gpu),
            "audio": section(self.audio),
            "ethernet": section(self.ethernet),
            "wifi": section(self.wifi),
            "bluetooth": section(self.bluetooth),
            "usb": section(self.usb),
            "storage": section(self.storage),
            "net": section(self.net),
            "acpi": section(self.acpi),
        }

    def summary(self) -> Dict[str, str]:
        def gs(d: Dict[str, DetectedValue]) -> str:
            return str(next(iter(d.values()))) if d else UNKNOWN

        return {
            "manufacturer": str(self.dmi.get("system_vendor", unknown())),
            "model": str(self.dmi.get("product_name", unknown())),
            "board": str(self.dmi.get("board_name", unknown())),
            "cpu": str(self.cpu.get("model", unknown())),
            "gpu": str(self.gpu.get("gpu", unknown())),
            "audio": str(self.audio.get("audio", unknown())),
            "ethernet": str(self.ethernet.get("ethernet", unknown())),
        }


def detect_platform() -> Dict[str, DetectedValue]:
    out = {
        "system": detected(platform.system()),
        "node": detected(platform.node()),
        "release": detected(platform.release()),
        "version": detected(platform.version()),
        "machine": detected(platform.machine()),
        "python": detected(platform.python_version()),
    }
    # UEFI vs Legacy: indizio forte solo su Linux (sysfs). Su macOS/Windows non
    # lo simuliamo: NOT_AVAILABLE_ON_PLATFORM.
    if platform.system().lower() == "linux":
        efi_dir = Path("/sys/firmware/efi")
        try:
            if efi_dir.exists():
                out["uefi_mode"] = deduced("UEFI")
            else:
                out["uefi_mode"] = deduced("Legacy BIOS")
        except Exception:
            out["uefi_mode"] = unknown()
    else:
        out["uefi_mode"] = not_available("UEFI/Legacy detection via sysfs not available on this platform")
    return out


_SECTION_FIELDS = {
    "platform": ["system", "node", "release", "version", "machine", "python", "uefi_mode"],
    "dmi": ["system_vendor", "product_name", "product_version", "board_vendor",
            "board_name", "board_version", "bios_vendor", "bios_version", "bios_date"],
    "cpu": ["processor", "architecture", "model", "vendor", "frequency_mhz",
            "cores", "threads", "generation", "features", "feature_list"],
    "gpu": ["gpu", "gpu_id", "gpu_vendor", "gpu_model", "gpu_vendor_id",
            "gpu_device_id", "gpu_pci", "gpu_type", "gpu_vram"],
    "audio": ["audio", "audio_id", "audio_vendor", "audio_model",
              "audio_vendor_id", "audio_device_id", "audio_pci"],
    "ethernet": ["ethernet", "ethernet_id", "ethernet_vendor", "ethernet_model",
                 "ethernet_vendor_id", "ethernet_device_id", "ethernet_pci"],
    "wifi": ["wifi", "wifi_id", "wifi_vendor", "wifi_model",
             "wifi_vendor_id", "wifi_device_id", "wifi_pci"],
    "bluetooth": ["bluetooth", "bluetooth_id", "bluetooth_vendor",
                  "bluetooth_vendor_id", "bluetooth_device_id"],
}


def _safe_detect(section: str, func, info: HardwareInfo, **kwargs) -> None:
    """Rileva una sezione senza mai far fallire l'intera diagnosi."""
    try:
        value = func(**kwargs) if kwargs else func()
        if section == "storage":
            info.storage.update(value)
        elif section == "usb":
            info.usb.update(value)
        else:
            setattr(info, section, value)
    except Exception as exc:
        # Sezione non disponibile: segnaliamo NOT_DETECTED, non inventiamo nulla.
        fallback = {f: unknown() for f in _SECTION_FIELDS.get(section, ["unknown_field"])}
        setattr(info, section, fallback)
        info.detection_errors.append(f"{section}: {exc}")


def detect_all() -> HardwareInfo:
    """Rileva hardware disponibile. Non lancia mai eccezioni e non si ferma
    su una singola sezione fallita."""
    info = HardwareInfo()
    _safe_detect("platform", detect_platform, info)
    _safe_detect("dmi", detect_dmi, info)
    _safe_detect("cpu", detect_cpu, info)
    _safe_detect("pci", detect_pci, info)
    _safe_detect("gpu", detect_gpu, info)
    _safe_detect("audio", detect_audio, info)
    _safe_detect("ethernet", detect_ethernet, info)
    _safe_detect("wifi", detect_wifi, info)
    _safe_detect("bluetooth", detect_bluetooth, info)
    _safe_detect("usb", detect_usb_controllers, info)
    _safe_detect("net", detect_net_interfaces, info)
    _safe_detect("acpi", detect_acpi, info)
    # Storage: drives + controller SATA/NVMe in un'unica sezione.
    _safe_detect("storage", detect_storage, info)
    _safe_detect("storage", detect_sata_nvme_controllers, info)
    return info


def detect_limited() -> HardwareInfo:
    """Rileva solo i campi utili per i test / senza subprocess pesanti."""
    info = HardwareInfo()
    _safe_detect("platform", detect_platform, info)
    _safe_detect("dmi", detect_dmi, info)
    _safe_detect("cpu", detect_cpu, info)
    _safe_detect("gpu", detect_gpu, info)
    _safe_detect("audio", detect_audio, info)
    _safe_detect("ethernet", detect_ethernet, info)
    return info


if __name__ == "__main__":
    info = detect_all()
    print(json.dumps(info.to_dict(), indent=2, ensure_ascii=False))
