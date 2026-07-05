"""
L.N.D Tribe Logs — main.py
Black / electric-purple theme. Logo as ghost background.
"""
import tkinter as tk
from tkinter import ttk
import json, os, sys
from PIL import Image, ImageTk

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOGO_PATH   = os.path.join(BASE_DIR, "logo.png")
LOGO_BG     = os.path.join(BASE_DIR, "logo_bg.png")
ICON_PATH   = os.path.join(BASE_DIR, "icon.ico")

# ── Colour palette — Black & Electric Purple ──────────────────────────────────
BG_DARK       = "#080808"   # near-black app background
BG_PANEL      = "#0f0f0f"   # card background
BG_SECTION    = "#141414"   # section header strip
BORDER        = "#2a0a3a"   # dark purple border
ACCENT        = "#1a0828"   # deep purple input bg
ACCENT_BRIGHT = "#9d00ff"   # electric purple — primary accent
ACCENT_GLOW   = "#bf40ff"   # lighter purple — hover / active
ACCENT_DIM    = "#5a0099"   # muted purple — inactive elements
TEXT_MAIN     = "#f0e6ff"   # soft lavender-white primary text
TEXT_DIM      = "#6b5580"   # muted purple-grey secondary text
TEXT_WARN     = "#ffaa00"   # amber warning
TEXT_DANGER   = "#ff3355"   # red danger
TEXT_OK       = "#39ff7a"   # neon green ok
STATUS_DOT    = "#9d00ff"   # status bar dot

# ── Config ────────────────────────────────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            content = open(CONFIG_PATH).read().strip()
            return json.loads(content) if content else {}
        except Exception:
            return {}
    return {}

def save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

# ── Main App ──────────────────────────────────────────────────────────────────
class LNDApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("L.N.D Tribe Logs  v1.0.0")
        self.geometry("740x700")
        self.minsize(720, 620)
        self.configure(bg=BG_DARK)
        self.resizable(True, True)

        self.config_data = load_config()
        self.status_var  = tk.StringVar(value="● Ready")
        self._bg_photo   = None   # keep reference alive

        # App icon
        if os.path.exists(ICON_PATH):
            try:
                self.iconbitmap(ICON_PATH)
            except Exception:
                pass

        self._build_styles()
        self._build_background()
        self._build_header()
        self._build_tabs()
        self._build_statusbar()

    # ── TTK styles ────────────────────────────────────────────────────────────
    def _build_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TNotebook",
                    background=BG_DARK, borderwidth=0, tabmargins=[0,0,0,0])
        s.configure("TNotebook.Tab",
                    background=BG_SECTION, foreground=TEXT_DIM,
                    font=("Segoe UI", 9, "bold"),
                    padding=[20, 9], borderwidth=0)
        s.map("TNotebook.Tab",
              background=[("selected", BG_DARK)],
              foreground=[("selected", ACCENT_BRIGHT)])
        s.configure("Vertical.TScrollbar",
                    background=ACCENT_DIM, troughcolor=BG_PANEL,
                    borderwidth=0, arrowcolor=TEXT_MAIN)

    # ── Ghost logo background ─────────────────────────────────────────────────
    def _build_background(self):
        if not os.path.exists(LOGO_BG):
            return
        try:
            # Load source image ONCE and cache it — never re-open from disk
            self._bg_source    = Image.open(LOGO_BG).convert("RGBA")
            self._bg_canvas    = tk.Canvas(self, bg=BG_DARK, highlightthickness=0)
            self._bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
            self._bg_photo     = None
            self._last_bg_size = (0, 0)
            self._resize_job   = None
            self.after(150, self._render_bg)
            self.bind("<Configure>", self._on_resize)
        except Exception:
            pass

    def _render_bg(self):
        """Only redraws if window size actually changed."""
        try:
            w = self.winfo_width()  or 740
            h = self.winfo_height() or 700
            if (w, h) == self._last_bg_size:
                return
            self._last_bg_size = (w, h)
            src   = self._bg_source
            ratio = min(w / src.width, h / src.height)
            nw, nh = int(src.width * ratio), int(src.height * ratio)
            # BILINEAR is much faster than LANCZOS; ghost is dim so quality doesn't matter
            resized = src.resize((nw, nh), Image.BILINEAR)
            bg = Image.new("RGB", (w, h), (8, 8, 8))
            bg.paste(resized, ((w - nw)//2, (h - nh)//2), resized)
            self._bg_photo = ImageTk.PhotoImage(bg)
            self._bg_canvas.delete("all")
            self._bg_canvas.create_image(0, 0, anchor="nw", image=self._bg_photo)
            self._bg_canvas.lower("all")
        except Exception:
            pass

    def _on_resize(self, _e=None):
        # Debounce: only re-render 300ms after the last resize event fires
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(300, self._render_bg)

    # ── Header ────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=BG_PANEL, height=72)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        # Purple left accent stripe
        tk.Frame(hdr, bg=ACCENT_BRIGHT, width=4).pack(side="left", fill="y")

        # Small logo thumbnail
        if os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH).convert("RGBA")
                img.thumbnail((52, 52), Image.LANCZOS)
                self._hdr_logo = ImageTk.PhotoImage(img)
                tk.Label(hdr, image=self._hdr_logo,
                         bg=BG_PANEL).pack(side="left", padx=(10, 6), pady=10)
            except Exception:
                pass

        # Title block
        title_block = tk.Frame(hdr, bg=BG_PANEL)
        title_block.pack(side="left", pady=12)

        tk.Label(title_block, text="L.N.D TRIBE LOGS",
                 bg=BG_PANEL, fg=TEXT_MAIN,
                 font=("Segoe UI", 17, "bold")).pack(anchor="w")

        sub = tk.Frame(title_block, bg=BG_PANEL)
        sub.pack(anchor="w")
        tk.Label(sub, text="ARK TRIBE LOG MONITOR",
                 bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(side="left")
        tk.Label(sub, text="  ·  ",
                 bg=BG_PANEL, fg=ACCENT_DIM,
                 font=("Segoe UI", 8)).pack(side="left")
        tk.Label(sub, text="L.N.D",
                 bg=BG_PANEL, fg=ACCENT_BRIGHT,
                 font=("Segoe UI", 8, "bold")).pack(side="left")

        # Version badge
        tk.Label(hdr, text=" v1.0.0 ",
                 bg=ACCENT_DIM, fg=ACCENT_BRIGHT,
                 font=("Consolas", 7, "bold")).place(x=78, y=54)

        # Purple accent line under header
        tk.Frame(self, bg=ACCENT_BRIGHT, height=2).pack(fill="x", side="top")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    def _build_tabs(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        from modules.license_tab      import LicenseTab
        from modules.generators_tab   import GeneratorsTab
        from modules.settings_tab     import SettingsTab
        from modules.monitor_tab      import MonitorTab
        from modules.upload_timer_tab import UploadTimerTab
        from modules.server_tracker_tab import ServerTrackerTab

        self.tab_license    = LicenseTab(self.notebook, self)
        self.tab_generators = GeneratorsTab(self.notebook, self)
        self.tab_settings   = SettingsTab(self.notebook, self)
        self.tab_monitor    = MonitorTab(self.notebook, self)
        self.tab_upload     = UploadTimerTab(self.notebook, self)
        self.tab_server     = ServerTrackerTab(self.notebook, self)

        self.notebook.add(self.tab_license,    text="  LICENSE  ")
        self.notebook.add(self.tab_generators, text="  GENERATORS  ")
        self.notebook.add(self.tab_settings,   text="  SETTINGS  ")
        self.notebook.add(self.tab_monitor,    text="  MONITOR  ")
        self.notebook.add(self.tab_upload,     text="  UPLOAD TIMER  ")
        self.notebook.add(self.tab_server,     text="  SERVER TRACKER  ")

    # ── Status bar ────────────────────────────────────────────────────────────
    def _build_statusbar(self):
        bar = tk.Frame(self, bg="#0a0a0a", height=26)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=ACCENT_BRIGHT, width=2).pack(side="left", fill="y")
        self._status_lbl = tk.Label(bar, textvariable=self.status_var,
                                     bg="#0a0a0a", fg=STATUS_DOT,
                                     font=("Segoe UI", 8))
        self._status_lbl.pack(side="left", padx=10)
        tk.Label(bar, text="L.N.D © 2026",
                 bg="#0a0a0a", fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(side="right", padx=10)

    def set_status(self, msg: str, colour: str = STATUS_DOT):
        self.status_var.set(f"● {msg}")
        self._status_lbl.config(fg=colour)


if __name__ == "__main__":
    app = LNDApp()
    app.mainloop()