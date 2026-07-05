"""Upload Timer Tab — black/purple theme"""
import tkinter as tk
from tkinter import messagebox
import threading, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from main import (BG_DARK, BG_PANEL, BG_SECTION, BORDER, ACCENT, ACCENT_BRIGHT,
                  ACCENT_GLOW, ACCENT_DIM, TEXT_MAIN, TEXT_DIM, TEXT_OK,
                  TEXT_WARN, TEXT_DANGER)
from modules.discord_sender import _post

RESET_SECONDS = 15 * 60

def send_upload_alert(webhook_url, role_id, msg, colour):
    content = f"<@&{role_id}>" if role_id else ""
    _post(webhook_url, {"username":"L.N.D Tribe Logs","content":content,
        "embeds":[{"title":"⏱️ Upload Timer Alert","description":msg,
                   "color":colour,"footer":{"text":"L.N.D Tribe Logs • L.N.D"}}]})

def _card(parent, title):
    outer = tk.Frame(parent, bg=BORDER, bd=0)
    outer.pack(fill="x", padx=14, pady=6)
    hdr = tk.Frame(outer, bg=BG_SECTION); hdr.pack(fill="x")
    tk.Frame(hdr, bg=ACCENT_BRIGHT, width=3).pack(side="left", fill="y")
    tk.Label(hdr, text=title, bg=BG_SECTION, fg=ACCENT_BRIGHT,
             font=("Segoe UI",9,"bold"), padx=10, pady=7).pack(side="left")
    inner = tk.Frame(outer, bg=BG_PANEL); inner.pack(fill="x")
    return outer, inner

def _btn(p, t, cmd, bg=None):
    return tk.Button(p, text=t, command=cmd,
                     bg=bg or ACCENT_BRIGHT, fg="#ffffff",
                     activebackground=ACCENT_GLOW, activeforeground="#ffffff",
                     relief="flat", font=("Segoe UI",8,"bold"),
                     cursor="hand2", padx=10, pady=6)

class UploadTimerTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_DARK)
        self.app = app
        self._seconds_left = 0
        self._running = False
        self._thread  = None
        self._alerted_5 = False
        self._alerted_2 = False
        self._build()

    def _build(self):
        # Big countdown
        disp = tk.Frame(self, bg=BG_DARK); disp.pack(pady=(30,0))
        tk.Label(disp, text="ARK UPLOAD TIMER", bg=BG_DARK, fg=TEXT_DIM,
                 font=("Segoe UI",9,"bold")).pack()
        self.countdown_lbl = tk.Label(disp, text="15:00", bg=BG_DARK,
                                       fg=ACCENT_BRIGHT,
                                       font=("Segoe UI",58,"bold"))
        self.countdown_lbl.pack(pady=(2,0))
        self.status_lbl = tk.Label(disp, text="Not running", bg=BG_DARK,
                                    fg=TEXT_DIM, font=("Segoe UI",9))
        self.status_lbl.pack(pady=(2,14))

        # Progress bar
        self.prog_canvas = tk.Canvas(self, bg=BG_PANEL, height=8,
                                      highlightthickness=0)
        self.prog_canvas.pack(fill="x", padx=14, pady=(0,18))
        self._prog_bar = self.prog_canvas.create_rectangle(
            0,0,0,8, fill=ACCENT_BRIGHT, outline="")
        self.prog_canvas.bind("<Configure>", self._redraw_progress)

        # Set time card
        _, c = _card(self, "SET CURRENT TIME REMAINING")
        tk.Label(c, text="Enter how much time is left on your upload timer:",
                 bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI",8)).pack(anchor="w", padx=14, pady=(8,4))
        fr = tk.Frame(c, bg=BG_PANEL); fr.pack(padx=14, pady=(0,10), anchor="w")
        self.v_mins = tk.StringVar(value="7")
        self.v_secs = tk.StringVar(value="43")
        tk.Entry(fr, textvariable=self.v_mins, width=5, bg=ACCENT, fg=TEXT_MAIN,
                 insertbackground=ACCENT_BRIGHT, relief="flat",
                 font=("Segoe UI",16,"bold"), justify="center").pack(side="left")
        tk.Label(fr, text=" min  ", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI",11)).pack(side="left")
        tk.Entry(fr, textvariable=self.v_secs, width=5, bg=ACCENT, fg=TEXT_MAIN,
                 insertbackground=ACCENT_BRIGHT, relief="flat",
                 font=("Segoe UI",16,"bold"), justify="center").pack(side="left")
        tk.Label(fr, text=" sec", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Segoe UI",11)).pack(side="left")

        br = tk.Frame(c, bg=BG_PANEL); br.pack(fill="x", padx=14, pady=(0,14))
        _btn(br,"▶  START TIMER", self._start).pack(side="left", padx=(0,8))
        _btn(br,"■  STOP",        self._stop, ACCENT_DIM).pack(side="left", padx=(0,8))
        _btn(br,"↺  RESET TO 15:00", self._manual_reset, ACCENT_DIM).pack(side="left")

        # Alert settings
        _, c = _card(self, "DISCORD ALERTS")
        self.v_wb = tk.StringVar(value=self.app.config_data.get("ut_webhook","Not set — add in Settings"))
        tk.Entry(c, textvariable=self.v_wb, bg=BG_SECTION, fg=TEXT_DIM,
                 relief="flat", font=("Consolas",8),
                 state="readonly").pack(fill="x", padx=14, pady=(8,4))
        self.v_a5 = tk.BooleanVar(value=True)
        self.v_a2 = tk.BooleanVar(value=True)
        self.v_ar = tk.BooleanVar(value=True)
        cbf = tk.Frame(c, bg=BG_PANEL); cbf.pack(anchor="w", padx=14, pady=(4,12))
        for var, lbl in [(self.v_a5,"Ping at 5 minutes remaining"),
                          (self.v_a2,"Ping at 2 minutes remaining"),
                          (self.v_ar,"Ping when timer resets (15:00)")]:
            tk.Checkbutton(cbf, text=lbl, variable=var,
                           bg=BG_PANEL, fg=TEXT_MAIN, selectcolor=ACCENT,
                           activebackground=BG_PANEL, activeforeground=TEXT_MAIN,
                           font=("Segoe UI",8)).pack(anchor="w")

        # History
        _, c = _card(self, "ALERT HISTORY")
        self.history = tk.Text(c, bg=BG_PANEL, fg=TEXT_DIM, font=("Consolas",8),
                                relief="flat", height=6, state="disabled",
                                wrap="word", highlightthickness=0)
        self.history.pack(fill="x", padx=4, pady=4)
        self.history.tag_configure("warn",   foreground=TEXT_WARN)
        self.history.tag_configure("danger", foreground=TEXT_DANGER)
        self.history.tag_configure("ok",     foreground=TEXT_OK)
        self.history.tag_configure("blue",   foreground=ACCENT_BRIGHT)
        self.history.tag_configure("dim",    foreground=TEXT_DIM)
        _btn(c,"CLEAR HISTORY", self._clear_history, ACCENT_DIM).pack(
            padx=14, pady=(0,10), anchor="w")

    def _start(self):
        if self._running: return
        try:
            mins, secs = int(self.v_mins.get()), int(self.v_secs.get())
        except ValueError:
            messagebox.showwarning("Invalid Time","Enter whole numbers."); return
        total = mins*60 + secs
        if total <= 0 or total > RESET_SECONDS:
            messagebox.showwarning("Invalid Time","Time must be 0:01 to 15:00."); return
        self._seconds_left = total
        self._alerted_5 = total <= 300
        self._alerted_2 = total <= 120
        self._running = True
        self._thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._thread.start()
        self._log(f"▶ Timer started at {mins:02d}:{secs:02d}", "ok")
        self.app.set_status("Upload timer running", TEXT_OK)

    def _stop(self):
        self._running = False
        self.status_lbl.config(text="Stopped", fg=TEXT_DIM)
        self.app.set_status("Upload timer stopped", TEXT_DIM)
        self._log("■ Timer stopped.", "dim")

    def _manual_reset(self):
        was = self._running; self._running = False; time.sleep(0.15)
        self._seconds_left = RESET_SECONDS
        self._alerted_5 = self._alerted_2 = False
        self._update_display(RESET_SECONDS)
        if was:
            self._running = True
            self._thread = threading.Thread(target=self._tick_loop, daemon=True)
            self._thread.start()
        self._log("↺ Timer reset to 15:00", "blue")

    def _tick_loop(self):
        while self._running:
            time.sleep(1)
            if not self._running: break
            self._seconds_left -= 1
            if self._seconds_left == 300 and not self._alerted_5:
                self._alerted_5 = True
                if self.v_a5.get(): self._fire("⚠️ **Upload timer hits 0 in 5 minutes!** Log in and grab your uploads!", 0xffaa00)
                self._log("⚠ 5 min warning sent", "warn")
            elif self._seconds_left == 120 and not self._alerted_2:
                self._alerted_2 = True
                if self.v_a2.get(): self._fire("🚨 **Upload timer hits 0 in 2 minutes!** Get your uploads NOW!", 0xff3355)
                self._log("🚨 2 min warning sent", "danger")
            if self._seconds_left <= 0:
                self._seconds_left = RESET_SECONDS
                self._alerted_5 = self._alerted_2 = False
                if self.v_ar.get(): self._fire("🔄 **Upload timer reset to 15:00.** Fresh 15 minutes.", 0x9d00ff)
                self._log("🔄 Timer reset — Discord notified", "blue")
            self.after(0, self._update_display, self._seconds_left)

    def _update_display(self, secs):
        m, s = secs//60, secs%60
        self.countdown_lbl.config(text=f"{m:02d}:{s:02d}")
        if secs <= 120:
            self.countdown_lbl.config(fg=TEXT_DANGER)
            self.status_lbl.config(text="⚠ Urgent!", fg=TEXT_DANGER)
        elif secs <= 300:
            self.countdown_lbl.config(fg=TEXT_WARN)
            self.status_lbl.config(text="Running — 5 min zone", fg=TEXT_WARN)
        else:
            self.countdown_lbl.config(fg=ACCENT_BRIGHT)
            self.status_lbl.config(text="Running ●", fg=TEXT_OK)
        self._redraw_progress()

    def _redraw_progress(self, _e=None):
        w = self.prog_canvas.winfo_width()
        if w < 2: return
        ratio = self._seconds_left / RESET_SECONDS
        fill  = int(w * ratio)
        secs  = self._seconds_left
        col   = TEXT_DANGER if secs <= 120 else (TEXT_WARN if secs <= 300 else ACCENT_BRIGHT)
        self.prog_canvas.coords(self._prog_bar, 0, 0, fill, 8)
        self.prog_canvas.itemconfig(self._prog_bar, fill=col)

    def _fire(self, msg, colour):
        hook = self.app.config_data.get("ut_webhook","")
        role = self.app.config_data.get("ut_role","")
        if hook:
            threading.Thread(target=send_upload_alert,
                args=(hook, role, msg, colour), daemon=True).start()

    def _log(self, msg, tag="dim"):
        ts = time.strftime("%H:%M:%S")
        def _w():
            self.history.config(state="normal")
            self.history.insert("end", f"[{ts}] {msg}\n", tag)
            self.history.see("end")
            self.history.config(state="disabled")
        self.after(0, _w)

    def _clear_history(self):
        self.history.config(state="normal")
        self.history.delete("1.0","end")
        self.history.config(state="disabled")