"""
Detection dei controller USB XHCI e dei loro porti.

Linux: sysfs. Il conteggio porti e' un FATTO misurato (oggetti usbN-portM
del root hub). Su altre piattaforme la topologia non e' rilevabile dal tool:
restituisce lista vuota e la pipeline salta la mappa (mai inventarla).

Tutte le funzioni accettano una radice sysfs iniettabile: i test usano un
albero finto, nessuna dipendenza dall'hardware reale.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from .model import (
    CONNECTOR_TYPE_A,
    PORT_STATUS_DETECTED,
    UsbController,
    UsbPort,
)

#: Classe PCI "Serial bus controller / USB controller / XHCI".
PCI_CLASS_XHCI = "0x0c0330"


def _read_sysfs(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _pci_slot_from_address(address: str) -> str:
    """'0000:00:14.0' -> '0:20:0' (bus:device:function in decimali, formato pcidebug)."""
    match = re.fullmatch(r"[0-9a-fA-F]{4}:([0-9a-fA-F]{2}):([0-9a-fA-F]{2})\.([0-7])", address)
    if not match:
        return address
    bus, device, function = (int(part, 16) for part in match.groups())
    return f"{bus}:{device}:{function}"


def _count_root_hub_ports(controller_dir_name: str, devices_root: Path) -> int:
    """Conta i porti del root hub: oggetti 'usbN-portM' sotto il controller."""
    max_index = 0
    if not devices_root.is_dir():
        return 0
    for entry in devices_root.rglob("*"):
        if not entry.is_dir():
            continue
        if controller_dir_name not in str(entry):
            continue
        match = re.fullmatch(r"usb(\d+)-port(\d+)", entry.name)
        if match:
            max_index = max(max_index, int(match.group(2)))
    return max_index


def detect_usb_controllers_linux(sys_root: Optional[Path] = None) -> List[UsbController]:
    """Controller XHCI dal sysfs. Lista vuota se non rilevabili."""
    root = Path(sys_root) if sys_root else Path("/sys")
    pci_devices = root / "bus" / "pci" / "devices"
    if not pci_devices.is_dir():
        return []

    controllers: List[UsbController] = []
    devices_root = root / "devices"

    for dev in sorted(pci_devices.iterdir()):
        if _read_sysfs(dev / "class") != PCI_CLASS_XHCI:
            continue

        vendor = _read_sysfs(dev / "vendor").replace("0x", "")
        device = _read_sysfs(dev / "device").replace("0x", "")
        pci_id = f"{vendor}:{device}" if vendor and device else "unknown"

        port_count = _count_root_hub_ports(dev.name, devices_root)
        ports = [
            UsbPort(
                name=f"PRT{index:02d}",
                index=index,
                connector=CONNECTOR_TYPE_A,
                status=PORT_STATUS_DETECTED,
                comment="Bozza automatica: porta rilevata, tipo connettore da verificare.",
            )
            for index in range(1, port_count + 1)
        ]

        controllers.append(UsbController(
            pci_id=pci_id,
            pci_slot=_pci_slot_from_address(dev.name),
            ports=ports,
            status=PORT_STATUS_DETECTED if ports else "DETECTED_NO_PORTS",
            notes=(f"{port_count} porti rilevati dal root hub"
                   if port_count else
                   "Controller rilevato ma nessun porto enumerato dal root hub"),
        ))

    return controllers


def detect_usb_controllers(sys_root: Optional[Path] = None) -> List[UsbController]:
    """Dispatch per piattaforma. Solo Linux espone la topologia via sysfs."""
    from utils.platforms import current_platform

    if current_platform() == "linux":
        return detect_usb_controllers_linux(sys_root)
    return []
