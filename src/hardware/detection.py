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


@dataclass
class DetectedValue:
    """Valore hardware + provenienza del dato."""

    value: str = UNKNOWN
    source: str = "unknown"  # detected | deduced | unknown

    def to_dict(self) -> Dict[str, str]:
        return {"value": self.value, "source": self.source}

    def __str__(self) -> str:
        return self.value


def detected(value: Any) -> DetectedValue:
    return DetectedValue(str(value) if value not in (None, "") else UNKNOWN, "detected")


def deduced(value: Any) -> DetectedValue:
    return DetectedValue(str(value) if value not in (None, "") else UNKNOWN, "deduced")


def unknown() -> DetectedValue:
    return DetectedValue(UNKNOWN, "unknown")


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

def detect_cpu() -> Dict[str, DetectedValue]:
    info: Dict[str, DetectedValue] = {}

    # platform.processor()
    p = platform.processor() or platform.machine()
    info["processor"] = detected(p) if p and p not in ("unknown",) else unknown()

    # /proc/cpuinfo: model name / vendor
    model = ""
    vendor = ""
    mhz = ""
    try:
        for line in Path("/proc/cpuinfo").read_text(errors="replace").splitlines():
            if line.lower().startswith("model name") and not model:
                model = line.split(":", 1)[1].strip()
            elif line.lower().startswith("vendor_id") and not vendor:
                vendor = line.split(":", 1)[1].strip()
            elif line.lower().startswith("cpu mhz") and not mhz:
                mhz = line.split(":", 1)[1].strip()
    except Exception:
        pass

    info["model"] = detected(model) if model else unknown()
    info["vendor"] = detected(vendor) if vendor else unknown()
    info["frequency_mhz"] = detected(mhz) if mhz else unknown()
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
    bin_name = _lspci_bin()
    if not bin_name:
        return {"pci_devices": unknown(), "pci_count": unknown()}
    text = _run([bin_name, "-nn", "-D"])
    devices = parse_lspci(text)
    if not devices:
        return {"pci_devices": unknown(), "pci_count": unknown()}
    return {
        "pci_devices": detected(json.dumps(devices, separators=(",", ":"))),
        "pci_count": detected(len(devices)),
    }


def _pci_grouped() -> Dict[str, List[Dict[str, Any]]]:
    text = _run([_lspci_bin() or "lspci", "-nn", "-D"])
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for dev in parse_lspci(text):
        grouped.setdefault(dev["class"], []).append(dev)
    return grouped


def detect_gpu() -> Dict[str, DetectedValue]:
    grouped = _pci_grouped()
    displays = grouped.get("display", [])
    if not displays:
        return {"gpu": unknown(), "gpu_id": unknown()}
    primary = displays[0]
    return {
        "gpu": detected(f"{primary['description']} [{primary['id']}]"),
        "gpu_id": detected(primary["id"]),
    }


def detect_audio() -> Dict[str, DetectedValue]:
    grouped = _pci_grouped()
    audio = grouped.get("audio", [])
    if not audio:
        return {"audio": unknown(), "audio_id": unknown()}
    dev = audio[0]
    return {
        "audio": detected(f"{dev['description']} [{dev['id']}]"),
        "audio_id": detected(dev["id"]),
    }


def detect_ethernet() -> Dict[str, DetectedValue]:
    grouped = _pci_grouped()
    eth = grouped.get("ethernet", [])
    if not eth:
        return {"ethernet": unknown(), "ethernet_id": unknown()}
    dev = eth[0]
    return {
        "ethernet": detected(f"{dev['description']} [{dev['id']}]"),
        "ethernet_id": detected(dev["id"]),
    }


def detect_wifi() -> Dict[str, DetectedValue]:
    grouped = _pci_grouped()
    net = grouped.get("network", [])
    if not net:
        return {"wifi": unknown(), "wifi_id": unknown()}
    dev = net[0]
    return {
        "wifi": detected(f"{dev['description']} [{dev['id']}]"),
        "wifi_id": detected(dev["id"]),
    }


def detect_usb_controllers() -> Dict[str, DetectedValue]:
    grouped = _pci_grouped()
    usb = grouped.get("usb", [])
    if not usb:
        return {"usb_controllers": unknown()}
    names = ", ".join(f"{d['description']} [{d['id']}]" for d in usb)
    return {"usb_controllers": detected(names)}


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
    base = Path("/sys/firmware/acpi/tables")
    if base.exists():
        tables = sorted(p.name for p in base.iterdir() if p.is_file())
        return {"acpi_tables": detected(", ".join(tables)) if tables else unknown()}
    return {"acpi_tables": unknown()}


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
    usb: Dict[str, DetectedValue] = field(default_factory=dict)
    storage: Dict[str, DetectedValue] = field(default_factory=dict)
    net: Dict[str, DetectedValue] = field(default_factory=dict)
    acpi: Dict[str, DetectedValue] = field(default_factory=dict)
    platform: Dict[str, DetectedValue] = field(default_factory=dict)

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
    return {
        "system": detected(platform.system()),
        "node": detected(platform.node()),
        "release": detected(platform.release()),
        "version": detected(platform.version()),
        "machine": detected(platform.machine()),
        "python": detected(platform.python_version()),
    }


def detect_all() -> HardwareInfo:
    """Rileva hardware disponibile. Non lancia mai eccezioni."""
    info = HardwareInfo()
    info.platform = detect_platform()
    info.dmi = detect_dmi()
    info.cpu = detect_cpu()
    info.pci = detect_pci()
    info.gpu = detect_gpu()
    info.audio = detect_audio()
    info.ethernet = detect_ethernet()
    info.wifi = detect_wifi()
    info.usb = detect_usb_controllers()
    info.storage = detect_storage()
    info.net = detect_net_interfaces()
    info.acpi = detect_acpi()
    # SATA / NVMe controllers
    sata_nvme = detect_sata_nvme_controllers()
    info.storage.update(sata_nvme)
    return info


def detect_limited() -> HardwareInfo:
    """Rileva solo i campi utili per i test / senza subprocess pesanti."""
    info = HardwareInfo()
    info.platform = detect_platform()
    info.dmi = detect_dmi()
    info.cpu = detect_cpu()
    info.gpu = detect_gpu()
    info.audio = detect_audio()
    info.ethernet = detect_ethernet()
    return info


if __name__ == "__main__":
    info = detect_all()
    print(json.dumps(info.to_dict(), indent=2, ensure_ascii=False))
