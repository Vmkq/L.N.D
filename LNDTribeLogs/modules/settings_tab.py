"""Settings Tab — black/purple theme"""
import tkinter as tk
from tkinter import messagebox
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from main import (BG_DARK, BG_PANEL, BG_SECTION, BORDER, ACCENT, ACCENT_BRIGHT,
                  ACCENT_GLOW, ACCENT_DIM, TEXT_MAIN, TEXT_DIM, TEXT_OK,
                  STATUS_DOT, save_config)
from modules.discord_sender import send_test_message

# ── Shared widget builders ────────────────────────────────────────────────────
def _card(parent, title):
    outer = tk.Frame(parent, bg=BORDER, bd=0)
    outer.pack(fill="x", padx=14, pady=6)
    hdr = tk.Frame(outer, bg=BG_SECTION)
    hdr.pack(fill="x")
    # purple left stripe on each card
    tk.Frame(hdr, bg=ACCENT_BRIGHT, width=3).pack(side="left", fill="y")
    tk.Label(hdr, text=title, bg=BG_SECTION, fg=ACCENT_BRIGHT,
             font=("Segoe UI", 9, "bold"), padx=10, pady=7).pack(side="left")
    inner = tk.Frame(outer, bg=BG_PANEL)
    inner.pack(fill="x")
    return outer, inner

def _lbl(parent, text):
    tk.Label(parent, text=text, bg=BG_PANEL, fg=TEXT_DIM,
             font=("Segoe UI", 8)).pack(anchor="w", padx=14, pady=(6,1))

def _entry(parent, var):
    e = tk.Entry(parent, textvariable=var, bg=ACCENT, fg=TEXT_MAIN,
                 insertbackground=ACCENT_BRIGHT, relief="flat",
                 font=("Consolas", 8), highlightthickness=1,
                 highlightbackground=BORDER, highlightcolor=ACCENT_BRIGHT)
    e.pack(fill="x", padx=14, pady=(0,6))
    return e

def _btn(parent, text, cmd, bg=None):
    b = tk.Button(parent, text=text, command=cmd,
                  bg=bg or ACCENT_BRIGHT, fg="#ffffff",
                  activebackground=ACCENT_GLOW, activeforeground="#ffffff",
                  relief="flat", font=("Segoe UI", 8, "bold"),
                  cursor="hand2", padx=12, pady=6)
    return b

class SettingsTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_DARK)
        self.app = app
        canvas = tk.Canvas(self, bg=BG_DARK, highlightthickness=0)
        scroll = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(canvas, bg=BG_DARK)
        wid = canvas.create_window((0,0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: (
            canvas.configure(scrollregion=canvas.bbox("all")),
            canvas.itemconfig(wid, width=canvas.winfo_width())))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(wid, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120),"units"))

        cfg = app.config_data
        def sv(k, d=""): return tk.StringVar(value=cfg.get(k, d))
        self.v_tl_webhook  = sv("tl_webhook")
        self.v_tl_role     = sv("tl_role")
        self.v_tl_interval = sv("tl_interval","5")
        self.v_ps_webhook  = sv("ps_webhook")
        self.v_ps_role     = sv("ps_role")
        self.v_tm_webhook  = sv("tm_webhook")
        self.v_tm_role     = sv("tm_role")
        self.v_ut_enabled  = tk.BooleanVar(value=cfg.get("ut_enabled", True))
        self.v_ut_webhook  = sv("ut_webhook")
        self.v_ut_role     = sv("ut_role")
        self.v_ut_interval = sv("ut_interval","1")
        self._build()

    def _build(self):
        p = self.inner

        # ── Tribe Log ────────────────────────────────────────────────────
        _, c = _card(p, "TRIBE LOG ALERTS")
        _lbl(c, "Webhook URL"); _entry(c, self.v_tl_webhook)
        _lbl(c, "Role ID for pings (kills & destroyed only)")
        _entry(c, self.v_tl_role)
        _lbl(c, "Scan interval")
        fr = tk.Frame(c, bg=BG_PANEL); fr.pack(anchor="w", padx=14, pady=(0,4))
        tk.Entry(fr, textvariable=self.v_tl_interval, width=6,
                 bg=ACCENT, fg=TEXT_MAIN, insertbackground=ACCENT_BRIGHT,
                 relief="flat", font=("Consolas", 8)).pack(side="left")
        tk.Label(fr, text=" seconds", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI",8)).pack(side="left")
        br = tk.Frame(c, bg=BG_PANEL); br.pack(fill="x", padx=14, pady=(0,12))
        _btn(br,"SAVE", self._save).pack(side="left", padx=(0,8))
        _btn(br,"TEST DISCORD", lambda: self._test(self.v_tl_webhook.get()),
             ACCENT_DIM).pack(side="left")

        # ── Parasaur ─────────────────────────────────────────────────────
        _, c = _card(p, "PARASAUR ALERTS")
        _lbl(c,"Webhook URL"); _entry(c, self.v_ps_webhook)
        _lbl(c,"Role ID to ping"); _entry(c, self.v_ps_role)

        # ── Tribe Members ─────────────────────────────────────────────────
        _, c = _card(p, "TRIBE MEMBERS")
        _lbl(c,"Webhook URL"); _entry(c, self.v_tm_webhook)
        _lbl(c,"Role ID to ping (optional)"); _entry(c, self.v_tm_role)

        # ── Upload Timer ──────────────────────────────────────────────────
        _, c = _card(p, "UPLOAD TIMER")
        tk.Checkbutton(c, text=" Enable upload timer alerts",
                       variable=self.v_ut_enabled,
                       bg=BG_PANEL, fg=TEXT_MAIN, selectcolor=ACCENT,
                       activebackground=BG_PANEL, activeforeground=TEXT_MAIN,
                       font=("Segoe UI",8)).pack(anchor="w", padx=14, pady=(8,2))
        _lbl(c,"Webhook URL"); _entry(c, self.v_ut_webhook)
        _lbl(c,"Role ID to ping"); _entry(c, self.v_ut_role)
        _lbl(c,"Check interval")
        fr2 = tk.Frame(c, bg=BG_PANEL); fr2.pack(anchor="w", padx=14, pady=(0,12))
        tk.Entry(fr2, textvariable=self.v_ut_interval, width=6,
                 bg=ACCENT, fg=TEXT_MAIN, insertbackground=ACCENT_BRIGHT,
                 relief="flat", font=("Consolas",8)).pack(side="left")
        tk.Label(fr2, text=" minutes", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI",8)).pack(side="left")

        _btn(p, "  SAVE ALL SETTINGS  ", self._save, ACCENT_BRIGHT).pack(
            pady=14, padx=14, fill="x")

    def _save(self):
        self.app.config_data.update({
            "tl_webhook": self.v_tl_webhook.get(), "tl_role": self.v_tl_role.get(),
            "tl_interval": self.v_tl_interval.get(), "ps_webhook": self.v_ps_webhook.get(),
            "ps_role": self.v_ps_role.get(), "tm_webhook": self.v_tm_webhook.get(),
            "tm_role": self.v_tm_role.get(), "ut_enabled": self.v_ut_enabled.get(),
            "ut_webhook": self.v_ut_webhook.get(), "ut_role": self.v_ut_role.get(),
            "ut_interval": self.v_ut_interval.get(),
        })
        save_config(self.app.config_data)
        self.app.set_status("Settings saved", TEXT_OK)

    def _test(self, url):
        if not url:
            messagebox.showerror("Error","Enter a webhook URL first.")
            return
        ok, msg = send_test_message(url)
        if ok: self.app.set_status("Test message sent to Discord", TEXT_OK)
        else:  messagebox.showerror("Discord Error", msg)