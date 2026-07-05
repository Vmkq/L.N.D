"""Generators Tab — black/purple theme. Fixed duplicate name entry bug."""
import tkinter as tk
from tkinter import messagebox
import threading, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from main import (BG_DARK, BG_PANEL, BG_SECTION, BORDER, ACCENT, ACCENT_BRIGHT,
                  ACCENT_GLOW, ACCENT_DIM, TEXT_MAIN, TEXT_DIM, TEXT_OK,
                  TEXT_WARN, TEXT_DANGER, save_config)
from modules.discord_sender import send_generator_alert, send_generator_list

LOCATIONS = ["None","Main Base","North Cave","South Cave",
             "Beach Base","Warroom","Gacha Tower","Other"]

def _card(parent, title):
    outer = tk.Frame(parent, bg=BORDER, bd=0)
    outer.pack(fill="x", padx=14, pady=6)
    hdr = tk.Frame(outer, bg=BG_SECTION); hdr.pack(fill="x")
    tk.Frame(hdr, bg=ACCENT_BRIGHT, width=3).pack(side="left", fill="y")
    tk.Label(hdr, text=title, bg=BG_SECTION, fg=ACCENT_BRIGHT,
             font=("Segoe UI", 9, "bold"), padx=10, pady=7).pack(side="left")
    inner = tk.Frame(outer, bg=BG_PANEL); inner.pack(fill="x")
    return outer, inner

def _lbl(p, t):
    tk.Label(p, text=t, bg=BG_PANEL, fg=TEXT_DIM,
             font=("Segoe UI",8)).pack(anchor="w", padx=14, pady=(6,1))

def _entry_var(p, var, **kw):
    e = tk.Entry(p, textvariable=var, bg=ACCENT, fg=TEXT_MAIN,
                 insertbackground=ACCENT_BRIGHT, relief="flat",
                 font=("Consolas",8), highlightthickness=1,
                 highlightbackground=BORDER, highlightcolor=ACCENT_BRIGHT, **kw)
    e.pack(fill="x", padx=14, pady=(0,6))
    return e

def _btn(p, t, cmd, bg=None):
    return tk.Button(p, text=t, command=cmd,
                     bg=bg or ACCENT_BRIGHT, fg="#ffffff",
                     activebackground=ACCENT_GLOW, activeforeground="#ffffff",
                     relief="flat", font=("Segoe UI",8,"bold"),
                     cursor="hand2", padx=10, pady=6)

class GeneratorsTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_DARK)
        self.app = app
        self.generators = list(app.config_data.get("generators", []))
        self._running = True
        threading.Thread(target=self._countdown_loop, daemon=True).start()
        self._build()

    def _build(self):
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
        p = self.inner

        # ── Discord ───────────────────────────────────────────────────────
        _, c = _card(p, "DISCORD")
        _lbl(c, "Webhook URL for generator alerts")
        self.v_webhook = tk.StringVar(value=self.app.config_data.get("gen_webhook",""))
        _entry_var(c, self.v_webhook)
        _lbl(c, "Role ID to ping (optional)")
        self.v_role = tk.StringVar(value=self.app.config_data.get("gen_role",""))
        _entry_var(c, self.v_role)
        _btn(c,"SAVE", self._save_discord).pack(padx=14, pady=(0,12), anchor="w")

        # ── Add Generator ─────────────────────────────────────────────────
        _, c = _card(p, "ADD GENERATOR")
        _lbl(c, "Generator name")
        # ── FIX: use a plain Entry (not textvariable) to avoid shared-var bug ──
        self._name_entry = tk.Entry(c, bg=ACCENT, fg=TEXT_DIM,
                                     insertbackground=ACCENT_BRIGHT, relief="flat",
                                     font=("Consolas",8), highlightthickness=1,
                                     highlightbackground=BORDER,
                                     highlightcolor=ACCENT_BRIGHT)
        self._name_entry.insert(0, "e.g. South Base Gen")
        self._name_entry.bind("<FocusIn>",  self._clear_placeholder)
        self._name_entry.bind("<FocusOut>", self._restore_placeholder)
        self._name_entry.pack(fill="x", padx=14, pady=(0,6))

        _lbl(c, "Fuel remaining")
        fr = tk.Frame(c, bg=BG_PANEL); fr.pack(anchor="w", padx=14, pady=(0,6))
        self.v_days  = tk.StringVar(value="0")
        self.v_hours = tk.StringVar(value="0")
        tk.Entry(fr, textvariable=self.v_days, width=7, bg=ACCENT, fg=TEXT_MAIN,
                 insertbackground=ACCENT_BRIGHT, relief="flat",
                 font=("Segoe UI",10,"bold"), justify="center").pack(side="left")
        tk.Label(fr, text=" days  ", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI",8)).pack(side="left")
        tk.Entry(fr, textvariable=self.v_hours, width=7, bg=ACCENT, fg=TEXT_MAIN,
                 insertbackground=ACCENT_BRIGHT, relief="flat",
                 font=("Segoe UI",10,"bold"), justify="center").pack(side="left")
        tk.Label(fr, text=" hours", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI",8)).pack(side="left")

        _lbl(c, "Location (optional)")
        self.v_loc = tk.StringVar(value="None")
        om = tk.OptionMenu(c, self.v_loc, *LOCATIONS)
        om.config(bg=ACCENT, fg=TEXT_MAIN, activebackground=ACCENT_BRIGHT,
                  activeforeground="#ffffff", relief="flat",
                  font=("Segoe UI",8), highlightthickness=0,
                  indicatoron=True)
        om["menu"].config(bg=ACCENT, fg=TEXT_MAIN,
                          activebackground=ACCENT_BRIGHT, activeforeground="#ffffff")
        om.pack(fill="x", padx=14, pady=(0,6))

        _btn(c,"ADD GENERATOR", self._add).pack(fill="x", padx=14, pady=(4,14))

        # ── Active Generators ─────────────────────────────────────────────
        _, self._active_card = _card(p, "ACTIVE GENERATORS")
        btn_r = tk.Frame(self._active_card, bg=BG_PANEL)
        btn_r.pack(fill="x", padx=14, pady=6)
        _btn(btn_r,"SEND ACTIVE LIST", self._send_list, ACCENT_DIM).pack(side="right")
        self._list_frame = tk.Frame(self._active_card, bg=BG_PANEL)
        self._list_frame.pack(fill="x", padx=14, pady=(0,10))
        self._refresh_list()

    def _clear_placeholder(self, _e):
        if self._name_entry.get() == "e.g. South Base Gen":
            self._name_entry.delete(0, "end")
            self._name_entry.config(fg=TEXT_MAIN)

    def _restore_placeholder(self, _e):
        if not self._name_entry.get():
            self._name_entry.insert(0, "e.g. South Base Gen")
            self._name_entry.config(fg=TEXT_DIM)

    def _add(self):
        name = self._name_entry.get().strip()
        if not name or name == "e.g. South Base Gen":
            messagebox.showwarning("Missing Name","Enter a generator name.")
            return
        try:
            d, h = int(self.v_days.get()), int(self.v_hours.get())
        except ValueError:
            messagebox.showwarning("Invalid Fuel","Days and hours must be numbers.")
            return
        loc = self.v_loc.get() if self.v_loc.get() != "None" else ""
        self.generators.append({"name":name,"days":d,"hours":h,
                                 "location":loc,"added_ts":time.time()})
        self._save_gens()
        self._refresh_list()
        self.app.set_status(f"Generator '{name}' added.", TEXT_OK)
        self._name_entry.delete(0,"end")
        self._name_entry.insert(0,"e.g. South Base Gen")
        self._name_entry.config(fg=TEXT_DIM)
        self.v_days.set("0"); self.v_hours.set("0"); self.v_loc.set("None")

    def _remove(self, i):
        n = self.generators[i]["name"]
        self.generators.pop(i)
        self._save_gens(); self._refresh_list()
        self.app.set_status(f"'{n}' removed.", TEXT_WARN)

    def _refresh_list(self):
        for w in self._list_frame.winfo_children(): w.destroy()
        if not self.generators:
            tk.Label(self._list_frame, text="No generators added yet.",
                     bg=BG_PANEL, fg=TEXT_DIM,
                     font=("Segoe UI",8)).pack(anchor="w", pady=4)
            return
        for i, g in enumerate(self.generators):
            alive = g["days"] > 0 or g["hours"] > 0
            row = tk.Frame(self._list_frame, bg=BG_SECTION); row.pack(fill="x", pady=2)
            tk.Frame(row, bg=ACCENT_BRIGHT if alive else TEXT_DANGER,
                     width=3).pack(side="left", fill="y")
            dot = "🟢" if alive else "🔴"
            loc = f"  ·  {g['location']}" if g.get("location") else ""
            tk.Label(row, text=f" {dot}  {g['name']}{loc}",
                     bg=BG_SECTION, fg=TEXT_MAIN,
                     font=("Segoe UI",8,"bold")).pack(side="left", padx=6)
            fc = TEXT_OK if alive else TEXT_DANGER
            tk.Label(row, text=f"{g['days']}d {g['hours']}h remaining",
                     bg=BG_SECTION, fg=fc,
                     font=("Segoe UI",8)).pack(side="left", padx=8)
            tk.Button(row, text=" ✕ ", command=lambda idx=i: self._remove(idx),
                      bg=BG_SECTION, fg=TEXT_DANGER, relief="flat",
                      font=("Segoe UI",9,"bold"), cursor="hand2",
                      activebackground="#1a0010").pack(side="right", padx=4)

    def _send_list(self):
        hook = self.app.config_data.get("gen_webhook","")
        if not hook:
            messagebox.showwarning("No Webhook","Set the Discord webhook first.")
            return
        ok, err = send_generator_list(hook, self.generators)
        if ok: self.app.set_status("Active generator list sent.", TEXT_OK)
        else:  messagebox.showerror("Discord Error", err)

    def _countdown_loop(self):
        while self._running:
            time.sleep(60)
            changed = False
            for g in self.generators:
                if g["hours"] > 0 or g["days"] > 0:
                    g["hours"] -= 1
                    if g["hours"] < 0:
                        g["hours"] = 23; g["days"] = max(0, g["days"]-1)
                    changed = True
                    total = g["days"]*24 + g["hours"]
                    if total in (24, 6, 1):
                        hook = self.app.config_data.get("gen_webhook","")
                        role = self.app.config_data.get("gen_role","")
                        if hook:
                            threading.Thread(target=send_generator_alert,
                                args=(hook,role,g["name"],g["days"],
                                      g["hours"],g.get("location","")),
                                daemon=True).start()
            if changed:
                self._save_gens()
                self.after(0, self._refresh_list)

    def _save_discord(self):
        self.app.config_data["gen_webhook"] = self.v_webhook.get()
        self.app.config_data["gen_role"]    = self.v_role.get()
        save_config(self.app.config_data)
        self.app.set_status("Generator Discord settings saved.", TEXT_OK)

    def _save_gens(self):
        self.app.config_data["generators"] = self.generators
        save_config(self.app.config_data)
