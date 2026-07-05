"""
L.N.D Tribe Logs — Protected Loader (Original Beautiful UI)
Only downloads the EXE from Releases
"""

import tkinter as tk
from tkinter import ttk
import threading
import subprocess
import sys
import os
import urllib.request
import shutil

# Single instance guard
import ctypes
_MUTEX_NAME = "LNDTribeLogsLoader_SingleInstance"
_mutex = ctypes.windll.kernel32.CreateMutexW(None, True, _MUTEX_NAME)
if ctypes.windll.kernel32.GetLastError() == 183:
    sys.exit(0)

# Config
GITHUB_USER   = "Vmkq"
GITHUB_REPO   = "L.N.D"
INSTALL_DIR   = os.path.join(os.path.expanduser("~"), "LNDTribeLogs")
EXE_NAME      = "LND.Tribe.Logs.exe"
RELEASE_TAG   = "v1.0.0"          # ← Update this when you release new version

PYTHON_URL    = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
TESSERACT_URL = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"

PIP_PACKAGES = ["pillow", "pytesseract", "requests", "numpy", "pystray"]

# Colours (your original)
BG = "#080808"
BG_PANEL = "#0f0f0f"
BG_SECTION = "#141414"
BORDER = "#2a0a3a"
ACCENT = "#1a0828"
PURPLE = "#9d00ff"
PURPLE_LT = "#bf40ff"
PURPLE_DIM = "#5a0099"
TEXT = "#f0e6ff"
TEXT_DIM = "#6b5580"
OK = "#39ff7a"
WARN = "#ffaa00"
DANGER = "#ff3355"

class LNDLoader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("L.N.D Tribe Logs — Installer")
        self.geometry("620x560")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=BG_PANEL, height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Frame(hdr, bg=PURPLE, width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="L.N.D", bg=BG_PANEL, fg=PURPLE, font=("Segoe UI", 20, "bold")).pack(side="left", padx=(12,0), pady=12)
        tk.Label(hdr, text=" TRIBE LOGS", bg=BG_PANEL, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(side="left", pady=12)
        tk.Label(hdr, text="  Installer", bg=BG_PANEL, fg=TEXT_DIM, font=("Segoe UI", 10)).pack(side="left", pady=18)
        tk.Frame(self, bg=PURPLE, height=2).pack(fill="x")

        # Mode
        mode_frame = tk.Frame(self, bg=BG_PANEL)
        mode_frame.pack(fill="x")
        self.v_mode = tk.IntVar(value=1)
        for val, label, col in [(1,"[1] Install",OK),(2,"[2] Update",WARN),(3,"[3] Uninstall",DANGER)]:
            tk.Radiobutton(mode_frame, text=label, variable=self.v_mode, value=val,
                           bg=BG_PANEL, fg=col, selectcolor=ACCENT, font=("Consolas", 9, "bold")).pack(side="left", padx=20)

        # Steps (kept for nice look)
        self._steps_frame = tk.Frame(self, bg=BG)
        self._steps_frame.pack(fill="x", padx=20, pady=12)

        steps = ["python", "tesseract", "packages", "files", "shortcuts"]
        labels = ["Python 3.11", "Tesseract OCR", "Core Packages", "Program (EXE)", "Finalizing"]
        self._step_vars = {}
        for key, label in zip(steps, labels):
            row = tk.Frame(self._steps_frame, bg=BG)
            row.pack(fill="x", pady=3)
            dot = tk.Label(row, text="○", bg=BG, fg=TEXT_DIM, font=("Consolas", 10))
            dot.pack(side="left", padx=(0,10))
            tk.Label(row, text=label, bg=BG, fg=TEXT_DIM, font=("Consolas", 9)).pack(side="left")
            status = tk.Label(row, text="", bg=BG, fg=TEXT_DIM, font=("Consolas", 9))
            status.pack(side="right")
            self._step_vars[key] = (dot, status)

        # Log
        self.log_text = tk.Text(self, bg=BG_SECTION, fg=TEXT_DIM, font=("Consolas", 8), height=6)
        self.log_text.pack(fill="x", padx=20, pady=8)

        # Buttons
        btn_row = tk.Frame(self, bg=BG_PANEL, height=52)
        btn_row.pack(fill="x", side="bottom")
        tk.Button(btn_row, text="▶  START", command=self._start,
                  bg=PURPLE, fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(side="left", padx=20, pady=8)
        tk.Button(btn_row, text="CLOSE", command=self.destroy,
                  bg=BG_SECTION, fg=TEXT_DIM).pack(side="right", padx=20, pady=8)

    def _log(self, msg):
        def write():
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
        self.after(0, write)

    def _step_done(self, key, text="Done ✓"):
        dot, status = self._step_vars[key]
        self.after(0, lambda: (dot.config(text="●", fg=OK), status.config(text=text, fg=OK)))

    def _step_error(self, key, text="Failed"):
        dot, status = self._step_vars[key]
        self.after(0, lambda: (dot.config(text="✕", fg=DANGER), status.config(text=text, fg=DANGER)))

    def _start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        mode = self.v_mode.get()
        if mode == 3:
            self._uninstall()
            return

        self._step_done("python")
        self._step_done("tesseract")
        self._step_done("packages")

        # Only download EXE
        self._log("Downloading latest program...")
        success = self._download_exe_only()
        if success:
            self._step_done("files", "EXE Downloaded ✓")
        else:
            self._step_error("files", "Download Failed")

        self._create_launcher()
        self._step_done("shortcuts")
        self._log("\n✅ Installation Complete! Use desktop shortcut.")

    def _download_exe_only(self):
        os.makedirs(INSTALL_DIR, exist_ok=True)
        url = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/download/{RELEASE_TAG}/{EXE_NAME}"
        dest = os.path.join(INSTALL_DIR, EXE_NAME)

        try:
            urllib.request.urlretrieve(url, dest)
            self._log("✅ EXE downloaded successfully")
            return True
        except Exception as e:
            self._log(f"❌ Download failed: {e}")
            return False

    def _create_launcher(self):
        exe_path = os.path.join(INSTALL_DIR, EXE_NAME)
        bat = os.path.join(INSTALL_DIR, "Launch_LND.bat")
        with open(bat, "w") as f:
            f.write(f'@echo off\ncd /d "{INSTALL_DIR}"\nstart "" "{exe_path}"\n')

        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            with open(os.path.join(desktop, "L.N.D Tribe Logs.bat"), "w") as f:
                f.write(f'@echo off\ncd /d "{INSTALL_DIR}"\nstart "" "{exe_path}"\n')
        except:
            pass

    def _uninstall(self):
        if os.path.exists(INSTALL_DIR):
            shutil.rmtree(INSTALL_DIR)
            self._log("Uninstalled.")

if __name__ == "__main__":
    app = LNDLoader()
    app.mainloop()
