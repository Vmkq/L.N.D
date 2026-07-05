"""
license_tab.py
License validation against L.N.D license server.
HWID-locked, server-validated.
"""
import tkinter as tk
import threading
import hashlib
import subprocess
import platform
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import (BG_DARK, BG_PANEL, BG_SECTION, BORDER, ACCENT, ACCENT_BRIGHT,
                  ACCENT_GLOW, ACCENT_DIM, TEXT_MAIN, TEXT_DIM, TEXT_OK,
                  TEXT_DANGER, save_config, LOGO_PATH)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── Update this URL after you deploy to Render ────────────────────────────────
LICENSE_SERVER = "https://lndlicenseserver.onrender.com"
# ─────────────────────────────────────────────────────────────────────────────


def get_hwid() -> str:
    """Generate a unique hardware ID for this PC."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "csproduct", "get", "uuid"],
                capture_output=True, text=True)
            uid = result.stdout.strip().split()[-1]
        else:
            uid = platform.node()
        return hashlib.sha256(uid.encode()).hexdigest()[:32]
    except Exception:
        # Fallback — use machine name hash
        return hashlib.sha256(platform.node().encode()).hexdigest()[:32]


def validate_key(key: str, hwid: str, username: str = "") -> tuple:
    """
    Validate key against server.
    Retries once to handle Render free tier cold start (can take 30-60s).
    Returns (valid: bool, message: str)
    """
    if not HAS_REQUESTS:
        return False, "requests library not installed."

    for attempt in range(2):   # try twice
        try:
            r = requests.post(
                f"{LICENSE_SERVER}/validate",
                json={"key": key, "hwid": hwid, "username": username},
                timeout=30)   # 30s timeout for cold start
            data = r.json()
            return data.get("valid", False), data.get("message", "Unknown error")
        except requests.exceptions.ConnectionError:
            if attempt == 0:
                time.sleep(3)
                continue
            return False, "Cannot reach license server. Check your internet connection."
        except requests.exceptions.Timeout:
            if attempt == 0:
                continue   # retry once on timeout
            return False, "License server is waking up — please try again in 30 seconds."
        except Exception as e:
            return False, f"Server error: {e}"
    return False, "Could not connect to license server."


class LicenseTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_DARK)
        self.app      = app
        self._logo    = None
        self._hwid    = get_hwid()
        self._valid   = app.config_data.get("licensed", False)
        self._key     = app.config_data.get("license_key", "")
        self._build()

        # If already licensed, re-validate silently in background
        if self._valid and self._key:
            threading.Thread(target=self._silent_revalidate, daemon=True).start()

    def _build(self):
        # Logo
        if HAS_PIL and os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH).convert("RGBA")
                img.thumbnail((130, 130), Image.LANCZOS)
                self._logo = ImageTk.PhotoImage(img)
                tk.Label(self, image=self._logo,
                         bg=BG_DARK).pack(pady=(30, 0))
            except Exception:
                pass

        tk.Label(self, text="L.N.D TRIBE LOGS",
                 bg=BG_DARK, fg=TEXT_MAIN,
                 font=("Segoe UI", 20, "bold")).pack(pady=(10, 0))
        tk.Label(self, text="ARK: Survival Ascended — Tribe Monitor",
                 bg=BG_DARK, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).pack(pady=(2, 20))

        # Card
        outer = tk.Frame(self, bg=BORDER)
        outer.pack(padx=60, fill="x")
        hdr = tk.Frame(outer, bg=BG_SECTION); hdr.pack(fill="x")
        tk.Frame(hdr, bg=ACCENT_BRIGHT, width=3).pack(side="left", fill="y")
        tk.Label(hdr, text="LICENSE KEY", bg=BG_SECTION, fg=ACCENT_BRIGHT,
                 font=("Segoe UI", 9, "bold"),
                 padx=10, pady=7).pack(side="left")
        inner = tk.Frame(outer, bg=BG_PANEL); inner.pack(fill="x")

        # HWID display
        tk.Label(inner, text=f"Hardware ID: {self._hwid[:16]}...",
                 bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Consolas", 7)).pack(anchor="w", padx=14, pady=(8, 2))

        self.v_key = tk.StringVar(value=self._key)
        tk.Entry(inner, textvariable=self.v_key,
                 bg=ACCENT, fg=TEXT_MAIN, insertbackground=ACCENT_BRIGHT,
                 relief="flat", font=("Consolas", 10),
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT_BRIGHT).pack(
            fill="x", padx=14, pady=(0, 6))

        self.status_lbl = tk.Label(inner, text="", bg=BG_PANEL,
                                    font=("Segoe UI", 8))
        self.status_lbl.pack(anchor="w", padx=14, pady=(0, 4))

        self.btn = tk.Button(inner, text="ACTIVATE",
                             command=self._activate,
                             bg=ACCENT_BRIGHT, fg="#ffffff",
                             activebackground=ACCENT_GLOW,
                             activeforeground="#ffffff",
                             relief="flat",
                             font=("Segoe UI", 9, "bold"),
                             cursor="hand2", pady=8)
        self.btn.pack(fill="x", padx=14, pady=(0, 14))

        # Show status if already licensed
        if self._valid:
            assigned = self.app.config_data.get("assigned_to", "")
            msg = f"✅  License active"
            if assigned:
                msg += f" — {assigned}"
            self.status_lbl.config(text=msg, fg=TEXT_OK)
            self.btn.config(text="RE-VALIDATE", bg=ACCENT_DIM)

        tk.Label(self, text="Contact Demon for a license key",
                 bg=BG_DARK, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(pady=(16, 0))

    def _activate(self):
        key = self.v_key.get().strip().upper()
        if not key:
            self.status_lbl.config(text="Enter a license key.", fg=TEXT_DANGER)
            return

        self.btn.config(state="disabled", text="Validating...")
        self.status_lbl.config(text="Contacting license server...", fg=TEXT_DIM)
        self.update_idletasks()

        def _do():
            ok, msg = validate_key(key, self._hwid)
            self.after(0, self._on_result, ok, msg, key)

        threading.Thread(target=_do, daemon=True).start()

    def _on_result(self, ok: bool, msg: str, key: str):
        self.btn.config(state="normal")
        if ok:
            assigned = self.app.config_data.get("assigned_to", "")
            self.app.config_data["license_key"] = key
            self.app.config_data["licensed"]    = True
            if "welcome back" in msg.lower() or "activated for" in msg.lower():
                parts = msg.split(",")
                if len(parts) > 1:
                    assigned = parts[-1].strip().rstrip("!")
                    self.app.config_data["assigned_to"] = assigned
            save_config(self.app.config_data)
            self._valid = True
            self._key   = key
            self.status_lbl.config(text=f"✅  {msg}", fg=TEXT_OK)
            self.btn.config(text="RE-VALIDATE", bg=ACCENT_DIM)
            self.app.set_status("License activated", TEXT_OK)
            # Unlock all other tabs
            self.app.unlock_tabs()
        else:
            self.app.config_data["licensed"] = False
            save_config(self.app.config_data)
            self._valid = False
            self.status_lbl.config(text=f"❌  {msg}", fg=TEXT_DANGER)
            self.btn.config(text="ACTIVATE", bg=ACCENT_BRIGHT)

    def _silent_revalidate(self):
        """Re-check license in background on startup."""
        ok, msg = validate_key(self._key, self._hwid)
        if not ok:
            # Only invalidate if server is reachable (not a network error)
            if "invalid" in msg.lower() or "revoked" in msg.lower():
                self.app.config_data["licensed"] = False
                save_config(self.app.config_data)
                self.after(0, self._force_lock, msg)

    def _force_lock(self, msg: str):
        """Lock all tabs and show revoked message."""
        self.app._apply_lock()
        self.app.notebook.select(0)   # force back to license tab
        self.status_lbl.config(
            text=f"❌ {msg}", fg=TEXT_DANGER)
        self.app.set_status("License invalid — access revoked", TEXT_DANGER)
