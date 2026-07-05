"""
LND_Loader.py
L.N.D Tribe Logs — Installer & Auto-Updater
Checks/installs Python, Tesseract, pip packages, then launches the app.
Pulls latest files from GitHub automatically.
"""
import tkinter as tk
from tkinter import ttk
import threading
import subprocess
import sys
import os
import json
import urllib.request
import urllib.error
import zipfile
import shutil
import time
import winreg

# ── Single instance guard (Windows mutex) ─────────────────────────────────────
import ctypes
_MUTEX_NAME = "LNDTribeLogsLoader_SingleInstance"
_mutex = ctypes.windll.kernel32.CreateMutexW(None, True, _MUTEX_NAME)
if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
    # Another instance is already running — silently exit
    sys.exit(0)

# ── Config ────────────────────────────────────────────────────────────────────
GITHUB_USER   = "Vmkq"
GITHUB_REPO   = "L.N.D"
GITHUB_BRANCH = "main"
APP_FOLDER    = "LNDTribeLogs"
VERSION_FILE  = "version.json"
INSTALL_DIR   = os.path.join(os.path.expanduser("~"), "LNDTribeLogs")
RAW_BASE      = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{APP_FOLDER}"
API_BASE      = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{APP_FOLDER}"

PYTHON_VERSION = "3.11.9"
PYTHON_URL     = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
TESSERACT_URL  = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"

PIP_PACKAGES = [
    "pillow",
    "pytesseract",
    "requests",
    "numpy",
    "pystray",
]

# ── Colour palette ────────────────────────────────────────────────────────────
BG          = "#080808"
BG_PANEL    = "#0f0f0f"
BG_SECTION  = "#141414"
BORDER      = "#2a0a3a"
ACCENT      = "#1a0828"
PURPLE      = "#9d00ff"
PURPLE_LT   = "#bf40ff"
PURPLE_DIM  = "#5a0099"
TEXT        = "#f0e6ff"
TEXT_DIM    = "#6b5580"
OK          = "#39ff7a"
WARN        = "#ffaa00"
DANGER      = "#ff3355"


class LNDLoader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("L.N.D Tribe Logs — Installer")
        self.geometry("620x560")
        self.resizable(False, False)
        self.configure(bg=BG)

        # set icon if available
        ico = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(ico):
            try: self.iconbitmap(ico)
            except: pass

        self._steps  = []
        self._thread = None
        self._build()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=BG_PANEL, height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Frame(hdr, bg=PURPLE, width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="L.N.D", bg=BG_PANEL, fg=PURPLE,
                 font=("Segoe UI", 20, "bold")).pack(side="left", padx=(12,0), pady=12)
        tk.Label(hdr, text=" TRIBE LOGS", bg=BG_PANEL, fg=TEXT,
                 font=("Segoe UI", 20, "bold")).pack(side="left", pady=12)
        tk.Label(hdr, text="  Installer  v1.0", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 10)).pack(side="left", pady=18)
        tk.Frame(self, bg=PURPLE, height=2).pack(fill="x")

        # Mode row
        mode_frame = tk.Frame(self, bg=BG_PANEL)
        mode_frame.pack(fill="x", padx=0)
        self.v_mode = tk.IntVar(value=1)
        for val, label, col in [(1,"[1] Install",OK),(2,"[2] Update",WARN),(3,"[3] Uninstall",DANGER)]:
            rb = tk.Radiobutton(mode_frame, text=label, variable=self.v_mode,
                                value=val, bg=BG_PANEL, fg=col,
                                selectcolor=ACCENT, activebackground=BG_PANEL,
                                activeforeground=col,
                                font=("Consolas", 9, "bold"), padx=16, pady=10)
            rb.pack(side="left")
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # Steps list
        steps_outer = tk.Frame(self, bg=BG)
        steps_outer.pack(fill="both", expand=True, padx=0, pady=0)

        self._steps_frame = tk.Frame(steps_outer, bg=BG)
        self._steps_frame.pack(fill="x", padx=20, pady=12)

        steps_info = [
            ("python",    "Python 3.11"),
            ("tesseract", "Tesseract OCR"),
            ("pip",       "pip upgrade"),
            ("packages",  "Core packages (pillow, numpy, requests)"),
            ("pytess_pkg","pytesseract"),
            ("pystray",   "pystray (system tray)"),
            ("files",     "L.N.D Tribe Logs files"),
            ("shortcuts", "Finalizing"),
        ]
        self._step_vars = {}
        for key, label in steps_info:
            row = tk.Frame(self._steps_frame, bg=BG)
            row.pack(fill="x", pady=3)
            dot_lbl = tk.Label(row, text="○", bg=BG, fg=TEXT_DIM,
                               font=("Consolas", 10))
            dot_lbl.pack(side="left", padx=(0,10))
            tk.Label(row, text=label, bg=BG, fg=TEXT_DIM,
                     font=("Consolas", 9)).pack(side="left")
            status_lbl = tk.Label(row, text="", bg=BG, fg=TEXT_DIM,
                                  font=("Consolas", 9))
            status_lbl.pack(side="right")
            self._step_vars[key] = (dot_lbl, status_lbl)

        # Progress bar
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        prog_frame = tk.Frame(self, bg=BG, height=8)
        prog_frame.pack(fill="x")
        prog_frame.pack_propagate(False)
        self._prog_canvas = tk.Canvas(prog_frame, bg=BG_SECTION,
                                       highlightthickness=0, height=8)
        self._prog_canvas.pack(fill="x")
        self._prog_bar = self._prog_canvas.create_rectangle(
            0, 0, 0, 8, fill=PURPLE, outline="")
        self._prog_canvas.bind("<Configure>", self._redraw_prog)
        self._prog_val = 0.0

        # Log output
        log_frame = tk.Frame(self, bg=BG_SECTION)
        log_frame.pack(fill="x", padx=0)
        self._log_text = tk.Text(log_frame, bg=BG_SECTION, fg=TEXT_DIM,
                                  font=("Consolas", 8), height=5,
                                  relief="flat", state="disabled",
                                  highlightthickness=0)
        self._log_text.pack(fill="x", padx=8, pady=6)

        # Bottom buttons
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        btn_row = tk.Frame(self, bg=BG_PANEL, height=52)
        btn_row.pack(fill="x", side="bottom")
        btn_row.pack_propagate(False)

        self.btn_start = tk.Button(btn_row, text="▶  START",
                                    command=self._start,
                                    bg=PURPLE, fg="#ffffff",
                                    activebackground=PURPLE_LT,
                                    activeforeground="#ffffff",
                                    relief="flat",
                                    font=("Segoe UI", 10, "bold"),
                                    cursor="hand2", padx=30, pady=10)
        self.btn_start.pack(side="left", padx=20, pady=8)

        self.btn_close = tk.Button(btn_row, text="CLOSE",
                                    command=self.destroy,
                                    bg=BG_SECTION, fg=TEXT_DIM,
                                    activebackground=BORDER,
                                    activeforeground=TEXT,
                                    relief="flat",
                                    font=("Segoe UI", 10, "bold"),
                                    cursor="hand2", padx=20, pady=10)
        self.btn_close.pack(side="right", padx=20, pady=8)

        self.status_lbl = tk.Label(btn_row, text="Ready.",
                                    bg=BG_PANEL, fg=TEXT_DIM,
                                    font=("Segoe UI", 8))
        self.status_lbl.pack(side="left", padx=10)

    # ── Progress helpers ──────────────────────────────────────────────────────
    def _redraw_prog(self, _e=None):
        w = self._prog_canvas.winfo_width()
        fill = int(w * self._prog_val)
        self._prog_canvas.coords(self._prog_bar, 0, 0, fill, 8)

    def _set_prog(self, val: float):
        self._prog_val = val
        self.after(0, self._redraw_prog)

    def _step_pending(self, key):
        self.after(0, self._ui_step_pending, key)

    def _step_done(self, key, text="Done ✓"):
        self.after(0, self._ui_step_done, key, text)

    def _step_skip(self, key, text="Skipped"):
        self.after(0, self._ui_step_skip, key, text)

    def _step_error(self, key, text="Error"):
        self.after(0, self._ui_step_error, key, text)

    def _ui_step_pending(self, key):
        dot, status = self._step_vars[key]
        dot.config(text="●", fg=PURPLE)
        status.config(text="Installing...", fg=WARN)

    def _ui_step_done(self, key, text):
        dot, status = self._step_vars[key]
        dot.config(text="●", fg=OK)
        status.config(text=text, fg=OK)

    def _ui_step_skip(self, key, text):
        dot, status = self._step_vars[key]
        dot.config(text="—", fg=TEXT_DIM)
        status.config(text=text, fg=TEXT_DIM)

    def _ui_step_error(self, key, text):
        dot, status = self._step_vars[key]
        dot.config(text="✕", fg=DANGER)
        status.config(text=text, fg=DANGER)

    def _log(self, msg: str):
        def _w():
            self._log_text.config(state="normal")
            self._log_text.insert("end", msg + "\n")
            self._log_text.see("end")
            self._log_text.config(state="disabled")
        self.after(0, _w)

    def _set_status(self, msg: str, col=None):
        self.after(0, lambda: self.status_lbl.config(
            text=msg, fg=col or TEXT_DIM))

    # ── Install logic ─────────────────────────────────────────────────────────
    def _start(self):
        self.btn_start.config(state="disabled")
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        mode = self.v_mode.get()
        if mode == 3:
            self._uninstall()
            return
        self._install_or_update(update_only=(mode == 2))

    def _install_or_update(self, update_only=False):
        total_steps = 8
        step = 0

        # ── 1. Python ─────────────────────────────────────────────────────
        self._step_pending("python")
        if self._python_installed():
            self._step_skip("python", "Already installed ✓")
            self._log("Python already installed.")
        elif update_only:
            self._step_skip("python", "Skipped (update mode)")
        else:
            self._log(f"Downloading Python {PYTHON_VERSION}...")
            ok = self._install_python()
            if ok: self._step_done("python")
            else:  self._step_error("python", "Failed — install manually")
        step += 1; self._set_prog(step/total_steps)

        # ── 2. Tesseract ──────────────────────────────────────────────────
        self._step_pending("tesseract")
        if self._tesseract_installed():
            self._step_skip("tesseract", "Already installed ✓")
            self._log("Tesseract already installed.")
        elif update_only:
            self._step_skip("tesseract", "Skipped (update mode)")
        else:
            self._log("Downloading Tesseract OCR...")
            ok = self._install_tesseract()
            if ok: self._step_done("tesseract")
            else:  self._step_error("tesseract", "Failed — install manually")
        step += 1; self._set_prog(step/total_steps)

        # ── 3. pip upgrade ────────────────────────────────────────────────
        self._step_pending("pip")
        self._log("Upgrading pip...")
        self._run_pip(["install", "--upgrade", "pip"])
        self._step_done("pip")
        step += 1; self._set_prog(step/total_steps)

        # ── 4. Core packages ──────────────────────────────────────────────
        self._step_pending("packages")
        self._log("Installing pillow, numpy, requests...")
        self._run_pip(["install", "pillow", "numpy", "requests",
                       "--break-system-packages"])
        self._step_done("packages")
        step += 1; self._set_prog(step/total_steps)

        # ── 5. pytesseract ────────────────────────────────────────────────
        self._step_pending("pytess_pkg")
        self._log("Installing pytesseract...")
        self._run_pip(["install", "pytesseract", "--break-system-packages"])
        self._step_done("pytess_pkg")
        step += 1; self._set_prog(step/total_steps)

        # ── 6. pystray ────────────────────────────────────────────────────
        self._step_pending("pystray")
        self._log("Installing pystray...")
        self._run_pip(["install", "pystray", "--break-system-packages"])
        self._step_done("pystray")
        step += 1; self._set_prog(step/total_steps)

        # ── 7. Download app files from GitHub ─────────────────────────────
        self._step_pending("files")
        self._log("Downloading latest L.N.D Tribe Logs from GitHub...")
        ok = self._download_files()
        if ok: self._step_done("files")
        else:  self._step_error("files", "Check internet connection")
        step += 1; self._set_prog(step/total_steps)

        # ── 8. Finalize ───────────────────────────────────────────────────
        self._step_pending("shortcuts")
        self._log("Creating launcher shortcut...")
        self._create_launcher()
        self._step_done("shortcuts", "Done ✓")
        step += 1; self._set_prog(1.0)

        self._set_status("✅  Installation complete! Click CLOSE to exit.", OK)
        self._log("All done! Run LND_Launch.bat or double-click the shortcut.")
        self.after(0, lambda: self.btn_close.config(bg=PURPLE, fg="#ffffff"))

    def _uninstall(self):
        self._log(f"Removing {INSTALL_DIR}...")
        if os.path.exists(INSTALL_DIR):
            shutil.rmtree(INSTALL_DIR)
        self._set_status("Uninstalled.", WARN)
        self._log("Done.")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _python_installed(self) -> bool:
        try:
            result = subprocess.run(
                ["python", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _tesseract_installed(self) -> bool:
        tess_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        return os.path.exists(tess_path)

    def _install_python(self) -> bool:
        try:
            CREATE_NO_WINDOW = 0x08000000
            installer = os.path.join(os.environ["TEMP"], "python_installer.exe")
            urllib.request.urlretrieve(PYTHON_URL, installer,
                                       self._url_progress("python"))
            subprocess.run([installer, "/quiet", "InstallAllUsers=1",
                            "PrependPath=1", "Include_test=0"],
                           check=True, creationflags=CREATE_NO_WINDOW)
            os.remove(installer)
            return True
        except Exception as e:
            self._log(f"Python install failed: {e}")
            return False

    def _install_tesseract(self) -> bool:
        try:
            CREATE_NO_WINDOW = 0x08000000
            installer = os.path.join(os.environ["TEMP"], "tesseract_installer.exe")
            urllib.request.urlretrieve(TESSERACT_URL, installer,
                                       self._url_progress("tesseract"))
            subprocess.run([installer, "/S"], check=True,
                           creationflags=CREATE_NO_WINDOW)
            os.remove(installer)
            return True
        except Exception as e:
            self._log(f"Tesseract install failed: {e}")
            return False

    def _url_progress(self, key):
        def _hook(block, block_size, total):
            if total > 0:
                pct = min(block * block_size / total, 1.0)
                self.after(0, self._ui_step_pending, key)
        return _hook

    def _run_pip(self, args: list):
        try:
            # CREATE_NO_WINDOW prevents subprocess from spawning visible windows
            # which was causing the duplicate loader instance bug
            CREATE_NO_WINDOW = 0x08000000
            subprocess.run(
                [sys.executable, "-m", "pip"] + args + ["--quiet"],
                capture_output=True,
                check=False,
                creationflags=CREATE_NO_WINDOW
            )
        except Exception as e:
            self._log(f"pip error: {e}")

    def _download_files(self) -> bool:
        """
        Download all files from GitHub.
        .py files come from raw repo (under 25MB fine).
        .exe comes from GitHub Releases (no size limit).
        """
        try:
            os.makedirs(INSTALL_DIR, exist_ok=True)
            modules_dir = os.path.join(INSTALL_DIR, "modules")
            os.makedirs(modules_dir, exist_ok=True)

            # ── Python source files from raw repo ─────────────────────────
            files = [
                "main.py",
                "version.json",
                "modules/__init__.py",
                "modules/discord_sender.py",
                "modules/generators_tab.py",
                "modules/license_tab.py",
                "modules/monitor_tab.py",
                "modules/ocr_scanner.py",
                "modules/region_selector.py",
                "modules/server_tracker_tab.py",
                "modules/settings_tab.py",
                "modules/upload_timer_tab.py",
            ]
            extras = ["logo.png", "logo_bg.png", "icon.ico"]

            for f in files + extras:
                url  = f"{RAW_BASE}/{f}"
                dest = os.path.join(INSTALL_DIR, f.replace("/", os.sep))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                try:
                    urllib.request.urlretrieve(url, dest)
                    self._log(f"  ↓ {f}")
                except Exception:
                    if f in extras:
                        pass   # optional
                    else:
                        self._log(f"  ✗ Failed: {f}")

            # ── Main .exe from GitHub Releases ────────────────────────────
            # URL format: github.com/USER/REPO/releases/download/TAG/FILE
            exe_name    = "LND.Tribe.Logs.exe"
            release_tag = "v1.0.0"
            exe_url  = (f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}"
                        f"/releases/download/{release_tag}/"
                        f"{exe_name.replace(' ', '%20')}")
            exe_dest = os.path.join(INSTALL_DIR, exe_name)
            self._log(f"  ↓ Downloading {exe_name} from Releases...")
            try:
                urllib.request.urlretrieve(exe_url, exe_dest)
                self._log(f"  ✅ {exe_name} downloaded")
            except Exception as e:
                self._log(f"  ⚠ Could not download exe: {e}")
                self._log(f"  App will run via Python instead.")

            return True
        except Exception as e:
            self._log(f"Download error: {e}")
            return False

            return True
        except Exception as e:
            self._log(f"Download error: {e}")
            return False

    def _create_launcher(self):
        """Create desktop shortcut and install-dir launcher."""
        exe_path = os.path.join(INSTALL_DIR, "LND Tribe Logs.exe")
        py_path  = os.path.join(INSTALL_DIR, "main.py")

        # Determine launch command — prefer .exe if it exists
        if os.path.exists(exe_path):
            launch_cmd = f'start "" "{exe_path}"'
        else:
            launch_cmd = f'start "" pythonw "{py_path}"'

        # Launcher inside install dir
        bat = os.path.join(INSTALL_DIR, "Launch_LND.bat")
        with open(bat, "w") as f:
            f.write(f'@echo off\ncd /d "{INSTALL_DIR}"\n{launch_cmd}\n')

        # Get correct desktop path via Windows shell API
        try:
            import ctypes.wintypes
            CSIDL_DESKTOP = 0
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(
                None, CSIDL_DESKTOP, None, 0, buf)
            desktop = buf.value
        except Exception:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")

        desktop_bat = os.path.join(desktop, "L.N.D Tribe Logs.bat")
        try:
            with open(desktop_bat, "w") as f:
                f.write(f'@echo off\ncd /d "{INSTALL_DIR}"\n{launch_cmd}\n')
            self._log("✅ Desktop shortcut created.")
        except Exception as e:
            self._log(f"Could not create desktop shortcut: {e}")


if __name__ == "__main__":
    app = LNDLoader()
    app.mainloop()
