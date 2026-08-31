"""
OpenHackintosh - GUI professionale per creazione EFI
"""
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import customtkinter as ctk
    HAS_CTK = True
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
except ImportError:
    HAS_CTK = False
    ctk = None

sys.path.insert(0, str(Path(__file__).parent.parent))

from efi_builder.hardware import PROFILES, MACOS_VERSIONS, Q556_2
from efi_builder.builder import EFIBuilder

if HAS_CTK:
    class EFICreatorGUI:
        def __init__(self):
            self.root = ctk.CTk()
            self.root.title("OpenHackintosh - EFI Creator")
            # Finestra adattabile allo schermo - fix per pulsanti non visibili
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            width = min(1100, max(900, int(screen_width * 0.85)))
            height = min(750, max(600, int(screen_height * 0.85)))
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            self.root.geometry(f"{width}x{height}+{x}+{y}")
            self.root.minsize(900, 600)
            self.output_dir = Path.home() / "Desktop" / "EFI_Q5562"
            self.setup_ui()
        
        def setup_ui(self):
            main_frame = ctk.CTkFrame(self.root)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            header = ctk.CTkFrame(main_frame, fg_color="transparent")
            header.pack(fill="x", padx=15, pady=(10,5))
            
            title = ctk.CTkLabel(header, text="OpenHackintosh", font=ctk.CTkFont(size=24, weight="bold"))
            title.pack(anchor="w")
            
            subtitle = ctk.CTkLabel(header, text="Crea EFI per Fujitsu Esprimo Q556/2 e altri", font=ctk.CTkFont(size=13), text_color="gray")
            subtitle.pack(anchor="w")
            
            content = ctk.CTkFrame(main_frame, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=10, pady=5)
            
            # Left scrollabile per schermi piccoli
            left = ctk.CTkScrollableFrame(content, width=350)
            left.pack(side="left", fill="both", expand=False, padx=(0,5), pady=0)
            
            right = ctk.CTkFrame(content)
            right.pack(side="right", fill="both", expand=True, padx=(5,0), pady=0)
            
            ctk.CTkLabel(left, text="Configurazione", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=15, pady=(15,10))
            
            ctk.CTkLabel(left, text="Modello PC").pack(anchor="w", padx=15, pady=(10,0))
            self.profile_var = ctk.StringVar(value="Q556/2")
            self.profile_menu = ctk.CTkOptionMenu(left, values=list(PROFILES.keys()), variable=self.profile_var, command=self.on_profile_change)
            self.profile_menu.pack(fill="x", padx=15, pady=5)
            
            self.profile_info = ctk.CTkLabel(left, text="", justify="left", font=ctk.CTkFont(size=11), text_color="gray")
            self.profile_info.pack(anchor="w", padx=15, pady=5)
            self.on_profile_change("Q556/2")
            
            ctk.CTkLabel(left, text="Versione macOS").pack(anchor="w", padx=15, pady=(12,0))
            self.macos_var = ctk.StringVar(value="Ventura 13.x")
            self.macos_menu = ctk.CTkOptionMenu(left, values=list(MACOS_VERSIONS.keys()), variable=self.macos_var)
            self.macos_menu.pack(fill="x", padx=15, pady=5)
            
            ctk.CTkLabel(left, text="SMBIOS").pack(anchor="w", padx=15, pady=(12,0))
            self.smbios_var = ctk.StringVar(value="iMac18,1")
            self.smbios_menu = ctk.CTkOptionMenu(left, values=["iMac17,1", "iMac18,1", "iMac19,1", "Macmini8,1", "iMacPro1,1", "MacPro7,1"], variable=self.smbios_var)
            self.smbios_menu.pack(fill="x", padx=15, pady=5)
            
            ctk.CTkLabel(left, text="Layout Audio (ALC671)").pack(anchor="w", padx=15, pady=(12,0))
            self.audio_var = ctk.StringVar(value="11")
            self.audio_menu = ctk.CTkOptionMenu(left, values=["11", "13", "15", "21", "27", "28"], variable=self.audio_var)
            self.audio_menu.pack(fill="x", padx=15, pady=5)
            
            ctk.CTkLabel(left, text="Componenti opzionali").pack(anchor="w", padx=15, pady=(12,0))
            self.wifi_var = ctk.BooleanVar(value=False)
            self.bt_var = ctk.BooleanVar(value=False)
            self.optional_kexts_var = ctk.BooleanVar(value=False)
            self.optional_ssdts_var = ctk.BooleanVar(value=False)
            self.dev_mode_var = ctk.BooleanVar(value=False)
            self.minimal_var = ctk.BooleanVar(value=True)
            
            self.wifi_check = ctk.CTkCheckBox(left, text="WiFi Intel (AirportItlwm)", variable=self.wifi_var)
            self.wifi_check.pack(anchor="w", padx=15, pady=3)
            
            self.bt_check = ctk.CTkCheckBox(left, text="Bluetooth Intel", variable=self.bt_var)
            self.bt_check.pack(anchor="w", padx=15, pady=3)

            self.optional_kexts_check = ctk.CTkCheckBox(left, text="Kext opzionali (NVMeFix)", variable=self.optional_kexts_var)
            self.optional_kexts_check.pack(anchor="w", padx=15, pady=3)

            self.optional_ssdts_check = ctk.CTkCheckBox(left, text="SSDT-PMC opzionale", variable=self.optional_ssdts_var)
            self.optional_ssdts_check.pack(anchor="w", padx=15, pady=3)

            ctk.CTkLabel(left, text="Modalità").pack(anchor="w", padx=15, pady=(12,0))
            self.dev_check = ctk.CTkCheckBox(left, text="Modalità sviluppo (debug)", variable=self.dev_mode_var)
            self.dev_check.pack(anchor="w", padx=15, pady=3)

            self.minimal_check = ctk.CTkCheckBox(left, text="Configurazione minimal Q556/2", variable=self.minimal_var)
            self.minimal_check.pack(anchor="w", padx=15, pady=3)
            
            ctk.CTkLabel(left, text="Cartella di output").pack(anchor="w", padx=15, pady=(12,0))
            output_frame = ctk.CTkFrame(left, fg_color="transparent")
            output_frame.pack(fill="x", padx=15, pady=5)
            
            self.output_entry = ctk.CTkEntry(output_frame, placeholder_text=str(self.output_dir))
            self.output_entry.pack(side="left", fill="x", expand=True, padx=(0,5))
            self.output_entry.insert(0, str(self.output_dir))
            
            browse_btn = ctk.CTkButton(output_frame, text="Sfoglia", width=70, command=self.browse_output)
            browse_btn.pack(side="right")
            
            # Pulsante sempre visibile
            self.build_btn = ctk.CTkButton(left, text="Crea EFI", font=ctk.CTkFont(size=15, weight="bold"), height=45, command=self.start_build)
            self.build_btn.pack(fill="x", padx=15, pady=15)
            
            ctk.CTkLabel(right, text="Log", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(15,5))
            
            self.progress = ctk.CTkProgressBar(right)
            self.progress.pack(fill="x", padx=15, pady=5)
            self.progress.set(0)
            
            self.status_label = ctk.CTkLabel(right, text="Pronto", font=ctk.CTkFont(size=12))
            self.status_label.pack(anchor="w", padx=15, pady=2)
            
            self.log_box = ctk.CTkTextbox(right, font=ctk.CTkFont(family="Courier", size=11))
            self.log_box.pack(fill="both", expand=True, padx=15, pady=10)
            self.log_box.insert("1.0", """OpenHackintosh - Generatore EFI per Q556/2

Seleziona il modello, la versione di macOS e clicca Crea EFI.

La EFI generata include:
- OpenCore da Acidanthera
- Kext essenziali (Lilu, VirtualSMC, WhateverGreen, AppleALC, LAN)
- SSDT specifici per Q556/2 (PLUG-DRTNIA + EC-USBX-DESKTOP)
- Config.plist ottimizzato per HD 530 e ALC671

Per problemi di avvio verifica BIOS: DVMT 64MB, Secure Boot disabilitato.
""")
            
            self.smbios_preview = ctk.CTkFrame(right)
            self.smbios_preview.pack(fill="x", padx=15, pady=(0,10))
            
            ctk.CTkLabel(self.smbios_preview, text="SMBIOS generato:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(8,0))
            self.smbios_text = ctk.CTkLabel(self.smbios_preview, text="Verrà generato durante la creazione EFI", justify="left", font=ctk.CTkFont(family="Courier", size=10), text_color="gray")
            self.smbios_text.pack(anchor="w", padx=10, pady=8)
        
        def on_profile_change(self, value):
            profile = PROFILES.get(value, Q556_2)
            info = f"Board: {profile.board}\nLAN: {profile.lan_chip}\nAudio: {profile.audio_codec}\nCPU: {', '.join(profile.cpu_generations[:1])}"
            self.profile_info.configure(text=info)
        
        def browse_output(self):
            folder = filedialog.askdirectory(initialdir=str(self.output_dir))
            if folder:
                self.output_dir = Path(folder)
                self.output_entry.delete(0, "end")
                self.output_entry.insert(0, folder)
        
        def log(self, msg):
            self.root.after(0, lambda: self._log(msg))
        
        def _log(self, msg):
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.status_label.configure(text=msg[:65])
        
        def progress_callback(self, name, current, total):
            if total > 0:
                pct = current / total
                self.root.after(0, lambda: self.progress.set(pct))
        
        def start_build(self):
            self.build_btn.configure(state="disabled", text="Creazione in corso...")
            self.progress.set(0.1)
            self.log_box.delete("1.0", "end")
            
            profile = self.profile_var.get()
            macos = self.macos_var.get()
            smbios_model = self.smbios_var.get()
            audio_layout = int(self.audio_var.get())
            include_wifi = self.wifi_var.get()
            include_bt = self.bt_var.get()
            include_optional_kexts = self.optional_kexts_var.get()
            include_optional_ssdts = self.optional_ssdts_var.get()
            dev_mode = self.dev_mode_var.get()
            minimal_q5562 = self.minimal_var.get()
            output = Path(self.output_entry.get())
            
            def build_thread():
                try:
                    builder = EFIBuilder(output, progress_callback=self.progress_callback)
                    def log_wrapper(event, msg=""):
                        if event == "log":
                            self.log(msg)
                    builder.progress_callback = log_wrapper
                    
                    result = builder.build(
                        profile_name=profile,
                        smbios_model=smbios_model,
                        audio_layout=audio_layout,
                        macos_version=macos,
                        include_wifi=include_wifi,
                        include_bluetooth=include_bt,
                        include_optional_kexts=include_optional_kexts,
                        include_optional_ssdts=include_optional_ssdts,
                        dev_mode=dev_mode,
                        minimal_q5562=minimal_q5562,
                        generate_zip=True
                    )
                    
                    if result["success"]:
                        self.root.after(0, lambda: self.on_build_success(result))
                    else:
                        self.root.after(0, lambda: self.on_build_failed(result))
                except Exception as e:
                    import traceback
                    err = traceback.format_exc()
                    self.root.after(0, lambda: self.on_build_error(str(e), err))
            
            threading.Thread(target=build_thread, daemon=True).start()
        
        def on_build_success(self, result):
            self.progress.set(1.0)
            self.build_btn.configure(state="normal", text="Crea EFI")
            self.status_label.configure(text="Completato")
            
            smbios = result["smbios"]
            preview = f"Model: {smbios['ProductName']}\nSerial: {smbios['SerialNumber']}\nMLB: {smbios['MLB']}\nUUID: {smbios['SystemUUID'][:8]}...\nROM: {smbios['ROM']}"
            self.smbios_text.configure(text=preview)
            
            self.log(f"\nCompletato! EFI in: {result['efi_path']}")
            self.log(f"ZIP: {result['zip_path']}")
            
            messagebox.showinfo("Completato", f"EFI creata!\n\nPercorso: {result['efi_path']}\nZIP: {result['zip_path']}\n\nSeriale: {smbios['SerialNumber']}\nModello: {smbios['ProductName']}")
        
        def on_build_failed(self, result):
            self.progress.set(0)
            self.build_btn.configure(state="normal", text="Crea EFI")
            self.status_label.configure(text="Errore")
            messagebox.showerror("Errore", f"Creazione fallita: {result.get('error', 'errore sconosciuto')}\nVerifica la connessione internet.")
        
        def on_build_error(self, msg, traceback_str):
            self.progress.set(0)
            self.build_btn.configure(state="normal", text="Crea EFI")
            self.status_label.configure(text="Errore")
            self.log(f"\nErrore: {msg}\n{traceback_str}")
            messagebox.showerror("Errore", f"Errore: {msg}")
        
        def run(self):
            self.root.mainloop()

else:
    class EFICreatorGUI:
        def __init__(self):
            self.root = tk.Tk()
            self.root.title("OpenHackintosh - EFI Creator")
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            width = min(900, int(screen_width * 0.8))
            height = min(600, int(screen_height * 0.8))
            self.root.geometry(f"{width}x{height}")
            self.root.minsize(800, 500)
            self.output_dir = Path.home() / "Desktop" / "EFI_Q5562"
            self.setup_ui()
        
        def setup_ui(self):
            frame = ttk.Frame(self.root, padding=15)
            frame.pack(fill="both", expand=True)
            ttk.Label(frame, text="OpenHackintosh", font=("Arial", 14, "bold")).pack(anchor="w", pady=5)
            ttk.Label(frame, text="Installa customtkinter: pip install customtkinter").pack(anchor="w")
            self.profile_var = tk.StringVar(value="Q556/2")
            ttk.OptionMenu(frame, self.profile_var, "Q556/2", *PROFILES.keys()).pack(fill="x", pady=5)
            ttk.Button(frame, text="Crea EFI", command=self.start_build).pack(fill="x", pady=15)
            self.log_text = tk.Text(frame, height=15)
            self.log_text.pack(fill="both", expand=True, pady=5)
            self.log_text.insert("1.0", "Interfaccia base - installa customtkinter\n")
        
        def start_build(self):
            import threading
            def build():
                self.log_text.insert("end", "Avvio creazione EFI...\n")
                try:
                    from efi_builder.builder import EFIBuilder
                    builder = EFIBuilder(self.output_dir)
                    result = builder.build(profile_name=self.profile_var.get())
                    self.log_text.insert("end", f"Completato: {result}\n")
                except Exception as e:
                    self.log_text.insert("end", f"Errore: {e}\n")
            threading.Thread(target=build, daemon=True).start()
        
        def run(self):
            self.root.mainloop()

def main():
    app = EFICreatorGUI()
    app.run()

if __name__ == "__main__":
    main()
