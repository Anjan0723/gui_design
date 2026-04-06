# ═══════════════════════════════════════════════════════════════
#  REGISTER MAP UI - Treeview table and description
# ═══════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk
from config import COLORS, FONTS, TABLE_COLUMNS, TABLE_COL_WIDTHS
from register_data import REGISTERS


class RegisterMapUI:
    """Register map table and description panel."""

    def __init__(self, parent, reg_lw, reg_lr):
        self.parent = parent
        self.reg_lw = reg_lw
        self.reg_lr = reg_lr
        self.iid_to_reg = {}

        self.frame = ttk.LabelFrame(parent, text="Register Map")
        self.frame.pack(fill="both", expand=True)

        self._create_table()
        self._create_description()

    def _create_table(self):
        """Create the register map Treeview."""
        self.tree = ttk.Treeview(self.frame, columns=TABLE_COLUMNS,
                                  show="headings", selectmode="browse")

        for col, w in zip(TABLE_COLUMNS, TABLE_COL_WIDTHS):
            self.tree.heading(col, text=col)
            anchor = "w" if col == "Block / Register Name" else "center"
            self.tree.column(col, width=w, anchor=anchor, minwidth=w)

        # Define sub-groups
        sub_groups = [
            (" configuration reg ", [0x01, 0x02, 0x03, 0x04, 0x05, 0x0B, 0x0C,
                                              0x30, 0x31, 0x32, 0x33, 0x34]),
            (" data registers ", [0x38, 0x39, 0x3A]),
            (" status registers ", [0x20, 0x3B, 0x3F]),
        ]

        # Configure tags for styling
        self.tree.tag_configure("group", background=COLORS["bg_group"],
                                font=("Arial", 9, "bold"))
        self.tree.tag_configure("subgroup", background="#E8E8E8",
                                font=("Arial", 9, "bold"))
        self.tree.tag_configure("even", background=COLORS["bg_even"])
        self.tree.tag_configure("odd", background=COLORS["bg_odd"])
        self.tree.tag_configure("note", foreground=COLORS["fg_gray"],
                                font=FONTS["tiny_italic"])

        # Insert main group header
        self.tree.insert("", "end", iid="main_hdr",
                         values=("  LDC1101 EVM Registers", "", "", "", "", "", ""),
                         tags=("group",))

        # Insert sub-groups and registers
        reg_idx = 0
        for subgroup_name, addresses in sub_groups:
            # Insert sub-group header (non-selectable)
            self.tree.insert("", "end", iid=f"subgrp_{subgroup_name}",
                             values=(f"  >> {subgroup_name}", "", "", "", "", "", ""),
                             tags=("subgroup",))

            # Insert registers for this sub-group
            for addr in addresses:
                reg = next((r for r in REGISTERS if r["address"] == addr), None)
                if reg:
                    lw = self.reg_lw.get(reg["address"], "0x00")
                    lr = self.reg_lr.get(reg["address"], "0x00")
                    iid = f"reg_{reg['address']}"
                    tag = "even" if reg_idx % 2 == 0 else "odd"

                    self.tree.insert("", "end", iid=iid,
                                     values=(f"        {reg['name']}",
                                             f"0x{reg['address']:02X}",
                                             f"0x{reg['default']:02X}",
                                             reg["mode"], reg["size"], lw, lr),
                                     tags=(tag,))
                    self.iid_to_reg[iid] = reg
                    reg_idx += 1

        # Scrollbar
        sb = ttk.Scrollbar(self.frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # Note footer
        self.tree.insert("", "end",
                         values=("", "", "", "", "", "*LW=Last Write", "*LR=Last Read"),
                         tags=("note",))

    def _create_description(self):
        """Create register description panel."""
        desc_frame = ttk.LabelFrame(self.parent, text="Register Description")
        desc_frame.pack(fill="x", pady=(4, 0))

        self.desc_text = tk.Text(desc_frame, height=7, font=FONTS["courier"],
                                 bg=COLORS["bg_white"], relief="sunken", bd=1,
                                 wrap="word", state="disabled")

        desc_sb = ttk.Scrollbar(desc_frame, orient="vertical",
                                command=self.desc_text.yview)
        self.desc_text.configure(yscrollcommand=desc_sb.set)
        desc_sb.pack(side="right", fill="y")
        self.desc_text.pack(fill="both", expand=True, padx=4, pady=4)

    def get_tree(self):
        """Return the treeview widget."""
        return self.tree

    def update_row(self, reg, lw_val=None, lr_val=None):
        """Update a row in the table."""
        iid = f"reg_{reg['address']}"
        if lw_val is not None:
            self.reg_lw[reg["address"]] = f"0x{lw_val:02X}"
        if lr_val is not None:
            self.reg_lr[reg["address"]] = f"0x{lr_val:02X}"

        lw = self.reg_lw.get(reg["address"], "0x00")
        lr = self.reg_lr.get(reg["address"], "0x00")

        self.tree.item(iid, values=(
            f"        {reg['name']}",
            f"0x{reg['address']:02X}",
            f"0x{reg['default']:02X}",
            reg["mode"], reg["size"], lw, lr
        ))

    def update_description(self, reg):
        """Update the description text."""
        self.desc_text.config(state="normal")
        self.desc_text.delete("1.0", "end")
        self.desc_text.insert("end", reg["description"])
        self.desc_text.config(state="disabled")