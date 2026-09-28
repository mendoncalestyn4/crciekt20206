"""A normal Windows 'choose folder' window.

This only works when the site runs on the user's own PC (the program and
the browser are on the same computer), which is how the stats pack is used.
"""

from __future__ import annotations


def choose_folder(start: str = "") -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None
    try:
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        path = filedialog.askdirectory(initialdir=start or None, title="Choose your Cricket Captain Scorecards folder")
        root.destroy()
    except Exception:
        return None
    return path or None
