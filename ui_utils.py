# ═══════════════════════════════════════════════════════════════
#  UI UTILITIES - Reusable UI helper functions
# ═══════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk
from config import COLORS, FONTS


def make_row(parent, row_idx, label_text, is_input=True, dropdown_opts=None):
    """
    Creates a label + entry or dropdown in a grid parent.
    Returns (var, widget).
    """
    tk.Label(parent, text=label_text, bg=COLORS["bg_white"], font=FONTS["normal"],
             anchor="w", bd=1, relief="solid",
             padx=4).grid(row=row_idx, column=0, sticky="ew", ipady=3)

    if dropdown_opts:
        var = tk.StringVar(value=dropdown_opts[0])
        cb = ttk.Combobox(parent, textvariable=var, values=dropdown_opts,
                          state="readonly", font=FONTS["normal"], width=14)
        cb.grid(row=row_idx, column=1, sticky="ew", padx=2, pady=1)
        return var, cb
    else:
        var = tk.StringVar()
        state = "normal" if is_input else "readonly"
        bg = COLORS["bg_white"]
        e = tk.Entry(parent, textvariable=var, font=FONTS["normal"],
                     width=16, state=state, bg=bg,
                     relief="solid", bd=1)
        e.grid(row=row_idx, column=1, sticky="ew", padx=2, pady=1)
        return var, e


def make_section_header(parent, row_idx, text):
    """Create a section header spanning two columns."""
    lbl = tk.Label(parent, text=text, bg=COLORS["bg_white"],
                   font=FONTS["normal_bold"], fg=COLORS["fg_bold"],
                   anchor="w", padx=4, bd=1, relief="solid")
    lbl.grid(row=row_idx, column=0, columnspan=2, sticky="ew", ipady=4)


def make_dropdown(parent, row_idx, label_text, options, default_idx=0):
    """Create a labeled dropdown combobox."""
    tk.Label(parent, text=label_text, bg=COLORS["bg_white"], font=FONTS["normal"],
             anchor="w", bd=1, relief="solid", padx=4).grid(
                 row=row_idx, column=0, sticky="ew", ipady=3)

    frame = tk.Frame(parent, bg=COLORS["bg_white"])
    frame.grid(row=row_idx, column=1, sticky="ew", padx=2, pady=1)

    var = tk.StringVar(value=options[default_idx])
    cb = ttk.Combobox(frame, textvariable=var, values=options,
                      state="readonly", font=FONTS["normal"], width=14)
    cb.pack(side="left")

    return var, cb, frame


def create_button(parent, text, command, width=14, bg=None, fg=None, font=None):
    """Create a standardized button."""
    if font is None:
        font = FONTS["normal"]
    if bg is None:
        bg = COLORS["bg_white"]
    if fg is None:
        fg = COLORS["fg_normal"]

    return tk.Button(parent, text=text, command=command,
                     font=font, width=width, bg=bg, fg=fg, relief="groove")


def create_labeled_frame(parent, text):
    """Create a labeled frame with standard styling."""
    return ttk.LabelFrame(parent, text=text)


def center_window(window, width, height):
    """Center a window on the screen."""
    window.update_idletasks()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")