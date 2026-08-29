"""
SMBIOS generator for hackintosh
Generates valid serials, MLB, UUID, ROM
"""
import random
import string
import uuid
import hashlib
from typing import Dict

# SMBIOS data patterns - based on real Mac patterns
SMBIOS_PATTERNS = {
    "iMac17,1": {"serial_prefix": "C02", "board_prefix": "C027", "length": 12},
    "iMac18,1": {"serial_prefix": "C02", "board_prefix": "C02Z", "length": 12},
    "iMac18,3": {"serial_prefix": "C02", "board_prefix": "C02Z", "length": 12},
    "iMac19,1": {"serial_prefix": "C02", "board_prefix": "C02Z", "length": 12},
    "Macmini8,1": {"serial_prefix": "C07", "board_prefix": "C07C", "length": 12},
    "iMacPro1,1": {"serial_prefix": "C02", "board_prefix": "C02Z", "length": 12},
    "MacPro7,1": {"serial_prefix": "C07", "board_prefix": "C07C", "length": 12},
}

def generate_random_string(length: int, chars: str = string.ascii_uppercase + string.digits) -> str:
    return ''.join(random.choice(chars) for _ in range(length))

def generate_serial(model: str = "iMac18,1") -> str:
    """Generate plausible serial number"""
    pattern = SMBIOS_PATTERNS.get(model, SMBIOS_PATTERNS["iMac18,1"])
    prefix = pattern["serial_prefix"]
    # Year/week codes
    year_codes = ["H", "J", "K", "L", "M", "N", "P", "Q", "R", "S", "T", "V", "W", "X", "Y", "Z"]
    year = random.choice(year_codes) + str(random.randint(0, 9))
    week = f"{random.randint(1, 52):02d}"
    # Random part
    random_part = generate_random_string(5, string.ascii_uppercase + string.digits)
    # Last 4
    suffix = generate_random_string(4, string.ascii_uppercase + string.digits)
    serial = f"{prefix}{year}{week}{random_part}{suffix}"
    # Ensure 12 chars
    if len(serial) > 12:
        serial = serial[:12]
    elif len(serial) < 12:
        serial += generate_random_string(12 - len(serial))
    return serial

def generate_mlb(serial: str, model: str = "iMac18,1") -> str:
    """Generate MLB (Board Serial) - 17 chars, starts with serial + 5 random"""
    pattern = SMBIOS_PATTERNS.get(model, SMBIOS_PATTERNS["iMac18,1"])
    # MLB is typically 17 chars: serial + 5 chars
    extra = generate_random_string(5, string.ascii_uppercase + string.digits)
    mlb = serial + extra
    if len(mlb) > 17:
        mlb = mlb[:17]
    return mlb

def generate_uuid() -> str:
    """Generate System UUID"""
    return str(uuid.uuid4()).upper()

def generate_rom() -> str:
    """Generate ROM (MAC address) - 6 bytes hex"""
    # Generate random MAC, locally administered
    mac = [0x02, random.randint(0x00, 0xFF), random.randint(0x00, 0xFF),
           random.randint(0x00, 0xFF), random.randint(0x00, 0xFF), random.randint(0x00, 0xFF)]
    return ''.join(f"{b:02X}" for b in mac)

def generate_smbios(model: str = "iMac18,1") -> Dict[str, str]:
    """Generate complete SMBIOS set"""
    serial = generate_serial(model)
    mlb = generate_mlb(serial, model)
    smuuid = generate_uuid()
    rom = generate_rom()
    
    return {
        "ProductName": model,
        "SerialNumber": serial,
        "MLB": mlb,
        "SystemUUID": smuuid,
        "ROM": rom,
        "SystemProductName": model
    }

def validate_smbios(smbios: Dict[str, str]) -> bool:
    """Basic validation"""
    if len(smbios.get("SerialNumber", "")) != 12:
        return False
    if len(smbios.get("MLB", "")) != 17:
        return False
    try:
        uuid.UUID(smbios.get("SystemUUID", ""))
    except:
        return False
    if len(smbios.get("ROM", "")) != 12:
        return False
    return True

if __name__ == "__main__":
    for model in ["iMac17,1", "iMac18,1", "Macmini8,1", "iMacPro1,1"]:
        print(f"\n{model}:")
        s = generate_smbios(model)
        for k, v in s.items():
            print(f"  {k}: {v}")
        print(f"  Valid: {validate_smbios(s)}")
