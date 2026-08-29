# Da file finti a file veri - La storia di come ho bestemmiato 3 giorni

Ok, ti racconto cosa è successo davvero, senza giri di parole.

## Il tool di prima (quello fatto con Google AI Studio)

Ero gasato, avevo appena scoperto AI Studio di Google, gli dico "fammi un tool che crea EFI per Q556/2". Lui mi fa una roba bellissima, cartelle ordinate, codice pulito, GUI carina.

Lo provo. Genero l'EFI. La metto sulla chiavetta. Booto. 

Niente. Logo Fujitsu, riavvio, logo Fujitsu, riavvio. All'infinito.

Controllo i file:

```bash
$ ls -lh EFI/BOOT/BOOTx64.efi
0 bytes

$ ls -lh EFI/OC/Kexts/Lilu.kext/Contents/MacOS/
total 0
vuoto

$ cat EFI/OC/Kexts/Lilu.kext/Contents/Info.plist
"fake plist"
```

Cioè, aveva creato la struttura, ma dentro file vuoti o con scritto "fake". Come se fai una torta bellissima fuori ma dentro è di cartone.

Ecco perché non bootava. OpenCore non può partire se BOOTx64.efi è vuoto. I kext non possono caricarsi se non hanno il binario dentro.

Ho perso 3 giorni a pensare fosse colpa del BIOS, di DVMT, di CFG Lock... invece erano file finti.

## Ora come funziona davvero

Ho riscritto tutto. Quando clicchi "Genera EFI", succede questo:

### 1. Scarica OpenCore vero

```python
# Chiama GitHub API ufficiale
https://api.github.com/repos/acidanthera/OpenCorePkg/releases/latest

# Trova il file tipo OpenCore-1.0.1-RELEASE.zip (10MB, non 0 byte)
# Lo scarica davvero
# Estrae BOOTx64.efi vero (50KB, PE32+ executable, non testo)
```

Non è un file che creo io a caso. È quello ufficiale di Acidanthera, gli stessi che fanno OpenCore.

### 2. Scarica i kext veri

Stessa cosa per ogni kext:

```python
# Per Lilu:
https://api.github.com/repos/acidanthera/Lilu/releases/latest
# Scarica Lilu-1.6.7-RELEASE.zip
# Estrae Lilu.kext con:
# - Info.plist vero (5KB, con CFBundleIdentifier vero)
# - MacOS/Lilu binario vero (245KB)
```

Prima il tool faceva:

```python
open("Lilu.kext/Contents/Info.plist", "w").write("fake")
```

Ora fa:

```python
download_file("https://github.com/acidanthera/Lilu/releases/download/.../Lilu-1.6.7-RELEASE.zip")
extract_kext_from_zip()
# Verifica che il binario esista e sia >100KB
```

### 3. Controlla che non siano finti

Ho aggiunto un validatore che dice:

```python
if file_size < 100 bytes:
    "Questo file è troppo piccolo, probabilmente è finto"
```

Così se qualcosa va storto nel download, te lo dice subito invece di farti una EFI che non boota.

### 4. Config.plist fatto come si deve

Prima il config era uno scheletro vuoto. Ora è basato sulla guida Dortania per Skylake Desktop, che è la Bibbia:

- ACPI con SSDT-PLUG, EC-USBX, AWAC, PMC (quelli veri, non nomi a caso)
- Kernel con Lilu per primo (obbligatorio, altrimenti non funziona nulla)
- DeviceProperties con ig-platform-id giusto per HD 530 (00001219)
- NVRAM con alcid=11 per ALC671
- UEFI con ReleaseUsbOwnership YES (fix per EXITBS:START)

Non l'ho inventato io, ho seguito Dortania passo passo.

## Come capisci se è vero o finto?

### Finto (prima):

```bash
$ file EFI/BOOT/BOOTx64.efi
empty

$ ls -lh EFI/OC/Kexts/Lilu.kext/Contents/MacOS/
total 0

$ ls -lh EFI/OC/Drivers/
total 0
```

### Vero (ora):

```bash
$ file EFI/BOOT/BOOTx64.efi
PE32+ executable (EFI application) x86-64

$ ls -lh EFI/OC/Kexts/Lilu.kext/Contents/MacOS/
-rwxr-xr-x  245K Lilu

$ ls -lh EFI/OC/Drivers/
40K HfsPlus.efi
30K OpenRuntime.efi
80K OpenCanopy.efi
```

Vedi la differenza? Uno è vuoto, l'altro ha roba dentro.

## Perché è importante?

Perché su Hackintosh non puoi barare. OpenCore è un bootloader vero che gira prima di macOS, deve essere un eseguibile EFI vero. I kext sono driver veri che macOS carica, devono avere binari veri.

Se sono finti, non boota. Punto.

Ora bootano. Testato sul mio Q556/2.

## Morale

Non fidarti dei tool che generano file senza scaricarli da fonti ufficiali. Se vedi una EFI di 100KB totale, è finta. Una EFI vera è almeno 10-15MB con tutti i kext e driver.

Il mio tool ora genera EFI da 15-20MB, con file veri. Quella è la prova.

Basta file finti. Basta bestemmiare davanti al logo Fujitsu.
