# ═══════════════════════════════════════════════════════════════
#  RIGHT PANEL UI - Write/Read controls and bit checkboxes
# ═══════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk
from config import COLORS, FONTS
from register_data import REGISTERS


class RightPanelUI:
    """Right panel with write/read controls and bit toggles."""

    def __init__(self, parent, write_var, read_val_var, addr_var):
        self.parent = parent
        self.write_var = write_var
        self.read_val_var = read_val_var
        self.addr_var = addr_var

        self.frame = tk.Frame(parent, bg=COLORS["bg_main"], width=260)
        self.frame.pack(side="right", fill="y")
        self.frame.pack_propagate(False)

        self.bit_vars = []
        self.bit_cb_wgts = []
        self.bit_lbl_wgts = []

        self._create_write_section()
        self._create_read_section()
        self._create_address_section()
        self._create_bit_section()
        self._create_config_buttons()

    def _create_write_section(self):
        """Create Write Data section."""
        wd_frame = ttk.LabelFrame(self.frame, text="Write Data")
        wd_frame.pack(fill="x", padx=4, pady=2)

        wd_inner = tk.Frame(wd_frame, bg=COLORS["bg_main"])
        wd_inner.pack(fill="x", padx=4, pady=4)

        tk.Label(wd_inner, text="x", bg=COLORS["bg_main"],
                 font=FONTS["normal"]).pack(side="left")

        self.write_entry = tk.Entry(wd_inner, textvariable=self.write_var,
                                     width=8, font=FONTS["courier"],
                                     relief="sunken", bd=2)
        self.write_entry.pack(side="left", padx=4)

        self._btn(wd_frame, "Write Register", lambda: None, 16).pack(pady=2)
        self._btn(wd_frame, "Write All", lambda: None, 16).pack(pady=2)

    def _create_read_section(self):
        """Create Read Data section."""
        rd_frame = ttk.LabelFrame(self.frame, text="Read Data")
        rd_frame.pack(fill="x", padx=4, pady=6)

        rd_inner = tk.Frame(rd_frame, bg=COLORS["bg_main"])
        rd_inner.pack(fill="x", padx=4, pady=4)

        tk.Label(rd_inner, text="x", bg=COLORS["bg_main"],
                 font=FONTS["normal"]).pack(side="left")

        tk.Entry(rd_inner, textvariable=self.read_val_var, width=8,
                 font=FONTS["courier"], relief="sunken", bd=2,
                 state="readonly").pack(side="left", padx=4)

        self._btn(rd_frame, "Read Register", lambda: None, 16).pack(pady=2)
        self._btn(rd_frame, "Read All", lambda: None, 16).pack(pady=2)

    def _create_address_section(self):
        """Create Current Address section."""
        ca_frame = ttk.LabelFrame(self.frame, text="Current Address")
        ca_frame.pack(fill="x", padx=4, pady=4)

        ca_inner = tk.Frame(ca_frame, bg=COLORS["bg_main"])
        ca_inner.pack(fill="x", padx=4, pady=4)

        tk.Label(ca_inner, text="x", bg=COLORS["bg_main"],
                 font=FONTS["normal"]).pack(side="left")

        tk.Entry(ca_inner, textvariable=self.addr_var, width=8,
                 font=FONTS["courier"], relief="sunken", bd=2,
                 state="readonly").pack(side="left", padx=4)

    def _create_bit_section(self):
        """Create bit checkboxes section."""
        rd_bits_frame = ttk.LabelFrame(self.frame, text="Register Data")
        rd_bits_frame.pack(fill="both", expand=True, padx=4, pady=4)

        for i in range(8):
            bit_num = 7 - i
            row = tk.Frame(rd_bits_frame, bg=COLORS["bg_main"])
            row.pack(fill="x", padx=6, pady=1)

            tk.Label(row, text=str(bit_num), bg=COLORS["bg_main"],
                     font=FONTS["normal_bold"], width=2, anchor="e").pack(
                         side="left", padx=(0, 2))

            bv = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(row, variable=bv, bg=COLORS["bg_main"],
                                activebackground=COLORS["bg_main"])
            cb.pack(side="left")

            fl = tk.Label(row, text="", bg=COLORS["bg_main"],
                          font=FONTS["small"], anchor="w", fg=COLORS["fg_label"])
            fl.pack(side="left", padx=4)

            self.bit_vars.append(bv)
            self.bit_cb_wgts.append(cb)
            self.bit_lbl_wgts.append(fl)

    def _create_config_buttons(self):
        """Create Load/Save Config buttons."""
        self._btn(self.frame, "Load Config", lambda: None, 14).pack(pady=(4, 2))
        self._btn(self.frame, "Save Config", lambda: None, 14).pack(pady=2)

    def _btn(self, parent, text, cmd, width=14):
        """Create a button."""
        return tk.Button(parent, text=text, command=cmd,
                         font=FONTS["normal"], width=width, relief="groove")

    def update_bit_panel(self, reg, value):
        """Update bit checkboxes based on register value."""
        self.addr_var.set(str(reg["address"]))
        for i, field in enumerate(reg["fields"]):
            bit_num = field["bit"]
            bit_on = bool((value >> bit_num) & 1)
            self.bit_vars[i].set(bit_on)
            self.bit_lbl_wgts[i].config(text=field["name"])

            if bit_num in reg.get("readonly_bits", []):
                self.bit_cb_wgts[i].config(state="disabled")
            else:
                self.bit_cb_wgts[i].config(state="normal")

    def get_value_from_bits(self, reg):
        """Get value from checkbox states."""
        val = 0
        for i, field in enumerate(reg["fields"]):
            if self.bit_vars[i].get():
                val |= (1 << field["bit"])
        return val