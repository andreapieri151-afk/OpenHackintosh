"""
Costruisce l'inject-kext USBMap (solo Info.plist, niente binario).

E' lo stesso formato dei USBMap.kext prodotti a mano o da USBToolBox:
personalita' AppleUSBHostMergeProperties per controller, con port-count e
dizionario ports. Un inject-kext SENZA eseguibile e' legittimo: la validazione
lo tratta come caso a parte (validate_inject_kext).
"""

from __future__ import annotations

import plistlib
from pathlib import Path
from typing import Dict, List

from .model import UsbController

BUNDLE_ID_TEMPLATE = "com.openhackintosh.usbmap.{profile}"


def build_usb_map_plist(controllers: List[UsbController], profile_id: str) -> Dict:
    personalities: Dict = {}
    for controller in controllers:
        key = f"XHCI-{controller.pci_slot.replace(':', '_')}-{controller.pci_id.replace(':', '_')}"
        personalities[key] = controller.personality()

    total_ports = sum(c.port_count for c in controllers)
    return {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleIdentifier": BUNDLE_ID_TEMPLATE.format(profile=profile_id),
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": f"USBMap {profile_id}",
        "CFBundlePackageType": "KEXT",
        "CFBundleShortVersionString": "1.0",
        "CFBundleVersion": "1.0",
        "IOKitPersonalities": personalities,
        "OSBundleRequired": "Root",
        # Metadati OpenHackintosh (ignorati dal kernel, utili all'utente).
        "com.openhackintosh.profile": profile_id,
        "com.openhackintosh.status": "DRAFT",
        "com.openhackintosh.note": (
            f"Mappa USB generata automaticamente: {len(controllers)} controller, "
            f"{total_ports} porte rilevate. Bozza: verificare i tipi connettore "
            "dopo l'installazione (USBToolBox) e segnare le porte interne come "
            "UsbConnector=255."
        ),
    }


def save_usb_map_kext(controllers: List[UsbController], bundle_dir: Path,
                      profile_id: str) -> Path:
    """Scrive <bundle_dir>/Contents/Info.plist. Restituisce il path dell'Info.plist."""
    bundle_dir = Path(bundle_dir)
    contents = bundle_dir / "Contents"
    contents.mkdir(parents=True, exist_ok=True)
    info_plist = contents / "Info.plist"
    plist = build_usb_map_plist(controllers, profile_id)
    with open(info_plist, "wb") as fh:
        plistlib.dump(plist, fh)
    return info_plist
