# Tools

Utility scripts for Q556/2 Hackintosh.

## Script del repository

- `build_release.py` — costruisce lo ZIP di distribuzione (`releases/`), deterministico.
- `junit_annotate.py` — legge un report JUnit XML di pytest ed emette i fallimenti come annotazioni GitHub (utile quando i log CI non sono scaricabili).
- `pty_probe.py` — sonda diagnostica per select/pty su macOS (usata per individuare il wake-up mancato di `select()` su pty slave Darwin; esce sempre 0).

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
