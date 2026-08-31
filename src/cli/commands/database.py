"""openhackintosh database — consulta i profili hardware."""

from __future__ import annotations

from database import load_all_profiles, get_profile
from ..output import Out


def run_database(args, out: Out) -> dict:
    sub = getattr(args, "db_command", "list")
    profiles = load_all_profiles()

    if sub == "list":
        if out.json_output:
            out.data({"profiles": {p.id: p.to_dict() for p in profiles.values()}})
            return profiles
        out.table(
            ["ID", "Name", "State", "Verified"],
            [[p.id, p.name, p.state, "yes" if p.verified else "no"] for p in profiles.values()],
        )
        return profiles

    if sub == "show":
        target = args.id or ""
        profile = get_profile(target) or next((p for p in profiles.values() if target.lower() in p.id.lower() or target.lower() in p.name.lower()), None)
        if not profile:
            msg = f"Profilo non trovato: {target}"
            if out.json_output:
                out.data({"ok": False, "error": msg})
            else:
                print(msg)
            raise SystemExit(2)
        out.data(profile.to_dict(), profile.name)
        return profile.to_dict()

    return {"profiles": {p.id: p.to_dict() for p in profiles.values()}}
