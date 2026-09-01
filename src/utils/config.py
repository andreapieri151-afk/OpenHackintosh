"""
Configurazione runtime di OpenHackintosh.

La modalita' release NON abilita debug args. La modalita' --dev li abilita
solo come opzione esplicita per diagnostica.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    dev: bool = False
    json_output: bool = False
    verbose: bool = False
    default_output_dir: str = "output/EFI"
    default_macos: str = "Ventura 13.x"
    # Boot args di debug: MAI di default in release.
    debug_boot_args: bool = False


def load_settings_from_env() -> Settings:
    return Settings(
        dev=os.environ.get("OPENHACKINTOSH_DEV") == "1",
        json_output=os.environ.get("OPENHACKINTOSH_JSON") == "1",
        debug_boot_args=os.environ.get("OPENHACKINTOSH_DEBUG_BOOT") == "1",
    )
