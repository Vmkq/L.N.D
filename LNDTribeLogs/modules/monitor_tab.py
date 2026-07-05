"""
monitor_tab.py
Start/Stop scanning, live log feed, region selection.
Black/purple theme.
"""
import tkinter as tk
from tkinter import messagebox
import threading
import time
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from main import (BG_DARK, BG_PANEL, BG_SECTION, BORDER, ACCENT, ACCENT_BRIGHT,
                  ACCENT_GLOW, ACCENT_DIM, TEXT_MAIN, TEXT_DIM, TEXT_OK, TEXT_WARN,
                  TEXT_DANGER, STATUS_DOT, save_config)
from modules.region_selector import select_region
from modules.ocr_scanner     import (ocr_region_with_colours, dedup_key,
                                      ui_tag, detect_parasaur_alert,
                                      capture_region, parse_member_lines,
                                      ocr_member_region)
from modules.discord_sender  import (send_tribe_log_event, send_parasaur_alert,
                                      send_parasaur_cleared, send_member_status)


def _btn(parent, text, cmd, bg=None, **kw):
    return tk.Button(parent, text=text, command=cmd,
                     bg=bg or ACCENT_BRIGHT, fg="#ffffff",
                     activebackground=ACCENT_GLOW, activeforeground="#ffffff",
                     relief="flat", font=("Segoe UI", 8, "bold"),
                     cursor="hand2", padx=10, pady=6, **kw)

def _card(parent, title):
    outer = tk.Frame(parent, bg=BORDER, bd=0)
    outer.pack(fill="x", padx=14, pady=6)
    hdr = tk.Frame(outer, bg=BG_SECTION)
    hdr.pack(fill="x")
    tk.Frame(hdr, bg=ACCENT_BRIGHT, width=3).pack(side="left", fill="y")
    tk.Label(hdr, text=title, bg=BG_SECTION, fg=ACCENT_BRIGHT,
             font=("Segoe UI", 9, "bold"), padx=10, pady=7).pack(side="left")
    inner = tk.Frame(outer, bg=BG_PANEL)
    inner.pack(fill="x")
    return outer, inner


class MonitorTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_DARK)
        self.app = app

        def _load(key):
            r = app.config_data.get(key)
            return tuple(r) if r else None

        self.region_tribelog = _load("region_tribelog")
        self.region_parasaur = _load("region_parasaur")
        self.region_members  = _load("region_members")

        self._running      = False
        self._thread       = None
        self._last_lines   = set()
        self._last_members = []
        self._ps_alerted   = False

        self._build()

    # ─────────────────────────────────────────────────────────────────────────
    def _build(self):
        cfg = self.app.config_data

        # ── Enable toggles (persisted in config) ─────────────────────────
        self.v_enable_tribelog  = tk.BooleanVar(value=cfg.get("enable_tribelog",  True))
        self.v_enable_parasaur  = tk.BooleanVar(value=cfg.get("enable_parasaur",  True))
        self.v_enable_members   = tk.BooleanVar(value=cfg.get("enable_members",   True))

        # ── Tribe Log ────────────────────────────────────────────────────
        _, card = _card(self, "TRIBE LOG")
        top = tk.Frame(card, bg=BG_PANEL)
        top.pack(fill="x", padx=12, pady=(6, 0))
        tk.Checkbutton(top, text="Enable tribe log scanning",
                       variable=self.v_enable_tribelog,
                       command=self._save_toggles,
                       bg=BG_PANEL, fg=TEXT_MAIN, selectcolor=ACCENT,
                       activebackground=BG_PANEL, activeforeground=TEXT_MAIN,
                       font=("Segoe UI", 8)).pack(side="left")
        tk.Label(card, text="Drag over the tribe log area in the ARK UI",
                 bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(2, 0))
        row = tk.Frame(card, bg=BG_PANEL)
        row.pack(fill="x", padx=12, pady=(4, 8))
        self.lbl_tl = tk.Label(row, bg=BG_PANEL, fg=TEXT_DIM, font=("Segoe UI", 8))
        self.lbl_tl.pack(side="left")
        _btn(row, "SELECT REGION",
             lambda: self._select("tribelog"), "#163a6e").pack(side="right")
        self._refresh_label("tribelog")

        # ── Parasaur Detection ────────────────────────────────────────────
        _, card = _card(self, "PARASAUR DETECTION")
        top2 = tk.Frame(card, bg=BG_PANEL)
        top2.pack(fill="x", padx=12, pady=(6, 0))
        tk.Checkbutton(top2, text="Enable parasaur detection",
                       variable=self.v_enable_parasaur,
                       command=self._save_toggles,
                       bg=BG_PANEL, fg=TEXT_MAIN, selectcolor=ACCENT,
                       activebackground=BG_PANEL, activeforeground=TEXT_MAIN,
                       font=("Segoe UI", 8)).pack(side="left")
        tk.Label(card,
                 text="Select the top-left corner where '[Name] (Parasaur) detected an enemy!' appears",
                 bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(2, 0))
        tk.Label(card,
                 text="Tip: in ARK, trigger a parasaur alert, then alt-tab and select that region",
                 bg=BG_PANEL, fg="#4a6a9e",
                 font=("Segoe UI", 7, "italic")).pack(anchor="w", padx=12)
        row2 = tk.Frame(card, bg=BG_PANEL)
        row2.pack(fill="x", padx=12, pady=(4, 8))
        self.lbl_ps = tk.Label(row2, bg=BG_PANEL, fg=TEXT_DIM, font=("Segoe UI", 8))
        self.lbl_ps.pack(side="left")
        _btn(row2, "SELECT REGION",
             lambda: self._select("parasaur"), "#163a6e").pack(side="right")
        self._refresh_label("parasaur")

        # ── Tribe Members ─────────────────────────────────────────────────
        _, card = _card(self, "TRIBE MEMBERS")
        top3 = tk.Frame(card, bg=BG_PANEL)
        top3.pack(fill="x", padx=12, pady=(6, 0))
        tk.Checkbutton(top3, text="Enable tribe member tracking",
                       variable=self.v_enable_members,
                       command=self._save_toggles,
                       bg=BG_PANEL, fg=TEXT_MAIN, selectcolor=ACCENT,
                       activebackground=BG_PANEL, activeforeground=TEXT_MAIN,
                       font=("Segoe UI", 8)).pack(side="left")
        tk.Label(card,
                 text="Drag over the member list — start underneath TRIBE GROUP",
                 bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(2, 0))
        row3 = tk.Frame(card, bg=BG_PANEL)
        row3.pack(fill="x", padx=12, pady=(4, 8))
        self.lbl_tm = tk.Label(row3, bg=BG_PANEL, fg=TEXT_DIM, font=("Segoe UI", 8))
        self.lbl_tm.pack(side="left")
        _btn(row3, "SELECT REGION",
             lambda: self._select("members"), "#163a6e").pack(side="right")
        self._refresh_label("members")

        # ── Start / Stop ──────────────────────────────────────────────────
        btn_row = tk.Frame(self, bg=BG_DARK)
        btn_row.pack(fill="x", padx=12, pady=8)
        self.btn_start = _btn(btn_row, "▶  START", self._start, ACCENT_BRIGHT)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.btn_stop = _btn(btn_row, "■  STOP", self._stop, ACCENT_DIM)
        self.btn_stop.pack(side="left", fill="x", expand=True)
        self.btn_stop.config(state="disabled")

        # ── Live Log Events ───────────────────────────────────────────────
        log_outer = tk.Frame(self, bg=BORDER)
        log_outer.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        log_hdr = tk.Frame(log_outer, bg=BG_SECTION)
        log_hdr.pack(fill="x")
        tk.Label(log_hdr, text="LIVE LOG EVENTS", bg=BG_SECTION,
                 fg=ACCENT_BRIGHT, font=("Segoe UI", 9, "bold"),
                 padx=10, pady=6).pack(side="left")
        _btn(log_hdr, "CLEAR", self._clear_log, "#163a6e").pack(
            side="right", padx=8, pady=4)

        inner = tk.Frame(log_outer, bg=BG_PANEL)
        inner.pack(fill="both", expand=True)
        self.log_text = tk.Text(inner, bg=BG_PANEL, fg=TEXT_DIM,
                                 font=("Consolas", 8), relief="flat",
                                 state="disabled", wrap="word",
                                 highlightthickness=0)
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)
        self.log_text.tag_configure("danger",  foreground=TEXT_DANGER)
        self.log_text.tag_configure("magenta", foreground="#cc44ff")
        self.log_text.tag_configure("warn",    foreground=TEXT_WARN)
        self.log_text.tag_configure("ok",      foreground=TEXT_OK)
        self.log_text.tag_configure("blue",    foreground=ACCENT_BRIGHT)
        self.log_text.tag_configure("dim",     foreground=TEXT_DIM)

    # ─────────────────────────────────────────────────────────────────────────
    # Region selection
    # ─────────────────────────────────────────────────────────────────────────

    def _select(self, kind: str):
        self.app.withdraw()
        self.app.update()
        time.sleep(0.2)
        result = select_region()
        self.app.deiconify()
        self.app.lift()

        if result:
            x, y, w, h = result
            if kind == "tribelog":
                self.region_tribelog = result
                self.app.config_data["region_tribelog"] = list(result)
            elif kind == "parasaur":
                self.region_parasaur = result
                self.app.config_data["region_parasaur"] = list(result)
            elif kind == "members":
                self.region_members = result
                self.app.config_data["region_members"] = list(result)
            save_config(self.app.config_data)
            self._refresh_label(kind)
            self._log(f"✅ Region set: {kind} ({w}×{h}px) at ({x},{y})", "ok")
            self.app.set_status(f"Region set ({w}×{h}px)", TEXT_OK)
        else:
            self._log("⚠ Region selection cancelled.", "warn")

    def _refresh_label(self, kind: str):
        mapping = {
            "tribelog": (getattr(self, "lbl_tl", None), self.region_tribelog),
            "parasaur": (getattr(self, "lbl_ps", None), self.region_parasaur),
            "members":  (getattr(self, "lbl_tm", None), self.region_members),
        }
        lbl, region = mapping.get(kind, (None, None))
        if lbl is None:
            return
        if region:
            x, y, w, h = region
            lbl.config(text=f"✅ Region set ({w}×{h}px) at ({x},{y})", fg=TEXT_OK)
        else:
            lbl.config(text="⬜ Not set — click SELECT REGION", fg=TEXT_DIM)

    def _save_toggles(self):
        """Persist enable/disable toggle state to config."""
        self.app.config_data["enable_tribelog"] = self.v_enable_tribelog.get()
        self.app.config_data["enable_parasaur"] = self.v_enable_parasaur.get()
        self.app.config_data["enable_members"]  = self.v_enable_members.get()
        save_config(self.app.config_data)

    # ─────────────────────────────────────────────────────────────────────────
    # Start / Stop
    # ─────────────────────────────────────────────────────────────────────────

    def _start(self):
        if self._running:
            return
        if self.v_enable_tribelog.get() and not self.region_tribelog:
            messagebox.showwarning("No Region",
                "Please SELECT REGION on Tribe Log, or disable tribe log scanning.")
            return
        if self.v_enable_tribelog.get() and not self.app.config_data.get("tl_webhook"):
            messagebox.showwarning("No Webhook",
                "Please set the Tribe Log webhook in Settings, or disable tribe log scanning.")
            return
        self._running = True
        self._last_lines.clear()
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.app.set_status("Active — scanning...", TEXT_OK)
        self._log("▶ Monitoring started.", "ok")
        self._log(f"  Tribe log region: {self.region_tribelog}", "dim")
        if self.region_parasaur:
            self._log(f"  Parasaur region: {self.region_parasaur}", "dim")
        else:
            self._log("  ⚠ No parasaur region set — parasaur detection disabled", "warn")
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()

    def _stop(self):
        self._running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.app.set_status("Stopped", TEXT_DIM)
        self._log("■ Monitoring stopped.", "dim")

    # ─────────────────────────────────────────────────────────────────────────
    # Scan loop
    # ─────────────────────────────────────────────────────────────────────────

    def _scan_loop(self):
        cfg             = self.app.config_data
        tl_interval     = float(cfg.get("tl_interval", 5))
        member_timer    = 30   # fire immediately on first cycle
        MEMBER_INTERVAL = 30
        scan_count      = 0

        while self._running:
            try:
                scan_count += 1

                # ── Tribe Log ─────────────────────────────────────────────
                if self.region_tribelog and self.v_enable_tribelog.get():
                    x, y, w, h = self.region_tribelog
                    is_first = (scan_count == 1)
                    events   = ocr_region_with_colours(x, y, w, h, save_debug=is_first)

                    if is_first:
                        self._log(f"  ✅ Scanning started — region {w}×{h}px", "ok")

                    new_count = 0
                    for ev in events:
                        key = ev.get("key", "")
                        if not key or key in self._last_lines:
                            continue
                        self._last_lines.add(key)
                        if len(self._last_lines) > 500:
                            try: self._last_lines.pop()
                            except KeyError: pass
                        self._dispatch_tribe_log(ev)
                        new_count += 1

                    # show scan summary every 10 scans
                    if scan_count % 10 == 0:
                        self._log(
                            f"  📡 Scan #{scan_count} — {len(events)} events in log"
                            f"{f', {new_count} new' if new_count else ''}", "dim")

                # ── Parasaur ──────────────────────────────────────────────
                if self.region_parasaur and self.v_enable_parasaur.get():
                    x, y, w, h = self.region_parasaur
                    detected = detect_parasaur_alert(x, y, w, h,
                                                     save_debug=(scan_count == 1))
                    if detected:
                        self._ps_alerted = True
                        self._log("🚨 PARASAUR ALERT: Enemy detected near base!", "danger")
                        ps_hook = cfg.get("ps_webhook", "")
                        ps_role = cfg.get("ps_role", "")
                        if ps_hook:
                            send_parasaur_alert(ps_hook, ps_role)
                    else:
                        if self._ps_alerted:
                            self._log("✅ Parasaur alert cleared — enemy gone.", "ok")
                            ps_hook = cfg.get("ps_webhook", "")
                            ps_role = cfg.get("ps_role", "")
                            if ps_hook:
                                send_parasaur_cleared(ps_hook, ps_role)
                        self._ps_alerted = False

                # ── Members ───────────────────────────────────────────────
                if self.region_members and self.v_enable_members.get():
                    member_timer += tl_interval
                    if member_timer >= MEMBER_INTERVAL:
                        member_timer = 0
                        self._log("  👥 Scanning members...", "dim")
                        try:
                            self._scan_members(save_debug=(scan_count == 1))
                        except Exception as me:
                            self._log(f"  ⚠ Member scan error: {me}", "warn")
                else:
                    if scan_count == 1:
                        self._log("  ⚠ No member region set — member tracking disabled", "warn")

            except Exception as e:
                self._log(f"⚠ Scanner error: {e}", "warn")

            time.sleep(tl_interval)

    def _dispatch_tribe_log(self, ev: dict):
        colour = ev["colour"]
        line   = ev["line"]
        label  = ev["label"]
        ping   = ev["ping"]
        self._log(f"{label}  {line}", ui_tag(colour))
        hook = self.app.config_data.get("tl_webhook", "")
        role = self.app.config_data.get("tl_role", "")
        if hook:
            threading.Thread(
                target=send_tribe_log_event,
                args=(hook, role, line, colour, ping, label),
                daemon=True
            ).start()

    def _scan_members(self, save_debug: bool = False):
        cfg        = self.app.config_data
        x, y, w, h = self.region_members
        screenshot = capture_region(x, y, w, h)

        if save_debug:
            from modules.ocr_scanner import save_debug_screenshot
            save_debug_screenshot(screenshot, "members")

        lines   = ocr_member_region(x, y, w, h)
        members = parse_member_lines(lines)
        online  = sum(1 for m in members if m["online"])

        if members != self._last_members:
            self._last_members = members
            summary = ", ".join(
                f"{'🟢' if m['online'] else '🔴'}{m['name']}"
                for m in members) or "No members detected"
            self._log(f"👥 Members: {summary}", "blue")
            hook = cfg.get("tm_webhook", "")
            role = cfg.get("tm_role", "")
            if hook:
                threading.Thread(
                    target=send_member_status,
                    args=(hook, role, online, members, screenshot),
                    daemon=True
                ).start()

    # ─────────────────────────────────────────────────────────────────────────
    def _log(self, msg: str, tag: str = "dim"):
        def _write():
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n", tag)
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.after(0, _write)

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
