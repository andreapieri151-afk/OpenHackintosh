"""Test del provider Windows (hardware/windows.py).

Nessun test richiede Windows o PowerShell: tutto lavora su fixture JSON
sintetiche (lo stesso formato emesso da `ConvertTo-Json`), coerente con la
filosofia del progetto: parsing puro, mai inventato, verificabile ovunque.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hardware import windows as win  # noqa: E402
from hardware.detection import (  # noqa: E402
    STATUS_DETECTED,
    STATUS_INFERRED,
    STATUS_NOT_AVAILABLE,
    STATUS_NOT_DETECTED,
)


# ---------------------------------------------------------------------------
# Fixture: lo stesso payload che produrrebbe lo script PowerShell su un Q556/2
# ---------------------------------------------------------------------------

Q5562_PAYLOAD = {
    "computerSystem": {
        "Manufacturer": "FUJITSU",
        "Model": "ESPRIMO Q5562",
        "SystemFamily": "ESPRIMO Q",
    },
    "baseBoard": {
        "Manufacturer": "FUJITSU",
        "Product": "D3403-U",
        "Version": "S26361-D3403-U",
        "SerialNumber": "123456",
    },
    "bios": {
        "Manufacturer": "FUJITSU // American Megatrends Inc.",
        "SMBIOSBIOSVersion": "V5.0.0.13 R1.13.0 for D3403-U1x",
        "ReleaseDate": "2021-03-18T00:00:00+01:00",
    },
    "cpu": {
        "Name": "Intel(R) Core(TM) i5-6500T CPU @ 2.50GHz",
        "Manufacturer": "GenuineIntel",
        "NumberOfCores": 4,
        "NumberOfLogicalProcessors": 4,
        "MaxClockSpeed": 2500,
    },
    "pnp": [
        {"Name": "Intel(R) HD Graphics 530", "PNPClass": "Display",
         "DeviceID": "PCI\\VEN_8086&DEV_1912&SUBSYS_11D01734&REV_06\\3&11583659&0&10"},
        {"Name": "High Definition Audio Controller", "PNPClass": "Media",
         "DeviceID": "PCI\\VEN_8086&DEV_A170&SUBSYS_11E01734&REV_31\\3&11583659&0&FB"},
        {"Name": "Realtek PCIe GbE Family Controller", "PNPClass": "Net",
         "DeviceID": "PCI\\VEN_10EC&DEV_8168&SUBSYS_11C01734&REV_15\\4&123456&0&00E0"},
        {"Name": "Intel(R) Wireless-AC 8260", "PNPClass": "Net",
         "DeviceID": "PCI\\VEN_8086&DEV_24F3&SUBSYS_00108086&REV_3A\\4&ABC&0&00E1"},
        {"Name": "Intel(R) 100 Series/C230 Series Chipset Family USB 3.0 xHCI Controller",
         "PNPClass": "USB",
         "DeviceID": "PCI\\VEN_8086&DEV_A12F&SUBSYS_11DD1734&REV_31\\3&11583659&0&A0"},
        {"Name": "USB Composite Device", "PNPClass": "USB",
         "DeviceID": "USB\\VID_046D&PID_C52B\\6&ABCDEF&0&4"},
        {"Name": "Intel(R) Wireless Bluetooth(R)", "PNPClass": "Bluetooth",
         "DeviceID": "USB\\VID_8087&PID_0A2B\\5&1111&0&9"},
        {"Name": "Intel(R) 6th Generation Core Processor Family Platform I/O SATA AHCI Controller",
         "PNPClass": "SCSIAdapter",
         "DeviceID": "PCI\\VEN_8086&DEV_A102&SUBSYS_11D01734&REV_31\\3&11583659&0&B8"},
        {"Name": "ACPI x64-based PC", "PNPClass": "Computer",
         "DeviceID": "ACPI_HAL\\PNP0C08\\0"},
    ],
    "disks": [
        {"Model": "Samsung SSD 860 EVO 250GB", "Size": 250059350016},
        {"Model": "USB Flash Drive", "Size": 8000000000},
    ],
    "netAdapters": [
        {"Name": "Ethernet", "InterfaceDescription": "Realtek PCIe GbE Family Controller"},
        {"Name": "Wi-Fi", "InterfaceDescription": "Intel(R) Wireless-AC 8260"},
    ],
    "firmwareType": 2,
}


@pytest.fixture(autouse=True)
def _reset_cache(monkeypatch):
    """Ogni test parte da cache vuota; payload iniettato dove serve."""
    win._clear_windows_cache()
    yield
    win._clear_windows_cache()


def _inject(monkeypatch, payload):
    monkeypatch.setattr(win, "windows_data", lambda: payload)


# ---------------------------------------------------------------------------
# Parsing ID PnP
# ---------------------------------------------------------------------------


class TestParseIds:
    def test_pci(self):
        ids = win.parse_ids("PCI\\VEN_8086&DEV_A12F&SUBSYS_11DD1734&REV_31\\3&X&0&A0")
        assert ids == {"vendor_id": "8086", "device_id": "a12f", "id": "8086:a12f"}

    def test_usb(self):
        ids = win.parse_ids("USB\\VID_046D&PID_C52B\\6&ABCDEF&0&4")
        assert ids == {"vendor_id": "046d", "device_id": "c52b", "id": "046d:c52b"}

    def test_uppercase_normalizzato(self):
        ids = win.parse_ids("PCI\\VEN_10EC&DEV_8168")
        assert ids["id"] == "10ec:8168"

    def test_nessun_id(self):
        assert win.parse_ids("ACPI_HAL\\PNP0C08\\0") == {
            "vendor_id": "", "device_id": "", "id": ""}

    def test_stringa_vuota(self):
        assert win.parse_ids("")["id"] == ""
        assert win.parse_ids(None)["id"] == ""


# ---------------------------------------------------------------------------
# Classificazione device
# ---------------------------------------------------------------------------


class TestClassify:
    @pytest.mark.parametrize(
        "name,cls,expected",
        [
            ("Intel(R) HD Graphics 530", "Display", "display"),
            ("High Definition Audio Controller", "Media", "audio"),
            ("NVIDIA HDMI Audio", "Media", "audio"),
            ("Realtek PCIe GbE Family Controller", "Net", "ethernet"),
            ("Intel(R) Wireless-AC 8260", "Net", "wifi"),
            ("Qualcomm Wi-Fi 6 Adapter", "Net", "wifi"),
            ("Intel 802.11ax Wireless", "Net", "wifi"),
            ("xHCI USB 3.0 extensible Host Controller", "USB", "usb_ctrl"),
            ("USB Composite Device", "USB", "usb_dev"),
            ("Intel(R) Wireless Bluetooth(R)", "Bluetooth", "bluetooth"),
            ("SATA AHCI Controller", "SCSIAdapter", "sata"),
            ("Standard NVM Express Controller", "SCSIAdapter", "nvme"),
            ("Microsoft ACPI-Compliant System", "System", "other"),
        ],
    )
    def test_categorie(self, name, cls, expected):
        assert win.classify_pnp_device(name, cls, "PCI\\VEN_0000&DEV_0000") == expected


class TestParsePnpDevices:
    def test_raggruppamento(self):
        grouped = win.parse_pnp_devices(Q5562_PAYLOAD["pnp"])
        assert len(grouped["display"]) == 1
        assert grouped["display"][0]["vendor_id"] == "8086"
        assert len(grouped["audio"]) == 1
        assert len(grouped["ethernet"]) == 1
        assert len(grouped["wifi"]) == 1
        assert len(grouped["usb_ctrl"]) == 1
        assert len(grouped["usb_dev"]) == 1
        assert len(grouped["bluetooth"]) == 1
        assert len(grouped["sata"]) == 1

    def test_i_device_noti_vengono_ignorati(self):
        grouped = win.parse_pnp_devices(Q5562_PAYLOAD["pnp"])
        # "Computer" non deve finire in nessuna categoria utile.
        flat = [d for entries in grouped.values() for d in entries]
        assert all("ACPI" not in d["slot"] or d["id"] for d in flat)
        assert "other" not in grouped

    def test_oggetto_singolo_invece_di_lista(self):
        grouped = win.parse_pnp_devices({"Name": "GPU", "PNPClass": "Display",
                                         "DeviceID": "PCI\\VEN_8086&DEV_1912"})
        assert len(grouped["display"]) == 1

    def test_input_vuoto(self):
        assert win.parse_pnp_devices([]) == {}
        assert win.parse_pnp_devices(None) == {}


# ---------------------------------------------------------------------------
# BIOS date
# ---------------------------------------------------------------------------


class TestBiosDate:
    def test_iso(self):
        assert win.parse_bios_date("2021-03-18T00:00:00+01:00") == "2021-03-18"

    def test_legacy_ps51(self):
        # /Date(1631664000000)/ -> 2021-09-15
        assert win.parse_bios_date("/Date(1631664000000)/") == "2021-09-15"

    def test_vuota(self):
        assert win.parse_bios_date(None) == ""
        assert win.parse_bios_date("") == ""


# ---------------------------------------------------------------------------
# Sezioni di detection (con payload iniettato)
# ---------------------------------------------------------------------------


class TestDmi:
    def test_campi(self, monkeypatch):
        _inject(monkeypatch, Q5562_PAYLOAD)
        out = win.detect_dmi_windows()
        assert out["system_vendor"].value == "FUJITSU"
        assert out["product_name"].value == "ESPRIMO Q5562"
        assert out["board_name"].value == "D3403-U"
        assert out["bios_date"].value == "2021-03-18"
        assert all(v.status == STATUS_DETECTED for v in out.values())

    def test_payload_vuoto(self, monkeypatch):
        _inject(monkeypatch, {})
        out = win.detect_dmi_windows()
        assert all(v.status == STATUS_NOT_DETECTED and v.value is None
                   for v in out.values())


class TestCpu:
    def test_campi(self, monkeypatch):
        _inject(monkeypatch, Q5562_PAYLOAD)
        out = win.detect_cpu_windows()
        assert "i5-6500T" in out["model"].value
        assert out["vendor"].value == "GenuineIntel"
        assert out["cores"].value == "4"
        assert out["cores"].status == STATUS_DETECTED
        assert out["threads"].value == "4"
        # Generazione: INFERRED (deduced), mai DETECTED.
        assert out["generation"].status == STATUS_INFERRED
        assert "Skylake" in out["generation"].value
        # Feature flags non disponibili via CIM: onesti, non inventati.
        assert out["features"].status == STATUS_NOT_DETECTED

    def test_cpu_sconosciuta(self, monkeypatch):
        _inject(monkeypatch, {"cpu": {"Name": "ARM Something"}})
        out = win.detect_cpu_windows()
        assert out["generation"].status == STATUS_NOT_DETECTED


class TestGpu:
    def test_gpu(self, monkeypatch):
        _inject(monkeypatch, Q5562_PAYLOAD)
        out = win.detect_gpu_windows()
        assert out["gpu_id"].value == "8086:1912"
        assert out["gpu_vendor"].value == "Intel"
        assert out["gpu_type"].value == "integrated"
        assert out["gpu_type"].status == STATUS_INFERRED
        assert out["gpu_vram"].status == STATUS_NOT_DETECTED

    def test_nessuna_gpu(self, monkeypatch):
        _inject(monkeypatch, {})
        out = win.detect_gpu_windows()
        assert out["gpu"].status == STATUS_NOT_DETECTED


class TestUsb:
    def test_controller_e_device(self, monkeypatch):
        _inject(monkeypatch, Q5562_PAYLOAD)
        out = win.detect_usb_windows()
        assert "xHCI" in out["usb_controllers"].value
        assert out["usb_count"].value == 1
        assert out["usb_devices"].value[0]["id"] == "046d:c52b"


class TestBluetooth:
    def test_radio_bt(self, monkeypatch):
        _inject(monkeypatch, Q5562_PAYLOAD)
        out = win.detect_bluetooth_windows()
        assert out["bluetooth_id"].value == "8087:0a2b"
        assert out["bluetooth_vendor"].value == "Intel"


class TestStorage:
    def test_dischi(self, monkeypatch):
        _inject(monkeypatch, Q5562_PAYLOAD)
        out = win.detect_storage_windows()
        assert out["storage_count"].value == 2
        assert "Samsung SSD 860 EVO" in out["storage"].value
        assert "232 GB" in out["storage"].value

    def test_controller_sata_nvme(self, monkeypatch):
        _inject(monkeypatch, Q5562_PAYLOAD)
        out = win.detect_sata_nvme_windows()
        assert "AHCI" in out["sata_controllers"].value
        assert out["nvme_controllers"].status == STATUS_NOT_DETECTED


class TestNet:
    def test_interfacce(self, monkeypatch):
        _inject(monkeypatch, Q5562_PAYLOAD)
        out = win.detect_net_interfaces_windows()
        assert out["net_interfaces"].value == "Ethernet, Wi-Fi"


class TestUefi:
    def test_uefi(self, monkeypatch):
        _inject(monkeypatch, {"firmwareType": 2})
        assert win.detect_uefi_windows().value == "UEFI"

    def test_legacy(self, monkeypatch):
        _inject(monkeypatch, {"firmwareType": 1})
        assert win.detect_uefi_windows().value == "Legacy BIOS"

    def test_sconosciuto(self, monkeypatch):
        _inject(monkeypatch, {})
        assert win.detect_uefi_windows().status == STATUS_NOT_DETECTED

    def test_valore_non_numerico(self, monkeypatch):
        _inject(monkeypatch, {"firmwareType": "nope"})
        assert win.detect_uefi_windows().status == STATUS_NOT_DETECTED


class TestAcpi:
    def test_not_available_onesta(self):
        out = win.detect_acpi_windows()
        assert out["acpi_tables"].status == STATUS_NOT_AVAILABLE


# ---------------------------------------------------------------------------
# Runner PowerShell (fuori da Windows non deve mai partire)
# ---------------------------------------------------------------------------


class TestRunner:
    def test_fuori_windows_ritorna_none(self, monkeypatch):
        monkeypatch.setattr(win, "current_platform", lambda: "linux")
        assert win.run_powershell() is None

    def test_senza_powershell_ritorna_none(self, monkeypatch):
        monkeypatch.setattr(win, "current_platform", lambda: "windows")
        monkeypatch.setattr(win, "_powershell_bin", lambda: None)
        assert win.run_powershell() is None

    def test_cache(self, monkeypatch):
        calls = []

        def fake_run(script=win._PS_SCRIPT, timeout=win.PS_TIMEOUT):
            calls.append(1)
            return {"firmwareType": 2}

        monkeypatch.setattr(win, "run_powershell", fake_run)
        win._clear_windows_cache()
        assert win.windows_data() == {"firmwareType": 2}
        assert win.windows_data() == {"firmwareType": 2}
        assert len(calls) == 1

    def test_run_powershell_json_valido(self, monkeypatch):
        import subprocess as sp

        class FakeProc:
            returncode = 0
            stdout = '{"firmwareType": 2, "cpu": {"Name": "x"}}'
            stderr = ""

        monkeypatch.setattr(win, "current_platform", lambda: "windows")
        monkeypatch.setattr(win, "_powershell_bin", lambda: "powershell")
        monkeypatch.setattr(sp, "run", lambda *a, **kw: FakeProc())
        assert win.run_powershell() == {"firmwareType": 2, "cpu": {"Name": "x"}}

    def test_run_powershell_json_rot(self, monkeypatch):
        import subprocess as sp

        class FakeProc:
            returncode = 0
            stdout = "not json at all"
            stderr = ""

        monkeypatch.setattr(win, "current_platform", lambda: "windows")
        monkeypatch.setattr(win, "_powershell_bin", lambda: "powershell")
        monkeypatch.setattr(sp, "run", lambda *a, **kw: FakeProc())
        assert win.run_powershell() is None
