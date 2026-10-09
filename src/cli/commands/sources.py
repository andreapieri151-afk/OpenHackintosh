"""openhackintosh sources — consulta e valida il database delle fonti."""

from __future__ import annotations

from database import load_all_profiles
from sources import (
    ManifestError,
    available_manifests,
    check_against_profile,
    load_manifest_for_profile,
    manifest_path_for,
)
from ..output import Out


def run_sources(args, out: Out) -> dict:
    action = getattr(args, "sources_command", None) or "list"

    if action == "list":
        rows = []
        for pid in available_manifests():
            try:
                manifest = load_manifest_for_profile(pid)
                rows.append({
                    "profile": pid,
                    "components": len(manifest.components),
                    "required": len(manifest.required_components()),
                    "status": "VALID",
                })
            except ManifestError as exc:
                rows.append({"profile": pid, "status": f"INVALID: {exc}"})

        if out.json_output:
            out.data({"manifests": rows})
        else:
            out.table(
                ["Profilo", "Componenti", "Required", "Stato"],
                [[r["profile"], r.get("components", "-"), r.get("required", "-"), r["status"]]
                 for r in rows],
            )
        return {"ok": True, "manifests": rows}

    # show / check richiedono un profilo
    profile_id = getattr(args, "profile", None)
    if not profile_id:
        if out.json_output:
            out.data({"ok": False, "error": "Specifica --profile (es. fujitsu_q556_2)"})
        else:
            print("Specifica --profile (es. fujitsu_q556_2)")
        raise SystemExit(2)

    try:
        manifest = load_manifest_for_profile(profile_id)
    except ManifestError as exc:
        if out.json_output:
            out.data({"ok": False, "error": str(exc)})
        else:
            print(f"Errore: {exc}")
        raise SystemExit(2)

    if action == "show":
        if out.json_output:
            out.data({
                "profile": profile_id,
                "manifest_path": str(manifest_path_for(profile_id)),
                "manifest": manifest.to_dict(),
            })
        else:
            print(f"Sources manifest: {manifest_path_for(profile_id)}\n")
            print(f"{'ID':22} {'KIND':10} {'REQ':5} {'TARGET':40} FONTE")
            print("-" * 115)
            for c in manifest.components:
                req = "SI'" if c.required else f"({c.optional_group})"
                print(f"{c.id:22} {c.kind:10} {req:5} {c.target:40} "
                      f"{c.source.summary()}  [{c.provenance}]")
        return {"ok": True, "profile": profile_id}

    if action == "check":
        profiles = load_all_profiles()
        profile = profiles.get(profile_id)
        if not profile:
            if out.json_output:
                out.data({"ok": False, "error": f"Profilo non trovato: {profile_id}"})
            else:
                print(f"Profilo non trovato: {profile_id}")
            raise SystemExit(2)

        problems = check_against_profile(manifest, profile)
        ok = not problems
        if out.json_output:
            out.data({"ok": ok, "profile": profile_id, "problems": problems})
        else:
            if ok:
                print(f"OK: il manifest di {profile_id} copre tutti i componenti "
                      f"required del profilo.")
            else:
                print(f"PROBLEMI ({len(problems)}):")
                for p in problems:
                    print(f"  - {p}")
        if not ok:
            raise SystemExit(1)
        return {"ok": True}

    if out.json_output:
        out.data({"ok": False, "error": f"Azione sconosciuta: {action}"})
    else:
        print(f"Azione sconosciuta: {action}")
    raise SystemExit(2)
