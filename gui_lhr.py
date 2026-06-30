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
import numpy as np

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
        self.colors = COLORS
        self.fonts = FONTS
        
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
        self.data_to_display_var = tk.StringVar(value="Frequency (MHz)")
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
        self.displacement_buffer = deque(maxlen=100)  # stores normalized displacement in mm (relative to first reading)
        self.displacement_ref = None  # reference point — set on first reading after reset
        self._last_valid_displacement = 0.0  # for sync fallback
        self.sample_count = 0
        self.raw_data_history = []
        self.update_counter = 0

        # Stable graph buffers (batch averaging)
        self.stable_disp_buffer = []    # averaged stable displacement values
        self.stable_ind_buffer = []     # averaged stable inductance values
        self.batch_disp = []            # current batch accumulator
        self.batch_ind = []             # current batch accumulator
        self.BATCH_SIZE = 20            # average every 20 readings → 1 stable point
        self.MAX_STABLE_POINTS = 100    # keep last 100 stable points on graph
        
        # Create sub-view frames
        self.config_frame = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        self.measure_frame = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        
        self._build_config_view()
        self._build_measure_view()
        
        # Show configuration view by default
        self.config_frame.pack(fill="both", expand=True)

    def get_frame(self):
        return self.main_frame

    def update_csensor_display(self, display_str):
        """Called by gui_main when Apps Calculator Csensor changes."""
        self.csensor_lbl.config(text=display_str)
        
        # Parse the capacitance value (in pF) and update self.sensor_cap_var
        # so that the inductance calculations automatically use the correct value
        import re
        match = re.match(r"^\s*([0-9.]+)", display_str)
        if match:
            try:
                val = float(match.group(1))
                clean_str = display_str.lower()
                if 'n' in clean_str:
                    val_pf = val * 1000.0
                elif 'u' in clean_str:
                    val_pf = val * 1000000.0
                elif 'f' in clean_str and not ('p' in clean_str or 'n' in clean_str or 'u' in clean_str):
                    val_pf = val * 1e12
                else:
                    val_pf = val
                self.sensor_cap_var.set(val_pf)
            except Exception:
                pass

    def update_device_id(self, chip_id_val):
        """Called after connect with the real chip_id byte read from device."""
        if chip_id_val is not None:
            self.did_lbl.config(text=f"{chip_id_val:02X}")
        else:
            self.did_lbl.config(text="--")

    def _switch_to_measure(self):
        self.config_frame.pack_forget()
        self.measure_frame.pack(fill="both", expand=True)

    def _switch_to_config(self):
        self.measure_frame.pack_forget()
        self.config_frame.pack(fill="both", expand=True)

    def _make_section_card(self, parent, title, icon=""):
        """Create a styled section card with header."""
        outer = tk.Frame(parent,
            bg=COLORS["bg_white"],
            highlightbackground=COLORS["border"],
            highlightthickness=1)
        outer.pack(fill="x", padx=8, pady=4)

        header = tk.Frame(outer, bg=COLORS["bg_section"],
            highlightbackground=COLORS["border"],
            highlightthickness=1)
        header.pack(fill="x")
        tk.Label(header,
            text=f"  {icon}  {title}" if icon else f"  {title}",
            font=FONTS["heading"],
            bg=COLORS["bg_section"],
            fg="#3a4a5c").pack(
            side="left", padx=8, pady=5)

        body = tk.Frame(outer, bg=COLORS["bg_white"])
        body.pack(fill="both", expand=True, padx=10, pady=8)
        return body

    def _make_display_card(self, parent, label, unit, var_name):
        """Styled metric card for live values."""
        card = tk.Frame(parent,
            bg=COLORS["bg_section"],
            highlightbackground=COLORS["border"],
            highlightthickness=1)
        card.pack(side="left", fill="both",
                  expand=True, padx=4, pady=2)

        tk.Label(card,
            text=label.upper(),
            font=("Segoe UI", 8, "bold"),
            bg=COLORS["bg_section"],
            fg=COLORS["text_muted"]).pack(
            anchor="w", padx=8, pady=(6,0))

        lbl = tk.Label(card,
            text="--",
            font=FONTS["value_lg"],
            bg=COLORS["bg_section"],
            fg=COLORS["accent"])
        lbl.pack(anchor="w", padx=8)

        tk.Label(card,
            text=unit,
            font=FONTS["small"],
            bg=COLORS["bg_section"],
            fg=COLORS["text_muted"]).pack(
            anchor="w", padx=8, pady=(0,6))

        setattr(self, var_name, lbl)
        return lbl

    def _update_mode_button(self, running: bool):
        """Update the mode button appearance based on running state."""
        if running:
            self.mode_btn.config(
                text="● Running",
                bg=COLORS["success"],
                fg="#ffffff",
                font=("Segoe UI", 10, "bold"),
                relief="flat", padx=12, pady=4)
        else:
            self.mode_btn.config(
                text="Sleep",
                bg=COLORS["bg_white"],
                fg=COLORS["text_secondary"],
                font=FONTS["normal"],
                relief="flat", padx=12, pady=4,
                highlightbackground=COLORS["border"],
                highlightthickness=1)

    def _build_config_view(self):
        """Build the LHR Configuration sub-view."""
        # Top Header - Modern card style
        header = tk.Frame(self.config_frame, bg=COLORS["primary"], height=44)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Go to Streaming button - left side
        self.goto_stream_btn = tk.Button(header,
            text="\u2611 Go to Streaming",
            font=FONTS["normal"],
            bg=COLORS["bg_white"],
            fg=COLORS["text_primary"],
            relief="flat",
            padx=10, pady=4,
            cursor="hand2",
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            command=self._switch_to_measure)
        self.goto_stream_btn.pack(side="left", padx=(12, 8))

        tk.Label(header, text="\ud83d\udcca LHR Configuration",
            font=FONTS["title"],
            bg=COLORS["primary"], fg="white").pack(side="left", padx=16, pady=8)

        tk.Label(header, text=f"24-bit Resolution",
            font=FONTS["small"],
            bg=COLORS["primary"], fg="white").pack(side="right", padx=16, pady=8)

        # Mode Toggle & Logging - Modern card style
        ctrl_section = tk.Frame(self.config_frame, bg=COLORS["bg_section"], bd=1, relief="solid",
                                highlightbackground=COLORS["border"], highlightthickness=1)
        ctrl_section.pack(fill="x", padx=10, pady=8)

        tk.Label(ctrl_section, text="Device & Logging", font=FONTS["section_title"],
                bg=COLORS["bg_section"], fg=COLORS["primary"]).pack(anchor="w", padx=12, pady=(8, 4))

        controls_row = tk.Frame(ctrl_section, bg=COLORS["bg_section"])
        controls_row.pack(fill="x", padx=12, pady=(0, 8))

        mode_btn = tk.Checkbutton(controls_row, textvariable=self.mode_var, variable=self.mode_var,
                                  onvalue="Running", offvalue="Sleep", indicatoron=False,
                                  font=FONTS["normal_bold"], width=12, selectcolor=COLORS["success"],
                                  command=self._on_mode_toggle)
        mode_btn.pack(side="left", padx=4)

        tk.Checkbutton(controls_row, text="Enable Data Log", variable=self.enable_log_var,
                       bg=COLORS["bg_section"], font=FONTS["small"]).pack(side="left", padx=12)

        log_row = tk.Frame(ctrl_section, bg=COLORS["bg_section"])
        log_row.pack(fill="x", padx=12, pady=(0, 8))

        tk.Entry(log_row, textvariable=self.log_path_var, width=40, font=FONTS["small"],
                bg=COLORS["bg_input"]).pack(side="left", fill="x", expand=True)
        tk.Button(log_row, text="Browse", command=self._browse_log_file,
                 bg=COLORS["primary"], fg="white", relief="flat", padx=8).pack(side="left", padx=4)

        # Device Info Row - Modern card style
        info_card = tk.Frame(self.config_frame, bg=COLORS["bg_section"], bd=1, relief="solid",
                            highlightbackground=COLORS["border"], highlightthickness=1)
        info_card.pack(fill="x", padx=10, pady=8)

        info_row = tk.Frame(info_card, bg=COLORS["bg_section"])
        info_row.pack(fill="x", padx=12, pady=8)

        tk.Label(info_row, text="Csensor:", bg=COLORS["bg_section"], font=FONTS["normal"],
                fg=COLORS["text_secondary"]).pack(side="left")
        self.csensor_lbl = tk.Label(info_row, text="390 pF", bg=COLORS["bg_white"],
                                    font=FONTS["courier"], padx=8, relief="flat")
        self.csensor_lbl.pack(side="left", padx=4)

        tk.Label(info_row, text="Device ID:", bg=COLORS["bg_section"], font=FONTS["normal"],
                fg=COLORS["text_secondary"]).pack(side="left", padx=(20, 0))
        self.did_lbl = tk.Label(info_row, text="--", bg=COLORS["bg_white"],
                               font=FONTS["courier"], padx=8, relief="flat")
        self.did_lbl.pack(side="left", padx=4)
        # Main two-column container
        main_row = tk.Frame(self.config_frame, bg=COLORS["bg_main"])
        main_row.pack(fill="both", expand=True, padx=10, pady=10)

        # ── LEFT COLUMN — Status Indicators ──
        left_col = tk.LabelFrame(main_row, text="Status Indicators",
            bg=COLORS["bg_main"], font=FONTS["normal"])
        left_col.pack(side="left", fill="y", padx=(0, 20), pady=5)

        # All 8 indicators listed serially — NO sub-groups, NO titles
        indicators = [
            # (bit_num, field_name,    description,              reg_key)
            (4, "ERR_ZC",        "Zero Count Error",        "lhr_status"),
            (3, "ERR_OR",        "Over-range Error",        "lhr_status"),
            (2, "ERR_UR",        "Under-range Error",       "lhr_status"),
            (1, "ERR_OF",        "Overflow Error",          "lhr_status"),
            (0, "LHR_DRDY",      "Data Ready",              "lhr_status"),
            (7, "NO_SENSOR_OSC", "Sensor Oscillation Error","status"),
            (6, "DRDYB",         "RP+L Data Ready",         "status"),
            (0, "POR_READ",      "Power-On-Reset",          "status"),
        ]

        self.all_status_leds = {}  # unified dict for all LEDs

        for bit, name, desc, reg_key in indicators:
            row = tk.Frame(left_col, bg=COLORS["bg_main"])
            row.pack(fill="x", padx=8, pady=2)

            tk.Label(row, text=f"Bit {bit}", width=5,
                font=FONTS["small"], bg=COLORS["bg_main"],
                anchor="w").pack(side="left")

            led = tk.Label(row, text="  ", bg=COLORS["led_green"],
                width=3, relief="raised")
            led.pack(side="left", padx=4)

            tk.Label(row, text=name, width=14,
                font=FONTS["normal"], bg=COLORS["bg_main"],
                anchor="w").pack(side="left")

            tk.Label(row, text=desc,
                font=FONTS["small"], fg=COLORS["text_muted"],
                bg=COLORS["bg_main"],
                anchor="w").pack(side="left")

            self.all_status_leds[name] = (led, bit, reg_key)

        # ── RIGHT COLUMN — Display ──
        right_col = tk.LabelFrame(main_row, text="Display",
            bg=COLORS["bg_main"], font=FONTS["normal"])
        right_col.pack(side="left", fill="both", expand=True, pady=5)

        display_inner = tk.Frame(right_col, bg=COLORS["bg_main"])
        display_inner.pack(expand=True, pady=30)

        # LHR Count
        tk.Label(display_inner, text="LHR Count:",
            font=FONTS["normal"], bg=COLORS["bg_main"],
            anchor="e", width=12).grid(row=0, column=0, padx=8, pady=10, sticky="e")
        self.lhr_count_lbl = tk.Label(display_inner, text="--",
            font=("Consolas", 13, "bold"), bg="#FFFFFF",
            width=12, relief="solid", bd=1, anchor="center")
        self.lhr_count_lbl.config(bg='#FFFFFF', fg='#212121')
        self.lhr_count_lbl.grid(row=0, column=1, padx=5)
        tk.Label(display_inner, text="counts",
            font=FONTS["small"], bg=COLORS["bg_main"],
            anchor="w").grid(row=0, column=2, padx=4, sticky="w")

        # Frequency
        tk.Label(display_inner, text="Frequency:",
            font=FONTS["normal"], bg=COLORS["bg_main"],
            anchor="e", width=12).grid(row=1, column=0, padx=8, pady=10, sticky="e")
        self.freq_lbl = tk.Label(display_inner, text="--",
            font=("Consolas", 13, "bold"), bg="#FFFFFF",
            width=12, relief="solid", bd=1, anchor="center")
        self.freq_lbl.config(bg='#FFFFFF', fg='#212121')
        self.freq_lbl.grid(row=1, column=1, padx=5)
        tk.Label(display_inner, text="MHz",
            font=FONTS["small"], bg=COLORS["bg_main"],
            anchor="w").grid(row=1, column=2, padx=4, sticky="w")

        # Inductance
        tk.Label(display_inner, text="Inductance:",
            font=FONTS["normal"], bg=COLORS["bg_main"],
            anchor="e", width=12).grid(row=2, column=0, padx=8, pady=10, sticky="e")
        self.inductance_lbl = tk.Label(display_inner, text="--",
            font=("Consolas", 13, "bold"), bg="#FFFFFF",
            width=12, relief="solid", bd=1, anchor="center")
        self.inductance_lbl.config(bg='#FFFFFF', fg='#212121')
        self.inductance_lbl.grid(row=2, column=1, padx=5)
        tk.Label(display_inner, text="µH",
            font=FONTS["small"], bg=COLORS["bg_main"],
            anchor="w").grid(row=2, column=2, padx=4, sticky="w")

        # Rs (Parasitic Resistance)
        tk.Label(display_inner, text="Rs:",
            font=FONTS["normal"], bg=COLORS["bg_main"],
            anchor="e", width=12).grid(row=3, column=0, padx=8, pady=10, sticky="e")
        self.rs_lbl = tk.Label(display_inner, text="--",
            font=("Consolas", 13, "bold"), bg="#FFFFFF",
            width=12, relief="solid", bd=1, anchor="center")
        self.rs_lbl.config(bg='#FFFFFF', fg='#212121')
        self.rs_lbl.grid(row=3, column=1, padx=5)
        tk.Label(display_inner, text="Ω",
            font=FONTS["small"], bg=COLORS["bg_main"],
            anchor="w").grid(row=3, column=2, padx=4, sticky="w")

        # Rp (Parasitic)
        tk.Label(display_inner, text="Rp:",
            font=FONTS["normal"], bg=COLORS["bg_main"],
            anchor="e", width=12).grid(row=4, column=0, padx=8, pady=10, sticky="e")
        self.rp_lbl = tk.Label(display_inner, text="--",
            font=("Consolas", 13, "bold"), bg="#FFFFFF",
            width=12, relief="solid", bd=1, anchor="center")
        self.rp_lbl.config(bg='#FFFFFF', fg='#212121')
        self.rp_lbl.grid(row=4, column=1, padx=5)
        tk.Label(display_inner, text="kΩ",
            font=FONTS["small"], bg=COLORS["bg_main"],
            anchor="w").grid(row=4, column=2, padx=4, sticky="w")

        # Q Factor
        tk.Label(display_inner, text="Q Factor:",
            font=FONTS["normal"], bg=COLORS["bg_main"],
            anchor="e", width=12).grid(row=5, column=0, padx=8, pady=10, sticky="e")
        self.qfactor_lbl = tk.Label(display_inner, text="--",
            font=("Consolas", 13, "bold"), bg="#FFFFFF",
            width=12, relief="solid", bd=1, anchor="center")
        self.qfactor_lbl.config(bg='#FFFFFF', fg='#212121')
        self.qfactor_lbl.grid(row=5, column=1, padx=5)
        tk.Label(display_inner, text="",
            font=FONTS["small"], bg=COLORS["bg_main"],
            anchor="w").grid(row=5, column=2, padx=4, sticky="w")

        self._sync_config_with_registers()

    def _build_measure_view(self):
        """Build the LHR Measurement sub-view."""
        # Top Header
        header = tk.Frame(self.measure_frame, bg=COLORS["bg_main"])
        header.pack(fill="x", padx=10, pady=5)
        
        tk.Button(header, text="\u2611 Go to Configuration", font=FONTS["normal_bold"], 
                  command=self._switch_to_config).pack(side="left")
        
        LHR_RESOLUTION_BITS = 24   # LHR_DATA is 24-bit (3 registers × 8 bits)
        tk.Label(header, text=f"LHR Measurement  ({LHR_RESOLUTION_BITS}-bit)", font=("Arial", 12, "bold"), 
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
        
        self.stats_unit_var = tk.StringVar(value="MHz")

        for label, var in [("Minimum", self.stat_min), ("Maximum", self.stat_max),
                          ("Average", self.stat_avg), ("Std.dev", self.stat_std)]:
            row = tk.Frame(stat_sec, bg=COLORS["bg_main"])
            row.pack(fill="x", padx=5, pady=5)
            tk.Label(row, text=f"{label}:", bg=COLORS["bg_main"], font=FONTS["normal"]).pack(anchor="w")
            val_frame = tk.Frame(row, bg="#FFFFFF", relief="solid", bd=1)
            val_frame.pack(fill="x")
            tk.Label(val_frame, textvariable=var, bg="#FFFFFF", fg="#212121", font=FONTS["courier"]).pack(side="left", padx=2)
            tk.Label(val_frame, textvariable=self.stats_unit_var, bg="#FFFFFF", fg="#757575", font=FONTS["tiny_italic"]).pack(side="right", padx=2)

        # Right Graph Panel
        right_panel = tk.Frame(body, bg=COLORS["bg_main"])
        right_panel.pack(side="right", fill="both", expand=True)
        
        graph_ctrl = tk.Frame(right_panel, bg=COLORS["bg_main"])
        graph_ctrl.pack(fill="x")
        
        tk.Label(graph_ctrl, text="Data to display:", bg=COLORS["bg_main"]).pack(side="left")
        self.display_om = ttk.OptionMenu(graph_ctrl, self.data_to_display_var, "Frequency (MHz)", "Frequency (MHz)", "Inductance (µH)", "Displacement vs Inductance")
        self.display_om.pack(side="left", padx=5)
        self.data_to_display_var.trace_add("write", self._on_display_type_change)
        
        tk.Label(graph_ctrl, text="Graph update rate:", bg=COLORS["bg_main"]).pack(side="left", padx=(20, 0))
        self.rate_om = ttk.OptionMenu(graph_ctrl, self.graph_update_rate_var, "1:10", "1:1", "1:2", "1:5", "1:10", "1:20", "1:50")
        self.rate_om.pack(side="left", padx=5)
        
        tk.Label(graph_ctrl, text="Smoothing:", bg=COLORS["bg_main"], font=FONTS["normal"]).pack(side="left", padx=(15,2))
        self.smooth_var = tk.IntVar(value=8)
        smooth_sp = tk.Spinbox(graph_ctrl, from_=1, to=30, textvariable=self.smooth_var, width=4, font=FONTS["normal"])
        smooth_sp.pack(side="left")
        
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
        

        # Device ID (register 0x3F) — only show when connected, else show "--"
        is_connected = bool(self.ser_conn and self.ser_conn.connected)
        if is_connected or self._is_sim_mode:
            did = self.reg_live_values.get(0x3F)
            if did is not None:
                self.did_lbl.config(text=f"{did:02X}")
            else:
                self.did_lbl.config(text="--")
        else:
            self.did_lbl.config(text="--")
        
        pass

    def _on_mode_toggle(self):
        """Handle Sleep/Running toggle button click."""
        is_connected = bool(self.ser_conn and self.ser_conn.connected)
        # When not connected, automatically fall back to simulation mode
        is_sim = self._is_sim_mode or not is_connected

        if self.mode_var.get() == "Running":
            # Update button appearance
            self._update_mode_button(True)
            # Reset displacement reference for new measurement session
            self.displacement_ref = None
            self.displacement_buffer.clear()
            # Clear stable buffers for fresh start
            self.stable_disp_buffer.clear()
            self.stable_ind_buffer.clear()
            self.batch_disp.clear()
            self.batch_ind.clear()
            # Write FUNC_MODE = 0x00 (Active) to register 0x0B
            val = self.reg_live_values.get(0x0B, 0x01) & ~0x03
            self._write_reg(0x0B, val)
        else:
            # Update button appearance
            self._update_mode_button(False)
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
        
        lhr_status_reg = self.reg_live_values.get(0x3B, 0x00)
        status_reg     = self.reg_live_values.get(0x20, 0x00)

        for name, (led, bit, reg_key) in self.all_status_leds.items():
            if reg_key == "lhr_status":
                bit_val = (lhr_status_reg >> bit) & 1
            else:
                bit_val = (status_reg >> bit) & 1
            
            # Configuration View LED - flat style with new colors
            led.config(bg=COLORS["led_red"] if bit_val else COLORS["led_green"])
            
            # Measurement View Canvas LED (only LHR bits)
            if name in self.leds:
                if is_connected or is_sim:
                    if name == "LHR_DRDY":
                        meas_color = COLORS["success"] if bit_val else COLORS["error"]
                    else:
                        meas_color = COLORS["error"] if bit_val else COLORS["success"]
                else:
                    meas_color = "gray"
                self.leds[name].delete("all")
                self.leds[name].create_rectangle(0, 0, 40, 12, fill=meas_color)
        
        if not is_connected and not is_sim:
            # Force statistics to 0 and clear history
            self.stat_min.set("0")
            self.stat_max.set("0")
            self.stat_avg.set("0")
            self.stat_std.set("0")
            self.raw_data_history = []
            self.data_buffer.clear()
            self.displacement_buffer.clear()
            self.displacement_ref = None  # Reset reference point
            # Clear stable buffers on disconnect
            self.stable_disp_buffer.clear()
            self.stable_ind_buffer.clear()
            self.batch_disp.clear()
            self.batch_ind.clear()
            # Still refresh graph to show flat empty canvas
            self._refresh_graph(self.data_to_display_var.get())
            self.did_lbl.config(text="--")
            return

        # Process Data point
        self.raw_data_history.append(raw_val)
        
        # --- Live Display values ---
        lhr_raw = self.reg_live_values.get(0x38, 0) | \
                   (self.reg_live_values.get(0x39, 0) << 8) | \
                   (self.reg_live_values.get(0x3A, 0) << 16)

        self.lhr_count_lbl.config(text=f"{lhr_raw}")

        f_sensor = 0
        inductance = 0
        # Default Rs value (parasitic resistance) - can be adjusted
        rs_val = 5.0  # Ohms (default typical value)
        if lhr_raw > 0:
            import math
            clkin = self.clkin_freq_var.get() * 1e6   # MHz → Hz

            # Read SENSOR_DIV directly from register since clk_div_cb is removed
            sdiv_bits = self.reg_live_values.get(0x34, 0x00) & 0x03
            sdiv = 1 << sdiv_bits

            freq_hz = (clkin * sdiv * lhr_raw) / 16777216.0
            freq_mhz = freq_hz / 1e6
            self.freq_lbl.config(text=f"{freq_mhz:.4f}")

            c_f = self.sensor_cap_var.get() * 1e-12
            if c_f > 0 and freq_hz > 0:
                L_uH = (1.0 / (4.0 * math.pi**2 * freq_hz**2 * c_f)) * 1e6
                self.inductance_lbl.config(text=f"{L_uH:.4f}")
                f_sensor = freq_hz
                inductance = L_uH

                # Calculate Rp (parasitic) = L / (Rs × C)
                L_H = L_uH * 1e-6
                if rs_val > 0 and c_f > 0:
                    rp_val = L_H / (rs_val * c_f) / 1000  # Convert to kΩ
                    self.rp_lbl.config(text=f"{rp_val:.4f}")

                    # Calculate Q Factor = (1/Rs) × sqrt(L/C)
                    q_val = (1.0 / rs_val) * math.sqrt(L_H / c_f)
                    self.qfactor_lbl.config(text=f"{q_val:.2f}")
                else:
                    self.rp_lbl.config(text="--")
                    self.qfactor_lbl.config(text="--")

                # Display Rs
                self.rs_lbl.config(text=f"{rs_val:.1f}")
            else:
                self.rp_lbl.config(text="--")
                self.qfactor_lbl.config(text="--")
                self.rs_lbl.config(text="--")
        else:
            self.freq_lbl.config(text="--")
            self.inductance_lbl.config(text="--")
            self.rs_lbl.config(text="--")
            self.rp_lbl.config(text="--")
            self.qfactor_lbl.config(text="--")
            
        view_type = self.data_to_display_var.get()
            
        self.data_buffer.append(raw_val)
        self.sample_count += 1
        
        # Logging
        if self.enable_log_var.get():
            self._log_to_file(raw_val, f_sensor, inductance)
            
        self._update_stats_display()

        # Update displacement buffer - always sync with data_buffer length
        # Normalize displacement to start from 0 (relative to first reading)
        if inductance > 0:
            raw_displacement = self._inductance_to_displacement(inductance)
            self._last_valid_displacement = raw_displacement

            # Set reference on first valid reading after reset
            if self.displacement_ref is None:
                self.displacement_ref = raw_displacement

            # Normalize — always starts from 0
            normalized_displacement = raw_displacement - self.displacement_ref

            # Batch averaging: collect readings, average each batch, only plot stable values
            self.batch_disp.append(normalized_displacement)
            self.batch_ind.append(inductance)

            # When batch is full → compute average → add ONE stable point
            if len(self.batch_disp) >= self.BATCH_SIZE:
                avg_disp = sum(self.batch_disp) / len(self.batch_disp)
                avg_ind = sum(self.batch_ind) / len(self.batch_ind)

                self.stable_disp_buffer.append(avg_disp)
                self.stable_ind_buffer.append(avg_ind)

                # Keep only last MAX_STABLE_POINTS
                if len(self.stable_disp_buffer) > self.MAX_STABLE_POINTS:
                    self.stable_disp_buffer.pop(0)
                    self.stable_ind_buffer.pop(0)

                # Clear batch for next round
                self.batch_disp.clear()
                self.batch_ind.clear()

            # Still append to displacement_buffer for other uses (statistics)
            self.displacement_buffer.append(normalized_displacement)
        else:
            # Use last known displacement to keep buffers in sync
            last_disp = getattr(self, '_last_valid_displacement', 0.0)
            if self.displacement_ref is not None:
                normalized_displacement = last_disp - self.displacement_ref
            else:
                normalized_displacement = 0.0
            self.displacement_buffer.append(normalized_displacement)

        # Update current displacement display (show with + sign for direction)
        # Update Graph with rate control
        rate_str = self.graph_update_rate_var.get()
        rate = int(rate_str.split(":")[-1])
        if self.sample_count % rate == 0:
            self._refresh_graph(view_type)

    def _inductance_to_displacement(self, L_uH):
        """
        Convert inductance (µH) to displacement (mm).
        3rd order polynomial fit from calibration data.
        R-squared = 0.9994 (excellent fit)

        Calibration points used:
        L(µH): 6.52, 6.66, 6.90, 7.20, 7.42, 7.57, 7.75, 7.90, 7.99, 8.20, 8.38
        d(mm): 1.0,  1.2,  1.5,  1.8,  2.0,  2.2,  2.5,  2.8,  3.0,  3.5,  4.0

        Formula: d = a*L³ + b*L² + c*L + d_const
        """
        a =   0.433113
        b =  -9.162041
        c =  65.644598
        d_const = -157.555257
        return a * (L_uH**3) + b * (L_uH**2) + c * L_uH + d_const

    def _get_display_values(self):
        """Convert data_buffer to display units based on selected type."""
        selected = self.data_to_display_var.get()
        if "Frequency" in selected:
            return [(16000000.0 * v) / 16777216.0 / 1e6 for v in self.data_buffer]
        elif "Inductance" in selected or "Displacement" in selected:
            import math
            c_f = self.sensor_cap_var.get() * 1e-12
            result = []
            for v in self.data_buffer:
                f = (16000000.0 * v) / 16777216.0
                if f > 0 and c_f > 0:
                    result.append((1.0 / (4.0 * math.pi**2 * f**2 * c_f)) * 1e6)
                else:
                    result.append(0.0)
            return result
        return list(self.data_buffer)

    def _smooth_data(self, data, window=8):
        """
        Apply moving average smoothing for display only.
        Raw data is never modified — only the plotted line is smoothed.
        window: number of samples to average (higher = smoother)
        """
        if len(data) < window:
            return data
        smoothed = []
        for i in range(len(data)):
            start = max(0, i - window // 2)
            end   = min(len(data), i + window // 2 + 1)
            smoothed.append(sum(data[start:end]) / (end - start))
        return smoothed

    def _update_stats_display(self):
        """Update statistics panel based on currently selected data type."""
        selected = self.data_to_display_var.get()

        if not self.data_buffer:
            return

        if "Frequency" in selected:
            # Convert LHR counts to MHz
            values = [
                (16000000.0 * v) / 16777216.0 / 1e6
                for v in self.data_buffer
            ]
            self.stats_unit_var.set("MHz")
            fmt = "{:.4f}"
        elif "Inductance" in selected and "Displacement" not in selected:
            # Convert LHR counts -> frequency -> inductance
            c_pf = self.sensor_cap_var.get()   # pF from Sensor Capacitor field
            c_f  = c_pf * 1e-12
            values = []
            for v in self.data_buffer:
                f = (16000000.0 * v) / 16777216.0
                if f > 0 and c_f > 0:
                    import math
                    L = 1.0 / (4.0 * math.pi * math.pi * f * f * c_f)
                    values.append(L * 1e6)   # Convert to uH
                else:
                    values.append(0.0)
            self.stats_unit_var.set("µH")
            fmt = "{:.4f}"
        elif "Displacement" in selected:
            # Show statistics for displacement buffer
            if self.displacement_buffer:
                values = list(self.displacement_buffer)
                self.stats_unit_var.set("mm")
                fmt = "{:.4f}"
            else:
                return
        else:
            return

        if values:
            self.stat_min.set(fmt.format(min(values)))
            self.stat_max.set(fmt.format(max(values)))
            self.stat_avg.set(fmt.format(sum(values) / len(values)))
            std = (sum((x - sum(values)/len(values))**2 for x in values) / len(values)) ** 0.5
            self.stat_std.set(fmt.format(std))

    def _refresh_graph(self, ylabel):
        if not self.smooth_updates.get():
            # If not smooth, we might want to skip some draws or use different logic
            # but usually immediate draw is fine for TkAgg
            pass

        selected = self.data_to_display_var.get()

        self.ax.clear()

        # Handle Displacement vs Inductance mode (X = displacement, Y = inductance)
        if "Displacement" in selected:
            # Use stable buffers (batch-averaged)
            disp_vals = list(self.stable_disp_buffer)
            ind_vals = list(self.stable_ind_buffer)

            if len(disp_vals) >= 2:
                # Sort by displacement for clean left-to-right curve
                paired = sorted(zip(disp_vals, ind_vals), key=lambda x: x[0])
                sorted_d = [p[0] for p in paired]
                sorted_l = [p[1] for p in paired]

                # Smooth the already-stable data lightly
                smooth_d = self._smooth_data(sorted_d, window=3)
                smooth_l = self._smooth_data(sorted_l, window=3)

                self.ax.cla()
                self.ax.set_title("Displacement vs Inductance",
                    fontsize=11, fontweight="bold")
                self.ax.set_xlabel("Displacement (mm)", fontsize=9)
                self.ax.set_ylabel("Inductance (µH)", fontsize=9)
                self.ax.grid(True, linestyle="--", alpha=0.4)

                self.ax.plot(smooth_d, smooth_l,
                    color="#1f77b4",
                    linewidth=2.0,
                    antialiased=True,
                    solid_capstyle="round",
                    solid_joinstyle="round")

                # Axis padding
                if smooth_d and smooth_l:
                    d_min, d_max = min(smooth_d), max(smooth_d)
                    l_min, l_max = min(smooth_l), max(smooth_l)
                    d_pad = max(0.05, (d_max - d_min) * 0.2)
                    l_pad = max(0.01, (l_max - l_min) * 0.2)
                    self.ax.set_xlim(d_min - d_pad, d_max + d_pad)
                    self.ax.set_ylim(l_min - l_pad, l_max + l_pad)

                self.canvas.draw_idle()
                return

            # Default state when insufficient data
            self.ax.cla()
            self.ax.set_title("Displacement vs Inductance", fontsize=11, fontweight="bold")
            self.ax.set_xlabel("Displacement (mm)", fontsize=9)
            self.ax.set_ylabel("Inductance (µH)", fontsize=9)
            self.ax.grid(True, linestyle="--", alpha=0.4, color="gray", linewidth=0.5)
            self.ax.set_xlim(0, 1)
            self.ax.set_ylim(6, 8)
            self.canvas.draw_idle()
            return
        else:
            # Normal strip chart (Frequency or Inductance vs Samples)
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

            data = self._get_display_values()
            if data:
                try:
                    window_size = self.smooth_var.get()
                except Exception:
                    window_size = 1

                smoothed_vals = self._smooth_data(data, window=window_size)
                self.ax.plot(smoothed_vals,
                             color="#1f77b4",
                             linewidth=1.8,
                             antialiased=True,
                             solid_capstyle="round",
                             solid_joinstyle="round")

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
        selected = self.data_to_display_var.get()
        if "Frequency" in selected:
            self.ax.set_xlabel("Samples")
            self.ax.set_ylabel("Frequency (MHz)")
            self.ax.set_title("LHR Frequency (MHz) Strip Chart")
            self.stats_unit_var.set("MHz")
        elif "Inductance" in selected and "Displacement" not in selected:
            self.ax.set_xlabel("Samples")
            self.ax.set_ylabel("Inductance (µH)")
            self.ax.set_title("LHR Inductance (µH) Strip Chart")
            self.stats_unit_var.set("µH")
        elif "Displacement" in selected:
            self.ax.set_xlabel("Displacement (mm)")
            self.ax.set_ylabel("Inductance (µH)")
            self.ax.set_title("Displacement vs Inductance")
            self.stats_unit_var.set("mm")
            # Refresh graph immediately when switching to Displacement mode
            self._refresh_graph("Inductance (µH)")
            return
        self.canvas.draw_idle()
        self._update_stats_display()

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
        self.displacement_buffer.clear()
        self.displacement_ref = None  # Reset reference point
        self.raw_data_history = []
        self.stat_min.set("0")
        self.stat_max.set("0")
        self.stat_avg.set("0")
        self.stat_std.set("0")
        # Clear stable buffers too
        self.stable_disp_buffer.clear()
        self.stable_ind_buffer.clear()
        self.batch_disp.clear()
        self.batch_ind.clear()
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
