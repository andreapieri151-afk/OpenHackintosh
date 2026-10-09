"""
Modello dati per la mappa USB.

Onesta': la detection dice quanti porti ESISTONO su un controller (fatto
misurabile dal sysfs). Il TIPO di connettore (Type-A/Type-C/interno) non e'
deducibile senza provare fisicamente le porte: i porti rilevati partono con
UsbConnector=0 e commentati come bozza da verificare. Mai inventare layout.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List

#: UsbConnector secondo OpenCore/IOKit.
CONNECTOR_TYPE_A = 0        # USB2/3 Type-A
CONNECTOR_TYPE_C_SWITCH = 10  # Type-C con switch
CONNECTOR_INTERNAL = 255    # interno / proprietario

PORT_STATUS_DETECTED = "DETECTED"        # conteggio rilevato dal sistema
PORT_STATUS_DOCUMENTED = "DOCUMENTED"    # da documentazione profilo
PORT_STATUS_UNKNOWN = "UNKNOWN"


@dataclass
class UsbPort:
    name: str                    # es. "PRT01", "HS01", "SS01"
    index: int                   # 1-based, come nel registro ports di XHCI
    connector: int = CONNECTOR_TYPE_A
    status: str = PORT_STATUS_DETECTED
    comment: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class UsbController:
    pci_id: str                  # es. "8086:a12f"
    pci_slot: str                # formato pcidebug: "0:20:0" (bus:dev:func decimali)
    provider_class: str = "AppleUSBXHCIPCI"
    ports: List[UsbPort] = field(default_factory=list)
    status: str = PORT_STATUS_DETECTED   # stato della rilevazione
    notes: str = ""

    @property
    def port_count(self) -> int:
        return max((p.index for p in self.ports), default=0)

    def personality(self) -> Dict:
        """Personalita' IOKit nel formato canonico di USBMap.kext."""
        ports: Dict = {}
        for port in self.ports:
            ports[port.name] = {
                "UsbConnector": port.connector,
                "port": port.index.to_bytes(4, "little"),
            }
        return {
            "CFBundleIdentifier": "com.apple.driver.AppleUSBHostMergeProperties",
            "IOClass": "AppleUSBHostMergeProperties",
            "IOParentMatch": {
                "IOPropertyMatch": {"pcidebug": self.pci_slot},
            },
            "IOProviderClass": self.provider_class,
            "IOProviderMergeProperties": {
                "port-count": self.port_count.to_bytes(4, "little"),
                "ports": ports,
            },
        }

    def to_dict(self) -> Dict:
        return {
            "pci_id": self.pci_id,
            "pci_slot": self.pci_slot,
            "provider_class": self.provider_class,
            "port_count": self.port_count,
            "status": self.status,
            "notes": self.notes,
            "ports": [p.to_dict() for p in self.ports],
        }
