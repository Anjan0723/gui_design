# ═══════════════════════════════════════════════════════════════
#  MODERN UI STYLES - Reusable Styled Components
# ═══════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk
from config import COLORS, FONTS, SPACING, RADIUS, SHADOWS


def create_modern_button(parent, text, command, bg=None, fg=None, hover_bg=None,
                         font=None, padx=12, pady=6, width=None, icon=""):
    """Create a modern flat button with hover effect."""
    if bg is None:
        bg = COLORS["primary"]
    if fg is None:
        fg = COLORS["text_on_primary"]
    if hover_bg is None:
        hover_bg = COLORS["primary_light"]
    if font is None:
        font = FONTS["normal_bold"]

    btn = tk.Button(
        parent,
        text=f"{icon} {text}".strip(),
        command=command,
        font=font,
        bg=bg,
        fg=fg,
        activebackground=hover_bg,
        activeforeground=fg,
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=padx,
        pady=pady,
        width=width,
        highlightthickness=0
    )

    # Hover effects
    def on_enter(e):
        btn.config(bg=hover_bg)

    def on_leave(e):
        btn.config(bg=bg)

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)

    return btn


def create_card(parent, title=None, icon="", padding=SPACING["md"]):
    """Create a modern card with optional title."""
    # Card container
    card = tk.Frame(parent, bg=COLORS["bg_white"], bd=1, relief="solid",
                   highlightbackground=COLORS["border"], highlightthickness=1)

    # Optional title bar
    if title:
        title_bar = tk.Frame(card, bg=COLORS["bg_section"], height=36)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        # Icon if provided
        if icon:
            tk.Label(title_bar, text=icon, font=("Segoe UI", 12),
                    bg=COLORS["bg_section"], fg=COLORS["primary"]).pack(side="left", padx=(SPACING["sm"], 0))

        tk.Label(title_bar, text=title, font=FONTS["section_title"],
                bg=COLORS["bg_section"], fg=COLORS["text_primary"]).pack(side="left", padx=SPACING["sm"])

        # Content area
        content = tk.Frame(card, bg=COLORS["bg_white"])
    else:
        content = tk.Frame(card, bg=COLORS["bg_white"])

    return card, content


def create_kpi_card(parent, label, value, unit="", color=None):
    """Create a KPI display card (measurement value)."""
    card = tk.Frame(parent, bg=COLORS["bg_white"], bd=1, relief="solid",
                   highlightbackground=COLORS["border"], highlightthickness=1,
                   padx=SPACING["md"], pady=SPACING["md"])

    # Label (small, muted)
    lbl = tk.Label(card, text=label.upper(), font=FONTS["kpi_label"],
                   bg=COLORS["bg_white"], fg=COLORS["text_muted"])
    lbl.pack(anchor="w")

    # Value (large, bold)
    value_color = color if color else COLORS["primary"]
    val = tk.Label(card, text=value, font=FONTS["kpi_value"],
                  bg=COLORS["bg_white"], fg=value_color)
    val.pack(anchor="w", pady=(2, 0))

    # Unit (small, secondary)
    if unit:
        tk.Label(card, text=unit, font=FONTS["kpi_unit"],
                bg=COLORS["bg_white"], fg=COLORS["text_secondary"]).pack(anchor="w")

    return card, val


def create_status_badge(parent, text, status="inactive"):
    """Create a status badge (Connected, Disconnected, Warning, etc.)."""
    status_colors = {
        "connected": (COLORS["success"], COLORS["success_light"]),
        "disconnected": (COLORS["error"], COLORS["error_light"]),
        "warning": (COLORS["warning"], COLORS["warning_light"]),
        "inactive": (COLORS["text_muted"], COLORS["bg_section"]),
    }

    bg_color, fg_color = status_colors.get(status, status_colors["inactive"])

    # Status indicator dot
    indicator = "●" if status == "connected" else "○"
    if status == "warning":
        indicator = "⚠"

    badge = tk.Label(parent, text=f"{indicator} {text}",
                    font=FONTS["small_bold"],
                    bg=bg_color, fg=fg_color,
                    padx=SPACING["sm"], pady=SPACING["xs"],
                    relief="flat", bd=0)

    return badge


def create_status_indicator(parent, label_text, is_active=True, size="md"):
    """Create a status LED indicator with label."""
    frame = tk.Frame(parent, bg=COLORS["bg_main"])

    # LED indicator
    led_size = {"sm": (20, 10), "md": (30, 14), "lg": (40, 16)}
    w, h = led_size.get(size, (30, 14))

    led_color = COLORS["led_green"] if is_active else COLORS["led_red"]
    led = tk.Label(frame, text="  ", bg=led_color, width=w, height=h//8,
                  relief="flat", bd=0)
    led.pack(side="left")

    # Label
    tk.Label(frame, text=label_text, font=FONTS["small"],
            bg=COLORS["bg_main"], fg=COLORS["text_secondary"]).pack(side="left", padx=SPACING["xs"])

    return frame, led


def create_input_field(parent, label, variable, width=14, tooltip=None, unit=""):
    """Create a styled input field with label."""
    row = tk.Frame(parent, bg=COLORS["bg_main"])

    tk.Label(row, text=label, font=FONTS["label"],
            bg=COLORS["bg_main"], fg=COLORS["text_primary"],
            anchor="w").pack(fill="x")

    entry = tk.Entry(row, textvariable=variable,
                    font=FONTS["normal"],
                    bg=COLORS["bg_input"],
                    fg=COLORS["text_primary"],
                    relief="flat",
                    bd=1,
                    highlightbackground=COLORS["border"],
                    highlightthickness=1,
                    width=width)
    entry.pack(fill="x", pady=(2, 0))

    if unit:
        tk.Label(row, text=unit, font=FONTS["small"],
                bg=COLORS["bg_main"], fg=COLORS["text_secondary"]).pack(anchor="w")

    return row, entry


def create_result_card(parent, label, value, unit="", is_valid=True):
    """Create a read-only result card with validation indicator."""
    card = tk.Frame(parent, bg=COLORS["bg_output"], bd=1, relief="flat",
                   highlightbackground=COLORS["success"] if is_valid else COLORS["error"],
                   highlightthickness=1,
                   padx=SPACING["md"], pady=SPACING["sm"])

    # Label and validation indicator row
    header = tk.Frame(card, bg=COLORS["bg_output"])
    header.pack(fill="x")

    tk.Label(header, text=label, font=FONTS["label_bold"],
            bg=COLORS["bg_output"], fg=COLORS["text_secondary"]).pack(side="left")

    # Validation indicator
    valid_icon = "✓" if is_valid else "⚠"
    valid_color = COLORS["success"] if is_valid else COLORS["warning"]
    valid_lbl = tk.Label(header, text=valid_icon, font=FONTS["small_bold"],
                        bg=COLORS["bg_output"], fg=valid_color)
    valid_lbl.pack(side="right")

    # Value
    value_lbl = tk.Label(card, text=value, font=FONTS["value_lg"],
                        bg=COLORS["bg_output"], fg=COLORS["success"] if is_valid else COLORS["error"])
    value_lbl.pack(anchor="w")

    # Unit
    if unit:
        tk.Label(card, text=unit, font=FONTS["small"],
                bg=COLORS["bg_output"], fg=COLORS["text_secondary"]).pack(anchor="w")

    return card, value_lbl, valid_lbl


def create_modern_separator(parent, orient="horizontal", color=None):
    """Create a modern styled separator."""
    sep_color = color if color else COLORS["border"]
    if orient == "horizontal":
        sep = tk.Frame(parent, bg=sep_color, height=1)
    else:
        sep = tk.Frame(parent, bg=sep_color, width=1)
    return sep


def create_toolbar_button(parent, text, command, icon="", tooltip=None):
    """Create a toolbar button (compact style)."""
    btn = tk.Button(
        parent,
        text=f"{icon} {text}".strip(),
        command=command,
        font=FONTS["small"],
        bg=COLORS["bg_section"],
        fg=COLORS["text_secondary"],
        activebackground=COLORS["accent_light"],
        activeforeground=COLORS["primary"],
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=SPACING["sm"],
        pady=SPACING["xs"]
    )

    if tooltip:
        Tooltip(btn, tooltip)

    return btn


class Tooltip:
    """Simple tooltip for widgets."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self._show)
        self.widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        if self.tooltip:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=self.text, bg="#ffffe0",
                        font=FONTS["small"], relief="solid", bd=1, padx=4, pady=2)
        label.pack()

    def _hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


def apply_scrollbar_style():
    """Apply modern scrollbar styling."""
    style = ttk.Style()
    style.theme_use("clam")

    style.configure("Vertical.TScrollbar",
                   gripcount=0,
                   background=COLORS["bg_section"],
                   troughcolor=COLORS["bg_main"],
                   bordercolor=COLORS["border"],
                   lightcolor=COLORS["bg_section"],
                   darkcolor=COLORS["bg_section"],
                   width=12)

    style.map("Vertical.TScrollbar",
             background=[("active", COLORS["primary_light"])])

    style.configure("Horizontal.TScrollbar",
                   gripcount=0,
                   background=COLORS["bg_section"],
                   troughcolor=COLORS["bg_main"],
                   width=12)

    style.map("Horizontal.TScrollbar",
             background=[("active", COLORS["primary_light"])])


def create_modern_combobox(parent, variable, values, width=None, command=None):
    """Create a modern styled combobox."""
    cb = ttk.Combobox(
        parent,
        textvariable=variable,
        values=values,
        state="readonly",
        font=FONTS["normal"],
        width=width
    )

    if command:
        cb.bind("<<ComboboxSelected>>", command)

    return cb


def create_search_field(parent, variable, placeholder="Search...", width=20):
    """Create a modern search field with icon."""
    frame = tk.Frame(parent, bg=COLORS["bg_main"])

    # Search icon
    search_icon = tk.Label(frame, text="🔍", font=("Segoe UI", 10),
                          bg=COLORS["bg_main"], fg=COLORS["text_muted"])
    search_icon.pack(side="left", padx=(0, SPACING["xs"]))

    # Search entry
    entry = tk.Entry(
        frame,
        textvariable=variable,
        font=FONTS["normal"],
        bg=COLORS["bg_input"],
        fg=COLORS["text_primary"],
        relief="flat",
        bd=1,
        highlightbackground=COLORS["border"],
        highlightthickness=1,
        width=width
    )
    entry.pack(side="left", fill="x", expand=True)

    # Placeholder behavior
    def on_focus_in(e):
        if variable.get() == placeholder:
            variable.set("")

    def on_focus_out(e):
        if variable.get() == "":
            variable.set(placeholder)

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)

    return frame, entry


def create_navigation_item(parent, text, icon, command, is_active=False):
    """Create a modern navigation item with icon and indicator."""
    container = tk.Frame(parent, bg=COLORS["bg_white"])
    container.pack(fill="x", padx=4, pady=2)

    # Active indicator bar
    indicator = tk.Frame(container, bg=COLORS["primary"], width=3)
    indicator.pack(side="left", fill="y")
    if not is_active:
        indicator.pack_forget()

    # Navigation button
    btn = tk.Button(
        container,
        text=f"  {icon}  {text}",
        font=FONTS["nav_item"],
        bg=COLORS["accent_light"] if is_active else COLORS["bg_white"],
        fg=COLORS["primary"] if is_active else COLORS["text_secondary"],
        relief="flat",
        anchor="w",
        padx=12,
        pady=10,
        cursor="hand2",
        bd=0,
        activebackground=COLORS["accent_light"],
        activeforeground=COLORS["primary"],
        command=command
    )
    btn.pack(fill="x", expand=True)

    return container, btn, indicator


def create_modern_nav_button(parent, text, icon, command):
    """Create a modern navigation button with icon."""
    btn = tk.Button(
        parent,
        text=f"  {icon}  {text}",
        font=FONTS["nav_item"],
        bg=COLORS["bg_white"],
        fg=COLORS["text_secondary"],
        relief="flat",
        anchor="w",
        padx=12,
        pady=10,
        cursor="hand2",
        bd=0,
        activebackground=COLORS["accent_light"],
        activeforeground=COLORS["primary"],
        command=command
    )
    return btn


def create_measurement_card(parent, label, value, unit="", status="normal"):
    """Create a measurement display card with status indicator."""
    # Status colors
    status_colors = {
        "normal": COLORS["primary"],
        "success": COLORS["success"],
        "warning": COLORS["warning"],
        "error": COLORS["error"],
    }
    status_bg = {
        "normal": COLORS["bg_section"],
        "success": COLORS["success_bg"],
        "warning": COLORS["warning_bg"],
        "error": COLORS["error_bg"],
    }

    color = status_colors.get(status, COLORS["primary"])
    bg = status_bg.get(status, COLORS["bg_section"])

    card = tk.Frame(parent, bg=bg, bd=1, relief="solid",
                   highlightbackground=COLORS["border"], highlightthickness=1)
    card.pack(side="left", fill="both", expand=True, padx=4, pady=2)

    # Status indicator dot
    indicator_dot = "●" if status == "success" else ("⚠" if status == "warning" else "")
    if indicator_dot:
        tk.Label(card, text=indicator_dot, font=("Segoe UI", 8),
                bg=bg, fg=color).pack(anchor="w", padx=8, pady=(6, 0))

    # Label
    tk.Label(card, text=label.upper(), font=FONTS["kpi_label"],
            bg=bg, fg=COLORS["text_muted"]).pack(anchor="w", padx=8, pady=(4, 0))

    # Value
    val = tk.Label(card, text=value, font=FONTS["kpi_value"],
                  bg=bg, fg=color)
    val.pack(anchor="w", padx=8, pady=(0, 2))

    # Unit
    if unit:
        tk.Label(card, text=unit, font=FONTS["kpi_unit"],
                bg=bg, fg=COLORS["text_secondary"]).pack(anchor="w", padx=8, pady=(0, 6))

    return card, val


def create_result_field(parent, label, variable, unit="", is_valid=True, width=16):
    """Create a result field with validation indicator."""
    row = tk.Frame(parent, bg=COLORS["bg_main"])
    row.pack(fill="x", padx=10, pady=4)

    # Label
    tk.Label(row, text=label, font=("Segoe UI", 9),
            bg=COLORS["bg_main"], fg="#333333", anchor="w", width=14).pack(side="left")

    # Entry with result styling
    entry = tk.Entry(row, textvariable=variable,
                    font=FONTS["value"],
                    bg=COLORS["bg_output"],
                    fg=COLORS["success"] if is_valid else COLORS["error"],
                    relief="flat",
                    bd=1,
                    state="readonly",
                    readonlybackground=COLORS["bg_output"],
                    highlightbackground=COLORS["success"] if is_valid else COLORS["error"],
                    highlightthickness=1,
                    width=width)
    entry.pack(side="left", fill="x", expand=True)

    # Unit
    if unit:
        tk.Label(row, text=unit, font=("Segoe UI", 9),
                bg=COLORS["bg_main"], fg="#666666", anchor="w").pack(side="left", padx=4)

    # Validation indicator
    valid_icon = "✓" if is_valid else "⚠"
    valid_color = COLORS["success"] if is_valid else COLORS["warning"]
    valid_lbl = tk.Label(row, text=valid_icon, font=FONTS["small_bold"],
                        bg=COLORS["bg_main"], fg=valid_color)
    valid_lbl.pack(side="left", padx=4)

    return row, entry, valid_lbl


def create_page_header(parent, title, subtitle="", icon=""):
    """Create a modern page header with title and optional subtitle."""
    header = tk.Frame(parent, bg=COLORS["primary"], height=50)
    header.pack(fill="x")
    header.pack_propagate(False)

    # Icon
    if icon:
        tk.Label(header, text=icon, font=("Segoe UI", 16),
                bg=COLORS["primary"], fg="white").pack(side="left", padx=(16, 8), pady=12)

    # Title
    tk.Label(header, text=title, font=FONTS["title"],
            bg=COLORS["primary"], fg="white").pack(side="left", pady=12)

    # Subtitle
    if subtitle:
        tk.Label(header, text=subtitle, font=FONTS["small"],
                bg=COLORS["primary"], fg="white").pack(side="right", padx=16, pady=12)

    return header


def create_compact_toolbar(parent):
    """Create a compact modern toolbar."""
    toolbar = tk.Frame(parent, bg=COLORS["bg_white"],
                      relief="flat", bd=0,
                      highlightbackground=COLORS["border"],
                      highlightthickness=1)
    toolbar.pack(fill="x", padx=0)
    return toolbar


def create_toolbar_separator(parent):
    """Create a vertical separator for toolbar."""
    sep = tk.Frame(parent, bg=COLORS["border"], width=1)
    sep.pack(side="left", padx=12, fill="y", pady=8)
    return sep


def apply_modern_treeview_style():
    """Apply modern styling to Treeview widgets."""
    style = ttk.Style()
    style.theme_use("clam")

    # Configure Treeview colors
    style.configure("Treeview",
                    background="white",
                    foreground="black",
                    fieldbackground="white",
                    font=FONTS["normal"])

    style.configure("Treeview.Heading",
                    background=COLORS["bg_section"],
                    foreground=COLORS["fg_bold"],
                    font=FONTS["normal_bold"],
                    relief="flat")

    style.map("Treeview",
             background=[("selected", COLORS["accent_blue"])],
             foreground=[("selected", "white")])

    # Configure alternating row colors
    style.configure("Treeview",
                    rowcolors=("even", COLORS["bg_white"], "odd", COLORS["bg_odd"]))


def create_modern_label_frame(parent, title, icon=""):
    """Create a modern styled label frame without heavy borders."""
    # Use a regular frame with subtle styling instead of ttk.LabelFrame
    frame = tk.Frame(parent, bg=COLORS["bg_white"], bd=1, relief="solid",
                    highlightbackground=COLORS["border"], highlightthickness=1)

    # Title bar
    if title:
        title_bar = tk.Frame(frame, bg=COLORS["bg_section"], height=32)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        if icon:
            tk.Label(title_bar, text=icon, font=("Segoe UI", 10),
                    bg=COLORS["bg_section"], fg=COLORS["primary"]).pack(side="left", padx=(8, 4))

        tk.Label(title_bar, text=title, font=FONTS["section_title"],
                bg=COLORS["bg_section"], fg=COLORS["text_primary"]).pack(side="left", padx=4)

    # Content area
    content = tk.Frame(frame, bg=COLORS["bg_white"])

    # Pack content below title bar if title exists
    if title:
        content.pack(fill="both", expand=True, padx=8, pady=8)
    else:
        content.pack(fill="both", expand=True, padx=4, pady=4)

    return frame, content


def create_status_row(parent, label, bit_num, is_error=False):
    """Create a status indicator row with bit number, label, and LED."""
    row = tk.Frame(parent, bg=COLORS["bg_main"])
    row.pack(fill="x", padx=8, pady=2)

    # Bit number
    tk.Label(row, text=f"Bit {bit_num}", width=6, font=FONTS["small"],
            bg=COLORS["bg_main"], anchor="w").pack(side="left")

    # LED indicator
    led = tk.Label(row, text="  ", bg=COLORS["led_inactive"],
                  width=3, relief="flat", bd=0)
    led.pack(side="left", padx=4)

    # Label
    tk.Label(row, text=label, width=14, font=FONTS["normal"],
            bg=COLORS["bg_main"], anchor="w").pack(side="left")

    # Description (remaining space)
    desc = tk.Label(row, text="", font=FONTS["small"], fg="gray",
                   bg=COLORS["bg_main"], anchor="w")
    desc.pack(side="left", fill="x", expand=True)

    return row, led, desc


def create_validation_badge(parent, text, is_valid):
    """Create a validation badge with checkmark or warning."""
    bg_color = COLORS["success_bg"] if is_valid else COLORS["warning_bg"]
    fg_color = COLORS["success"] if is_valid else COLORS["warning"]
    icon = "✓" if is_valid else "⚠"

    badge = tk.Label(parent, text=f"{icon} {text}",
                    font=FONTS["small_bold"],
                    bg=bg_color, fg=fg_color,
                    padx=8, pady=4,
                    relief="flat", bd=0)
    return badge


def create_connection_badge(parent, text, is_connected):
    """Create a connection status badge."""
    if is_connected:
        bg_color = COLORS["success"]
        fg_color = "white"
        indicator = "●"
    else:
        bg_color = COLORS["error"]
        fg_color = "white"
        indicator = "○"

    badge = tk.Label(parent, text=f"{indicator} {text}",
                    font=FONTS["small_bold"],
                    bg=bg_color, fg=fg_color,
                    padx=12, pady=4,
                    relief="flat", bd=0)
    return badge