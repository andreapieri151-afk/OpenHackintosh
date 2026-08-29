# Guida BIOS per Q556/2 - Senza di questa non boota manco per miracolo

Ok, questa è la parte più pallosa ma più importante. Se sbagli qui, puoi avere l'EFI più bella del mondo ma non boota.

Te lo dico per esperienza: ho passato un pomeriggio a pensare che l'EFI fosse sbagliata, invece avevo Secure Boot attivo.

## Come entrare nel BIOS

Accendi il PC, appena vedi il logo Fujitsu spamma **F2** come se non ci fosse un domani. Se non entra, prova F12 per boot menu, poi da lì vai in BIOS.

Se proprio non entra: togli l'SSD/HDD e accendi senza, a volte così entra più facile.

## La cosa più importante: DVMT Pre-Allocated

### Cos'è?
È quanta RAM la scheda madre riserva alla grafica integrata (HD 530). macOS ne vuole almeno 64MB, altrimenti fa kernel panic e ti saluta.

### Dove sta?
Advanced -> Graphics Configuration -> DVMT Pre-Allocated

### Cosa mettere?
**64MB**. O 128MB se c'è. Non 32MB. 32MB = non boota.

### Se non lo trovi?
E qui casca l'asino. Fujitsu su molti BIOS lo nasconde. Succede spesso.

Il mio tool ti mette già una patch nel config.plist (framebuffer-stolenmem 19MB, fbmem 9MB) che dovrebbe aggirare il problema, ma non è garantito al 100%.

Se vuoi fare il figo e sbloccarlo davvero:

1. **Metodo facile (ma non sempre funziona):** Cerca su bios-mods.com "Q556/2 DVMT unlock", qualcuno ha già moddato il BIOS.

2. **Metodo medio:** Usa setup_var da EFI Shell. Devi trovare l'offset giusto per il tuo BIOS (cambia per versione). Esempio:
   ```
   setup_var 0x123 0x2  # 0x2 = 64MB, ma 0x123 è un esempio, non è quello vero per Q556/2
   ```
   Per trovare offset vero: dumpa il BIOS con AFU o CH341A programmer, aprilo con AMIBCP o UEFITool, cerca DVMT.

3. **Metodo difficile (ma sicuro):** Compra un CH341A programmer (10€ su Amazon) + clip SOIC8, dumpa il BIOS, moddalo con AMIBCP sbloccando le opzioni nascoste, riflasha con programmer. Rischio brick quasi zero se usi programmer.

Se non vuoi sbatterti, prova prima con la patch del tool. A me con 32MB + patch ha bootato, ma con qualche glitch grafico ogni tanto.

## Cosa disabilitare (tutta roba che rompe le palle a macOS)

Vai in giro per il BIOS e disabilita:

- **Fast Boot** - In Boot, mettilo Disabled. Altrimenti salta dei check e fa casini.
- **Secure Boot** - In Security -> Secure Boot Configuration, Disabled. Altrimenti non fa bootare OpenCore perché non è firmato Microsoft.
- **Serial Port / COM Port** - In Advanced -> Super IO, Disabled. Non serve a nulla e occupa IRQ.
- **Parallel Port** - Se c'è, Disabled.
- **VT-d** - In Advanced -> CPU Configuration, Disabled. È la virtualizzazione IOMMU, macOS non la vuole. Oppure lasciala Enabled ma il config ha già DisableIoMapper YES che la bypassa.
- **CSM** - In Boot -> CSM, Disabled. Vogliamo solo UEFI puro, non legacy.
- **Intel SGX** - In Advanced o Security, Disabled. Roba di sicurezza Intel che rompe.
- **Intel Platform Trust** - In Security, Disabled.

## Cosa abilitare

- **VT-x** - In CPU Configuration, Enabled. È la virtualizzazione base, serve.
- **Above 4G decoding** - In Advanced -> PCI Subsystem, Enabled se c'è. Se non c'è, lascia stare e aggiungi boot-arg npci=0x2000 (ma il tool non lo mette di default, lo devi aggiungere tu se serve).
- **EHCI/XHCI Hand-off** - In USB Configuration, Enabled. Serve per USB.
- **OS Type** - In Boot, metti Windows 8.1/10 UEFI Mode. Sì, anche se installi macOS, metti Windows. È un trucco per far abilitare UEFI puro.
- **DVMT Total** - In Graphics, metti MAX.
- **Boot Mode** - UEFI only, non Legacy.

## CFG Lock - Il secondo boss

### Cos'è?
È un lock che impedisce a macOS di scrivere su un registro della CPU (MSR 0xE2). Se è Enabled, macOS si incazza.

### Come lo disabiliti?

**Opzione 1: Se lo trovi nel BIOS** (raro su Fujitsu, ma controlla in CPU Configuration)
- CFG Lock -> Disabled. Fatto.

**Opzione 2: Con CFGLock.efi (consigliato)**
1. Scarica OpenCorePkg, dentro c'è EFI/OC/Tools/CFGLock.efi
2. Mettilo in EFI/OC/Tools della tua chiavetta
3. Nel config.plist vai in Misc -> Tools e abilita CFGLock.efi (Enabled YES)
4. Boota da OpenCore, premi spazio per vedere i tools nascosti, seleziona CFGLock.efi
5. Ti dice se è Enabled o Disabled, e ti chiede se vuoi disabilitarlo. Dì di sì.
6. Riavvia, torna nel config e disabilita di nuovo CFGLock.efi (per non vederlo sempre)

**Opzione 3: Con setup_var**
Come per DVMT, trovi offset CFG Lock e fai:
```
setup_var 0x4ED 0x0  # 0x0 = Disabled, ma offset varia per BIOS
```
Devi dumpare BIOS e cercare.

**Opzione 4: Fregatene (quello che fa il tool)**
Il tool mette AppleXcpmCfgLock YES e AppleCpuPmCfgLock YES nel config. Così anche se CFG Lock è Enabled, macOS non si lamenta. Non è perfetto per power management, ma funziona. Io lo uso così da mesi e non ho problemi.

## Reset BIOS se hai incasinato tutto

Capita. Hai messo un valore sbagliato e ora non boota più nemmeno il BIOS.

1. Spegni PC, stacca spina
2. Apri case (2 viti dietro, scorri il coperchio)
3. Trova la batteria a bottone (CMOS) e il jumper vicino (di solito 3 pin con cappuccio su 1-2)
4. Sposta jumper da 1-2 a 2-3 per 10 secondi, poi rimetti su 1-2
5. Oppure togli batteria per 10 minuti
6. Riattacca tutto, accendi. BIOS resettato a default.

Oppure tieni premuto power 30 secondi senza alimentazione, a volte funziona.

## Note specifiche Q556/2

- **RAM:** 2 slot SO-DIMM DDR4, max 32GB. Metti 2 banchi uguali per dual channel, va più veloce. Io ho 2x8GB 2400MHz (che vanno a 2133 con 6th gen).
- **Storage:** Ha un M.2 (controlla se SATA o NVMe, il mio era SATA) + un 2.5" SATA. Io ho messo NVMe + SSD.
- **LAN:** Realtek RTL8111GN - funziona con RealtekRTL8111.kext, il tool lo mette già.
- **Audio:** ALC671 - layout 11 di solito va, ma prova 13,15,21 se non va. Io con 11 ho audio perfetto.
- **USB:** 2x USB 2.0 dietro, 4x USB 3.0 (2 davanti, 2 dietro). Mappale con USBToolBox dopo installazione, altrimenti vanno a caso.
- **Video:** Ha DP e DVI-D, non HDMI. Se vuoi HDMI compra adattatore DP->HDMI attivo (quelli passivi non vanno con HD 530).
- **WiFi/BT:** Se hai modulo M.2 2230 Intel, usa AirportItlwm + IntelBluetoothFirmware (il tool ha opzione per includerli).

## Dopo che hai sistemato BIOS

1. Crea chiavetta macOS con createinstallmedia (ci sono guide ovunque)
2. Usa OpenHackintosh per generare EFI (scegli Q556/2, Ventura, iMac18,1)
3. Monta EFI della chiavetta (con Hackintool o mountEFI)
4. Copia cartella EFI dentro
5. Boota da chiavetta (F12 all'avvio -> USB)
6. Installa macOS
7. Dopo install, monta EFI del disco interno e copia EFI lì
8. Poi mappa USB, genera SMBIOS tuo con GenSMBIOS, etc.

Se segui questa guida e usi EFI vera del tool, boota al 99%. Se non boota, 90% è BIOS, 9% è SMBIOS, 1% è sfiga.

Buona fortuna, e ricordati: DVMT 64MB!
