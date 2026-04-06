# ═══════════════════════════════════════════════════════════════
#  MAIN GUI WINDOW - Assembles all panels
# ═══════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import serial.tools.list_ports

from config import COLORS, FONTS, VERSION, WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE
from config import SIDEBAR_ITEMS, DEFAULT_SIDEBAR, MENU_ITEMS
from register_data import REGISTERS
from gui_register_map import RegisterMapUI
from gui_right_panel import RightPanelUI
from gui_apps_calculator import AppsCalculatorUI


class MainGUI:
    """Main GUI window that assembles all panels."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=COLORS["bg_main"])
        self.root.resizable(True, True)

        # Application state
        self.reg_live_values = {r["address"]: r["default"] for r in REGISTERS}
        self.reg_lw = {r["address"]: "0x00" for r in REGISTERS}
        self.reg_lr = {r["address"]: "0x00" for r in REGISTERS}
        self.selected_reg = [REGISTERS[0]]
        self.write_buffer = {}
        self.temp_bit_state = None

        # UI variables
        self.sim_var = tk.BooleanVar(value=False)
        self.port_var = tk.StringVar()
        self.sel_var = tk.StringVar(value=DEFAULT_SIDEBAR)
        self.write_var = tk.StringVar(value=str(REGISTERS[0]["default"]))
        self.read_val_var = tk.StringVar(value="0")
        self.addr_var = tk.StringVar(value="1")
        self.status_msg = tk.StringVar(value="idle")

        self._setup_style()
        self._create_menu()
        self._create_title_bar()
        self._create_top_bar()
        self._create_main_body()
        self._create_status_bar()
        self._setup_initial_load()

    def _setup_style(self):
        """Configure ttk styles."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="white", foreground="black",
                       fieldbackground="white", rowheight=22, font=FONTS["normal"])
        style.configure("Treeview.Heading", background=COLORS["bg_header"],
                       foreground=COLORS["fg_bold"], font=FONTS["normal_bold"],
                       relief="groove")
        style.map("Treeview", background=[("selected", COLORS["accent_blue"])],
                 foreground=[("selected", "white")])
        style.configure("TLabelframe", background=COLORS["bg_main"])
        style.configure("TLabelframe.Label", background=COLORS["bg_main"],
                       font=FONTS["normal_bold"], foreground=COLORS["fg_bold"])
        style.configure("TButton", font=FONTS["normal"])
        style.configure("TCombobox", font=FONTS["normal"])

    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        for menu_name in MENU_ITEMS:
            m = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label=menu_name, menu=m)
        self.root.config(menu=menubar)

    def _create_title_bar(self):
        """Create custom title bar."""
        title_bar = tk.Frame(self.root, bg=COLORS["bg_dark"], height=48)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        tk.Label(title_bar, text=WINDOW_TITLE,
                 bg=COLORS["bg_dark"], fg=COLORS["fg_white"],
                 font=FONTS["title"]).pack(side="left", padx=20, pady=8)

        tk.Checkbutton(title_bar, text="Simulate Communication",
                      variable=self.sim_var, bg=COLORS["bg_dark"], fg=COLORS["fg_white"],
                      selectcolor=COLORS["bg_dark"], activebackground=COLORS["bg_dark"],
                      font=FONTS["normal"]).pack(side="right", padx=16)

    def _create_top_bar(self):
        """Create COM port and Save/Load bar."""
        top_bar = tk.Frame(self.root, bg=COLORS["bg_top_bar"], pady=5, bd=1, relief="groove")
        top_bar.pack(fill="x", padx=0)

        tk.Label(top_bar, text="COM Port", bg=COLORS["bg_top_bar"],
                 font=FONTS["normal"]).pack(side="left", padx=(12, 4))

        self.port_cb = ttk.Combobox(top_bar, textvariable=self.port_var, width=18,
                                     state="readonly", font=FONTS["normal"])
        self.port_cb.pack(side="left", padx=4)

        def refresh_ports():
            ports = [p.device for p in serial.tools.list_ports.comports()]
            if not ports:
                ports = ["COM3 (Mock)", "COM4 (Mock)"]
                self.conn_lbl.config(text="  NOT CONNECTED  ", bg=COLORS["error"])
            else:
                self.conn_lbl.config(text="  CONNECTED  ", bg=COLORS["success"])
            self.port_cb["values"] = ports
            self.port_var.set(ports[0])

        tk.Button(top_bar, text="Refresh", command=refresh_ports,
                  font=FONTS["normal"], width=8).pack(side="left", padx=2)

        tk.Button(top_bar, text="Save Config",
                  font=FONTS["normal"], command=self.save_config).pack(side="right", padx=8)
        tk.Button(top_bar, text="Load Config",
                  font=FONTS["normal"], command=self.load_config).pack(side="right", padx=4)

    def _create_main_body(self):
        """Create main body with sidebar and content area."""
        self.body = tk.Frame(self.root, bg=COLORS["bg_main"])
        self.body.pack(fill="both", expand=True, padx=4, pady=4)

        # Left sidebar
        left_sb = ttk.LabelFrame(self.body, text="Selection", width=140)
        left_sb.pack(side="left", fill="y", padx=(0, 4), pady=0)
        left_sb.pack_propagate(False)

        for item in SIDEBAR_ITEMS:
            rb = tk.Radiobutton(left_sb, text=item, variable=self.sel_var, value=item,
                               bg=COLORS["bg_main"], font=FONTS["normal"],
                               anchor="w", indicatoron=True,
                               command=self.on_selection_change)
            rb.pack(fill="x", padx=6, pady=2)

        # Content area
        self.content_area = tk.Frame(self.body, bg=COLORS["bg_main"])
        self.content_area.pack(side="left", fill="both", expand=True)

        # Center panel (Register Map)
        self.center = tk.Frame(self.content_area, bg=COLORS["bg_main"])
        self.center.pack(side="left", fill="both", expand=True, padx=(0, 4))

        self.reg_map_ui = RegisterMapUI(self.center, self.reg_lw, self.reg_lr)
        self.tree = self.reg_map_ui.get_tree()

        # Right panel
        self.right_panel = tk.Frame(self.content_area, bg=COLORS["bg_main"], width=260)
        self.right_panel.pack(side="right", fill="y")
        self.right_panel.pack_propagate(False)

        self._create_right_panel_buttons()

        # Apps Calculator (hidden by default)
        self.apps_calc_ui = AppsCalculatorUI(
            self.content_area, self.reg_live_values, self.reg_lw, self.set_status,
            self.refresh_apps_calc_registers
        )

    def _create_right_panel_buttons(self):
        """Create right panel buttons."""
        tk.Button(self.right_panel, text="Tx R to W", font=FONTS["normal"], width=14,
                  command=self.tx_r_to_w).pack(pady=(4, 8))

        # Write Data section
        wd_frame = ttk.LabelFrame(self.right_panel, text="Write Data")
        wd_frame.pack(fill="x", padx=4, pady=2)

        wd_inner = tk.Frame(wd_frame, bg=COLORS["bg_main"])
        wd_inner.pack(fill="x", padx=4, pady=4)

        tk.Label(wd_inner, text="x", bg=COLORS["bg_main"],
                 font=FONTS["normal"]).pack(side="left")

        tk.Entry(wd_inner, textvariable=self.write_var, width=8,
                font=FONTS["courier"], relief="sunken", bd=2).pack(side="left", padx=4)

        tk.Button(wd_frame, text="Write Register", font=FONTS["normal"], width=16,
                  command=self.write_register_cmd).pack(pady=2)
        tk.Button(wd_frame, text="Write All", font=FONTS["normal"], width=16,
                  command=self.write_all_cmd).pack(pady=2)

        # Read Data section
        rd_frame = ttk.LabelFrame(self.right_panel, text="Read Data")
        rd_frame.pack(fill="x", padx=4, pady=6)

        rd_inner = tk.Frame(rd_frame, bg=COLORS["bg_main"])
        rd_inner.pack(fill="x", padx=4, pady=4)

        tk.Label(rd_inner, text="x", bg=COLORS["bg_main"],
                 font=FONTS["normal"]).pack(side="left")

        tk.Entry(rd_inner, textvariable=self.read_val_var, width=8,
                font=FONTS["courier"], relief="sunken", bd=2,
                state="readonly").pack(side="left", padx=4)

        tk.Button(rd_frame, text="Read Register", font=FONTS["normal"], width=16,
                  command=self.read_register_cmd).pack(pady=2)
        tk.Button(rd_frame, text="Read All", font=FONTS["normal"], width=16,
                  command=self.read_all_cmd).pack(pady=2)

        # Address display
        ca_frame = ttk.LabelFrame(self.right_panel, text="Current Address")
        ca_frame.pack(fill="x", padx=4, pady=4)

        ca_inner = tk.Frame(ca_frame, bg=COLORS["bg_main"])
        ca_inner.pack(fill="x", padx=4, pady=4)

        tk.Label(ca_inner, text="x", bg=COLORS["bg_main"],
                 font=FONTS["normal"]).pack(side="left")

        tk.Entry(ca_inner, textvariable=self.addr_var, width=8,
                font=FONTS["courier"], relief="sunken", bd=2,
                state="readonly").pack(side="left", padx=4)

        # Bit checkboxes
        self._create_bit_panel()

        # Config buttons
        tk.Button(self.right_panel, text="Load Config", font=FONTS["normal"], width=14,
                  command=self.load_config).pack(pady=(4, 2))
        tk.Button(self.right_panel, text="Save Config", font=FONTS["normal"], width=14,
                  command=self.save_config).pack(pady=2)

    def _create_bit_panel(self):
        """Create bit checkboxes."""
        rd_bits_frame = ttk.LabelFrame(self.right_panel, text="Register Data")
        rd_bits_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.bit_vars = []
        self.bit_cb_wgts = []
        self.bit_lbl_wgts = []

        for i in range(8):
            bit_num = 7 - i
            row = tk.Frame(rd_bits_frame, bg=COLORS["bg_main"])
            row.pack(fill="x", padx=6, pady=1)

            tk.Label(row, text=str(bit_num), bg=COLORS["bg_main"],
                     font=FONTS["normal_bold"], width=2, anchor="e").pack(side="left", padx=(0, 2))

            bv = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(row, variable=bv, bg=COLORS["bg_main"],
                               activebackground=COLORS["bg_main"],
                               command=self.on_bit_changed)
            cb.pack(side="left")

            fl = tk.Label(row, text="", bg=COLORS["bg_main"],
                         font=FONTS["small"], anchor="w", fg=COLORS["fg_label"])
            fl.pack(side="left", padx=4)

            self.bit_vars.append(bv)
            self.bit_cb_wgts.append(cb)
            self.bit_lbl_wgts.append(fl)

    def _create_status_bar(self):
        """Create status bar."""
        status_bar = tk.Frame(self.root, bg="#333333", height=24)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)

        self.status_lbl = tk.Label(status_bar, text="idle", bg="#333333",
                                  fg="white", font=FONTS["small"], anchor="w")
        self.status_lbl.pack(side="left", padx=8)

        tk.Label(status_bar, text=f"Version: {VERSION}", bg="#333333",
                fg=COLORS["fg_light_gray"], font=FONTS["small"]).pack(side="left", padx=20)

        self.conn_lbl = tk.Label(status_bar, text="  NOT CONNECTED  ",
                                bg=COLORS["error"], fg="white", font=FONTS["small_bold"])
        self.conn_lbl.pack(side="right", padx=4, pady=2)

        tk.Label(status_bar, text="Texas Instruments",
                bg=COLORS["ti_red"], fg="white", font=FONTS["small_bold"]).pack(
                    side="right", padx=2, pady=2)

    def _setup_initial_load(self):
        """Setup initial load and bindings."""
        # Tree selection binding
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Initial selection
        self.root.after(100, self._do_initial_load)

    def _do_initial_load(self):
        """Perform initial load."""
        first_iid = f"reg_{REGISTERS[0]['address']}"
        self.tree.selection_set(first_iid)
        self.tree.focus(first_iid)
        self.tree.see(first_iid)
        self.load_reg_into_ui(REGISTERS[0])

        # Refresh ports
        self.refresh_ports()

        # Bind Apps Calculator (recalculate + sync parameters)
        self.apps_calc_ui.bind_traces(
            self.apps_calc_ui.recalculate,
            self.apps_calc_ui.sync_parameters
        )

    def refresh_ports(self):
        """Refresh COM ports."""
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports:
            ports = ["COM3 (Mock)", "COM4 (Mock)"]
            self.conn_lbl.config(text="  NOT CONNECTED  ", bg=COLORS["error"])
        else:
            self.conn_lbl.config(text="  CONNECTED  ", bg=COLORS["success"])
        self.port_cb["values"] = ports
        self.port_var.set(ports[0])

    def set_status(self, msg):
        """Update status bar."""
        self.status_lbl.config(text=msg)

    def refresh_apps_calc_registers(self):
        """Refresh register map table rows after Apps Calculator update."""
        # Update RP_SET, TC1, TC2, DIG_CONF rows
        for addr in [0x01, 0x02, 0x03, 0x04]:
            for reg in REGISTERS:
                if reg["address"] == addr:
                    self.reg_map_ui.update_row(reg)
                    break

    def on_selection_change(self):
        """Handle sidebar selection change."""
        sel = self.sel_var.get()
        if sel == "Apps Calculator":
            self.center.pack_forget()
            self.right_panel.pack_forget()
            self.apps_calc_ui.get_frame().pack(fill="both", expand=True)
        else:
            self.apps_calc_ui.get_frame().pack_forget()
            self.center.pack(side="left", fill="both", expand=True, padx=(0, 4))
            self.right_panel.pack(side="right", fill="y")

    def on_tree_select(self, event):
        """Handle tree selection."""
        sel = self.tree.selection()
        if not sel:
            return

        iid = sel[0]
        reg_map_ui = self.reg_map_ui
        iid_to_reg = reg_map_ui.iid_to_reg

        if iid not in iid_to_reg:
            return

        new_reg = iid_to_reg[iid]
        if new_reg is self.selected_reg[0]:
            return

        self.save_current_reg_state()
        self.selected_reg[0] = new_reg
        self.load_reg_into_ui(new_reg)

    def load_reg_into_ui(self, reg):
        """Load register into UI."""
        addr = reg["address"]
        wval = self.write_buffer.get(addr)
        if wval is None:
            wval = self.reg_live_values.get(addr, reg.get("default", 0))

        self.addr_var.set(str(addr))
        try:
            lr_int = int(self.reg_lr[addr], 16) & 0xFF
        except (ValueError, TypeError):
            lr_int = 0
        self.read_val_var.set(str(lr_int))
        self.write_var.set(str(wval))

        self.update_bit_panel(reg, wval)
        self.reg_map_ui.update_description(reg)

    def save_current_reg_state(self):
        """Save current register state to buffer."""
        current = self.selected_reg[0]
        if not current:
            return
        addr = current["address"]
        if self.temp_bit_state is not None:
            val = self.temp_bit_state
        else:
            try:
                val = int(self.write_var.get()) & 0xFF
            except ValueError:
                val = self.write_buffer.get(addr, self.reg_live_values.get(addr, current.get("default", 0)))
        self.write_buffer[addr] = val
        self.temp_bit_state = None

    def update_bit_panel(self, reg, value):
        """Update bit panel."""
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
        """Get value from bit checkboxes."""
        val = 0
        for i, field in enumerate(reg["fields"]):
            if self.bit_vars[i].get():
                val |= (1 << field["bit"])
        return val

    def on_bit_changed(self):
        """Handle bit checkbox change."""
        reg = self.selected_reg[0]
        if not reg:
            return
        value = self.get_value_from_bits(reg)
        self.temp_bit_state = value
        self.write_var.set(str(value))

    def write_register_cmd(self):
        """Write register command."""
        reg = self.selected_reg[0]
        if not reg:
            return
        addr = reg["address"]
        if self.temp_bit_state is not None:
            val = self.temp_bit_state
        else:
            try:
                val = int(self.write_var.get() or 0) & 0xFF
            except ValueError:
                val = 0

        self.reg_live_values[addr] = val
        self.reg_lw[addr] = f"0x{val:02X}"
        self.write_buffer[addr] = val
        self.temp_bit_state = None

        self.reg_map_ui.update_row(reg)
        self.update_bit_panel(reg, val)
        self.set_status(f"Written 0x{val:02X} -> {reg['name']} (0x{addr:02X})")

    def write_all_cmd(self):
        """Write all registers."""
        for reg in REGISTERS:
            try:
                val = int(self.write_var.get().strip()) & 0xFF
            except ValueError:
                val = reg["default"]
            self.reg_live_values[reg["address"]] = val
            self.reg_map_ui.update_row(reg, lw_val=val)
        self.set_status("Write All complete.")

    def read_register_cmd(self):
        """Read register command."""
        reg = self.selected_reg[0]
        if not reg:
            return
        addr = reg["address"]
        val = self.reg_live_values.get(addr, reg.get("default", 0))
        self.read_val_var.set(str(val))
        self.reg_lr[addr] = f"0x{val:02X}"
        self.reg_map_ui.update_row(reg)
        self.set_status(f"Read 0x{val:02X} <- {reg['name']} (0x{addr:02X})")

    def read_all_cmd(self):
        """Read all registers."""
        for reg in REGISTERS:
            val = self.reg_live_values[reg["address"]]
            self.reg_map_ui.update_row(reg, lr_val=val)
        reg = self.selected_reg[0]
        val = self.reg_live_values[reg["address"]]
        self.read_val_var.set(str(val))
        self.set_status("Read All complete.")

    def tx_r_to_w(self):
        """Transfer read value to write."""
        self.write_var.set(self.read_val_var.get())
        self.set_status("Transferred Read -> Write.")

    def save_config(self):
        """Save configuration to JSON."""
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Config", "*.json")],
            title="Save Config")
        if not path:
            return
        data = {f"0x{addr:02X}": val for addr, val in self.reg_live_values.items()}
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            self.set_status(f"Config saved -> {path}")
        except IOError as e:
            messagebox.showerror("Error", f"Could not save file: {e}")

    def load_config(self):
        """Load configuration from JSON."""
        path = filedialog.askopenfilename(
            filetypes=[("JSON Config", "*.json")],
            title="Load Config")
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            for addr_str, val in data.items():
                addr = int(addr_str, 16)
                if addr in self.reg_live_values:
                    self.reg_live_values[addr] = val & 0xFF
                    for reg in REGISTERS:
                        if reg["address"] == addr:
                            self.reg_map_ui.update_row(reg)
            self.write_buffer.clear()
            self.load_reg_into_ui(self.selected_reg[0])
            self.set_status(f"Config loaded <- {path}")
        except (IOError, json.JSONDecodeError) as e:
            messagebox.showerror("Error", f"Could not load file: {e}")

    def run(self):
        """Run the main loop."""
        self.root.mainloop()