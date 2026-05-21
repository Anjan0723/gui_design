# ═══════════════════════════════════════════════════════════════
#  MAIN GUI WINDOW - Assembles all panels
# ═══════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import serial.tools.list_ports
import threading
import random
import time
from collections import deque

# Matplotlib imports for strip chart
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from config import COLORS, FONTS, VERSION, WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE
from config import SIDEBAR_ITEMS, DEFAULT_SIDEBAR, MENU_ITEMS, logger
from register_data import REGISTERS
from gui_register_map import RegisterMapUI
from gui_right_panel import RightPanelUI
from gui_apps_calculator import AppsCalculatorUI
from gui_lhr import LHRPageUI
from serial_comm import SerialConnection


class MainGUI:
    """Main GUI window that assembles all panels."""

    def __init__(self):
        logger.info("Initializing LDC1101 GUI application")
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=COLORS["bg_main"])
        self.root.resizable(True, True)

        self.reg_live_values = {r["address"]: r["default"] for r in REGISTERS}
        self.reg_lw = {r["address"]: "0x00" for r in REGISTERS}
        self.reg_lr = {r["address"]: "0x00" for r in REGISTERS}
        self.selected_reg = [REGISTERS[0]]
        self.write_buffer = {}
        self.temp_bit_state = None

        # Thread safety for serial communication
        self.serial_lock = threading.Lock()
        
        # Thread-safe mirrored variables
        self._is_active_mode = True
        self._is_sim_mode = False

        # UI variables
        self.sim_var = tk.BooleanVar(value=False)
        self.port_var = tk.StringVar()
        self.sel_var = tk.StringVar(value=DEFAULT_SIDEBAR)
        self.write_var = tk.StringVar(value=str(REGISTERS[0]["default"]))
        self.read_val_var = tk.StringVar(value="0")
        self.addr_var = tk.StringVar(value="1")
        self.status_msg = tk.StringVar(value="idle")

        # Device mode control
        self.device_mode = tk.StringVar(value="ACTIVE")  # ACTIVE, SLEEP, SHUTDOWN

        # Live data polling
        self.live_data_running = False
        self.live_data_thread = None
        self.live_data_frame = None  # Will be created later

        # Graph data buffers (max 50 points)
        self.graph_max_points = 50
        self.rp_data_buffer = deque(maxlen=50)
        self.l_data_buffer = deque(maxlen=50)
        self.graph_canvas = None
        self.graph_running = False
        self.graph_start_stop_btn = None

        self.ser_conn = SerialConnection()
        self.is_connecting = False

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
            real_ports = [p.device for p in serial.tools.list_ports.comports()]
            if real_ports:
                # Sort so COM3 comes before COM4 — Application UART is always the lower port
                real_ports = sorted(real_ports, key=lambda p: int(''.join(filter(str.isdigit, p)) or 0))
                ports = real_ports          # Only real ports if any exist
            else:
                ports = ["COM3 (Mock)", "COM4 (Mock)"]   # Fall back to mock only if nothing real
            self.port_cb["values"] = ports
            if ports:
                self.port_var.set(ports[0])

        tk.Button(top_bar, text="Refresh", command=refresh_ports,
                  font=FONTS["normal"], width=8).pack(side="left", padx=2)

        tk.Button(top_bar, text="Connect", command=self.connect_and_verify,
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

        # LHR Page
        self.lhr_ui = LHRPageUI(
            self.content_area, self.reg_live_values, self.reg_lw, self.set_status,
            self.reg_map_ui, self.ser_conn, self.sim_var
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

        # Device Mode Control panel
        self._create_mode_control_panel()

        # Live Data Readout panel
        self._create_live_data_panel()

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
                                  fg="white", font=FONTS["small"], anchor="w", width=40)
        self.status_lbl.pack(side="left", padx=8)

        tk.Label(status_bar, text=f"Version: {VERSION}", bg="#333333",
                fg=COLORS["fg_light_gray"], font=FONTS["small"]).pack(side="left", padx=20)

        self.conn_lbl = tk.Label(status_bar, text="  NOT CONNECTED  ",
                                bg=COLORS["error"], fg="white", font=FONTS["small_bold"])
        self.conn_lbl.pack(side="right", padx=4, pady=2)


    # ═══════════════════════════════════════════════════════════════
    #  DEVICE MODE CONTROL PANEL
    # ═══════════════════════════════════════════════════════════════

    def _create_mode_control_panel(self):
        """Create Device Mode Control panel."""
        mode_frame = ttk.LabelFrame(self.right_panel, text="Device Mode Control")
        mode_frame.pack(fill="x", padx=4, pady=6)

        # Mode buttons
        btn_frame = tk.Frame(mode_frame, bg=COLORS["bg_main"])
        btn_frame.pack(fill="x", padx=4, pady=4)

        tk.Button(btn_frame, text="Sleep", font=FONTS["normal"], width=8,
                  command=self.set_mode_sleep).pack(side="left", padx=2)
        tk.Button(btn_frame, text="Active", font=FONTS["normal"], width=8,
                  command=self.set_mode_active).pack(side="left", padx=2)
        tk.Button(btn_frame, text="Shutdown", font=FONTS["normal"], width=10,
                  command=self.set_mode_shutdown).pack(side="left", padx=2)

        # Status label
        self.mode_status_lbl = tk.Label(mode_frame, text="ACTIVE",
                                         bg=COLORS["success"], fg="white",
                                         font=FONTS["normal_bold"], width=14, relief="groove")
        self.mode_status_lbl.pack(pady=4)

    def set_mode_sleep(self):
        """Set device to Sleep mode."""
        # Sleep mode: FUNC_MODE = 0x01
        self.reg_live_values[0x0B] = 0x01
        self.reg_lw[0x0B] = "0x01"
        self.reg_map_ui.update_row(self._get_reg_by_addr(0x0B))
        self.device_mode.set("SLEEP")
        self._is_active_mode = False
        self.mode_status_lbl.config(text="SLEEP", bg="#FFA500")  # Orange/yellow
        self.set_status("Device mode: Sleep (0x01 -> START_CONFIG)")
        self.stop_live_data_polling()

    def set_mode_active(self):
        """Set device to Active mode."""
        # Active mode: FUNC_MODE = 0x00
        self.reg_live_values[0x0B] = 0x00
        self.reg_lw[0x0B] = "0x00"
        self.reg_map_ui.update_row(self._get_reg_by_addr(0x0B))
        self.device_mode.set("ACTIVE")
        self._is_active_mode = True
        self.mode_status_lbl.config(text="ACTIVE", bg=COLORS["success"])
        self.set_status("Device mode: Active (0x00 -> START_CONFIG)")
        self.start_live_data_polling()

    def set_mode_shutdown(self):
        """Set device to Shutdown mode."""
        # First set SHUTDOWN_EN = 1 in ALT_CONFIG (0x05)
        alt_config = self.reg_live_values.get(0x05, 0x00)
        alt_config |= 0x02  # Set SHUTDOWN_EN bit (bit 1)
        self.reg_live_values[0x05] = alt_config
        self.reg_lw[0x05] = f"0x{alt_config:02X}"
        self.reg_map_ui.update_row(self._get_reg_by_addr(0x05))

        # Then set FUNC_MODE = 0x02 in START_CONFIG (0x0B)
        self.reg_live_values[0x0B] = 0x02
        self.reg_lw[0x0B] = "0x02"
        self.reg_map_ui.update_row(self._get_reg_by_addr(0x0B))
        self.device_mode.set("SHUTDOWN")
        self._is_active_mode = False
        self.mode_status_lbl.config(text="SHUTDOWN", bg=COLORS["error"])
        self.set_status("Device mode: Shutdown (SHUTDOWN_EN=1, 0x02 -> START_CONFIG)")
        self.stop_live_data_polling()

    def _get_reg_by_addr(self, address):
        """Get register by address."""
        for reg in REGISTERS:
            if reg["address"] == address:
                return reg
        return None

    # ═══════════════════════════════════════════════════════════════
    #  LIVE DATA READOUT PANEL
    # ═══════════════════════════════════════════════════════════════

    def _create_live_data_panel(self):
        """Create Live Data Readout panel."""
        self.live_data_frame = ttk.LabelFrame(self.right_panel, text="Live Data Readout")
        self.live_data_frame.pack(fill="x", padx=4, pady=4)

        # Data ready status
        drdy_frame = tk.Frame(self.live_data_frame, bg=COLORS["bg_main"])
        drdy_frame.pack(fill="x", padx=4, pady=2)
        tk.Label(drdy_frame, text="Status:", bg=COLORS["bg_main"],
                 font=FONTS["normal"]).pack(side="left")
        self.drdy_lbl = tk.Label(drdy_frame, text="Waiting", bg=COLORS["warning"],
                                 fg="white", font=FONTS["normal_bold"], width=12, relief="groove")
        self.drdy_lbl.pack(side="left", padx=4)

        # RP_DATA display
        rp_frame = tk.Frame(self.live_data_frame, bg=COLORS["bg_main"])
        rp_frame.pack(fill="x", padx=4, pady=2)
        tk.Label(rp_frame, text="RP_DATA:", bg=COLORS["bg_main"],
                 font=FONTS["normal"]).pack(side="left")
        self.rp_data_lbl = tk.Label(rp_frame, text="0 / 0x0000", bg=COLORS["bg_white"],
                                    font=FONTS["courier"], width=14, relief="sunken")
        self.rp_data_lbl.pack(side="left", padx=4)

        # L_DATA display
        l_frame = tk.Frame(self.live_data_frame, bg=COLORS["bg_main"])
        l_frame.pack(fill="x", padx=4, pady=2)
        tk.Label(l_frame, text="L_DATA:", bg=COLORS["bg_main"],
                 font=FONTS["normal"]).pack(side="left")
        self.l_data_lbl = tk.Label(l_frame, text="0 / 0x0000", bg=COLORS["bg_white"],
                                   font=FONTS["courier"], width=14, relief="sunken")
        self.l_data_lbl.pack(side="left", padx=4)

        # LHR_DATA display
        lhr_frame = tk.Frame(self.live_data_frame, bg=COLORS["bg_main"])
        lhr_frame.pack(fill="x", padx=4, pady=2)
        tk.Label(lhr_frame, text="LHR_DATA:", bg=COLORS["bg_main"],
                 font=FONTS["normal"]).pack(side="left")
        self.lhr_data_lbl = tk.Label(lhr_frame, text="0 / 0x000000", bg=COLORS["bg_white"],
                                     font=FONTS["courier"], width=14, relief="sunken")
        self.lhr_data_lbl.pack(side="left", padx=4)

        # fSENSOR display (back-calculated)
        fsensor_frame = tk.Frame(self.live_data_frame, bg=COLORS["bg_main"])
        fsensor_frame.pack(fill="x", padx=4, pady=2)
        tk.Label(fsensor_frame, text="fSENSOR:", bg=COLORS["bg_main"],
                 font=FONTS["normal"]).pack(side="left")
        self.fsensor_lbl = tk.Label(fsensor_frame, text="0 Hz", bg=COLORS["bg_white"],
                                    font=FONTS["courier"], width=14, relief="sunken")
        self.fsensor_lbl.pack(side="left", padx=4)

        # Graph panel (Strip Chart)
        self._create_graph_panel()

    # ═══════════════════════════════════════════════════════════════
    #  STRIP CHART GRAPH PANEL
    # ═══════════════════════════════════════════════════════════════

    def _create_graph_panel(self):
        """Create Strip Chart Graph panel."""
        graph_frame = ttk.LabelFrame(self.right_panel, text="RP/L Strip Chart")
        graph_frame.pack(fill="x", padx=4, pady=4)

        # Start/Stop button
        self.graph_start_stop_btn = tk.Button(graph_frame, text="Start Graph",
                                               font=FONTS["normal"], width=14,
                                               command=self.toggle_graph)
        self.graph_start_stop_btn.pack(pady=2)

        # Matplotlib figure
        self.graph_fig = Figure(figsize=(4, 2.5), dpi=100)
        self.graph_ax = self.graph_fig.add_subplot(111)
        self.graph_ax.set_xlabel("Sample", fontsize=8)
        self.graph_ax.set_ylabel("Value", fontsize=8)
        self.graph_ax.set_title("RP/L Data", fontsize=9)
        self.graph_ax.grid(True, alpha=0.3)
        self.graph_ax.set_xlim(0, self.graph_max_points - 1)
        self.graph_ax.set_ylim(0, 65535)

        self.graph_canvas = FigureCanvasTkAgg(self.graph_fig, master=graph_frame)
        self.graph_canvas.get_tk_widget().pack(fill="x", padx=2, pady=2)
        self.graph_canvas.draw()

    def toggle_graph(self):
        """Toggle graph start/stop."""
        if self.graph_running:
            self.graph_running = False
            self.graph_start_stop_btn.config(text="Start Graph")
            self.set_status("Graph stopped")
        else:
            self.graph_running = True
            self.graph_start_stop_btn.config(text="Stop Graph")
            self.set_status("Graph started")
            # Clear buffers
            self.rp_data_buffer.clear()
            self.l_data_buffer.clear()

    def update_graph(self, rp_data, l_data):
        """Update graph with new data points."""
        if not self.graph_running:
            return

        self.rp_data_buffer.append(rp_data)
        self.l_data_buffer.append(l_data)

        # Update plot
        self.graph_ax.clear()
        self.graph_ax.set_xlabel("Sample", fontsize=8)
        self.graph_ax.set_ylabel("Value", fontsize=8)
        self.graph_ax.set_title("RP/L Data", fontsize=9)
        self.graph_ax.grid(True, alpha=0.3)
        self.graph_ax.set_xlim(0, self.graph_max_points - 1)
        self.graph_ax.set_ylim(0, 65535)

        # Convert deques to lists for plotting
        rp_list = list(self.rp_data_buffer)
        l_list = list(self.l_data_buffer)

        # Pad with zeros if needed
        while len(rp_list) < self.graph_max_points:
            rp_list.insert(0, 0)
            l_list.insert(0, 0)

        x_points = list(range(len(rp_list)))

        self.graph_ax.plot(x_points, rp_list, label="RP_DATA", color="blue", linewidth=1)
        self.graph_ax.plot(x_points, l_list, label="L_DATA", color="red", linewidth=1)
        self.graph_ax.legend(loc="upper right", fontsize=7)
        self.graph_canvas.draw()

    def start_live_data_polling(self):
        """Start live data polling thread."""
        if self.live_data_running:
            return
        self.live_data_running = True
        self.live_data_thread = threading.Thread(target=self._live_data_poll_loop, daemon=True)
        self.live_data_thread.start()
        self.set_status("Live data polling started")

    def stop_live_data_polling(self):
        """Stop live data polling thread."""
        self.live_data_running = False
        self.set_status("Live data polling stopped")

    def _live_data_poll_loop(self):
        """Background thread for live data polling."""
        while self.live_data_running:
            self._read_live_data()
            threading.Event().wait(0.5)  # 500ms interval

    def _read_live_data(self):
        """Read live data from device or simulate if not connected."""
        if not getattr(self, '_is_active_mode', True):
            return

        # Determine if we should use real hardware or simulate
        # We simulate if not connected OR if connected to a "Mock" port (no real serial object)
        is_hardware_ready = self.ser_conn.connected and self.ser_conn.serial is not None

        if not is_hardware_ready:
            # Auto-Simulation Mode: generate random values
            status_val = random.randint(0, 0xFF)
            lhr_status_val = random.randint(0, 0xFF)
            rp_data = random.randint(0, 65535)
            l_data = random.randint(0, 65535)
            lhr_data = random.randint(0, 16777215)
        else:
            # Real hardware: parse continuous UART text stream in a non-blocking way
            status_val = self.reg_live_values.get(0x20, 0x00)
            lhr_status_val = self.reg_live_values.get(0x3B, 0x00)
            lhr_data = (self.reg_live_values.get(0x3A, 0) << 16) | (self.reg_live_values.get(0x39, 0) << 8) | self.reg_live_values.get(0x38, 0)
            rp_data = 0
            l_data = 0

            try:
                # Read all lines currently available in the receive buffer
                with self.ser_conn.lock:
                    while self.ser_conn.serial.in_waiting > 0:
                        line = self.ser_conn.serial.readline().decode("ascii", errors="ignore").strip()
                        if not line:
                            continue
                        
                        if "LHR VALUE:" in line:
                            parts = line.split("0x")
                            if len(parts) > 1:
                                try:
                                    lhr_data = int(parts[-1].strip(), 16)
                                except ValueError:
                                    pass
                        elif "LHR_LSB" in line:
                            parts = line.split("0x")
                            if len(parts) > 1:
                                try:
                                    val = int(parts[-1].strip(), 16)
                                    self.reg_live_values[0x38] = val
                                except ValueError:
                                    pass
                        elif "LHR_MID" in line:
                            parts = line.split("0x")
                            if len(parts) > 1:
                                try:
                                    val = int(parts[-1].strip(), 16)
                                    self.reg_live_values[0x39] = val
                                except ValueError:
                                    pass
                        elif "LHR_MSB" in line:
                            parts = line.split("0x")
                            if len(parts) > 1:
                                try:
                                    val = int(parts[-1].strip(), 16)
                                    self.reg_live_values[0x3A] = val
                                except ValueError:
                                    pass
                        elif "Status: 0x" in line:
                            parts = line.split("0x")
                            if len(parts) > 1:
                                try:
                                    status_val = int(parts[-1].strip(), 16)
                                    self.reg_live_values[0x20] = status_val
                                except ValueError:
                                    pass
                        elif "LHR_STATUS: 0x" in line:
                            parts = line.split("0x")
                            if len(parts) > 1:
                                try:
                                    lhr_status_val = int(parts[-1].strip(), 16)
                                    self.reg_live_values[0x3B] = lhr_status_val
                                except ValueError:
                                    pass
                        elif "ERROR:" in line:
                            status_val = 0x80
                            self.reg_live_values[0x20] = status_val
                        elif "SUCCESS:" in line:
                            status_val = 0x00
                            self.reg_live_values[0x20] = status_val
                        elif "Chip ID:" in line:
                            parts = line.split("0x")
                            if len(parts) > 1:
                                try:
                                    val = int(parts[-1].strip(), 16)
                                    self.reg_live_values[0x3F] = val
                                except ValueError:
                                    pass
            except Exception as e:
                logger.error(f"Error parsing live UART data: {e}")

        # Schedule UI update safely on the main thread
        self.root.after(100, lambda: self._update_ui_with_data(status_val, lhr_status_val, rp_data, l_data, lhr_data))

    def _update_ui_with_data(self, status_val, lhr_status_val, rp_data, l_data, lhr_data):
        """Safely update UI with read data."""
        if status_val is None:
            status_val = 0
        if lhr_status_val is None:
            lhr_status_val = 0
            
        # Update UI
        # DRDYB is bit 6, active low (0 = data ready)
        drdyb = (status_val >> 6) & 1
        if drdyb:
            self.drdy_lbl.config(text="Waiting", bg=COLORS["warning"])
        else:
            self.drdy_lbl.config(text="Data Ready", bg=COLORS["success"])

        self.rp_data_lbl.config(text=f"{rp_data} / 0x{rp_data:04X}")
        self.l_data_lbl.config(text=f"{l_data} / 0x{l_data:04X}")
        self.lhr_data_lbl.config(text=f"{lhr_data} / 0x{lhr_data:06X}")

        # Update LHR page if it's the current view
        if hasattr(self, 'lhr_ui'):
            self.lhr_ui.update_from_main_poll(lhr_status_val, lhr_data)

        # Calculate fSENSOR
        if lhr_data > 0:
            # LHR mode: fSENSOR = (fCLKIN * SENSOR_DIV * LHR_DATA) / 2^24
            # We assume fCLKIN is 16MHz (standard for the MSP432 firmware)
            fCLKIN = 16e6
            sdiv_bits = self.reg_live_values.get(0x34, 0x00) & 0x03
            sdiv = 1 << sdiv_bits
            fsensor = (fCLKIN * sdiv * lhr_data) / 16777216.0
        elif l_data > 0:
            # Normal mode
            fCLKIN = 8e6  # 8 MHz (internal clock)
            dig_conf = self.reg_live_values.get(0x04, 0x03)
            resp_time_bits = dig_conf & 0x07
            resp_time_map = {2: 192e-6, 3: 384e-6, 4: 768e-6, 5: 1536e-6, 6: 3072e-6, 7: 6144e-6}
            resp_time = resp_time_map.get(resp_time_bits, 192e-6)
            fsensor = (fCLKIN * resp_time) / (3 * l_data)
        else:
            fsensor = 0

        if fsensor > 0:
            if fsensor >= 1e6:
                self.fsensor_lbl.config(text=f"{fsensor/1e6:.2f} MHz")
            elif fsensor >= 1e3:
                self.fsensor_lbl.config(text=f"{fsensor/1e3:.2f} kHz")
            else:
                self.fsensor_lbl.config(text=f"{fsensor:.0f} Hz")
        else:
            self.fsensor_lbl.config(text="-- Hz")

        # Update graph
        self.update_graph(rp_data, l_data)

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

        # Setup simulation variable tracing
        self._is_sim_mode = self.sim_var.get()
        def on_sim_change(*args):
            self._is_sim_mode = self.sim_var.get()
        self.sim_var.trace_add("write", on_sim_change)

        # Refresh ports
        self.refresh_ports()

        ports_real = [p.device for p in serial.tools.list_ports.comports()]
        if ports_real:
            # Sort so COM3 comes before COM4 — Application UART is always the lower port
            ports_real = sorted(ports_real, key=lambda p: int(''.join(filter(str.isdigit, p)) or 0))
            self.port_cb["values"] = ports_real
            self.port_var.set(ports_real[0])   # COM3 selected by default
        else:
            self.port_cb["values"] = ["COM3 (Mock)", "COM4 (Mock)"]
            self.port_var.set("COM3 (Mock)")

        # Bind Apps Calculator (recalculate + sync parameters)
        self.apps_calc_ui.bind_traces(
            self.apps_calc_ui.recalculate,
            self.apps_calc_ui.sync_parameters
        )

        def _on_csensor_changed(*args):
            raw = self.apps_calc_ui.nt_csensor_var.get()
            display = raw if raw else "390 pF"

            # Update LHR tab display
            self.lhr_ui.update_csensor_display(display)

            # Send to MCU via UART if connected
            from calculations import parse_capacitance
            c_farads, _ = parse_capacitance(raw)
            if c_farads is not None and self.ser_conn and self.ser_conn.connected:
                pf_value = c_farads * 1e12
                def _send_and_confirm():
                    ok = self.ser_conn.send_csensor(pf_value)
                    if ok:
                        self.root.after(0, lambda: self.set_status(
                            f"Csensor updated to {int(pf_value)}pF on MCU ✓"))
                    else:
                        self.root.after(0, lambda: self.set_status(
                            f"Csensor send failed — MCU not responding", color="#ff6666"))
                import threading
                threading.Thread(target=_send_and_confirm, daemon=True).start()

        self.apps_calc_ui.nt_csensor_var.trace_add("write", _on_csensor_changed)

        def _on_lhr_csensor_changed(*args):
            try:
                val = self.lhr_ui.sensor_cap_var.get()
                if val > 0 and self.ser_conn and self.ser_conn.connected:
                    def _send_and_confirm_lhr():
                        ok = self.ser_conn.send_csensor(val)
                        if ok:
                            self.root.after(0, lambda: self.set_status(
                                f"Csensor updated to {int(val)}pF on MCU ✓"))
                        else:
                            self.root.after(0, lambda: self.set_status(
                                f"Csensor send failed — MCU not responding", color="#ff6666"))
                    import threading
                    threading.Thread(target=_send_and_confirm_lhr, daemon=True).start()
            except Exception:
                pass

        self.lhr_ui.sensor_cap_var.trace_add("write", _on_lhr_csensor_changed)

        # Start live data polling (starts in Active mode by default)
        self.start_live_data_polling()

    def refresh_ports(self):
        """Refresh COM ports."""
        real_ports = [p.device for p in serial.tools.list_ports.comports()]
        if real_ports:
            # Sort so COM3 comes before COM4 — Application UART is always the lower port
            real_ports = sorted(real_ports, key=lambda p: int(''.join(filter(str.isdigit, p)) or 0))
            ports = real_ports
        else:
            ports = ["COM3 (Mock)", "COM4 (Mock)"]
            
        self.port_cb["values"] = ports
        if ports:
            self.port_var.set(ports[0])

    def connect_and_verify(self, retry=False):
        """Connect to device and verify CHIP_ID in a background thread."""
        if self.is_connecting:
            self.set_status("Connection attempt already in progress...")
            return

        port = self.port_var.get()
        if not port:
            self.set_status("Please select a COM port.")
            return

        if "(Mock)" in port:
            # No retry needed for mock ports
            self.is_connecting = True
            self.set_status(f"Connecting to {port}...")
            self.conn_lbl.config(text="  CONNECTING...  ", bg=COLORS["warning"])
            threading.Thread(target=self._bg_connect, args=(port,), daemon=True).start()
            return

        # For real ports, allow retry on failure
        self.is_connecting = True
        self.set_status(f"Connecting to {port}...")
        self.conn_lbl.config(text="  CONNECTING...  ", bg=COLORS["warning"])

        # Run connection in background thread to avoid UI freeze
        threading.Thread(target=self._bg_connect_with_retry, args=(port, retry), daemon=True).start()

    def _bg_connect_with_retry(self, port, retry):
        """Background thread for connection with retry logic."""
        max_retries = 3
        retry_delay = 0.5  # seconds

        for attempt in range(max_retries):
            success = False
            chip_id = None

            try:
                # Stop ALL polling before attempting connection
                self.root.after(0, self.stop_live_data_polling)

                if "(Mock)" in port:
                    time.sleep(0.5)
                    chip_id = self.reg_live_values.get(0x3F, 0xD4)
                    success = (chip_id == 0xD4)
                else:
                    self.ser_conn.port = port
                    if self.ser_conn.connect():
                        chip_id = self.ser_conn.read_register(0x3F)
                        success = (chip_id == 0xD4)
                    else:
                        success = False
                        chip_id = None

                if success:
                    break

                # Retry if failed and more attempts left
                if attempt < max_retries - 1:
                    logger.info(f"Connection attempt {attempt + 1} failed, retrying...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Connection failed after {max_retries} attempts")

            except Exception as e:
                logger.error(f"Connection error: {e}", exc_info=True)

        self.root.after(0, lambda: self._post_connect(success, chip_id, port))

    def _bg_connect(self, port):
        """Background thread for connection and verification."""
        success = False
        chip_id = None

        try:
            # Stop ALL polling before attempting connection
            self.stop_live_data_polling()
            if hasattr(self, 'lhr_ui'):
                self.lhr_ui._stop_polling()

            if "(Mock)" in port:
                # Mock mode
                time.sleep(0.5) # Simulate delay
                chip_id = self.reg_live_values.get(0x3F, 0xD4)
                success = (chip_id == 0xD4)
            else:
                # Real device
                self.ser_conn.port = port
                if self.ser_conn.connect():
                    # Read CHIP_ID (0x3F)
                    chip_id = self.ser_conn.read_register(0x3F)
                    success = (chip_id == 0xD4)
                else:
                    success = False
                    chip_id = None
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            success = False
            chip_id = None

        # Update UI safely on main thread
        self.root.after(0, lambda: self._post_connect(success, chip_id, port))

    def _check_connection_health(self):
        """Check if serial connection is still healthy."""
        if not self.ser_conn.connected:
            return False

        if self.ser_conn.serial is None:
            return False

        try:
            # Try a quick read to verify connection
            if self.ser_conn.serial.in_waiting > 0:
                self.ser_conn.serial.read(self.ser_conn.serial.in_waiting)
            return True
        except Exception as e:
            logger.warning(f"Connection health check failed: {e}")
            self._handle_connection_lost()
            return False

    def _handle_connection_lost(self):
        """Handle unexpected connection loss."""
        logger.warning("Connection lost - updating UI")
        self.ser_conn.connected = False
        self.conn_lbl.config(text="  CONNECTION LOST  ", bg=COLORS["error"])
        self.set_status("Connection lost. Please reconnect.", color="#ff6666")
        self.stop_live_data_polling()
        if hasattr(self, 'lhr_ui'):
            self.lhr_ui.update_device_id(None)

    def _post_connect(self, success, chip_id, port):
        """Handle UI updates after connection attempt."""
        self.is_connecting = False

        if success:
            self.conn_lbl.config(text="  LDC1101 detected ✓  ", bg=COLORS["success"])
            self.set_status(f"Connected to {port} - LDC1101 detected")
            if chip_id is not None:
                self.reg_live_values[0x3F] = chip_id
            # push real read value to Device ID label
            if hasattr(self, 'lhr_ui'):
                self.lhr_ui.update_device_id(chip_id)
            self.ser_conn.connected = True
            
            # reset LW* column since MCU booted fresh with LMode() defaults
            if hasattr(self, 'reg_map_ui'):
                self.root.after(100, self.reg_map_ui.reset_lw_column_to_defaults)
                self.root.after(150, lambda: self.set_status("MCU reconnected — register state reset to factory defaults"))
        else:
            # reset Device ID label on failed connect
            if hasattr(self, 'lhr_ui'):
                self.lhr_ui.update_device_id(None)
            if chip_id is not None:
                self.conn_lbl.config(text="  Device not recognized  ", bg=COLORS["error"])
                self.set_status(f"Device not recognized (CHIP_ID=0x{chip_id:02X})")
            else:
                self.conn_lbl.config(text="  NOT CONNECTED  ", bg=COLORS["error"])
                self.set_status(f"Connection failed on {port}")
            self.ser_conn.disconnect()

        # Sync reference and restart polling
        if hasattr(self, 'lhr_ui'):
            self.lhr_ui.ser_conn = self.ser_conn
            self.lhr_ui._sync_config_with_registers()
        self.start_live_data_polling()

    def set_status(self, msg, color="white"):
        """Update status bar."""
        self.status_lbl.config(text=msg, fg=color)

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
            self.lhr_ui.get_frame().pack_forget()
            self.apps_calc_ui.get_frame().pack(fill="both", expand=True)
        elif sel == "LHR":
            self.center.pack_forget()
            self.right_panel.pack_forget()
            self.apps_calc_ui.get_frame().pack_forget()
            self.lhr_ui._sync_config_with_registers()
            self.lhr_ui.get_frame().pack(fill="both", expand=True)
        else:
            self.apps_calc_ui.get_frame().pack_forget()
            self.lhr_ui.get_frame().pack_forget()
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
            raw = self.write_var.get().strip().lstrip("0x").lstrip("0X")
            try:
                val = int(raw, 16)   # Always parse as hex
                val &= 0xFF
            except ValueError:
                self.set_status("Invalid hex value in Write Data field", color="#ff6666")
                return

        # Additional bounds check
        if val < 0 or val > 255:
            messagebox.showerror("Invalid Range", "Value must be 0-255 (0x00-0xFF)")
            return

        self.reg_live_values[addr] = val
        self.reg_lw[addr] = f"0x{val:02X}"
        self.write_buffer[addr] = val
        self.temp_bit_state = None

        if self.ser_conn.connected:
            with self.serial_lock:
                success = self.ser_conn.write_register(addr, val)
                if success:
                    self.set_status(f"Written 0x{val:02X} → reg 0x{addr:02X} on MCU ✓ (readback verified)")
                    logger.info(f"Register {reg['name']} (0x{addr:02X}) written: 0x{val:02X}")
                else:
                    self.set_status(f"Write FAILED or readback mismatch for reg 0x{addr:02X} — SPI may have a timing issue", color="#ff6666")
                    logger.error(f"Failed to write 0x{val:02X} to register 0x{addr:02X}")

        self.reg_map_ui.update_row(reg)
        self.update_bit_panel(reg, val)

    def write_all_cmd(self):
        """Write all registers."""
        input_str = self.write_var.get().strip()
        try:
            if input_str.lower().startswith("0x"):
                val = int(input_str, 16) & 0xFF
            else:
                val = int(input_str) & 0xFF
        except ValueError:
            messagebox.showerror("Invalid Input",
                f"Invalid value: '{input_str}'. Enter 0-255 or 0x00-0xFF.")
            return

        for reg in REGISTERS:
            self.reg_live_values[reg["address"]] = val
            self.reg_map_ui.update_row(reg, lw_val=val)

        logger.info(f"Write All: set all registers to 0x{val:02X}")
        self.set_status(f"Write All complete (0x{val:02X}).")

    def read_register_cmd(self):
        """Read register command."""
        reg = self.selected_reg[0]
        if not reg:
            return
        addr = reg["address"]

        if self.ser_conn.connected:
            with self.serial_lock:
                val = self.ser_conn.read_register(addr)
            if val is not None:
                self.reg_live_values[addr] = val
                self.set_status(f"Read 0x{val:02X} ← reg 0x{addr:02X} from MCU ✓")
                self.read_val_var.set(f"{val:02X}")
                logger.debug(f"Register {reg['name']} (0x{addr:02X}) read: 0x{val:02X}")
            else:
                self.set_status(f"Read failed for reg 0x{addr:02X}", color="#ff6666")
                logger.error(f"Failed to read register 0x{addr:02X}")
                return
        else:
            val = self.reg_live_values.get(addr, reg.get("default", 0))
            self.read_val_var.set(str(val))
            self.set_status(f"Read 0x{val:02X} <- {reg['name']} (0x{addr:02X})")

        self.reg_lr[addr] = f"0x{val:02X}"
        self.reg_map_ui.update_row(reg)

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
        # Add cleanup handler for window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        logger.info("Starting main event loop")
        self.root.mainloop()

    def _on_closing(self):
        """Clean up resources before closing the application."""
        logger.info("Application closing - cleaning up resources")

        # Stop live data polling
        if self.live_data_running:
            self.live_data_running = False
            logger.debug("Stopped live data polling")

        # Stop LHR polling if running
        if hasattr(self, 'lhr_ui'):
            try:
                self.lhr_ui._stop_polling()
                logger.debug("Stopped LHR polling")
            except Exception as e:
                logger.warning(f"Error stopping LHR polling: {e}")

        # Stop graph if running
        if self.graph_running:
            self.graph_running = False
            logger.debug("Stopped graph")

        # Close serial connection
        if self.ser_conn and self.ser_conn.connected:
            self.ser_conn.disconnect()
            logger.info("Serial connection closed")

        # Destroy window
        self.root.destroy()
        logger.info("Application closed")