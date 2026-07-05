"""License Tab — black/purple theme"""
import tkinter as tk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from main import (BG_DARK, BG_PANEL, BG_SECTION, BORDER, ACCENT, ACCENT_BRIGHT,
                  ACCENT_GLOW, ACCENT_DIM, TEXT_MAIN, TEXT_DIM, TEXT_OK,
                  TEXT_DANGER, save_config, LOGO_PATH)
from PIL import Image, ImageTk

class LicenseTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_DARK)
        self.app = app
        self._logo_img = None
        self._build()

    def _build(self):
        # Logo centred at top
        if os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH).convert("RGBA")
                img.thumbnail((140, 140), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)
                tk.Label(self, image=self._logo_img,
                         bg=BG_DARK).pack(pady=(36, 0))
            except Exception:
                pass

        tk.Label(self, text="L.N.D TRIBE LOGS",
                 bg=BG_DARK, fg=TEXT_MAIN,
                 font=("Segoe UI", 20, "bold")).pack(pady=(10, 0))
        tk.Label(self, text="ARK: Survival Ascended — Tribe Monitor",
                 bg=BG_DARK, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).pack(pady=(2, 24))

        # Card
        outer = tk.Frame(self, bg=BORDER)
        outer.pack(padx=60, fill="x")
        hdr = tk.Frame(outer, bg=BG_SECTION)
        hdr.pack(fill="x")
        tk.Frame(hdr, bg=ACCENT_BRIGHT, width=3).pack(side="left", fill="y")
        tk.Label(hdr, text="LICENSE KEY", bg=BG_SECTION, fg=ACCENT_BRIGHT,
                 font=("Segoe UI", 9, "bold"), padx=10, pady=7).pack(side="left")
        inner = tk.Frame(outer, bg=BG_PANEL)
        inner.pack(fill="x")

        self.v_key = tk.StringVar(value=self.app.config_data.get("license_key",""))
        tk.Entry(inner, textvariable=self.v_key,
                 bg=ACCENT, fg=TEXT_MAIN, insertbackground=ACCENT_BRIGHT,
                 relief="flat", font=("Consolas", 9),
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT_BRIGHT).pack(fill="x", padx=14, pady=(10,4))

        self.status_lbl = tk.Label(inner, text="", bg=BG_PANEL,
                                    font=("Segoe UI", 8))
        self.status_lbl.pack(anchor="w", padx=14)

        tk.Button(inner, text="ACTIVATE", command=self._activate,
                  bg=ACCENT_BRIGHT, fg="#ffffff", activebackground=ACCENT_GLOW,
                  activeforeground="#ffffff", relief="flat",
                  font=("Segoe UI", 9, "bold"), cursor="hand2",
                  pady=8).pack(fill="x", padx=14, pady=(6,14))

        if self.app.config_data.get("licensed"):
            self.status_lbl.config(text="✅  License active", fg=TEXT_OK)

        tk.Label(self, text="Support: discord.gg/lnd",
                 bg=BG_DARK, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(pady=(20, 0))

    def _activate(self):
        key = self.v_key.get().strip()
        if not key:
            self.status_lbl.config(text="Enter a license key.", fg=TEXT_DANGER)
            return
        # Stub — replace with real server check later
        self.app.config_data["license_key"] = key
        self.app.config_data["licensed"]    = True
        save_config(self.app.config_data)
        self.status_lbl.config(text="✅  License active!", fg=TEXT_OK)
        self.app.set_status("License activated", TEXT_OK)