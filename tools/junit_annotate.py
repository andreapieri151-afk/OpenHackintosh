#!/usr/bin/env python3
"""Estrae i fallimenti da un junit XML e li emette come annotazioni GitHub.

Uso:  python tools/junit_annotate.py report.xml
Pensato per la CI: le annotazioni (check-run) sono l'unico canale leggibile
quando i log dei job non sono scaricabili.
"""

import sys
import xml.etree.ElementTree as ET


def main(path: str) -> int:
    try:
        root = ET.parse(path).getroot()
    except Exception as exc:
        print(f"::error ::junit_annotate: impossibile leggere {path}: {exc}")
        return 0  # non mascherare mai l'esito del test vero
    count = 0
    for tc in root.iter("testcase"):
        for detail in list(tc):
            if detail.tag not in ("failure", "error"):
                continue
            count += 1
            name = f"{tc.get('classname', '')}::{tc.get('name', '')}"
            text = (detail.text or detail.get("message", "") or "")[:1800]
            text = text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print(f"::error ::FAILED {name}%0A{text}")
    if count == 0:
        print(f"junit_annotate: nessun fallimento in {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "pytest-report.xml"))
