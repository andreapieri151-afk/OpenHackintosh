"""openhackintosh generate — genera EFI hardware-aware, con audit finale."""

from __future__ import annotations

from pathlib import Path

from hardware import detect_all, identify
from database import load_all_profiles, get_profile, match_profile
from efi.generator import build_efi
from cli.output import Out


def _print_report_generation(result: dict) -> None:
    report = result.get("generation_report") or {}
    detail = report.get("report") or {}
    print("\nOpenHackintosh EFI Generator")
    print("============================")
    print("Status (audit):", report.get("status", "-"))
    print("Profile:", report.get("profile", "-"))
    print("Profile state:", report.get("state", "-"))
    print("\nACPI:")
    for status, name in detail.get("acpi", []):
        print(f"  {'OK' if status == 'ok' else 'FAIL'} {name}")
    print("Drivers:")
    for status, name in detail.get("drivers", []):
        print(f"  {'OK' if status == 'ok' else 'FAIL'} {name}")
    print("Kexts:")
    for status, name in detail.get("kexts", []):
        print(f"  {'OK' if status == 'ok' else 'FAIL'} {name}")
    print("\nValidation:")
    checks = report.get("checks", {})
    for label, ok in checks.items():
        print(f"  {'OK' if ok else 'FAIL'} {label}")
    for err in report.get("errors", []):
        print(f"  FAIL {err}")


def run_generate(args, out: Out) -> dict:
    profiles = load_all_profiles()

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

    if profile.state == "UNSUPPORTED":
        msg = f"Profilo {profile.name} e' UNSUPPORTED. Non procedere."
        out.data({"ok": False, "error": msg}, "Errore")
        raise SystemExit(2)

    output_dir = Path(args.output)
    result = build_efi(
        profile=profile,
        output_dir=output_dir,
        smbios_model=args.smbios,
        audio_layout=args.audio_layout,
        macos_version=args.macos,
        include_wifi=args.wifi,
        include_bluetooth=args.bluetooth,
        include_nvme=args.include_nvme,
        include_restrict_events=args.include_restrict_events,
        include_optional_drivers=args.include_optional_drivers,
        generate_zip=not args.no_zip,
        strict=True,
        dev=args.dev,
        silent=out.json_output,
    )

    if result.get("success"):
        out.data(result, "Esito")
        if not out.json_output:
            _print_report_generation(result)
            print("\nEFI STATUS: VALID")
        return result

    out.data({
        "ok": False,
        "success": False,
        "error": result.get("error", "EFI generation aborted"),
        "efi_status": result.get("efi_status", "FAILED"),
        "generation_report": result.get("generation_report"),
    }, "Errore")
    if not out.json_output:
        _print_report_generation(result)
        print("\nEFI STATUS: FAILED")
        print("EFI generation aborted.")
    return result
