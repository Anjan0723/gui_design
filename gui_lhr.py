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
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from config import COLORS, FONTS
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
        
        # Polling & Graph Data
        self.is_polling = False
        self.poll_thread = None
        self.data_buffer = deque(maxlen=100)
        self.sample_count = 0
        self.raw_data_history = []
        
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
        ttk.OptionMenu(graph_ctrl, self.data_to_display_var, "Count", "Count", "Inductance (uH)", "Frequency (MHz)").pack(side="left", padx=5)
        
        tk.Label(graph_ctrl, text="Graph update rate:", bg=COLORS["bg_main"]).pack(side="left", padx=(20, 0))
        ttk.OptionMenu(graph_ctrl, self.graph_update_rate_var, "1:1", "1:1", "1:2", "1:5", "1:10").pack(side="left", padx=5)
        
        # Matplotlib Strip Chart
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Samples")
        self.ax.set_ylabel("Count")
        self.ax.grid(True, alpha=0.3)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_panel)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # ═══════════════════════════════════════════════════════════════
    #  LOGIC & EVENTS
    # ═══════════════════════════════════════════════════════════════

    def _sync_config_with_registers(self):
        """Sync UI controls with current register values."""
        # FUNC_MODE
        mode = self.reg_live_values.get(0x0B, 0x01) & 0x03
        self.mode_var.set("Running" if mode == 0 else "Sleep")
        
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
        new_mode = self.mode_var.get()
        func_mode = 0 if new_mode == "Running" else 1
        self._write_reg_bits(0x0B, 0, 0x03, func_mode)
        
        if new_mode == "Running":
            self._start_polling()
        else:
            self._stop_polling()

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

    def _start_polling(self):
        if not self.is_polling:
            self.is_polling = True
            self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self.poll_thread.start()
            self.set_status("LHR Polling Started")

    def _stop_polling(self):
        self.is_polling = False
        self.set_status("LHR Polling Stopped")

    def _poll_loop(self):
        while self.is_polling:
            self._do_read()
            time.sleep(0.5)

    def _do_read(self):
        # Real Hardware Read or Simulation
        is_sim = self.sim_var.get() if self.sim_var else False
        
        if not is_sim and self.ser_conn and self.ser_conn.connected:
            # Read registers from hardware
            msb = self.ser_conn.read_register(0x3A)
            mid = self.ser_conn.read_register(0x39)
            lsb = self.ser_conn.read_register(0x38)
            status = self.ser_conn.read_register(0x3B)
            
            if msb is not None: self.reg_live_values[0x3A] = msb
            if mid is not None: self.reg_live_values[0x39] = mid
            if lsb is not None: self.reg_live_values[0x38] = lsb
            if status is not None: self.reg_live_values[0x3B] = status
            
            lhr_data = (msb << 16) | (mid << 8) | lsb if (msb is not None and mid is not None and lsb is not None) else 0
        else:
            # Simulation Mode
            status = self.reg_live_values.get(0x3B, 0x01) 
            if time.time() % 2 < 0.5: status |= 0x01
            
            msb = self.reg_live_values.get(0x3A, 0)
            mid = self.reg_live_values.get(0x39, 0)
            lsb = self.reg_live_values.get(0x38, 0)
            lhr_data = (msb << 16) | (mid << 8) | lsb
            
            if lhr_data == 0: # Mock fallback pattern
                 lhr_data = 1000000 + int(math.sin(time.time()) * 5000)

        # Update UI in main thread
        self.parent.after(0, lambda: self._update_ui(status if status is not None else 0, lhr_data))

    def _update_ui(self, status, raw_val):
        # Update LEDs
        for i, bit_name in enumerate(["LHR_DRDY", "ERR_OF", "ERR_UR", "ERR_OR", "ERR_ZC"]):
            # LHR_STATUS bit mapping: 0=DRDY, 1=OF, 2=UR, 3=OR, 4=ZC
            state = (status >> i) & 1
            color = COLORS["success"] if ((i == 0 and state) or (i > 0 and not state)) else COLORS["error"]
            self.leds[bit_name].delete("all")
            self.leds[bit_name].create_rectangle(0, 0, 40, 12, fill=color)
        
        # Process Data point
        self.raw_data_history.append(raw_val)
        display_val = raw_val
        
        # Calculation
        f_clkin = self.clkin_freq_var.get() * 1e6
        sdiv_idx = self.clk_div_cb.current()
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
        self.ax.clear()
        self.ax.set_xlabel("Samples")
        self.ax.set_ylabel(ylabel)
        self.ax.set_title(f"LHR {ylabel} Strip Chart")
        self.ax.grid(True, alpha=0.3)
        
        data = list(self.data_buffer)
        self.ax.plot(data, color=COLORS["accent_blue"], linewidth=1.5)
        
        # Auto-scale Y with some margin
        if data:
            dmin, dmax = min(data), max(data)
            margin = (dmax - dmin) * 0.1 or dmax * 0.01 or 1
            self.ax.set_ylim(dmin - margin, dmax + margin)
            
        self.canvas.draw()

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
            print(f"Logging error: {e}")
