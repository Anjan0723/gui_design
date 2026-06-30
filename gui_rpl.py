import tkinter as tk
from tkinter import ttk
import math

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

RP_L_RESOLUTION_BITS = 16   # RP+L data is 16-bit

class RPLFrame(tk.Frame):
    def __init__(self, parent, colors, fonts, ser_conn=None, **kwargs):
        super().__init__(parent, bg=colors["bg_main"], **kwargs)
        self.colors = colors
        self.fonts  = fonts
        self.ser_conn = ser_conn

        self.rp_buffer  = []   # raw RP data
        self.l_buffer   = []   # raw L data
        self.max_buffer = 200

        # KPI display variables
        self.rp_value_var = tk.StringVar(value="--")
        self.inductance_var = tk.StringVar(value="--")
        self.average_var = tk.StringVar(value="--")
        self.status_var = tk.StringVar(value="Idle")

        self._build_ui()

    def _build_ui(self):
        # Direct frame — no canvas/scrollbar
        parent = self

        # ── Top bar ──
        top = tk.Frame(parent, bg=self.colors["primary"], height=36)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="📈 RP + L Measurement",
            font=self.fonts["title"],
            bg=self.colors["primary"], fg="white").pack(side="left", padx=10, pady=6)
        tk.Label(top, text=f"{RP_L_RESOLUTION_BITS}-bit Resolution",
            font=self.fonts["small"],
            bg=self.colors["primary"], fg="white").pack(side="right", padx=10)

        # ── KPI cards row — reduced height ──
        kpi_frame = tk.Frame(parent, bg=self.colors["bg_main"])
        kpi_frame.pack(fill="x", padx=6, pady=(4,2))

        # KPI Card factory
        def make_kpi(parent, label, var, unit, color):
            card = tk.Frame(parent, bg=self.colors["bg_white"], bd=1, relief="solid",
                          highlightbackground=self.colors["border"], highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=4)

            # Label
            tk.Label(card, text=label.upper(),
                font=self.fonts["kpi_label"],
                bg=self.colors["bg_white"],
                fg=self.colors["text_muted"]).pack(anchor="w", padx=8, pady=(4, 1))

            # Value - reduced font
            tk.Label(card, textvariable=var,
                font=("Segoe UI", 16, "bold"),
                bg=self.colors["bg_white"],
                fg=color).pack(anchor="w", padx=8, pady=(0, 1))

            # Unit
            tk.Label(card, text=unit,
                font=self.fonts["small"],
                bg=self.colors["bg_white"],
                fg=self.colors["text_secondary"]).pack(anchor="w", padx=8, pady=(0, 4))

            return card

        make_kpi(kpi_frame, "Rp Value", self.rp_value_var, "KΩ", self.colors["accent"])
        make_kpi(kpi_frame, "Inductance", self.inductance_var, "µH", self.colors["success"])
        make_kpi(kpi_frame, "Average", self.average_var, "µH", self.colors["info"])
        make_kpi(kpi_frame, "Status", self.status_var, "", self.colors["warning"])

        # ── Separator ──
        ttk.Separator(parent, orient='horizontal').pack(fill='x', padx=10, pady=(4, 4))

        # ── Device & Logging row — single compact row ──
        ctrl_frame = tk.Frame(parent, bg=self.colors["bg_white"], bd=1, relief="solid",
                            highlightbackground=self.colors["border"], highlightthickness=1)
        ctrl_frame.pack(fill="x", padx=6, pady=2)

        # Left controls
        ctrl_left = tk.Frame(ctrl_frame, bg=self.colors["bg_white"])
        ctrl_left.pack(side="left", padx=6, pady=4)

        # Mode button - compact
        self.mode_btn = tk.Button(ctrl_left, text="Sleep",
            font=self.fonts["small"],
            bg=self.colors["bg_section"],
            fg=self.colors["text_secondary"],
            relief="flat",
            padx=8, pady=3,
            cursor="hand2",
            command=self._toggle_mode)
        self.mode_btn.pack(side="left", padx=3)

        # Enable log checkbox
        tk.Checkbutton(ctrl_left, text="Enable Data Log",
            bg=self.colors["bg_white"],
            font=self.fonts["small"]).pack(side="left", padx=6)

        # Right: log file path
        ctrl_right = tk.Frame(ctrl_frame, bg=self.colors["bg_white"])
        ctrl_right.pack(side="left", fill="x", expand=True, padx=6, pady=4)

        self.log_path_var = tk.StringVar(value="C:/logs/rpl_data_log.csv")
        tk.Entry(ctrl_right, textvariable=self.log_path_var,
            width=35, font=self.fonts["small"],
            bg=self.colors["bg_input"]).pack(side="left", fill="x", expand=True)

        def _browse_log():
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
            if path:
                self.log_path_var.set(path)

        tk.Button(ctrl_right, text="📁",
            font=self.fonts["small"],
            command=_browse_log,
            relief="flat", padx=6).pack(side="left", padx=3)

        # ── Sensor params row — compact ──
        params = tk.Frame(parent, bg=self.colors["bg_main"])
        params.pack(fill="x", padx=6, pady=2)

        tk.Label(params, text="Sensor Capacitor (pF):",
            bg=self.colors["bg_main"], font=self.fonts["small"]).pack(side="left")
        self.cap_var = tk.IntVar(value=390)
        tk.Spinbox(params, from_=1, to=10000,
            textvariable=self.cap_var,
            width=5, font=self.fonts["small"]).pack(side="left", padx=2)

        tk.Label(params, text="CLKIN (MHz):",
            bg=self.colors["bg_main"], font=self.fonts["small"]).pack(side="left", padx=(12, 0))
        self.clkin_var = tk.IntVar(value=16)
        tk.Spinbox(params, from_=1, to=20,
            textvariable=self.clkin_var,
            width=3, font=self.fonts["small"]).pack(side="left", padx=2)

        # ── Separator ──
        ttk.Separator(parent, orient='horizontal').pack(fill='x', padx=10, pady=(4, 4))

        # ── Status row — compact, smaller LEDs ──
        status_frame = tk.Frame(parent, bg=self.colors["bg_white"], bd=1, relief="solid",
                               highlightbackground=self.colors["border"], highlightthickness=1)
        status_frame.pack(fill="x", padx=6, pady=2)

        tk.Label(status_frame, text="STATUS",
            font=self.fonts["kpi_label"],
            bg=self.colors["bg_white"],
            fg=self.colors["text_muted"]).pack(anchor="w", padx=8, pady=(4, 2))

        # Status bits from STATUS register 0x20 - organized in grid
        status_indicators = [
            (0, "POR_Read"), (4, "RP_HI_LON"), (2, "L_HI_LON"),
            (6, "DRDYB"), (5, "RP_HIN"), (3, "L_HIN"), (7, "NO_SENSOR_OSC"),
        ]

        # Create a grid layout for status indicators
        status_grid = tk.Frame(status_frame, bg=self.colors["bg_white"])
        status_grid.pack(anchor="w", padx=8, pady=(0, 4))

        self.status_leds = {}
        for i, (bit, name) in enumerate(status_indicators):
            row = i // 4
            col = i % 4

            # Container for each indicator
            indicator_frame = tk.Frame(status_grid, bg=self.colors["bg_white"])
            indicator_frame.grid(row=row, column=col, padx=8, pady=2, sticky="w")

            led = tk.Label(indicator_frame, text="●",
                font=("Segoe UI", 9),
                bg=self.colors["led_green"], fg=self.colors["led_green"])
            led.pack(side="left")

            tk.Label(indicator_frame, text=name,
                bg=self.colors["bg_white"],
                font=("Segoe UI", 8)).pack(side="left", padx=4)

            self.status_leds[name] = (led, bit)

        # ── Separator ──
        ttk.Separator(parent, orient='horizontal').pack(fill='x', padx=10, pady=(4, 4))

        # ── Graphs row — takes remaining space ──
        graphs_row = tk.Frame(parent, bg=self.colors["bg_main"])
        graphs_row.pack(fill="both", expand=True, padx=6, pady=2)

        self._build_rp_graph(graphs_row)
        self._build_l_graph(graphs_row)

    def _build_rp_graph(self, parent):
        """Left — RP Data strip chart - smaller size."""
        frame = tk.LabelFrame(parent, text="RP Data",
            bg=self.colors["bg_main"], font=self.fonts["heading"])
        frame.pack(side="left", fill="both", expand=True, padx=(0,4))

        # Controls
        ctrl = tk.Frame(frame, bg=self.colors["bg_main"])
        ctrl.pack(fill="x", padx=4, pady=2)
        tk.Label(ctrl, text="Display:",
            bg=self.colors["bg_main"],
            font=self.fonts["small"]).pack(side="left")
        self.rp_display_var = tk.StringVar(value="Rp (KOhms)")
        rp_opts = ["Rp (KOhms)", "Count"]
        ttk.Combobox(ctrl, textvariable=self.rp_display_var,
            values=rp_opts, width=10,
            state="readonly").pack(side="left", padx=2)

        # Chart - smaller size
        fig_rp = Figure(figsize=(4, 2.2), dpi=75)
        self.ax_rp = fig_rp.add_subplot(111)
        # White theme for chart
        fig_rp.patch.set_facecolor('#FFFFFF')
        self.ax_rp.set_facecolor('#F5F7FA')
        self.ax_rp.tick_params(colors='#212121')
        self.ax_rp.xaxis.label.set_color('#212121')
        self.ax_rp.yaxis.label.set_color('#212121')
        self.ax_rp.spines['bottom'].set_color('#DADCE0')
        self.ax_rp.spines['left'].set_color('#DADCE0')
        self.ax_rp.spines['top'].set_color('#DADCE0')
        self.ax_rp.spines['right'].set_color('#DADCE0')
        self.ax_rp.grid(color='#DADCE0', linestyle='--')
        self.ax_rp.set_xlabel("Samples", fontsize=8)
        self.ax_rp.set_ylabel("Rp (KOhms)", fontsize=8)
        # Default axis ranges
        self.ax_rp.set_ylim(0.65, 0.85)
        self.ax_rp.set_xlim(0, 200)
        self.ax_rp.yaxis.set_major_formatter(
            matplotlib.ticker.FormatStrFormatter('%.3f'))
        self.rp_line, = self.ax_rp.plot([], [],
            color="#1f77b4", linewidth=1.5)
        canvas_rp = FigureCanvasTkAgg(fig_rp, master=frame)
        canvas_rp.get_tk_widget().pack(fill="both", expand=True)

        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar_rp = NavigationToolbar2Tk(canvas_rp, frame)
        toolbar_rp.update()
        toolbar_rp.pack(side="bottom", fill="x")
        # Reduce toolbar padding
        for child in toolbar_rp.winfo_children():
            child.pack_configure(pady=0)

        self.canvas_rp = canvas_rp

        # Statistics
        self._build_stats(frame, prefix="rp", unit="KOhms", color="#1a3a5c")

    def _build_l_graph(self, parent):
        """Right — Inductance/Fsensor strip chart - smaller size."""
        frame = tk.LabelFrame(parent, text="Inductance",
            bg=self.colors["bg_main"], font=self.fonts["heading"])
        frame.pack(side="left", fill="both", expand=True)

        # Controls
        ctrl = tk.Frame(frame, bg=self.colors["bg_main"])
        ctrl.pack(fill="x", padx=4, pady=2)
        tk.Label(ctrl, text="Display:",
            bg=self.colors["bg_main"],
            font=self.fonts["small"]).pack(side="left")
        self.l_display_var = tk.StringVar(value="Inductance (µH)")
        l_opts = ["Count", "Inductance (µH)", "Fsensor (MHz)", "% of Full Scale"]
        ttk.Combobox(ctrl, textvariable=self.l_display_var,
            values=l_opts, width=12,
            state="readonly").pack(side="left", padx=2)

        tk.Label(ctrl, text="Update:",
            bg=self.colors["bg_main"],
            font=self.fonts["small"]).pack(side="left", padx=(6, 0))
        self.update_rate_var = tk.StringVar(value="1:1")
        ttk.Combobox(ctrl, textvariable=self.update_rate_var,
            values=["1:1","1:2","1:5","1:10"],
            width=4, state="readonly").pack(side="left", padx=2)

        # Chart - smaller size
        fig_l = Figure(figsize=(4, 2.2), dpi=75)
        self.ax_l = fig_l.add_subplot(111)
        # White theme for chart
        fig_l.patch.set_facecolor('#FFFFFF')
        self.ax_l.set_facecolor('#F5F7FA')
        self.ax_l.tick_params(colors='#212121')
        self.ax_l.xaxis.label.set_color('#212121')
        self.ax_l.yaxis.label.set_color('#212121')
        self.ax_l.spines['bottom'].set_color('#DADCE0')
        self.ax_l.spines['left'].set_color('#DADCE0')
        self.ax_l.spines['top'].set_color('#DADCE0')
        self.ax_l.spines['right'].set_color('#DADCE0')
        self.ax_l.grid(color='#DADCE0', linestyle='--')
        self.ax_l.set_xlabel("Samples", fontsize=8)
        self.ax_l.set_ylabel("Inductance (µH)", fontsize=8)
        # Default axis ranges
        self.ax_l.set_ylim(-1.25, 1.5)
        self.ax_l.set_xlim(0, 200)
        self.l_line, = self.ax_l.plot([], [],
            color="#2ca02c", linewidth=1.5)
        canvas_l = FigureCanvasTkAgg(fig_l, master=frame)
        canvas_l.get_tk_widget().pack(fill="both", expand=True)

        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar_l = NavigationToolbar2Tk(canvas_l, frame)
        toolbar_l.update()
        toolbar_l.pack(side="bottom", fill="x")
        # Reduce toolbar padding
        for child in toolbar_l.winfo_children():
            child.pack_configure(pady=0)

        self.canvas_l = canvas_l

        # Statistics
        self._build_stats(frame, prefix="l", unit="µH", color="#1a5c1a")

    def _build_stats(self, parent, prefix, unit, color):
        """Statistics row — Minimum, Maximum, Average, Std.dev - compact."""
        sf = tk.Frame(parent, bg=self.colors["bg_main"])
        sf.pack(fill="x", padx=4, pady=1)

        for label, attr in [
            ("Min", f"{prefix}_min"),
            ("Max", f"{prefix}_max"),
            ("Avg", f"{prefix}_avg"),
            ("σ", f"{prefix}_std"),
        ]:
            var = tk.StringVar(value="0.00")
            setattr(self, attr, var)
            tk.Label(sf, text=f"{label}:",
                font=("Segoe UI", 8),
                bg=self.colors["bg_main"],
                fg=color).pack(side="left", padx=(5, 1))
            tk.Label(sf, textvariable=var,
                font=("Consolas", 8, "bold"),
                bg=self.colors["bg_main"],
                fg=color).pack(side="left")

    def update_from_registers(self, reg_live_values):
        """Called by gui_main polling loop with latest register values."""
        # STATUS register 0x20 → update LEDs
        status_reg = reg_live_values.get(0x20, 0x00)
        status_map = {
            "POR_Read": 0, "DRDYB": 6, "RP_HIN": 5,
            "RP_HI_LON": 4, "L_HIN": 3, "L_HI_LON": 2,
            "NO_SENSOR_OSC": 7
        }

        # Determine status
        drdyb = (status_reg >> 6) & 1
        if drdyb:
            self.status_var.set("Waiting")
        else:
            self.status_var.set("Data Ready")

        for name, (led, bit) in self.status_leds.items():
            bit_num = status_map.get(name, 0)
            val = (status_reg >> bit_num) & 1
            if val:
                led.config(fg=self.colors["led_red"], text="●")
            else:
                led.config(fg=self.colors["led_green"], text="●")

        # RP_DATA register 0x22 (16-bit: 0x22 LSB, 0x23 MSB)
        rp_lsb = reg_live_values.get(0x22, 0)
        rp_msb = reg_live_values.get(0x23, 0)
        rp_raw = (rp_msb << 8) | rp_lsb   # 16-bit RP value

        # L_DATA register 0x28 (16-bit: 0x28 LSB, 0x29 MSB)
        l_lsb = reg_live_values.get(0x28, 0)
        l_msb = reg_live_values.get(0x29, 0)
        l_raw = (l_msb << 8) | l_lsb      # 16-bit L value

        # Convert RP raw to KOhms
        rp_kohms = rp_raw / 1000.0 if rp_raw > 0 else 0.0

        # Convert L raw to inductance µH
        c_f = self.cap_var.get() * 1e-12
        clkin = self.clkin_var.get() * 1e6
        if l_raw > 0 and c_f > 0 and clkin > 0:
            f_hz = (clkin * l_raw) / 65536.0
            L_uH = (1.0 / (4.0 * math.pi**2 * f_hz**2 * c_f)) * 1e6 \
                   if f_hz > 0 else 0.0
        else:
            f_hz = 0.0
            L_uH = 0.0

        # Update KPI cards
        self.rp_value_var.set(f"{rp_kohms:.2f}")
        self.inductance_var.set(f"{L_uH:.2f}")

        # Add to buffers
        if len(self.rp_buffer) >= self.max_buffer:
            self.rp_buffer.pop(0)
        self.rp_buffer.append(rp_kohms)

        if len(self.l_buffer) >= self.max_buffer:
            self.l_buffer.pop(0)
        self.l_buffer.append(L_uH)

        # Update average if we have data
        if self.l_buffer:
            avg = sum(self.l_buffer) / len(self.l_buffer)
            self.average_var.set(f"{avg:.2f}")

        self._update_rp_graph()
        self._update_l_graph(f_hz, L_uH)
        self._update_stats_display()

    def _update_rp_graph(self):
        selected = self.rp_display_var.get()
        vals = self.rp_buffer if "KOhms" in selected \
               else list(range(len(self.rp_buffer)))
        if len(vals) >= 2:
            self.rp_line.set_xdata(range(len(vals)))
            self.rp_line.set_ydata(vals)
            self.ax_rp.set_xlim(0, max(200, len(vals)))
            # Only update ylim when real non-zero data exists
            if len(vals) >= 2 and max(vals) != min(vals) and any(v != 0 for v in vals):
                margin = max(0.01, (max(vals)-min(vals))*0.2)
                self.ax_rp.set_ylim(min(vals)-margin, max(vals)+margin)
            self.ax_rp.set_ylabel(
                "Rp (KOhms)" if "KOhms" in selected else "Count")
            self.canvas_rp.draw_idle()

    def _update_l_graph(self, f_hz, L_uH):
        selected = self.l_display_var.get()
        if "Inductance" in selected:
            vals = self.l_buffer
            ylabel = "Inductance (µH)"
        elif "Fsensor" in selected:
            vals = [f_hz/1e6] * len(self.l_buffer)
            ylabel = "Fsensor (MHz)"
        elif "%" in selected:
            vals = [(v / 1.5 * 100) for v in self.l_buffer]
            ylabel = "% of Full Scale"
        else:
            vals = list(range(len(self.l_buffer)))
            ylabel = "Count"
        if len(vals) >= 2:
            self.l_line.set_xdata(range(len(vals)))
            self.l_line.set_ydata(vals)
            self.ax_l.set_xlim(0, max(200, len(vals)))
            # Only update ylim when real non-zero data exists
            if len(vals) >= 2 and max(vals) != min(vals) and any(v != 0 for v in vals):
                margin = max(0.01, (max(vals)-min(vals))*0.2)
                self.ax_l.set_ylim(min(vals)-margin, max(vals)+margin)
            self.ax_l.set_ylabel(ylabel, fontsize=9)
            self.canvas_l.draw_idle()

    def _update_stats_display(self):
        for buf, prefix, unit in [
            (self.rp_buffer, "rp", "KOhms"),
            (self.l_buffer,  "l",  "µH"),
        ]:
            if buf:
                avg = sum(buf) / len(buf)
                std = (sum((x-avg)**2 for x in buf)/len(buf))**0.5
                getattr(self, f"{prefix}_min").set(f"{min(buf):.2f}")
                getattr(self, f"{prefix}_max").set(f"{max(buf):.2f}")
                getattr(self, f"{prefix}_avg").set(f"{avg:.2f}")
                getattr(self, f"{prefix}_std").set(f"{std:.2f}")

    def _toggle_mode(self):
        if self.mode_btn["text"] in ("Sleep", "● Sleep"):
            # Switch to Running
            self.mode_btn.config(
                text="● Running",
                bg="#1b5e20",
                fg="white",
                activebackground="#2e7d32")
        else:
            # Switch to Sleep
            self.mode_btn.config(
                text="Sleep",
                bg=self.colors["bg_section"],
                fg=self.colors["text_secondary"],
                activebackground=self.colors["bg_section"])

    def reset_buffers(self):
        self.rp_buffer.clear()
        self.l_buffer.clear()