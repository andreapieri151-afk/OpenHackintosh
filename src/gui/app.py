"""
OpenHackintosh - GUI che parla come una persona
Non come quei tool freddi e tecnici
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
            self.root.title("OpenHackintosh - EFI vere, non finte")
            self.root.geometry("950x750")
            self.root.minsize(900, 700)
            self.output_dir = Path.home() / "Desktop" / "EFI_Q5562"
            self.setup_ui()
        
        def setup_ui(self):
            main_frame = ctk.CTkFrame(self.root)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            header = ctk.CTkFrame(main_frame, fg_color="transparent")
            header.pack(fill="x", padx=20, pady=(20,10))
            
            title = ctk.CTkLabel(header, text="OpenHackintosh 🍎", font=ctk.CTkFont(size=28, weight="bold"))
            title.pack(anchor="w")
            
            subtitle = ctk.CTkLabel(header, text="Nato perché mi ero rotto di EFI finte che non bootano", font=ctk.CTkFont(size=14), text_color="gray")
            subtitle.pack(anchor="w")
            
            badge = ctk.CTkLabel(header, text="✓ File veri da GitHub ufficiale • No fuffa • Funziona davvero", font=ctk.CTkFont(size=11), text_color="#30d158")
            badge.pack(anchor="w", pady=(5,0))
            
            content = ctk.CTkFrame(main_frame, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=20, pady=10)
            
            left = ctk.CTkFrame(content)
            left.pack(side="left", fill="both", expand=True, padx=(0,10))
            
            right = ctk.CTkFrame(content)
            right.pack(side="right", fill="both", expand=True, padx=(10,0))
            
            ctk.CTkLabel(left, text="Il tuo PC", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20,10))
            
            ctk.CTkLabel(left, text="Che PC hai?").pack(anchor="w", padx=20, pady=(10,0))
            self.profile_var = ctk.StringVar(value="Q556/2")
            self.profile_menu = ctk.CTkOptionMenu(left, values=list(PROFILES.keys()), variable=self.profile_var, command=self.on_profile_change)
            self.profile_menu.pack(fill="x", padx=20, pady=5)
            
            self.profile_info = ctk.CTkLabel(left, text="", justify="left", font=ctk.CTkFont(size=11), text_color="gray")
            self.profile_info.pack(anchor="w", padx=20, pady=5)
            self.on_profile_change("Q556/2")
            
            ctk.CTkLabel(left, text="Che macOS vuoi?").pack(anchor="w", padx=20, pady=(15,0))
            self.macos_var = ctk.StringVar(value="Ventura 13.x")
            self.macos_menu = ctk.CTkOptionMenu(left, values=list(MACOS_VERSIONS.keys()), variable=self.macos_var)
            self.macos_menu.pack(fill="x", padx=20, pady=5)
            
            ctk.CTkLabel(left, text="Che Mac fingiamo di essere?").pack(anchor="w", padx=20, pady=(15,0))
            self.smbios_var = ctk.StringVar(value="iMac18,1")
            self.smbios_menu = ctk.CTkOptionMenu(left, values=["iMac17,1", "iMac18,1", "iMac19,1", "Macmini8,1", "iMacPro1,1", "MacPro7,1"], variable=self.smbios_var)
            self.smbios_menu.pack(fill="x", padx=20, pady=5)
            
            ctk.CTkLabel(left, text="Audio - se non va prova altri").pack(anchor="w", padx=20, pady=(15,0))
            self.audio_var = ctk.StringVar(value="11")
            self.audio_menu = ctk.CTkOptionMenu(left, values=["11", "13", "15", "21", "27", "28"], variable=self.audio_var)
            self.audio_menu.pack(fill="x", padx=20, pady=5)
            
            ctk.CTkLabel(left, text="Extra (se hai WiFi Intel)").pack(anchor="w", padx=20, pady=(15,0))
            self.wifi_var = ctk.BooleanVar(value=False)
            self.bt_var = ctk.BooleanVar(value=False)
            self.optional_kexts_var = ctk.BooleanVar(value=False)
            self.optional_ssdts_var = ctk.BooleanVar(value=False)
            self.dev_mode_var = ctk.BooleanVar(value=False)
            self.minimal_var = ctk.BooleanVar(value=True)
            
            self.wifi_check = ctk.CTkCheckBox(left, text="Ho WiFi Intel (AirportItlwm)", variable=self.wifi_var)
            self.wifi_check.pack(anchor="w", padx=20, pady=5)
            
            self.bt_check = ctk.CTkCheckBox(left, text="Ho Bluetooth Intel", variable=self.bt_var)
            self.bt_check.pack(anchor="w", padx=20, pady=5)

            self.optional_kexts_check = ctk.CTkCheckBox(left, text="Kext opzionali (NVMeFix, RestrictEvents)", variable=self.optional_kexts_var)
            self.optional_kexts_check.pack(anchor="w", padx=20, pady=5)

            self.optional_ssdts_check = ctk.CTkCheckBox(left, text="SSDT-PMC opzionale (se NVRAM rotta)", variable=self.optional_ssdts_var)
            self.optional_ssdts_check.pack(anchor="w", padx=20, pady=5)

            ctk.CTkLabel(left, text="Modalità EFI").pack(anchor="w", padx=20, pady=(15,0))
            self.dev_check = ctk.CTkCheckBox(left, text="DEV mode (-v debug, per test)", variable=self.dev_mode_var)
            self.dev_check.pack(anchor="w", padx=20, pady=5)

            self.minimal_check = ctk.CTkCheckBox(left, text="Minimal Q556/2 specifica (consigliata)", variable=self.minimal_var)
            self.minimal_check.pack(anchor="w", padx=20, pady=5)
            
            ctk.CTkLabel(left, text="Dove la metto?").pack(anchor="w", padx=20, pady=(15,0))
            output_frame = ctk.CTkFrame(left, fg_color="transparent")
            output_frame.pack(fill="x", padx=20, pady=5)
            
            self.output_entry = ctk.CTkEntry(output_frame, placeholder_text=str(self.output_dir))
            self.output_entry.pack(side="left", fill="x", expand=True, padx=(0,5))
            self.output_entry.insert(0, str(self.output_dir))
            
            browse_btn = ctk.CTkButton(output_frame, text="Scegli", width=80, command=self.browse_output)
            browse_btn.pack(side="right")
            
            self.build_btn = ctk.CTkButton(left, text="🚀 Crea EFI vera, non finta", font=ctk.CTkFont(size=16, weight="bold"), height=50, command=self.start_build)
            self.build_btn.pack(fill="x", padx=20, pady=20)
            
            ctk.CTkLabel(right, text="Cosa sta facendo", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20,10))
            
            self.progress = ctk.CTkProgressBar(right)
            self.progress.pack(fill="x", padx=20, pady=10)
            self.progress.set(0)
            
            self.status_label = ctk.CTkLabel(right, text="Pronto a creare EFI vera", font=ctk.CTkFont(size=12))
            self.status_label.pack(anchor="w", padx=20, pady=5)
            
            self.log_box = ctk.CTkTextbox(right, font=ctk.CTkFont(family="Courier", size=11))
            self.log_box.pack(fill="both", expand=True, padx=20, pady=10)
            self.log_box.insert("1.0", """Ciao! Sono Andrea 👋

Questo è OpenHackintosh, nato perché mi ero rotto di tool che creano EFI finte.

Storia veloce:
- Avevo Q556/2, volevo Hackintosh
- Provo un tool vecchio, fa EFI bellissima ma file vuoti (0 byte)
- 3 giorni a bestemmiare davanti a logo Fujitsu che si riavvia
- Decido di riscriverlo da zero, con file veri

Ora fa così:
✓ Scarica OpenCore vero da Acidanthera (10MB, non 0 byte)
✓ Scarica kext veri con binari dentro (Lilu 245KB, non vuoto)
✓ Scarica SSDT veri da Dortania
✓ Genera config.plist giusto per Skylake (non a caso)
✓ Crea SMBIOS credibile
✓ Fa ZIP pronto per USB

Scegli il tuo PC a sinistra e clicca il bottone grosso.
Se non boota, 99% è BIOS - leggi docs/BIOS_GUIDE.md, c'è scritto DVMT 64MB ovunque perché è fondamentale.

Buon Hackintosh! 🍎
""")
            
            self.smbios_preview = ctk.CTkFrame(right)
            self.smbios_preview.pack(fill="x", padx=20, pady=(0,20))
            
            ctk.CTkLabel(self.smbios_preview, text="SMBIOS (generato a caso, poi rigenera con GenSMBIOS):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(10,0))
            self.smbios_text = ctk.CTkLabel(self.smbios_preview, text="Verrà generato quando crei EFI", justify="left", font=ctk.CTkFont(family="Courier", size=10), text_color="gray")
            self.smbios_text.pack(anchor="w", padx=10, pady=10)
        
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
            self.build_btn.configure(state="disabled", text="⏳ Sto scaricando file veri...")
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
            self.build_btn.configure(state="normal", text="🚀 Crea EFI vera, non finta")
            self.status_label.configure(text="Fatto! EFI vera pronta!")
            
            smbios = result["smbios"]
            preview = f"Model: {smbios['ProductName']}\nSerial: {smbios['SerialNumber']}\nMLB: {smbios['MLB']}\nUUID: {smbios['SystemUUID'][:8]}...\nROM: {smbios['ROM']}"
            self.smbios_text.configure(text=preview)
            
            self.log(f"\n🎉 FATTO! EFI vera in: {result['efi_path']}")
            self.log(f"📦 ZIP: {result['zip_path']}")
            self.log(f"Ora copia su USB e prova a bootare. Se non boota, leggi BIOS_GUIDE.md!")
            
            messagebox.showinfo("Fatto! 🎉", f"EFI vera creata!\n\nDove: {result['efi_path']}\nZIP: {result['zip_path']}\n\nSeriale: {smbios['SerialNumber']}\nModello: {smbios['ProductName']}\n\nOra copia su USB e boota. Se non va, è BIOS (DVMT 64MB!).")
        
        def on_build_failed(self, result):
            self.progress.set(0)
            self.build_btn.configure(state="normal", text="🚀 Crea EFI vera, non finta")
            self.status_label.configure(text="Fallito, riproviamo")
            messagebox.showerror("Ops", f"Non ce l'ho fatta: {result.get('error', 'boh')}\nControlla internet, GitHub a volte ha limiti.")
        
        def on_build_error(self, msg, traceback_str):
            self.progress.set(0)
            self.build_btn.configure(state="normal", text="🚀 Crea EFI vera, non finta")
            self.status_label.configure(text="Errore")
            self.log(f"\n💥 Errore: {msg}\n{traceback_str}")
            messagebox.showerror("Errore", f"Errore: {msg}\n\nSe non capisci, apri issue su GitHub con questo log.")
        
        def run(self):
            self.root.mainloop()

else:
    class EFICreatorGUI:
        def __init__(self):
            self.root = tk.Tk()
            self.root.title("OpenHackintosh - EFI vere")
            self.root.geometry("800x600")
            self.output_dir = Path.home() / "Desktop" / "EFI_Q5562"
            self.setup_ui()
        
        def setup_ui(self):
            frame = ttk.Frame(self.root, padding=20)
            frame.pack(fill="both", expand=True)
            ttk.Label(frame, text="OpenHackintosh - Installa customtkinter per GUI bella", font=("Arial", 14, "bold")).pack(anchor="w", pady=10)
            ttk.Label(frame, text="pip install customtkinter").pack(anchor="w")
            self.profile_var = tk.StringVar(value="Q556/2")
            ttk.OptionMenu(frame, self.profile_var, "Q556/2", *PROFILES.keys()).pack(fill="x", pady=5)
            ttk.Button(frame, text="Genera EFI (ma installa customtkinter prima)", command=self.start_build).pack(fill="x", pady=20)
            self.log_text = tk.Text(frame, height=20)
            self.log_text.pack(fill="both", expand=True, pady=10)
            self.log_text.insert("1.0", "GUI base - installa customtkinter per quella bella\n")
        
        def start_build(self):
            import threading
            def build():
                self.log_text.insert("end", "Avvio...\n")
                try:
                    from efi_builder.builder import EFIBuilder
                    builder = EFIBuilder(self.output_dir)
                    result = builder.build(profile_name=self.profile_var.get())
                    self.log_text.insert("end", f"Fatto: {result}\n")
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
