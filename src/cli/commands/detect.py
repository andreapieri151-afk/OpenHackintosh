"""openhackintosh detect — rileva l'hardware reale."""

from __future__ import annotations

import json

from hardware import detect_all, identify
from ..output import Out


def run_detect(args, out: Out) -> dict:
    info = detect_all()
    identity = identify(info)

    if out.json_output:
        payload = {
            "mode": "detect",
            "hardware": info.to_dict(),
            "identity": identity.to_dict(),
        }
        out.data(payload)
        return payload

    out.table(
        ["Field", "Value", "Source"],
        [
            ["System", info.platform.get("system", "?"), "detected"],
            ["Manufacturer", identity.manufacturer, info.dmi.get("system_vendor", "?").source],
            ["Model", identity.model, info.dmi.get("product_name", "?").source],
            ["Board", identity.board, info.dmi.get("board_name", "?").source],
            ["CPU", identity.cpu, info.cpu.get("model", "?").source],
            ["iGPU", identity.gpu, info.gpu.get("gpu", "?").source],
            ["Audio", identity.audio, info.audio.get("audio", "?").source],
            ["Ethernet", identity.ethernet, info.ethernet.get("ethernet", "?").source],
            ["Wi-Fi", identity.wifi, info.wifi.get("wifi", "?").source],
        ],
    )

    pci = info.pci.get("pci_devices", None)
    if pci and pci.value != "Unknown / Not detected":
        devices = json.loads(pci.value)
        rows = [[d.get("class", ""), d.get("description", ""), d.get("id", "")] for d in devices]
        out.table(["Class", "Device", "ID"], rows)

    return {"hardware": info.to_dict(), "identity": identity.to_dict()}
