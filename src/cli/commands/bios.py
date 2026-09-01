"""openhackintosh bios — guida BIOS specifica per il profilo (niente liste universali)."""

from __future__ import annotations

from database import load_all_profiles, get_profile
from cli.output import Out, green, yellow, red, dim


def run_bios(args, out: Out) -> dict:
    profiles = load_all_profiles()
    target = args.profile or None
    profile = None
    if target:
        profile = get_profile(target) or next(
            (p for p in profiles.values() if target.lower() in p.id.lower() or target.lower() in p.name.lower()),
            None,
        )
    if profile is None:
        if out.json_output:
            out.data({"ok": False, "error": "Specifica un profilo (es. fujitsu_q556_2)"})
        else:
            print("Specifica un profilo: --profile fujitsu_q556_2")
        raise SystemExit(2)

    settings = profile.bios_configuration
    payload = {
        "profile": profile.id,
        "name": profile.name,
        "state": profile.state,
        "settings": settings,
        "requires_hardware_verification": any(
            not s.get("verified") for s in settings
        ),
    }
    if out.json_output:
        out.data(payload, profile.name)
        return payload

    print(f"BIOS CONFIGURATION per {profile.name} ({profile.state})")
    print()
    for s in settings:
        name = s.get("name", "")
        value = s.get("value", "")
        required = "required" if s.get("required") else "optional"
        verified = s.get("verified")
        if verified is True:
            ok_text = "verified"
            color_fn = green
        elif verified is False:
            ok_text = "requires hardware verification"
            color_fn = yellow
        else:
            ok_text = "unknown"
            color_fn = dim
        line = f"{name:<38} {value:<12} [{required}]"
        print(color_fn(line) + "  " + dim(ok_text))
        if s.get("note"):
            print(f"    - {s['note']}")

    return payload
