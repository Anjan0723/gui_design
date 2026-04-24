# ═══════════════════════════════════════════════════════════════
#  LHR PAGE UI - Configuration and Measurement views
# ═══════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import math
from collections import deque
import statistics
import csv
import os

# Matplotlib imports
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from config import COLORS, FONTS, logger
from register_data import REGISTERS

class LHRPageUI:
    """LHR Page UI with Configuration and Measurement sub-views."""

    def __init__(self, parent, reg_live_values, reg_lw, set_status_callback, reg_map_ui=None, ser_conn=None, sim_var=None):
        self.parent = parent
        self.reg_live_values = reg_live_values
        self.reg_lw = reg_lw
        self.set_status = set_status_callback
        self.reg_map_ui = reg_map_ui
        self.ser_conn = ser_conn
        self.sim_var = sim_var
        
        # Thread-safe mirrored variables
        self._is_sim_mode = sim_var.get() if sim_var else False
        if sim_var:
            def sync_sim(*args):
                self._is_sim_mode = sim_var.get()
            sim_var.trace_add("write", sync_sim)

        self.main_frame = tk.Frame(parent, bg=COLORS["bg_main"])
        
        # Shared UI Variables
        self.mode_var = tk.StringVar(value="Sleep") # Sleep or Running
        self.enable_log_var = tk.BooleanVar(value=False)
        self.log_path_var = tk.StringVar(value=os.path.join(os.getcwd(), "lhr_data_log.csv"))
        
        # Measurement parameters
        self.sensor_cap_var = tk.DoubleVar(value=330.0) # pF
        self.clkin_freq_var = tk.DoubleVar(value=16.0)  # MHz
        self.data_to_display_var = tk.StringVar(value="Count")
        self.graph_update_rate_var = tk.StringVar(value="1:1")
        
        # Statistics variables
        self.stat_min = tk.StringVar(value="0")
        self.stat_max = tk.StringVar(value="0")
        self.stat_avg = tk.StringVar(value="0")
        self.stat_std = tk.StringVar(value="0")
        
        # Chart control flags
        self.autoscale_x = tk.BooleanVar(value=True)
        self.autoscale_y = tk.BooleanVar(value=False)
        self.smooth_updates = tk.BooleanVar(value=True)
        self.show_x_scale = tk.BooleanVar(value=True)
        self.show_y_scale = tk.BooleanVar(value=True)
        self.show_palette = tk.BooleanVar(value=True)
        self.show_legend = tk.BooleanVar(value=False)
        self.marker_spacing = tk.StringVar(value="Uniform")
        
        # Polling & Graph Data
        self.is_polling = False
        self.poll_thread = None
        self.data_buffer = deque(maxlen=100)
        self.sample_count = 0
        self.raw_data_history = []
        self.update_counter = 0
        
        # Create sub-view frames
        self.config_frame = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        self.measure_frame = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        
        self._build_config_view()
        self._build_measure_view()
        
        # Show configuration view by default
        self.config_frame.pack(fill="both", expand=True)

    def get_frame(self):
        return self.main_frame

    def _switch_to_measure(self):
        self.config_frame.pack_forget()
        self.measure_frame.pack(fill="both", expand=True)

    def _switch_to_config(self):
        self.measure_frame.pack_forget()
        self.config_frame.pack(fill="both", expand=True)

    def _build_config_view(self):
        """Build the LHR Configuration sub-view."""
        # Top Header
        header = tk.Frame(self.config_frame, bg=COLORS["bg_main"])
        header.pack(fill="x", padx=10, pady=5)
        
        tk.Button(header, text="\u2611 Go to Streaming", font=FONTS["normal_bold"], 
                  command=self._switch_to_measure).pack(side="left")
        
        tk.Label(header, text="LHR Configuration", font=("Arial", 12, "bold"), 
                 fg=COLORS["error"], bg=COLORS["bg_main"]).pack(side="right")
        
        # Mode Toggle & Logging
        ctrl_section = ttk.LabelFrame(self.config_frame, text="Device & Logging")
        ctrl_section.pack(fill="x", padx=10, pady=5)
        
        mode_btn = tk.Checkbutton(ctrl_section, textvariable=self.mode_var, variable=self.mode_var,
                                  onvalue="Running", offvalue="Sleep", indicatoron=False,
                                  font=FONTS["normal_bold"], width=15, selectcolor=COLORS["success"],
                                  command=self._on_mode_toggle)
        mode_btn.pack(side="left", padx=10, pady=5)
        
        tk.Checkbutton(ctrl_section, text="Enable Data Log", variable=self.enable_log_var,
                       bg=COLORS["bg_main"], font=FONTS["normal"]).pack(side="left", padx=10)
        
        tk.Entry(ctrl_section, textvariable=self.log_path_var, width=40, font=FONTS["small"]).pack(side="left", padx=5)
        tk.Button(ctrl_section, text="Browse", command=self._browse_log_file).pack(side="left", padx=2)
        
        # Device Info Row
        info_row = tk.Frame(self.config_frame, bg=COLORS["bg_main"])
        info_row.pack(fill="x", padx=10, pady=5)
        
        tk.Label(info_row, text="Revision ID:", bg=COLORS["bg_main"], font=FONTS["normal"]).pack(side="left")
        self.rid_lbl = tk.Label(info_row, text="0x00", bg="white", width=6, relief="sunken")
        self.rid_lbl.pack(side="left", padx=5)
        
        tk.Label(info_row, text="Device ID:", bg=COLORS["bg_main"], font=FONTS["normal"]).pack(side="left", padx=(20, 0))
        tk.Label(info_row, text="D4", bg="white", width=6, relief="sunken").pack(side="left", padx=5)
        
        # INTB & Optimization
        opt_row = tk.Frame(self.config_frame, bg=COLORS["bg_main"])
        opt_row.pack(fill="x", padx=10, pady=5)
        
        tk.Label(opt_row, text="INTB Disable:", bg=COLORS["bg_main"], font=FONTS["normal"]).pack(side="left")
        self.intb_disable_cb = ttk.Combobox(opt_row, values=["Report Data Ready", "Do not Report Data Ready"], state="readonly", width=25)
        self.intb_disable_cb.pack(side="left", padx=5)
        self.intb_disable_cb.bind("<<ComboboxSelected>>", lambda e: self._write_reg_bit(0x0A, 7, self.intb_disable_cb.current()))
        
        self.optimize_var = tk.BooleanVar()
        tk.Checkbutton(opt_row, text="Optimize LHR measurement", variable=self.optimize_var, 
                       bg=COLORS["bg_main"], font=FONTS["normal"],
                       command=lambda: self._write_reg_bit(0x05, 0, self.optimize_var.get())).pack(side="left", padx=20)
        
        # LHR Configuration Section
        lhr_sec = ttk.LabelFrame(self.config_frame, text="LHR Configuration")
        lhr_sec.pack(fill="both", expand=True, padx=10, pady=5)
        
        grid = tk.Frame(lhr_sec, bg=COLORS["bg_main"])
        grid.pack(padx=20, pady=10)
        
        # Row 0: RCount & Offset
        tk.Label(grid, text="Reference Count:", bg=COLORS["bg_main"]).grid(row=0, column=0, sticky="e", pady=5)
        self.rcount_sp = tk.Spinbox(grid, from_=0, to=65535, width=10, command=self._on_rcount_change)
        self.rcount_sp.grid(row=0, column=1, padx=5, sticky="w")
        self.rcount_sp.bind("<Return>", lambda e: self._on_rcount_change())
        
        tk.Label(grid, text="Offset:", bg=COLORS["bg_main"]).grid(row=0, column=2, sticky="e", padx=(20, 0))
        self.offset_sp = tk.Spinbox(grid, from_=0, to=65535, width=10, command=self._on_offset_change)
        self.offset_sp.grid(row=0, column=3, padx=5, sticky="w")
        self.offset_sp.bind("<Return>", lambda e: self._on_offset_change())
        
        # Row 1: INTB Function & Sensor FMIN
        tk.Label(grid, text="INTB Function:", bg=COLORS["bg_main"]).grid(row=1, column=0, sticky="e", pady=5)
        self.intb_func_cb = ttk.Combobox(grid, state="readonly", width=20, values=[
            "Disabled", "LHR Data Ready", "RP+L Data Ready", "RP Hysteresis", "RP High Threshold", "L Hysteresis", "L High Threshold"
        ])
        self.intb_func_cb.grid(row=1, column=1, padx=5, sticky="w")
        self.intb_func_cb.bind("<<ComboboxSelected>>", self._on_intb_func_change)
        
        tk.Label(grid, text="Sensor FMIN:", bg=COLORS["bg_main"]).grid(row=1, column=2, sticky="e", padx=(20, 0))
        self.fmin_cb = ttk.Combobox(grid, state="readonly", width=15, values=[
            "500 kHz", "533 kHz", "571 kHz", "615 kHz", "667 kHz", "727 kHz", "800 kHz", "889 kHz", 
            "1 MHz", "1.14 MHz", "1.33 MHz", "1.6 MHz", "2 MHz", "2.67 MHz", "4 MHz", "8 MHz"
        ])
        self.fmin_cb.grid(row=1, column=3, padx=5, sticky="w")
        self.fmin_cb.bind("<<ComboboxSelected>>", self._on_fmin_change)
        
        # Row 2: Clock Divider & RP Minimum
        tk.Label(grid, text="Clock Divider:", bg=COLORS["bg_main"]).grid(row=2, column=0, sticky="e", pady=5)
        self.clk_div_cb = ttk.Combobox(grid, state="readonly", width=20, values=["Not Divided", "Divide by 2", "Divide by 4", "Divide by 8"])
        self.clk_div_cb.grid(row=2, column=1, padx=5, sticky="w")
        self.clk_div_cb.bind("<<ComboboxSelected>>", self._on_clk_div_change)
        
        tk.Label(grid, text="RP Minimum:", bg=COLORS["bg_main"]).grid(row=2, column=2, sticky="e", padx=(20, 0))
        self.rp_min_cb = ttk.Combobox(grid, state="readonly", width=15, values=[
            "0.75 kOhms", "1.5 kOhms", "3 kOhms", "6 kOhms", "12 kOhms", "24 kOhms", "48 kOhms", "96 kOhms"
        ])
        self.rp_min_cb.grid(row=2, column=3, padx=5, sticky="w")
        self.rp_min_cb.bind("<<ComboboxSelected>>", self._on_rp_min_change)
        
        self._sync_config_with_registers()

    def _build_measure_view(self):
        """Build the LHR Measurement sub-view."""
        # Top Header
        header = tk.Frame(self.measure_frame, bg=COLORS["bg_main"])
        header.pack(fill="x", padx=10, pady=5)
        
        tk.Button(header, text="\u2611 Go to Configuration", font=FONTS["normal_bold"], 
                  command=self._switch_to_config).pack(side="left")
        
        tk.Label(header, text="LHR Measurement", font=("Arial", 12, "bold"), 
                 fg=COLORS["error"], bg=COLORS["bg_main"]).pack(side="right")
        
        # Mode Toggle & Logging (Synced with config)
        ctrl_section = ttk.LabelFrame(self.measure_frame, text="Device & Logging")
        ctrl_section.pack(fill="x", padx=10, pady=5)
        
        mode_btn = tk.Checkbutton(ctrl_section, textvariable=self.mode_var, variable=self.mode_var,
                                  onvalue="Running", offvalue="Sleep", indicatoron=False,
                                  font=FONTS["normal_bold"], width=15, selectcolor=COLORS["success"],
                                  command=self._on_mode_toggle)
        mode_btn.pack(side="left", padx=10, pady=5)
        
        tk.Checkbutton(ctrl_section, text="Enable Data Log", variable=self.enable_log_var,
                       bg=COLORS["bg_main"], font=FONTS["normal"]).pack(side="left", padx=10)
        
        tk.Entry(ctrl_section, textvariable=self.log_path_var, width=40, font=FONTS["small"]).pack(side="left", padx=5)
        
        # Parameters Row
        param_row = tk.Frame(self.measure_frame, bg=COLORS["bg_main"])
        param_row.pack(fill="x", padx=10, pady=5)
        
        tk.Label(param_row, text="Sensor Capacitor (pF):", bg=COLORS["bg_main"]).pack(side="left")
        tk.Spinbox(param_row, from_=0, to=10000, textvariable=self.sensor_cap_var, width=8).pack(side="left", padx=5)
        
        tk.Label(param_row, text="CLKIN Frequency (MHz):", bg=COLORS["bg_main"]).pack(side="left", padx=(20, 0))
        tk.Spinbox(param_row, from_=0, to=100, textvariable=self.clkin_freq_var, width=8).pack(side="left", padx=5)
        
        tk.Label(param_row, text="Inductance", font=("Arial", 10, "bold"), fg=COLORS["fg_bold"], bg=COLORS["bg_main"]).pack(side="right", padx=10)
        
        # Main Body (Split into Left Status and Right Graph)
        body = tk.Frame(self.measure_frame, bg=COLORS["bg_main"])
        body.pack(fill="both", expand=True, padx=10, pady=5)
        
        left_panel = tk.Frame(body, bg=COLORS["bg_main"], width=200)
        left_panel.pack(side="left", fill="both", padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Status LEDs
        status_sec = ttk.LabelFrame(left_panel, text="Status")
        status_sec.pack(fill="x", pady=(0, 10))
        
        self.leds = {}
        for bit_name in ["ERR_ZC", "LHR_DRDY", "ERR_OR", "ERR_UR", "ERR_OF"]:
            row = tk.Frame(status_sec, bg=COLORS["bg_main"])
            row.pack(fill="x", padx=5, pady=2)
            led = tk.Canvas(row, width=40, height=12, bg="gray", highlightthickness=0)
            led.pack(side="left")
            self.leds[bit_name] = led
            tk.Label(row, text=bit_name, bg=COLORS["bg_main"], font=FONTS["small"]).pack(side="left", padx=5)
            
        # Statistics
        stat_sec = ttk.LabelFrame(left_panel, text="Statistics")
        stat_sec.pack(fill="both", expand=True)
        
        for label, var in [("Minimum", self.stat_min), ("Maximum", self.stat_max), 
                          ("Average", self.stat_avg), ("Std.dev", self.stat_std)]:
            row = tk.Frame(stat_sec, bg=COLORS["bg_main"])
            row.pack(fill="x", padx=5, pady=5)
            tk.Label(row, text=f"{label}:", bg=COLORS["bg_main"], font=FONTS["normal"]).pack(anchor="w")
            val_frame = tk.Frame(row, bg="white", relief="sunken", bd=1)
            val_frame.pack(fill="x")
            tk.Label(val_frame, textvariable=var, bg="white", font=FONTS["courier"]).pack(side="left", padx=2)
            tk.Label(val_frame, text="Counts", bg="white", fg="blue", font=FONTS["tiny_italic"]).pack(side="right", padx=2)
            
        # Right Graph Panel
        right_panel = tk.Frame(body, bg=COLORS["bg_main"])
        right_panel.pack(side="right", fill="both", expand=True)
        
        graph_ctrl = tk.Frame(right_panel, bg=COLORS["bg_main"])
        graph_ctrl.pack(fill="x")
        
        tk.Label(graph_ctrl, text="Data to display:", bg=COLORS["bg_main"]).pack(side="left")
        self.display_om = ttk.OptionMenu(graph_ctrl, self.data_to_display_var, "Frequency (MHz)", "Frequency (MHz)", "Count")
        self.display_om.pack(side="left", padx=5)
        self.data_to_display_var.trace_add("write", self._on_display_type_change)
        
        tk.Label(graph_ctrl, text="Graph update rate:", bg=COLORS["bg_main"]).pack(side="left", padx=(20, 0))
        self.rate_om = ttk.OptionMenu(graph_ctrl, self.graph_update_rate_var, "1:10", "1:1", "1:2", "1:5", "1:10", "1:20", "1:50")
        self.rate_om.pack(side="left", padx=5)
        
        # Matplotlib Strip Chart
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Samples")
        self.ax.set_ylabel("Count")
        self.ax.grid(True, alpha=0.3)
        self.ax.set_ylim(0, 1)
        self.ax.set_xlim(0, 100)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_panel)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvas.get_tk_widget().bind("<Button-3>", self._show_context_menu)

        # Hidden standard toolbar to reuse its functions
        self.nav_toolbar = NavigationToolbar2Tk(self.canvas, right_panel)
        self.nav_toolbar.pack_forget()

        # Custom small toolbar buttons
        self.btn_frame = tk.Frame(right_panel, bg=COLORS["bg_main"])
        self.btn_frame.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-30)
        
        # Tooltip for coordinates (simple version)
        self.coord_label = tk.Label(right_panel, text="", font=FONTS["small"], bg=COLORS["bg_main"], fg="white")
        self.coord_label.place(relx=0.05, rely=0.95, anchor="sw")

        btn_style = {"width": 3, "font": ("Arial", 10), "bg": "#444444", "fg": "white", "relief": "raised", "bd": 1}
        self.crosshair_btn = tk.Button(self.btn_frame, text="✛", command=self._toggle_crosshair, **btn_style)
        self.crosshair_btn.pack(side="left", padx=1)
        self.zoom_btn = tk.Button(self.btn_frame, text="⊕", command=self._show_zoom_popup, **btn_style)
        self.zoom_btn.pack(side="left", padx=1)
        self.pan_btn = tk.Button(self.btn_frame, text="✥", command=self.nav_toolbar.pan, **btn_style)
        self.pan_btn.pack(side="left", padx=1)
        
        self.crosshair_active = False
        self.cid_motion = None

    # ═══════════════════════════════════════════════════════════════
    #  LOGIC & EVENTS
    # ═══════════════════════════════════════════════════════════════

    def _sync_config_with_registers(self):
        """Sync UI controls with current register values."""
        # FUNC_MODE
        mode = self.reg_live_values.get(0x0B, 0x01) & 0x03
        
        # Only allow "Running" if actually connected or in sim mode
        is_connected = self.ser_conn and self.ser_conn.connected
        is_sim = not is_connected
        if is_connected or is_sim:
            self.mode_var.set("Running" if mode == 0 else "Sleep")
        else:
            self.mode_var.set("Sleep")   # always Sleep when disconnected
        
        # RID
        rid = self.reg_live_values.get(0x3E, 0x00)
        self.rid_lbl.config(text=f"0x{rid:02X}")
        
        # INTB Disable (0x0A bit 7)
        intb2sdo = (self.reg_live_values.get(0x0A, 0x00) >> 7) & 1
        self.intb_disable_cb.current(intb2sdo)
        
        # Optimize (0x05 bit 0)
        self.optimize_var.set(bool(self.reg_live_values.get(0x05, 0x00) & 1))
        
        # RCount (0x30/0x31)
        rcount = (self.reg_live_values.get(0x31, 0x0F) << 8) | self.reg_live_values.get(0x30, 0xFF)
        self.rcount_sp.delete(0, "end")
        self.rcount_sp.insert(0, str(rcount))
        
        # Offset (0x32/0x33)
        offset = (self.reg_live_values.get(0x33, 0x00) << 8) | self.reg_live_values.get(0x32, 0x00)
        self.offset_sp.delete(0, "end")
        self.offset_sp.insert(0, str(offset))
        
        # INTB Function (0x0A bits 5:0)
        intb_mode = self.reg_live_values.get(0x0A, 0x00) & 0x3F
        # Simplified mapping (0-6)
        mode_idx = min(6, intb_mode) 
        self.intb_func_cb.current(mode_idx)
        
        # Sensor FMIN (0x04 bits 7:4)
        min_freq = (self.reg_live_values.get(0x04, 0x03) >> 4) & 0x0F
        self.fmin_cb.current(min_freq)
        
        # SENSOR_DIV (0x34 bits 1:0)
        sdiv = self.reg_live_values.get(0x34, 0x00) & 0x03
        self.clk_div_cb.current(sdiv)
        
        # RP_MIN (0x01 bits 2:0)
        rpmin = self.reg_live_values.get(0x01, 0x07) & 0x07
        self.rp_min_cb.current(7 - rpmin) # Correct mapping based on RP_OPTIONS

    def _on_mode_toggle(self):
        """Handle Sleep/Running toggle button click."""
        is_connected = bool(self.ser_conn and self.ser_conn.connected)
        # When not connected, automatically fall back to simulation mode
        is_sim = self._is_sim_mode or not is_connected

        if self.mode_var.get() == "Running":
            # Write FUNC_MODE = 0x00 (Active) to register 0x0B
            val = self.reg_live_values.get(0x0B, 0x01) & ~0x03
            self._write_reg(0x0B, val)
        else:
            # Write FUNC_MODE = 0x01 (Sleep) to register 0x0B
            val = (self.reg_live_values.get(0x0B, 0x01) & ~0x03) | 0x01
            self._write_reg(0x0B, val)

    def _browse_log_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="lhr_data_log.csv")
        if path:
            self.log_path_var.set(path)

    def _write_reg(self, addr, val):
        self.reg_live_values[addr] = val & 0xFF
        self.reg_lw[addr] = f"0x{val:02X}"
        if self.reg_map_ui:
            self.reg_map_ui.update_row(self._get_reg_by_addr(addr))

    def _write_reg_bit(self, addr, bit, state):
        val = self.reg_live_values.get(addr, 0)
        if state: val |= (1 << bit)
        else: val &= ~(1 << bit)
        self._write_reg(addr, val)

    def _write_reg_bits(self, addr, start_bit, mask, bits_val):
        val = self.reg_live_values.get(addr, 0)
        val = (val & ~(mask << start_bit)) | ((bits_val & mask) << start_bit)
        self._write_reg(addr, val)

    def _get_reg_by_addr(self, addr):
        for r in REGISTERS:
            if r["address"] == addr: return r
        return None

    def _on_rcount_change(self):
        try:
            val = int(self.rcount_sp.get())
            self._write_reg(0x30, val & 0xFF)
            self._write_reg(0x31, (val >> 8) & 0xFF)
        except ValueError: pass

    def _on_offset_change(self):
        try:
            val = int(self.offset_sp.get())
            self._write_reg(0x32, val & 0xFF)
            self._write_reg(0x33, (val >> 8) & 0xFF)
        except ValueError: pass

    def _on_intb_func_change(self, event):
        idx = self.intb_func_cb.current()
        self._write_reg_bits(0x0A, 0, 0x3F, idx)

    def _on_fmin_change(self, event):
        idx = self.fmin_cb.current()
        self._write_reg_bits(0x04, 4, 0x0F, idx)

    def _on_clk_div_change(self, event):
        idx = self.clk_div_cb.current()
        self._write_reg_bits(0x34, 0, 0x03, idx)

    def _on_rp_min_change(self, event):
        idx = 7 - self.rp_min_cb.current()
        self._write_reg_bits(0x01, 0, 0x07, idx)

    # ═══════════════════════════════════════════════════════════════
    #  POLLING & PLOTTING
    # ═══════════════════════════════════════════════════════════════

    def update_from_main_poll(self, status, lhr_data):
        """Update LHR UI with data polled from the main thread."""
        if self.mode_var.get() != "Running":
            return
            
        self.parent.after(100, lambda: self._update_ui(status, lhr_data))

    def _stop_polling(self):
        """Stopped by main GUI if needed."""
        pass

    def _update_ui(self, status, raw_val):
        # Check connection status OR simulation mode
        is_connected = self.ser_conn and self.ser_conn.connected
        is_sim = not is_connected
        
        # Update LEDs
        for i, bit_name in enumerate(["LHR_DRDY", "ERR_OF", "ERR_UR", "ERR_OR", "ERR_ZC"]):
            # LHR_STATUS bit mapping: 0=DRDY, 1=OF, 2=UR, 3=OR, 4=ZC
            if is_connected or is_sim:
                state = (status >> i) & 1
                color = COLORS["success"] if ((i == 0 and state) or (i > 0 and not state)) else COLORS["error"]
            else:
                color = "gray"
            self.leds[bit_name].delete("all")
            self.leds[bit_name].create_rectangle(0, 0, 40, 12, fill=color)
        
        if not is_connected and not is_sim:
            # Force statistics to 0 and clear history
            self.stat_min.set("0")
            self.stat_max.set("0")
            self.stat_avg.set("0")
            self.stat_std.set("0")
            self.raw_data_history = []
            self.data_buffer.clear()
            # Still refresh graph to show flat empty canvas
            self._refresh_graph(self.data_to_display_var.get())
            return

        # Process Data point
        self.raw_data_history.append(raw_val)
        display_val = raw_val
        
        # Calculation
        f_clkin = self.clkin_freq_var.get() * 1e6
        sdiv_idx = self.clk_div_cb.current()
        if sdiv_idx < 0: sdiv_idx = 0 # Fallback if not selected
        sdiv = 1 << sdiv_idx
        f_sensor = f_clkin * sdiv * raw_val / (2**24)
        
        c_sensor = self.sensor_cap_var.get() * 1e-12
        if f_sensor > 0 and c_sensor > 0:
            inductance = (1.0 / (c_sensor * (2 * math.pi * f_sensor)**2)) * 1e6 # uH
        else:
            inductance = 0
            
        view_type = self.data_to_display_var.get()
        if "Inductance" in view_type:
            display_val = inductance
        elif "Frequency" in view_type:
            display_val = f_sensor / 1e6 # MHz
            
        self.data_buffer.append(display_val)
        self.sample_count += 1
        
        # Logging
        if self.enable_log_var.get():
            self._log_to_file(raw_val, f_sensor, inductance)
            
        # Update Stats (on raw data as per standard)
        relevant_data = self.raw_data_history[-100:] # Last 100 points
        self.stat_min.set(f"{min(relevant_data):,}")
        self.stat_max.set(f"{max(relevant_data):,}")
        self.stat_avg.set(f"{int(statistics.mean(relevant_data)):,}")
        if len(relevant_data) > 1:
            self.stat_std.set(f"{int(statistics.stdev(relevant_data)):,}")
            
        # Update Graph with rate control
        rate_str = self.graph_update_rate_var.get()
        rate = int(rate_str.split(":")[-1])
        if self.sample_count % rate == 0:
            self._refresh_graph(view_type)

    def _refresh_graph(self, ylabel):
        if not self.smooth_updates.get():
            # If not smooth, we might want to skip some draws or use different logic
            # but usually immediate draw is fine for TkAgg
            pass

        self.ax.clear()
        self.ax.set_xlabel("Samples")
        self.ax.set_ylabel(ylabel)
        self.ax.set_title(f"LHR {ylabel} Strip Chart")
        
        # Visibility Toggles
        self.ax.xaxis.set_visible(self.show_x_scale.get())
        self.ax.yaxis.set_visible(self.show_y_scale.get())
        self.ax.spines['bottom'].set_visible(self.show_x_scale.get())
        self.ax.spines['left'].set_visible(self.show_y_scale.get())
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        
        self.ax.grid(True, alpha=0.3)
        
        data = list(self.data_buffer)
        if data:
            self.ax.plot(data, color=COLORS["accent_blue"], linewidth=1.5)
            
            # Auto-scale Y
            if self.autoscale_y.get():
                dmin, dmax = min(data), max(data)
                margin = (dmax - dmin) * 0.1 or dmax * 0.01 or 1
                self.ax.set_ylim(dmin - margin, dmax + margin)
            
            # Auto-scale X (scroll)
            if self.autoscale_x.get():
                # X-axis is naturally autoscaled by plot unless we set limits
                pass
            else:
                self.ax.set_xlim(0, 100) # Fixed view
        else:
            # Show empty line at 0
            self.ax.plot([0]*100, color=COLORS["accent_blue"], alpha=0)
            self.ax.set_ylim(0, 1)

        self.canvas.draw()

    def _on_display_type_change(self, *args):
        """Reset chart and stats when switching display mode."""
        self.data_buffer.clear()
        self.raw_data_history = []
        self.stat_min.set("0")
        self.stat_max.set("0")
        self.stat_avg.set("0")
        self.stat_std.set("0")
        self._refresh_graph(self.data_to_display_var.get())

    def _show_context_menu(self, event):
        menu = tk.Menu(self.parent, tearoff=0)
        
        menu.add_command(label="Copy Data", command=self._copy_data_to_clipboard)
        menu.add_command(label="Description and Tip...", command=lambda: messagebox.showinfo("Tip", "LHR Mode provides 24-bit resolution for high-precision inductance sensing."))
        
        # Visible Items Sub-menu
        visible_menu = tk.Menu(menu, tearoff=0)
        visible_menu.add_checkbutton(label="Plot Legend", variable=self.show_legend, command=self._toggle_legend)
        visible_menu.add_checkbutton(label="Graph Palette", variable=self.show_palette, command=self._toggle_palette)
        visible_menu.add_checkbutton(label="X Scale", variable=self.show_x_scale, command=self._toggle_axes)
        visible_menu.add_checkbutton(label="Y Scale", variable=self.show_y_scale, command=self._toggle_axes)
        menu.add_cascade(label="Visible Items", menu=visible_menu)
        
        menu.add_separator()
        menu.add_command(label="Clear Graph", command=self._clear_graph)
        menu.add_command(label="Create Annotation", command=self._feature_not_available)
        menu.add_command(label="Delete All Annotations", command=self._feature_not_available)
        
        menu.add_separator()
        
        # Marker Spacing Sub-menu
        marker_menu = tk.Menu(menu, tearoff=0)
        marker_menu.add_radiobutton(label="Uniform", variable=self.marker_spacing, value="Uniform")
        marker_menu.add_radiobutton(label="Arbitrary", variable=self.marker_spacing, value="Arbitrary")
        menu.add_cascade(label="Marker Spacing", menu=marker_menu)
        
        menu.add_checkbutton(label="AutoScale X", variable=self.autoscale_x)
        menu.add_checkbutton(label="AutoScale Y", variable=self.autoscale_y)
        menu.add_checkbutton(label="Smooth Updates", variable=self.smooth_updates)
        
        # Export Sub-menu
        export_menu = tk.Menu(menu, tearoff=0)
        export_menu.add_command(label="Export Data To Clipboard", command=self._copy_data_to_clipboard)
        export_menu.add_command(label="Export Data To Excel", command=self._export_data_to_excel)
        export_menu.add_command(label="Export Data To DIAdem", command=self._feature_not_available)
        menu.add_cascade(label="Export", menu=export_menu)
        
        menu.post(event.x_root, event.y_root)

    def _toggle_palette(self):
        if self.show_palette.get():
            self.btn_frame.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-30)
        else:
            self.btn_frame.place_forget()

    def _toggle_legend(self):
        if self.show_legend.get():
            self.ax.legend(loc="upper right", fontsize=8)
        else:
            leg = self.ax.get_legend()
            if leg: leg.remove()
        self.canvas.draw_idle()

    def _toggle_axes(self):
        self.ax.xaxis.set_visible(self.show_x_scale.get())
        self.ax.yaxis.set_visible(self.show_y_scale.get())
        self.canvas.draw_idle()

    def _clear_graph(self):
        self.data_buffer.clear()
        self.raw_data_history = []
        self.stat_min.set("0")
        self.stat_max.set("0")
        self.stat_avg.set("0")
        self.stat_std.set("0")
        self._refresh_graph(self.data_to_display_var.get())

    def _copy_data_to_clipboard(self):
        data = list(self.data_buffer)
        if not data:
            messagebox.showwarning("Warning", "No data to copy.")
            return
        text = "Sample\tValue\n"
        for i, val in enumerate(data):
            text += f"{i}\t{val}\n"
        self.parent.clipboard_clear()
        self.parent.clipboard_append(text)
        messagebox.showinfo("Success", "Data copied to clipboard.")

    def _export_data_to_excel(self):
        data = list(self.data_buffer)
        if not data:
            messagebox.showwarning("Warning", "No data to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if path:
            try:
                with open(path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Sample", "Value"])
                    for i, val in enumerate(data):
                        writer.writerow([i, val])
                messagebox.showinfo("Success", f"Data exported to {path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not export data: {e}")

    def _feature_not_available(self):
        messagebox.showinfo("Info", "Feature not available in this version.")

    def _toggle_crosshair(self):
        self.crosshair_active = not self.crosshair_active
        if self.crosshair_active:
            self.crosshair_btn.config(relief="sunken", bg="#666666")
            self.cid_motion = self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        else:
            self.crosshair_btn.config(relief="raised", bg="#444444")
            if self.cid_motion:
                self.canvas.mpl_disconnect(self.cid_motion)
                self.cid_motion = None
            self.coord_label.config(text="")

    def _on_mouse_move(self, event):
        if event.inaxes:
            x, y = event.xdata, event.ydata
            self.coord_label.config(text=f"x={x:.1f}  y={y:.4f}")
        else:
            self.coord_label.config(text="")

    def _show_zoom_popup(self):
        """Show zoom/interaction mode popup panel above the zoom button."""
        # Destroy any existing popup
        if hasattr(self, '_zoom_popup') and self._zoom_popup and self._zoom_popup.winfo_exists():
            self._zoom_popup.destroy()
            return

        popup = tk.Toplevel()
        popup.overrideredirect(True)        # no title bar / decorations
        popup.configure(bg="#2b2b2b")
        popup.attributes("-topmost", True)

        # Position popup above the zoom button
        self.zoom_btn.update_idletasks()
        bx = self.zoom_btn.winfo_rootx()
        by = self.zoom_btn.winfo_rooty()
        popup.geometry(f"138x92+{bx - 50}+{by - 98}")

        self._zoom_popup = popup

        # Track active mode (default = "zoom_xy")
        if not hasattr(self, '_active_zoom_mode'):
            self._active_zoom_mode = "zoom_xy"

        BTN_W = 40
        BTN_H = 36
        INACTIVE_BG = "#3c3f41"
        ACTIVE_BG   = "#2d6a9f"
        BTN_FG      = "white"
        FONT        = ("Arial", 14)

        def make_mode_btn(parent, symbol, mode, tooltip_text, row, col):
            bg = ACTIVE_BG if mode == self._active_zoom_mode else INACTIVE_BG

            def on_click():
                self._active_zoom_mode = mode
                self._apply_zoom_mode(mode)
                popup.destroy()

            btn = tk.Button(
                parent, text=symbol, width=3, height=1,
                font=FONT, bg=bg, fg=BTN_FG,
                relief="flat", bd=0, cursor="hand2",
                command=on_click
            )
            btn.grid(row=row, column=col, padx=2, pady=2, ipadx=2, ipady=2)

            # Simple tooltip on hover
            def show_tip(e):
                tip = tk.Toplevel()
                tip.overrideredirect(True)
                tip.geometry(f"+{e.x_root+10}+{e.y_root+10}")
                tk.Label(tip, text=tooltip_text, bg="#ffffe0", relief="solid", bd=1,
                         font=("Arial", 8)).pack()
                btn._tip = tip
                btn.after(1500, lambda: tip.destroy() if tip.winfo_exists() else None)
            def hide_tip(e):
                if hasattr(btn, '_tip') and btn._tip.winfo_exists():
                    btn._tip.destroy()
            btn.bind("<Enter>", show_tip)
            btn.bind("<Leave>", hide_tip)
            return btn

        grid_frame = tk.Frame(popup, bg="#2b2b2b")
        grid_frame.pack(padx=4, pady=4)

        # Row 0: AutoFit | Zoom X | Zoom XY
        make_mode_btn(grid_frame, "⤢", "autofit",  "Auto-fit / Reset view",  0, 0)
        make_mode_btn(grid_frame, "↔", "zoom_x",   "Zoom X axis only",       0, 1)
        make_mode_btn(grid_frame, "⤡", "zoom_xy",  "Zoom X and Y (default)", 0, 2)
        # Row 1: Zoom Y | Pan XY | Pan Free
        make_mode_btn(grid_frame, "↕", "zoom_y",   "Zoom Y axis only",       1, 0)
        make_mode_btn(grid_frame, "✛", "pan_xy",   "Pan X and Y",            1, 1)
        make_mode_btn(grid_frame, "✥", "pan_free", "Pan freely",             1, 2)

        # Close popup when it loses focus
        popup.focus_set()
        popup.bind("<FocusOut>", lambda e: popup.destroy() if popup.winfo_exists() else None)
        popup.bind("<Escape>",   lambda e: popup.destroy())

    def _apply_zoom_mode(self, mode):
        """Apply the selected zoom/pan mode to the matplotlib toolbar."""
        # Always reset toolbar to neutral state first
        # (calling zoom/pan a second time on an active mode toggles it off)
        try:
            current = self.nav_toolbar.mode.name if hasattr(self.nav_toolbar.mode, 'name') else str(self.nav_toolbar.mode)
        except Exception:
            current = ""

        if mode == "autofit":
            self.nav_toolbar.home()

        elif mode == "zoom_xy":
            # Standard XY zoom — engage zoom mode
            if "ZOOM" not in current.upper():
                self.nav_toolbar.zoom()

        elif mode == "zoom_x":
            # Zoom mode then lock Y: after user draws zoom box, restore Y limits
            if "ZOOM" not in current.upper():
                self.nav_toolbar.zoom()
            self._zoom_x_only = True   # flag checked in _on_zoom_complete (optional enhancement)

        elif mode == "zoom_y":
            if "ZOOM" not in current.upper():
                self.nav_toolbar.zoom()
            self._zoom_y_only = True

        elif mode in ("pan_xy", "pan_free"):
            if "PAN" not in current.upper():
                self.nav_toolbar.pan()

        # Redraw
        self.canvas.draw_idle()

    def _log_to_file(self, raw, freq, ind):
        file_path = self.log_path_var.get()
        file_exists = os.path.isfile(file_path)
        try:
            with open(file_path, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "LHR_Count", "Freq_MHz", "Inductance_uH"])
                writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), raw, f"{freq/1e6:.6f}", f"{ind:.6f}"])
        except Exception as e:
            logger.error(f"Failed to write log: {e}")
