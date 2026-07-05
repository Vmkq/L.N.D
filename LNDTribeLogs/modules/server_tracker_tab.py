"""
server_tracker_tab.py
Live server population tracker using BattleMetrics free API.
Tracks multiple servers, alerts on population spikes/drops.
"""
import tkinter as tk
from tkinter import messagebox
import threading
import time
import json
import requests
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from main import (BG_DARK, BG_PANEL, BG_SECTION, BORDER, ACCENT, ACCENT_BRIGHT,
                  ACCENT_GLOW, ACCENT_DIM, TEXT_MAIN, TEXT_DIM, TEXT_OK,
                  TEXT_WARN, TEXT_DANGER, save_config)

BM_BASE = "https://api.battlemetrics.com"

# ── helpers ───────────────────────────────────────────────────────────────────
def _card(parent, title):
    outer = tk.Frame(parent, bg=BORDER, bd=0)
    outer.pack(fill="x", padx=14, pady=6)
    hdr = tk.Frame(outer, bg=BG_SECTION); hdr.pack(fill="x")
    tk.Frame(hdr, bg=ACCENT_BRIGHT, width=3).pack(side="left", fill="y")
    tk.Label(hdr, text=title, bg=BG_SECTION, fg=ACCENT_BRIGHT,
             font=("Segoe UI", 9, "bold"), padx=10, pady=7).pack(side="left")
    inner = tk.Frame(outer, bg=BG_PANEL); inner.pack(fill="x")
    return outer, inner

def _btn(parent, text, cmd, bg=None, **kw):
    return tk.Button(parent, text=text, command=cmd,
                     bg=bg or ACCENT_BRIGHT, fg="#ffffff",
                     activebackground=ACCENT_GLOW, activeforeground="#ffffff",
                     relief="flat", font=("Segoe UI", 8, "bold"),
                     cursor="hand2", padx=10, pady=6, **kw)

def _lbl(parent, text):
    tk.Label(parent, text=text, bg=BG_PANEL, fg=TEXT_DIM,
             font=("Segoe UI", 8)).pack(anchor="w", padx=14, pady=(6,1))

def _entry(parent, var, **kw):
    e = tk.Entry(parent, textvariable=var, bg=ACCENT, fg=TEXT_MAIN,
                 insertbackground=ACCENT_BRIGHT, relief="flat",
                 font=("Consolas", 8), highlightthickness=1,
                 highlightbackground=BORDER, highlightcolor=ACCENT_BRIGHT, **kw)
    e.pack(fill="x", padx=14, pady=(0,6))
    return e

def search_server(name: str, api_token: str) -> list:
    """Search BattleMetrics for ARK ASA servers by name."""
    try:
        headers = {"Authorization": f"Bearer {api_token}"} if api_token else {}
        r = requests.get(f"{BM_BASE}/servers", params={
            "filter[game]": "arksa",
            "filter[search]": name,
            "page[size]": 10,
            "sort": "-players"
        }, headers=headers, timeout=8)
        if r.status_code != 200:
            return []
        data = r.json().get("data", [])
        results = []
        for s in data:
            attr = s.get("attributes", {})
            results.append({
                "id":      s["id"],
                "name":    attr.get("name", "Unknown"),
                "players": attr.get("players", 0),
                "maxPlayers": attr.get("maxPlayers", 0),
                "status":  attr.get("status", "unknown"),
                "rank":    attr.get("rank", 0),
            })
        return results
    except Exception:
        return []

def get_server_info(server_id: str, api_token: str) -> dict | None:
    """Fetch live info for a specific server ID."""
    try:
        headers = {"Authorization": f"Bearer {api_token}"} if api_token else {}
        r = requests.get(f"{BM_BASE}/servers/{server_id}",
                         headers=headers, timeout=8)
        if r.status_code != 200:
            return None
        attr = r.json().get("data", {}).get("attributes", {})
        return {
            "name":       attr.get("name", "Unknown"),
            "players":    attr.get("players", 0),
            "maxPlayers": attr.get("maxPlayers", 0),
            "status":     attr.get("status", "unknown"),
            "rank":       attr.get("rank", 0),
            "map":        attr.get("details", {}).get("map", ""),
            "updated":    time.strftime("%H:%M:%S"),
        }
    except Exception:
        return None


class ServerTrackerTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_DARK)
        self.app = app

        # tracked servers: [{id, name, players, maxPlayers, alert_spike,
        #                    alert_low, spike_threshold, low_threshold,
        #                    webhook, role, last_players}]
        self.servers  = list(app.config_data.get("tracked_servers", []))
        self._running = False
        self._thread  = None

        self._build()

    # ── UI ────────────────────────────────────────────────────────────────────
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
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))
        p = self.inner

        # ── API Token ─────────────────────────────────────────────────────
        _, c = _card(p, "BATTLEMETRICS API")
        tk.Label(c, text=(
            "Free API token from battlemetrics.com/developers\n"
            "Sign up free → Account → API Tokens → New Token"),
            bg=BG_PANEL, fg=TEXT_DIM, font=("Segoe UI", 8),
            justify="left").pack(anchor="w", padx=14, pady=(8,2))
        self.v_token = tk.StringVar(
            value=self.app.config_data.get("bm_token", ""))
        _entry(c, self.v_token)
        _btn(c, "SAVE TOKEN", self._save_token).pack(
            padx=14, pady=(0,10), anchor="w")

        # ── Search & Add Server ───────────────────────────────────────────
        _, c = _card(p, "ADD SERVER")
        _lbl(c, "Search by server name (e.g. NA-PVP-SmallTribes-TheIsland9087)")
        search_row = tk.Frame(c, bg=BG_PANEL)
        search_row.pack(fill="x", padx=14, pady=(0,6))
        self.v_search = tk.StringVar()
        tk.Entry(search_row, textvariable=self.v_search,
                 bg=ACCENT, fg=TEXT_MAIN, insertbackground=ACCENT_BRIGHT,
                 relief="flat", font=("Consolas", 8), highlightthickness=1,
                 highlightbackground=BORDER,
                 highlightcolor=ACCENT_BRIGHT).pack(side="left", fill="x",
                                                     expand=True, padx=(0,8))
        _btn(search_row, "🔍 SEARCH", self._search).pack(side="right")

        # Search results listbox
        self._results_frame = tk.Frame(c, bg=BG_PANEL)
        self._results_frame.pack(fill="x", padx=14, pady=(0,10))
        tk.Label(self._results_frame,
                 text="Search results will appear here.",
                 bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(anchor="w")

        # Alert settings for new server
        _lbl(c, "Pop spike alert threshold (ping when players jump by this many)")
        self.v_spike = tk.StringVar(value="5")
        tk.Entry(c, textvariable=self.v_spike, width=6,
                 bg=ACCENT, fg=TEXT_MAIN, insertbackground=ACCENT_BRIGHT,
                 relief="flat", font=("Consolas", 8)).pack(
            anchor="w", padx=14, pady=(0,6))

        _lbl(c, "Low pop alert threshold (ping when players drop below this)")
        self.v_low = tk.StringVar(value="3")
        tk.Entry(c, textvariable=self.v_low, width=6,
                 bg=ACCENT, fg=TEXT_MAIN, insertbackground=ACCENT_BRIGHT,
                 relief="flat", font=("Consolas", 8)).pack(
            anchor="w", padx=14, pady=(0,6))

        _lbl(c, "Discord webhook for this server's alerts")
        self.v_srv_webhook = tk.StringVar()
        _entry(c, self.v_srv_webhook)
        _lbl(c, "Role ID to ping (optional)")
        self.v_srv_role = tk.StringVar()
        _entry(c, self.v_srv_role)

        # ── Tracked Servers ───────────────────────────────────────────────
        _, self._tracked_card = _card(p, "TRACKED SERVERS")

        # Start/Stop row
        ctrl = tk.Frame(self._tracked_card, bg=BG_PANEL)
        ctrl.pack(fill="x", padx=14, pady=6)
        self.btn_start = _btn(ctrl, "▶  START TRACKING", self._start,
                              ACCENT_BRIGHT)
        self.btn_start.pack(side="left", padx=(0,8))
        self.btn_stop = _btn(ctrl, "■  STOP", self._stop, ACCENT_DIM)
        self.btn_stop.pack(side="left")
        self.btn_stop.config(state="disabled")
        _btn(ctrl, "↻ REFRESH NOW", self._refresh_all, ACCENT_DIM).pack(
            side="right")

        self._servers_frame = tk.Frame(self._tracked_card, bg=BG_PANEL)
        self._servers_frame.pack(fill="x", padx=14, pady=(0,10))
        self._refresh_server_list()

        # ── Live Log ──────────────────────────────────────────────────────
        log_outer = tk.Frame(p, bg=BORDER)
        log_outer.pack(fill="x", padx=14, pady=6)
        log_hdr = tk.Frame(log_outer, bg=BG_SECTION); log_hdr.pack(fill="x")
        tk.Frame(log_hdr, bg=ACCENT_BRIGHT, width=3).pack(side="left", fill="y")
        tk.Label(log_hdr, text="ACTIVITY LOG", bg=BG_SECTION,
                 fg=ACCENT_BRIGHT, font=("Segoe UI", 9, "bold"),
                 padx=10, pady=7).pack(side="left")
        _btn(log_hdr, "CLEAR", self._clear_log, ACCENT_DIM).pack(
            side="right", padx=8, pady=4)
        log_inner = tk.Frame(log_outer, bg=BG_PANEL); log_inner.pack(fill="x")
        self.log_text = tk.Text(log_inner, bg=BG_PANEL, fg=TEXT_DIM,
                                 font=("Consolas", 8), relief="flat",
                                 height=8, state="disabled", wrap="word",
                                 highlightthickness=0)
        self.log_text.pack(fill="x", padx=4, pady=4)
        self.log_text.tag_configure("ok",     foreground=TEXT_OK)
        self.log_text.tag_configure("warn",   foreground=TEXT_WARN)
        self.log_text.tag_configure("danger", foreground=TEXT_DANGER)
        self.log_text.tag_configure("blue",   foreground=ACCENT_BRIGHT)
        self.log_text.tag_configure("dim",    foreground=TEXT_DIM)

    # ── Search ────────────────────────────────────────────────────────────────
    def _search(self):
        name = self.v_search.get().strip()
        if not name:
            return
        for w in self._results_frame.winfo_children():
            w.destroy()
        tk.Label(self._results_frame, text="Searching...",
                 bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(anchor="w")
        self.update_idletasks()

        def _do():
            token   = self.v_token.get().strip()
            results = search_server(name, token)
            self.after(0, self._show_results, results)
        threading.Thread(target=_do, daemon=True).start()

    def _show_results(self, results):
        for w in self._results_frame.winfo_children():
            w.destroy()
        if not results:
            tk.Label(self._results_frame,
                     text="No servers found. Check name or API token.",
                     bg=BG_PANEL, fg=TEXT_DANGER,
                     font=("Segoe UI", 8)).pack(anchor="w")
            return
        for r in results:
            row = tk.Frame(self._results_frame, bg=BG_SECTION)
            row.pack(fill="x", pady=2)
            tk.Frame(row, bg=ACCENT_DIM, width=3).pack(side="left", fill="y")
            status_col = TEXT_OK if r["status"] == "online" else TEXT_DANGER
            tk.Label(row, text=f"● {r['name']}",
                     bg=BG_SECTION, fg=status_col,
                     font=("Segoe UI", 8, "bold")).pack(
                side="left", padx=6, pady=4)
            tk.Label(row,
                     text=f"{r['players']}/{r['maxPlayers']} players",
                     bg=BG_SECTION, fg=TEXT_DIM,
                     font=("Segoe UI", 8)).pack(side="left")
            _btn(row, "+ ADD", lambda srv=r: self._add_server(srv),
                 ACCENT_BRIGHT).pack(side="right", padx=4, pady=3)

    def _add_server(self, srv: dict):
        # check not already tracked
        if any(s["id"] == srv["id"] for s in self.servers):
            messagebox.showinfo("Already Added",
                                f"{srv['name']} is already being tracked.")
            return
        try:
            spike = int(self.v_spike.get())
            low   = int(self.v_low.get())
        except ValueError:
            spike, low = 5, 3

        self.servers.append({
            "id":             srv["id"],
            "name":           srv["name"],
            "players":        srv["players"],
            "maxPlayers":     srv["maxPlayers"],
            "spike_threshold": spike,
            "low_threshold":   low,
            "webhook":        self.v_srv_webhook.get().strip(),
            "role":           self.v_srv_role.get().strip(),
            "last_players":   srv["players"],
            "status":         srv["status"],
            "last_updated":   time.strftime("%H:%M:%S"),
        })
        self._save_servers()
        self._refresh_server_list()
        self._log(f"✅ Added server: {srv['name']}", "ok")
        self.app.set_status(f"Server added: {srv['name']}", TEXT_OK)

    # ── Server list UI ────────────────────────────────────────────────────────
    def _refresh_server_list(self):
        for w in self._servers_frame.winfo_children():
            w.destroy()
        if not self.servers:
            tk.Label(self._servers_frame,
                     text="No servers tracked yet. Search and add one above.",
                     bg=BG_PANEL, fg=TEXT_DIM,
                     font=("Segoe UI", 8)).pack(anchor="w", pady=4)
            return
        for i, s in enumerate(self.servers):
            self._build_server_row(i, s)

    def _build_server_row(self, i: int, s: dict):
        outer = tk.Frame(self._servers_frame, bg=BORDER)
        outer.pack(fill="x", pady=3)
        hdr = tk.Frame(outer, bg=BG_SECTION); hdr.pack(fill="x")

        # status colour
        status_col = TEXT_OK if s.get("status") == "online" else TEXT_DANGER
        players    = s.get("players", 0)
        max_p      = s.get("maxPlayers", 0)
        pop_col    = TEXT_DANGER if players >= max_p else (
                     TEXT_WARN if players >= max_p * 0.8 else TEXT_OK)

        tk.Frame(hdr, bg=status_col, width=3).pack(side="left", fill="y")
        tk.Label(hdr, text=f" {s['name']}",
                 bg=BG_SECTION, fg=TEXT_MAIN,
                 font=("Segoe UI", 8, "bold")).pack(side="left", padx=4, pady=5)

        # pop badge
        tk.Label(hdr, text=f"  {players}/{max_p}  ",
                 bg=ACCENT, fg=pop_col,
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)

        tk.Label(hdr, text=f"Updated: {s.get('last_updated','--')}",
                 bg=BG_SECTION, fg=TEXT_DIM,
                 font=("Segoe UI", 7)).pack(side="left", padx=8)

        # remove button
        tk.Button(hdr, text=" ✕ ",
                  command=lambda idx=i: self._remove_server(idx),
                  bg=BG_SECTION, fg=TEXT_DANGER, relief="flat",
                  font=("Segoe UI", 9, "bold"), cursor="hand2",
                  activebackground="#1a0010").pack(side="right", padx=4)

        # detail row
        det = tk.Frame(outer, bg=BG_PANEL); det.pack(fill="x", padx=10, pady=4)
        map_name = s.get("map","")
        tk.Label(det, text=f"{'🗺 ' + map_name if map_name else ''}"
                           f"   Spike alert: +{s['spike_threshold']} players"
                           f"   Low alert: <{s['low_threshold']} players",
                 bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 7)).pack(anchor="w")

    def _remove_server(self, i: int):
        name = self.servers[i]["name"]
        self.servers.pop(i)
        self._save_servers()
        self._refresh_server_list()
        self._log(f"Removed: {name}", "dim")

    # ── Tracking loop ─────────────────────────────────────────────────────────
    def _start(self):
        if self._running:
            return
        if not self.servers:
            messagebox.showwarning("No Servers",
                "Add at least one server to track first.")
            return
        self._running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.app.set_status("Server tracker active", TEXT_OK)
        self._log("▶ Server tracking started — refreshing every 30s", "ok")
        self._thread = threading.Thread(target=self._track_loop, daemon=True)
        self._thread.start()

    def _stop(self):
        self._running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.app.set_status("Server tracker stopped", TEXT_DIM)
        self._log("■ Tracking stopped.", "dim")

    def _track_loop(self):
        # immediate first refresh
        self._refresh_all()
        while self._running:
            time.sleep(30)
            if self._running:
                self._refresh_all()

    def _refresh_all(self):
        token = self.v_token.get().strip()
        for i, s in enumerate(self.servers):
            def _fetch(idx=i, srv=s):
                info = get_server_info(srv["id"], token)
                if info:
                    self.after(0, self._update_server, idx, info)
            threading.Thread(target=_fetch, daemon=True).start()

    def _update_server(self, i: int, info: dict):
        if i >= len(self.servers):
            return
        s    = self.servers[i]
        prev = s.get("last_players", 0)
        curr = info["players"]
        s.update({
            "players":      curr,
            "maxPlayers":   info["maxPlayers"],
            "status":       info["status"],
            "map":          info.get("map", s.get("map", "")),
            "last_updated": info["updated"],
            "last_players": curr,
        })

        # ── Check alerts ──────────────────────────────────────────────────
        spike = s.get("spike_threshold", 5)
        low   = s.get("low_threshold", 3)
        hook  = s.get("webhook", "")
        role  = s.get("role", "")

        if curr - prev >= spike:
            msg = (f"🚨 **Pop spike on {s['name']}!**\n"
                   f"Players jumped from **{prev}** → **{curr}/{s['maxPlayers']}**\n"
                   f"Possible raid incoming!")
            self._log(f"🚨 Pop spike! {prev}→{curr} on {s['name']}", "danger")
            if hook:
                threading.Thread(target=self._send_alert,
                    args=(hook, role, msg, 0xe03050), daemon=True).start()

        elif curr < low and prev >= low:
            msg = (f"📉 **Low pop on {s['name']}**\n"
                   f"Only **{curr}/{s['maxPlayers']}** players online.")
            self._log(f"📉 Low pop: {curr} players on {s['name']}", "warn")
            if hook:
                threading.Thread(target=self._send_alert,
                    args=(hook, role, msg, 0xffaa00), daemon=True).start()
        else:
            self._log(
                f"  📊 {s['name']} — {curr}/{s['maxPlayers']} players", "dim")

        self._save_servers()
        self._refresh_server_list()

    def _send_alert(self, webhook, role, msg, colour):
        content = f"<@&{role}>" if role else ""
        try:
            requests.post(webhook, json={
                "username": "L.N.D Tribe Logs",
                "content": content,
                "embeds": [{
                    "description": msg,
                    "color": colour,
                    "footer": {"text": "L.N.D Tribe Logs • L.N.D"}
                }]
            }, timeout=8)
        except Exception:
            pass

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _save_token(self):
        self.app.config_data["bm_token"] = self.v_token.get().strip()
        save_config(self.app.config_data)
        self.app.set_status("API token saved", TEXT_OK)

    def _save_servers(self):
        self.app.config_data["tracked_servers"] = self.servers
        save_config(self.app.config_data)

    def _log(self, msg: str, tag: str = "dim"):
        ts = time.strftime("%H:%M:%S")
        def _w():
            self.log_text.config(state="normal")
            self.log_text.insert("end", f"[{ts}] {msg}\n", tag)
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.after(0, _w)

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")