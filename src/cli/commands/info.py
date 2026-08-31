"""openhackintosh info — mostra informazioni dettagliate sul sistema."""

from __future__ import annotations

from hardware import detect_all, identify
from ..output import Out


def run_info(args, out: Out) -> dict:
    info = detect_all()
    identity = identify(info)

    if out.json_output:
        payload = info.to_dict()
        out.data(payload)
        return payload

    detail = info.to_dict()
    out.table(["Section", "Field", "Value", "Source"], [
        [sec, key, val.get("value", ""), val.get("source", "")]
        for sec, fields in detail.items()
        for key, val in fields.items()
    ])
    return {"identity": identity.to_dict(), "hardware": detail}
