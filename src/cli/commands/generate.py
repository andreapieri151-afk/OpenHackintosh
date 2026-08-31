"""openhackintosh generate — genera EFI hardware-aware."""

from __future__ import annotations

from pathlib import Path

from hardware import detect_all, identify
from database import load_all_profiles, get_profile, match_profile
from efi.generator import build_efi
from efi import validate_efi
from ..output import Out


def run_generate(args, out: Out) -> dict:
    profiles = load_all_profiles()

    # 1. Seleziona il profilo (dato oppure rilevato)
    profile = None
    if args.profile:
        profile = get_profile(args.profile, None)
        if not profile and args.profile in profiles:
            profile = profiles[args.profile]
        if not profile:
            candidate = [p for p in profiles.values()
                         if args.profile.lower() in p.id.lower() or args.profile.lower() in p.name.lower()]
            if len(candidate) == 1:
                profile = candidate[0]
        if not profile:
            msg = f"Profilo non trovato: {args.profile}"
            out.data({"ok": False, "error": msg}, "Errore")
            raise SystemExit(2)
    else:
        info = detect_all()
        identity = identify(info)
        match = match_profile(identity, profiles)
        profile = match.profile
        if not profile:
            if not args.force:
                msg = ("Nessun profilo corrispondente. "
                       "Usa --profile per forzare un profilo oppure --force a proprio rischio.")
                out.data({"ok": False, "error": msg}, "Errore")
                raise SystemExit(2)
            msg = "Nessun profilo corrispondente; --force richiesto. NON raccomandato."
            out.data({"ok": False, "error": msg}, "Attenzione")

    # 2. Rifiuto profili marcati UNSUPPORTED
    if profile.state == "UNSUPPORTED":
        msg = f"Profilo {profile.name} e' UNSUPPORTED. Non procedere."
        out.data({"ok": False, "error": msg}, "Errore")
        raise SystemExit(2)

    # 3. Genera
    output_dir = Path(args.output)
    result = build_efi(
        profile=profile,
        output_dir=output_dir,
        smbios_model=args.smbios,
        audio_layout=args.audio_layout,
        macos_version=args.macos,
        include_wifi=args.wifi,
        include_bluetooth=args.bluetooth,
        generate_zip=not args.no_zip,
        strict=True,
    )

    # 4. Valida sempre prima di dire che e' pronta
    if result.get("success"):
        validation = validate_efi(Path(result["efi_path"]))
        result["validation"] = validation
        if not validation.get("ready") and not args.force:
            result["success"] = False
            result["error"] = "EFI generation aborted. Validation failed: " + "; ".join(validation.get("errors", []))
            out.data(result, "Errore")
            return result

    out.data(result, "Esito")
    return result
