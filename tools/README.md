# Tools

Utility scripts for Q556/2 Hackintosh.

## GenSMBIOS

Use CorpNewt's GenSMBIOS for proper serial generation:

```bash
git clone https://github.com/corpnewt/GenSMBIOS
cd GenSMBIOS
python GenSMBIOS.py
```

Select iMac18,1 or iMacPro1,1 and generate.

## ProperTree

For editing config.plist:

```bash
git clone https://github.com/corpnewt/ProperTree
cd ProperTree
python ProperTree.py
```

## OCValidate

Validate config.plist with OpenCore's ocvalidate:

Download OpenCorePkg, find Utilities/ocvalidate/ocvalidate and run:

```bash
./ocvalidate EFI/OC/config.plist
```

## USBToolBox

For USB mapping:

https://github.com/USBToolBox/tool

## Hackintool

For post-install tweaks:

https://github.com/headkaze/Hackintool
