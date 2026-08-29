# Contributing

## Come contribuire

### Setup dev
```bash
git clone https://github.com/andreapieri151-afk/Fujistu-esprimo-q556-2-auxiliarty-tool
cd Fujistu-esprimo-q556-2-auxiliarty-tool
pip install -r requirements.txt
```

### Test
```bash
# Test import
python3 -c "import sys; sys.path.insert(0, 'src'); from efi_builder.builder import EFIBuilder; print('ok')"

# Test build offline (dummy files)
python3 src/cli.py --help

# Test web
python3 app.py
# Open http://localhost:5000

# Test GUI (macOS)
python3 main.py
```

### Struttura
- `src/efi_builder/hardware.py` - Profili hardware Q556/2, Q957, kext definitions
- `src/efi_builder/downloader.py` - Downloader REALI da GitHub
- `src/efi_builder/config_generator.py` - Generatore config.plist per Skylake
- `src/efi_builder/smbios.py` - Generatore SMBIOS
- `src/efi_builder/builder.py` - Orchestratore build
- `src/efi_builder/validator.py` - Validatore EFI
- `src/gui/app.py` - GUI moderna macOS
- `src/cli.py` - CLI
- `app.py` - Web Dashboard
- `templates/` - HTML template
- `assets/` - Icone, SSDT

### Aggiungere nuovo hardware

Modifica `src/efi_builder/hardware.py`:

```python
NEW_PROFILE = HardwareProfile(
    name="Fujitsu Esprimo XXX",
    board="DXXXX",
    ...
)

PROFILES["XXX"] = NEW_PROFILE
```

### Aggiungere nuovo kext

Modifica `KEXTS` in `hardware.py`:

```python
KEXTS["MyKext"] = {
    "repo": "user/repo",
    "required": False,
    "description": "...",
    "bundle": "MyKext.kext"
}
```

### Style

- Usa type hints
- Docstring per funzioni pubbliche
- Log con `self.log()` non print diretto
- Gestisci errori download (non crashare se GitHub down)

### Pull Request

1. Fork
2. Branch: `feature/mio-feature`
3. Commit con messaggio chiaro
4. Testa build
5. PR con descrizione

## Roadmap

- [ ] Integrazione macserial nativo (per seriali più accurati)
- [ ] USB mapping automatico
- [ ] OCAT integration
- [ ] Auto-update kexts
- [ ] Creazione installer USB automatica (createinstallmedia wrapper)
- [ ] Supporto per Q556 (non /2) e altri Esprimo
- [ ] Traduzione EN/DE oltre IT
