"""
USB mapping automatico (2.0.2).

Rileva i controller XHCI e i porti del root hub (Linux/sysfs) e genera un
inject-kext USBMap nel formato canonico. Nessun layout inventato: se la
topologia non e' rilevabile, la mappa non viene generata.

    model.py    -> UsbPort / UsbController (+ personalita' IOKit)
    detect.py   -> detection sysfs (radice iniettabile per i test)
    builder.py  -> Info.plist dell'inject-kext USBMap
"""

from .model import (
    CONNECTOR_INTERNAL,
    CONNECTOR_TYPE_A,
    CONNECTOR_TYPE_C_SWITCH,
    PORT_STATUS_DETECTED,
    PORT_STATUS_DOCUMENTED,
    PORT_STATUS_UNKNOWN,
    UsbController,
    UsbPort,
)
from .detect import detect_usb_controllers, detect_usb_controllers_linux
from .builder import build_usb_map_plist, save_usb_map_kext

__all__ = [
    "CONNECTOR_INTERNAL",
    "CONNECTOR_TYPE_A",
    "CONNECTOR_TYPE_C_SWITCH",
    "PORT_STATUS_DETECTED",
    "PORT_STATUS_DOCUMENTED",
    "PORT_STATUS_UNKNOWN",
    "UsbController",
    "UsbPort",
    "detect_usb_controllers",
    "detect_usb_controllers_linux",
    "build_usb_map_plist",
    "save_usb_map_kext",
]
