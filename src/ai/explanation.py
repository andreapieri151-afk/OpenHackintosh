"""
Spiegazione comprensibile dei risultati della compatibilita'.

Questo NON e' un AI che inventa: riceve un risultato deterministico
(CompatibilityResult) e lo traduce in testo. Non puo' trasformare
UNKNOWN/UNSUPPORTED in compatible.
"""

from __future__ import annotations

from typing import List

from compatibility import CompatibilityResult, ComponentStatus, OverallStatus


def explain_results(result: CompatibilityResult) -> List[str]:
    lines: List[str] = []
    if not result.profile:
        lines.append("Nessun computer nel database corrisponde all'hardware rilevato.")
        lines.append("Non e' possibile decidere la compatibilita' in modo affidabile.")
        if result.unknown_components:
            lines.append("Componenti non rilevati: " + ", ".join(result.unknown_components))
        lines.append("Stato: UNKNOWN. Richiede informazioni reali.")
        return lines

    profile = result.profile
    lines.append(f"Profilo scelto: {profile.name} ({profile.state})")
    lines.append(f"Verdetto complessivo: {result.overall.value}")

    if result.overall == OverallStatus.UNSUPPORTED:
        lines.append("Il profilo e' marcato UNSUPPORTED: non generare una EFI per questo computer.")
    elif result.overall == OverallStatus.UNKNOWN:
        lines.append("Dati insufficienti o profilo non verificato: servono test su hardware reale.")

    for comp in result.components:
        label = comp.name
        if comp.status == ComponentStatus.OK:
            lines.append(f"- {label}: compatibile ({comp.detected})")
        elif comp.status == ComponentStatus.PARTIAL:
            lines.append(f"- {label}: parziale ({comp.detected}) - differisce dal profilo")
        elif comp.status == ComponentStatus.UNKNOWN:
            lines.append(f"- {label}: non rilevato - requires real hardware testing")
        elif comp.status == ComponentStatus.UNSUPPORTED:
            lines.append(f"- {label}: non supportato ({comp.detected})")

    for note in result.notes:
        lines.append(f"* {note}")
    return lines


def answer_why_incompatible(result: CompatibilityResult, component_name: str) -> str:
    for comp in result.components:
        if comp.name.lower() == component_name.lower():
            if comp.status == ComponentStatus.OK:
                return (f"{component_name} risulta compatibile ({comp.detected}). "
                        "Se hai problemi, controlla prima BIOS/quirks, non l'hardware.")
            if comp.status == ComponentStatus.PARTIAL:
                return (f"{component_name} ({comp.detected}) differisce da quanto atteso "
                        f"({comp.expected}). Servono informazioni reali del dispositivo.")
            if comp.status == ComponentStatus.UNKNOWN:
                return (f"{component_name} non e' stato rilevato: "
                        "requires real hardware testing. Non posso affermare nulla.")
            return f"{component_name}: {comp.status.value}. {comp.detail}"
    return (f"Nessuna informazione su {component_name}. "
            "Non e' possibile concludere senza dati dal Compatibility Engine.")


def answer_recommended_macos(result: CompatibilityResult) -> str:
    if not result.profile:
        return "Nessun profilo: non posso consigliare macOS in modo affidabile."
    compat = result.profile.macos_compatibility
    verified = [k for k, v in compat.items() if v.get("status") == "verified"]
    documented = [k for k, v in compat.items() if v.get("status") == "documented"]
    parts: List[str] = []
    if verified:
        parts.append("verificate: " + ", ".join(verified))
    if documented:
        parts.append("documentate: " + ", ".join(documented))
    if not parts:
        return "Nessuna versione macOS documentata per questo profilo."
    return "Versioni raccomandate (incluse solo con evidenze): " + "; ".join(parts) + "."
