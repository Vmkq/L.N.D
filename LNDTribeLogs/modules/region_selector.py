"""
region_selector.py
Full-screen darkened overlay using a SINGLE Toplevel window (not a second Tk root).
This avoids the tkinter multi-root issue that caused the region to not be returned.
"""
import tkinter as tk
import threading


def select_region() -> tuple | None:
    """
    Opens a full-screen snip overlay.
    BLOCKS until the user draws a rectangle or presses ESC.
    Returns (x, y, w, h) in screen coordinates, or None if cancelled.
    Must be called from the main thread.
    """
    result = [None]
    done   = threading.Event()

    root = tk.Toplevel()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    root.attributes("-topmost", True)
    root.configure(bg="black")
    root.overrideredirect(True)

    canvas = tk.Canvas(root, bg="black", cursor="crosshair",
                       highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    # instruction label
    tk.Label(root,
             text="  Drag to select region   •   ESC to cancel  ",
             bg="#0d1224", fg="#4a7fff",
             font=("Segoe UI", 12, "bold"),
             pady=8, padx=14).place(relx=0.5, y=20, anchor="n")

    rect  = [None]
    start = [0, 0]

    def on_press(e):
        start[0], start[1] = e.x, e.y
        if rect[0]:
            canvas.delete(rect[0])
        rect[0] = canvas.create_rectangle(
            e.x, e.y, e.x, e.y,
            outline="#2d5be3", width=2, dash=(6, 3), fill="#1a2f6e")

    def on_drag(e):
        if rect[0]:
            canvas.coords(rect[0], start[0], start[1], e.x, e.y)

    def on_release(e):
        x1 = min(start[0], e.x)
        y1 = min(start[1], e.y)
        x2 = max(start[0], e.x)
        y2 = max(start[1], e.y)
        w  = x2 - x1
        h  = y2 - y1
        if w > 10 and h > 10:
            # convert canvas coords to screen coords
            # (Toplevel is fullscreen so canvas coords == screen coords)
            result[0] = (x1, y1, w, h)
        root.destroy()
        done.set()

    def on_esc(_e):
        result[0] = None
        root.destroy()
        done.set()

    canvas.bind("<ButtonPress-1>",   on_press)
    canvas.bind("<B1-Motion>",       on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>",            on_esc)
    root.focus_force()

    # wait until overlay closes
    root.wait_window()
    return result[0]


class RegionSelector:
    """Compatibility wrapper — keeps the old call style working."""
    def select(self) -> tuple | None:
        return select_region()