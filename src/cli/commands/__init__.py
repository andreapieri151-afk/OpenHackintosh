from .detect import run_detect
from .info import run_info
from .diagnose import run_diagnose
from .compatibility import run_compatibility
from .generate import run_generate
from .validate import run_validate
from .doctor import run_doctor
from .database import run_database
from .bios import run_bios

__all__ = [
    "run_detect",
    "run_info",
    "run_diagnose",
    "run_compatibility",
    "run_generate",
    "run_validate",
    "run_doctor",
    "run_database",
    "run_bios",
]
