# ACPI SSDTs for Fujitsu Esprimo Q556/2

This folder should contain prebuilt SSDTs for Q556/2.

## Required SSDTs (Skylake Desktop)

Based on Dortania guide for Skylake:

### SSDT-PLUG.aml
- **Purpose**: Enables XCPM (XNU CPU Power Management)
- **Source**: https://github.com/dortania/Getting-Started-With-ACPI/blob/master/extra-files/compiled/SSDT-PLUG-DRTNIA.aml
- **Required**: YES

### SSDT-EC-USBX.aml
- **Purpose**: Fixes Embedded Controller and USB power
- **Source**: https://github.com/dortania/Getting-Started-With-ACPI/blob/master/extra-files/compiled/SSDT-EC-USBX-DESKTOP.aml
- **Required**: YES

### SSDT-AWAC.aml
- **Purpose**: Fixes AWAC clock (RTC)
- **Source**: https://github.com/dortania/Getting-Started-With-ACPI/blob/master/extra-files/compiled/SSDT-AWAC.aml
- **Required**: YES (if AWAC present, check via DSDT)

### SSDT-PMC.aml
- **Purpose**: Fixes NVRAM on H110 chipset (PMC)
- **Source**: https://github.com/dortania/Getting-Started-With-ACPI/blob/master/extra-files/compiled/SSDT-PMC.aml
- **Required**: YES for H110/B250

## How to get them

The tool automatically downloads them from:
- https://raw.githubusercontent.com/dortania/Getting-Started-With-ACPI/master/extra-files/compiled/

If download fails, manually download from:
https://github.com/dortania/Getting-Started-With-ACPI/tree/master/extra-files/compiled

And place .aml files here.

## Q556/2 Specific

For Q556/2 with D3403-U board:
- All 4 SSDTs are needed
- SSDT-PMC is critical for NVRAM on H110
- If you have issues, also try SSDT-RHUB for USB

## Compilation

If you need to compile from DSL:
```bash
iasl SSDT-PLUG.dsl
```

Use latest iasl from Acidanthera.
