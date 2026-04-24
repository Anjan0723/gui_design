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

        # Define sub-groups
        self.sub_groups = [
            (" configuration reg ", [0x01, 0x02, 0x03, 0x04, 0x05, 0x0B, 0x0C,
                                      0x30, 0x31, 0x32, 0x33, 0x34]),
            (" data registers ", [0x38, 0x39, 0x3A]),
            (" status registers ", [0x20, 0x3B, 0x3F]),
        ]

        # Store original order of registers for restoration
        self.ordered_reg_list = []  # List of (subgroup_name, reg_dict)

        self.frame = ttk.LabelFrame(parent, text="Register Map")
        self.frame.pack(fill="both", expand=True)

        self._create_table()
        self._create_description()

    def _create_table(self):
        """Create the register map Treeview."""
        # Search bar
        search_frame = tk.Frame(self.frame, bg=COLORS["bg_main"])
        search_frame.pack(fill="x", padx=4, pady=(4, 2))

        tk.Label(search_frame, text="Search:", bg=COLORS["bg_main"],
                 font=FONTS["small"]).pack(side="left", padx=(0, 4))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                 width=20, font=FONTS["small"])
        search_entry.pack(side="left", padx=4)

        tk.Button(search_frame, text="Clear", font=FONTS["small"],
                  command=lambda: self.search_var.set(""),
                  width=6).pack(side="left", padx=2)

        self.tree = ttk.Treeview(self.frame, columns=TABLE_COLUMNS,
                                  show="headings", selectmode="browse")

        for col, w in zip(TABLE_COLUMNS, TABLE_COL_WIDTHS):
            self.tree.heading(col, text=col)
            anchor = "w" if col == "Block / Register Name" else "center"
            self.tree.column(col, width=w, anchor=anchor, minwidth=w)

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
        for subgroup_name, addresses in self.sub_groups:
            # Insert sub-group header
            subgrp_iid = f"subgrp_{subgroup_name}"
            self.tree.insert("", "end", iid=subgrp_iid,
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
                    # Store in ordered list for search
                    self.ordered_reg_list.append((subgroup_name, reg))
                    reg_idx += 1

        # Scrollbar
        sb = ttk.Scrollbar(self.frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # Note footer
        self.tree.insert("", "end", iid="note",
                         values=("", "", "", "", "", "*LW=Last Write", "*LR=Last Read"),
                         tags=("note",))

    def _on_search_changed(self, *args):
        """Filter registers based on search term."""
        search_term = self.search_var.get().lower().strip()

        # Delete all existing rows (except headers and footer)
        for item in self.tree.get_children(""):
            self.tree.delete(item)

        # Rebuild tree
        if search_term == "":
            # Show ALL registers in original order
            self._rebuild_tree(None)
        else:
            # Show only matching registers
            self._rebuild_tree(search_term)

    def _rebuild_tree(self, filter_term):
        """Rebuild tree with optional filter. filter_term=None means show all."""
        # Insert main header
        self.tree.insert("", "end", iid="main_hdr",
                         values=("  LDC1101 EVM Registers", "", "", "", "", "", ""),
                         tags=("group",))

        # Track current subgroup to avoid duplicates
        current_subgroup = None

        for idx, (subgroup_name, reg) in enumerate(self.ordered_reg_list):
            # Check if this register matches filter
            if filter_term:
                match = (filter_term in reg["name"].lower() or
                         filter_term in f"0x{reg['address']:02X}".lower() or
                         str(reg["address"]) == filter_term or
                         filter_term in reg.get("description", "").lower())
                if not match:
                    continue

            # Insert subgroup header if new
            if subgroup_name != current_subgroup:
                subgrp_iid = f"subgrp_{subgroup_name}"
                self.tree.insert("", "end", iid=subgrp_iid,
                                 values=(f"  >> {subgroup_name}", "", "", "", "", "", ""),
                                 tags=("subgroup",))
                current_subgroup = subgroup_name

            # Insert register row
            lw = self.reg_lw.get(reg["address"], "0x00")
            lr = self.reg_lr.get(reg["address"], "0x00")
            iid = f"reg_{reg['address']}"
            tag = "even" if idx % 2 == 0 else "odd"

            self.tree.insert("", "end", iid=iid,
                             values=(f"        {reg['name']}",
                                     f"0x{reg['address']:02X}",
                                     f"0x{reg['default']:02X}",
                                     reg["mode"], reg["size"], lw, lr),
                             tags=(tag,))

        # Insert note footer
        self.tree.insert("", "end", iid="note",
                         values=("", "", "", "", "", "*LW=Last Write", "*LR=Last Read"),
                         tags=("note",))

    def update_row(self, reg, lw_val=None, lr_val=None):
        """Update a specific register row with new LW/LR values."""
        iid = f"reg_{reg['address']}"

        # Get current values if not provided
        if lw_val is None:
            lw_val = self.reg_lw.get(reg["address"], "0x00")
        if lr_val is None:
            lr_val = self.reg_lr.get(reg["address"], "0x00")

        try:
            self.tree.item(iid, values=(
                f"        {reg['name']}",
                f"0x{reg['address']:02X}",
                f"0x{reg['default']:02X}",
                reg["mode"],
                reg["size"],
                lw_val,
                lr_val
            ))
        except Exception:
            pass  # Item may not exist during search filtering

    def update_description(self, reg):
        """Update the description panel for a register."""
        if reg and hasattr(self, 'desc_text'):
            desc = reg.get("description", "")
            self.desc_text.config(state="normal")
            self.desc_text.delete("1.0", "end")
            self.desc_text.insert("1.0", desc)
            self.desc_text.config(state="disabled")

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