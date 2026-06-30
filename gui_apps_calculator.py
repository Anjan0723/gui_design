# ═══════════════════════════════════════════════════════════════
#  APPS CALCULATOR UI - NO TARGET panel (redesigned)
# ═══════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk, messagebox
from config import COLORS, FONTS
from register_data import (
    RP_OPTIONS_LABELS, RP_OPTIONS_VALUES, C1_OPTIONS_LABELS, C1_OPTIONS_VALUES,
    C2_OPTIONS_LABELS, C2_OPTIONS_VALUES, R1_OPTIONS_LABELS, R2_OPTIONS_LABELS
)
from calculations import (
    calc_fsensor, calc_qmin, calc_r1, calc_r2,
    find_nearest_r1, find_nearest_r2, parse_capacitance, parse_sensor,
    safe_float, format_freq, format_res
)


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


class AppsCalculatorUI:
    """Apps Calculator panel with NO TARGET section (redesigned)."""

    # Constants for validation
    FSENSOR_MIN = 500e3   # 500 kHz
    FSENSOR_MAX = 10e6    # 10 MHz
    Q_MIN = 10
    Q_MAX = 400
    R1_MIN = 21.1e3       # 21.1 kOhms
    R1_MAX = 417e3        # 417 kOhms
    R2_MIN = 30.5e3       # 30.5 kOhms
    R2_MAX = 835e3        # 835 kOhms
    RP_MIN_DROPDOWN = 750  # Minimum Rp from dropdown (0.75k Ohms)

    def __init__(self, parent, reg_live_values, reg_lw, set_status_callback, register_map_callback=None):
        self.parent = parent
        self.reg_live_values = reg_live_values
        self.reg_lw = reg_lw
        self.set_status = set_status_callback
        self.register_map_callback = register_map_callback

        self.frame = tk.Frame(parent, bg=COLORS["bg_main"])

        # Create variables
        self._create_variables()

        # Build UI (redesigned)
        self._build_header()
        self._build_content()
        self._build_buttons()

        # Set defaults
        self._set_defaults()

    def _create_variables(self):
        """Create all tkinter variables."""
        # NO TARGET inputs
        self.nt_csensor_var = tk.StringVar()
        self.nt_lsensor_var = tk.StringVar()
        self.nt_fsensor_var = tk.StringVar()
        self.nt_rs_var = tk.StringVar()
        self.nt_rp_var = tk.StringVar()
        self.nt_rp_calc_var = tk.StringVar()  # Calculated RP
        self.nt_rpmin_var = tk.StringVar(value=RP_OPTIONS_LABELS[5])  # 3k default
        self.nt_rpmax_var = tk.StringVar(value=RP_OPTIONS_LABELS[2])   # 24k default
        self.nt_qmin_var = tk.StringVar()
        self.nt_c1_var = tk.StringVar(value=C1_OPTIONS_LABELS[2])     # 3p default
        self.nt_r1_var = tk.StringVar()
        self.nt_r1_calc_var = tk.StringVar()  # Calculated R1
        self.nt_c2_var = tk.StringVar(value=C2_OPTIONS_LABELS[2])     # 12p default
        self.nt_r2_var = tk.StringVar()
        self.nt_r2_calc_var = tk.StringVar()  # Calculated R2
        self.nt_min_freq_var = tk.StringVar()  # Min_frequency
        self.nt_response_var = tk.StringVar()  # response_time (user input)
        self.nt_convtime_var = tk.StringVar()  # ConvTime (calculated)

    def _build_header(self):
        """Build page header with title and connection badge."""
        # Page header bar - modern style
        header = tk.Frame(self.frame, bg=COLORS["primary"], height=50)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🧮 Apps Calculator",
            font=FONTS["title"],
            bg=COLORS["primary"], fg="white").pack(side="left", padx=15, pady=10)

        # Connection status badge — modern badge style
        self.conn_badge = tk.Label(header,
            text="○ NOT CONNECTED",
            font=FONTS["small_bold"],
            bg=COLORS["error"],
            fg="white",
            padx=12,
            pady=4,
            relief="flat")
        self.conn_badge.pack(side="right", padx=15, pady=10)

    def _build_content(self):
        """Build main content area with left and right panels."""
        # Main content area
        content = tk.Frame(self.frame, bg=COLORS["bg_main"])
        content.pack(fill="both", expand=True, padx=15, pady=10)

        # Left panel - Input Parameters
        left = tk.LabelFrame(content, text="NO TARGET  (d = ∞)",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_main"], fg="#1a3a5c",
            relief="groove", bd=2)
        left.pack(side="left", fill="both", expand=True, padx=(0,8))

        # Right panel - Calculated Results
        right = tk.LabelFrame(content, text="Calculated Results",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_main"], fg="#1a3a5c",
            relief="groove", bd=2)
        right.pack(side="left", fill="both", expand=True)

        # Build left panel content
        self._build_left_panel(left)

        # Build right panel content
        self._build_right_panel(right)

    def _build_left_panel(self, parent):
        """Build left panel with sensor and loop parameters."""
        # Input entry style - white background with border
        input_entry_style = {
            "font": FONTS["normal"],
            "bg":   COLORS["bg_white"],
            "fg":   COLORS["text_primary"],
            "relief": "flat",
            "bd": 1,
            "highlightbackground": COLORS["border"],
            "highlightthickness": 1,
            "highlightcolor": COLORS["border_focus"],
            "width": 14
        }

        # Sensor Parameters section
        tk.Label(parent, text="Sensor Parameters",
            font=FONTS["heading"],
            bg=COLORS["bg_main"], fg=COLORS["accent"]).pack(anchor="w", padx=10, pady=(10,2))

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=10, pady=2)

        # Csensor
        self._make_input_field(parent, "Csensor", self.nt_csensor_var, input_entry_style, pady=(8,4))

        # Lsensor
        self._make_input_field(parent, "Lsensor", self.nt_lsensor_var, input_entry_style, pady=4)

        # Rs_parasitic
        self._make_input_field(parent, "Rs_parasitic", self.nt_rs_var, input_entry_style, pady=4)

        # Loop Parameters section
        tk.Label(parent, text="Loop Parameters",
            font=FONTS["heading"],
            bg=COLORS["bg_main"], fg=COLORS["accent"]).pack(anchor="w", padx=10, pady=(15,2))

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=10, pady=2)

        # Rp_Min dropdown with warning
        self._make_dropdown_field(parent, "Rp_Min", self.nt_rpmin_var, RP_OPTIONS_LABELS, input_entry_style, pady=(8,4), has_warning=True)

        # Rp_Max dropdown with warning
        self._make_dropdown_field(parent, "Rp_Max", self.nt_rpmax_var, RP_OPTIONS_LABELS, input_entry_style, pady=4, has_warning=True)

        # C1 dropdown
        self._make_dropdown_field(parent, "C1", self.nt_c1_var, C1_OPTIONS_LABELS, input_entry_style, pady=4)

        # C2 dropdown
        self._make_dropdown_field(parent, "C2", self.nt_c2_var, C2_OPTIONS_LABELS, input_entry_style, pady=4)

        # Response time (user input)
        self._make_input_field(parent, "Response time (µs)", self.nt_response_var, input_entry_style, pady=4)

    def _build_right_panel(self, parent):
        """Build right panel with calculated results."""
        # Result style (read-only, light green background - indicates output)
        result_style = {
            "font": FONTS["value"],
            "bg":   COLORS["bg_output"],
            "fg":   COLORS["success"],
            "relief": "flat",
            "bd": 1,
            "state": "readonly",
            "readonlybackground": COLORS["bg_output"],
            "highlightbackground": COLORS["border"],
            "highlightthickness": 1,
            "width": 16
        }

        # Input style (white background with blue focus)
        input_style = {
            "font": FONTS["normal"],
            "bg":   COLORS["bg_white"],
            "fg":   COLORS["text_primary"],
            "relief": "flat",
            "bd": 1,
            "highlightbackground": COLORS["border"],
            "highlightthickness": 1,
            "highlightcolor": COLORS["border_focus"],
            "width": 14
        }

        # Fsensor with warning
        self._make_result_field(parent, "Fsensor", self.nt_fsensor_var, result_style, "Hz", pady=(10,4), has_warning=True)

        # Rp_parasitic
        self._make_result_field(parent, "Rp_parasitic", self.nt_rp_calc_var, result_style, "Ω", pady=4)

        # Q_Factor with warning
        self._make_result_field(parent, "Q_Factor", self.nt_qmin_var, result_style, "", pady=4, has_warning=True)

        # R1 (calculated) with warning
        self._make_result_field(parent, "R1 (calculated)", self.nt_r1_calc_var, result_style, "Ω", pady=4, has_warning=True)

        # R2 (calculated) with warning
        self._make_result_field(parent, "R2 (calculated)", self.nt_r2_calc_var, result_style, "Ω", pady=4, has_warning=True)

        # Min_frequency
        self._make_result_field(parent, "Min_frequency", self.nt_min_freq_var, result_style, "", pady=4)

        # Response time
        self._make_result_field(parent, "Response time", self.nt_response_var, result_style, "µs", pady=4)

        # ConvTime
        self._make_result_field(parent, "ConvTime", self.nt_convtime_var, result_style, "µs", pady=4)

        # Frequency range info box
        self._build_freq_info_box(parent)

    def _build_freq_info_box(self, parent):
        """Build frequency range info box at bottom of right panel."""
        info_frame = tk.Frame(parent, bg=COLORS["info_bg"], bd=1, relief="solid",
                             highlightbackground=COLORS["accent_blue"], highlightthickness=1)
        info_frame.pack(fill="x", padx=10, pady=15)

        tk.Label(info_frame, text="📡 Valid Sensor Frequency Range",
            font=FONTS["label_bold"],
            bg=COLORS["info_bg"], fg=COLORS["primary"]).pack(anchor="w", padx=12, pady=(8, 4))

        freq_row = tk.Frame(info_frame, bg=COLORS["info_bg"])
        freq_row.pack(fill="x", padx=12, pady=(0, 8))

        tk.Label(freq_row, text="Min:", font=FONTS["small"],
            bg=COLORS["info_bg"]).pack(side="left")
        self.freq_min_lbl = tk.Label(freq_row, text="500 kHz",
            font=FONTS["small_bold"], bg=COLORS["info_bg"], fg=COLORS["primary"])
        self.freq_min_lbl.pack(side="left", padx=(4, 20))

        tk.Label(freq_row, text="Max:", font=FONTS["small"],
            bg=COLORS["info_bg"]).pack(side="left")
        self.freq_max_lbl = tk.Label(freq_row, text="10 MHz",
            font=FONTS["small_bold"], bg=COLORS["info_bg"], fg=COLORS["primary"])
        self.freq_max_lbl.pack(side="left", padx=4)

        tk.Label(freq_row, text="  ⚠ Fsensor must be within this range",
            font=FONTS["tiny_italic"], bg=COLORS["info_bg"], fg=COLORS["text_muted"]).pack(side="left")

    def _make_input_field(self, parent, label_text, var, style, pady=4, tooltip=None, has_warning=False):
        """Create an input field with label."""
        row = tk.Frame(parent, bg=COLORS["bg_main"])
        row.pack(fill="x", padx=10, pady=pady)

        tk.Label(row, text=label_text, font=("Segoe UI", 9),
            bg=COLORS["bg_main"], fg="#333333", anchor="w", width=14).pack(side="left")

        entry = tk.Entry(row, textvariable=var, **style)
        entry.pack(side="left", fill="x", expand=True)

        if tooltip:
            Tooltip(entry, tooltip)

        # Add warning label if needed
        if has_warning:
            warn_lbl = tk.Label(row, text="", font=("Segoe UI", 8),
                              fg="#cc0000", bg=COLORS["bg_main"], anchor="w")
            warn_lbl.pack(side="left", padx=4)
            # Store reference based on label text
            if "Fsensor" in label_text:
                self.nt_fsensor_warn = warn_lbl
            elif "Q_Factor" in label_text:
                self.nt_q_warn = warn_lbl
            elif "R1" in label_text:
                self.nt_r1_warn = warn_lbl
            elif "R2" in label_text:
                self.nt_r2_warn = warn_lbl

        return entry if has_warning else None

    def _make_result_field(self, parent, label_text, var, style, unit, pady=4, has_warning=False):
        """Create a result field (read-only) with label and unit."""
        row = tk.Frame(parent, bg=COLORS["bg_main"])
        row.pack(fill="x", padx=10, pady=pady)

        tk.Label(row, text=label_text, font=("Segoe UI", 9),
            bg=COLORS["bg_main"], fg="#333333", anchor="w", width=14).pack(side="left")

        entry = tk.Entry(row, textvariable=var, **style)
        entry.config(bg='#FFFFFF', fg='#212121', insertbackground='#212121', relief='solid', bd=1)
        entry.pack(side="left", fill="x", expand=True)

        if unit:
            tk.Label(row, text=unit, font=("Segoe UI", 9),
                bg=COLORS["bg_main"], fg="#666666", anchor="w").pack(side="left", padx=4)

        # Add warning label if needed
        if has_warning:
            warn_lbl = tk.Label(row, text="", font=("Segoe UI", 8),
                              fg="#cc0000", bg=COLORS["bg_main"], anchor="w")
            warn_lbl.pack(side="left", padx=4)
            # Store reference based on label text
            if "Fsensor" in label_text:
                self.nt_fsensor_warn = warn_lbl
            elif "Q_Factor" in label_text:
                self.nt_q_warn = warn_lbl
            elif "R1" in label_text:
                self.nt_r1_warn = warn_lbl
            elif "R2" in label_text:
                self.nt_r2_warn = warn_lbl

    def _make_dropdown_field(self, parent, label_text, var, options, style, pady=4, has_warning=False):
        """Create a dropdown field with label."""
        row = tk.Frame(parent, bg=COLORS["bg_main"])
        row.pack(fill="x", padx=10, pady=pady)

        tk.Label(row, text=label_text, font=("Segoe UI", 9),
            bg=COLORS["bg_main"], fg="#333333", anchor="w", width=14).pack(side="left")

        cb_frame = tk.Frame(row, bg=COLORS["bg_main"])
        cb_frame.pack(side="left", fill="x", expand=True)

        cb = ttk.Combobox(cb_frame, textvariable=var, values=options,
                          state="readonly", font=("Segoe UI", 10), width=12)
        cb.pack(side="left", fill="x", expand=True)

        # Add warning label if needed
        if has_warning:
            warn_lbl = tk.Label(row, text="", font=("Segoe UI", 8),
                              fg="#cc0000", bg=COLORS["bg_main"], anchor="w")
            warn_lbl.pack(side="left", padx=4)
            # Store reference based on label text
            if "Rp_Max" in label_text:
                self.nt_rpmax_warn = warn_lbl
            elif "Rp_Min" in label_text:
                self.nt_rpmin_warn = warn_lbl

    def _build_buttons(self):
        """Build Calculate and Update Registers buttons."""
        btn_frame = tk.Frame(self.frame, bg=COLORS["bg_main"])
        btn_frame.pack(fill="x", padx=15, pady=(0,10))

        calc_btn = tk.Button(btn_frame, text="⟳  Calculate",
            font=("Segoe UI", 10, "bold"),
            bg="#1a3a5c", fg="white",
            activebackground="#2a5a8c", activeforeground="white",
            relief="flat", padx=15, pady=6,
            cursor="hand2",
            command=self.recalculate)
        calc_btn.pack(side="left", pady=(15,5), padx=(0,10))

        update_btn = tk.Button(btn_frame, text="↑  Update Registers",
            font=("Segoe UI", 10, "bold"),
            bg="#2e7d32", fg="white",
            activebackground="#1b5e20", activeforeground="white",
            relief="flat", padx=15, pady=6,
            cursor="hand2",
            command=self.update_registers)
        update_btn.pack(side="left", pady=5)

    def set_connection_status(self, connected: bool, port: str = ""):
        """Update the connection status badge."""
        if connected:
            self.conn_badge.config(
                text=f"● CONNECTED  {port}",
                bg=COLORS["success"],
                fg="white")
        else:
            self.conn_badge.config(
                text="○ NOT CONNECTED",
                bg=COLORS["error"],
                fg="white")

    def _set_warning(self, label, text, color):
        """Update warning label text and color."""
        if label is None:
            return
        label.config(text=text)
        if color == "red":
            label.config(fg="#cc0000")
        elif color == "orange":
            label.config(fg="#cc6600")
        else:
            label.config(fg=COLORS["bg_main"])  # Hide by matching bg

    def _set_defaults(self):
        """Set default values."""
        self.nt_csensor_var.set("330pF")
        self.nt_lsensor_var.set("9uH")
        self.nt_rs_var.set("5Ohms")

    def get_frame(self):
        """Return the main frame."""
        return self.frame

    def recalculate(self, *args):
        """Main calculation function with all validations."""
        self._calculate_no_target()

    def _calculate_no_target(self):
        """Calculate NO TARGET panel values with validations."""
        # Parse NO TARGET inputs
        csensor_str = self.nt_csensor_var.get()
        lsensor_str = self.nt_lsensor_var.get()
        rs_str = self.nt_rs_var.get()

        # Parse Csensor
        C_F, c_display = parse_capacitance(csensor_str)
        if C_F is None:
            self.set_status("Error: Invalid Csensor value")
            return
        self.nt_csensor_var.set(c_display)

        # Parse other sensors
        L_H = parse_sensor(lsensor_str, {"uH": 1e-6, "mH": 1e-3, "nH": 1e-9,
                                          "u": 1e-6, "m": 1e-3, "n": 1e-9})
        Rs = parse_sensor(rs_str, {"kOhms": 1e3, "Ohms": 1, "k": 1e3})

        # NO TARGET Fsensor
        f_nt = calc_fsensor(L_H, C_F)
        self.nt_fsensor_var.set(format_freq(f_nt) if f_nt else "")

        # ===== 1. FSENSOR RANGE VALIDATION =====
        if f_nt is not None:
            if f_nt < self.FSENSOR_MIN:
                self._set_warning(self.nt_fsensor_warn, "⚠ too small", "orange")
            elif f_nt > self.FSENSOR_MAX:
                self._set_warning(self.nt_fsensor_warn, "⚠ too large", "red")
            else:
                self._set_warning(self.nt_fsensor_warn, "", None)
        else:
            self._set_warning(self.nt_fsensor_warn, "", None)

        # ===== 2. RP CALCULATION AND VALIDATION =====
        # RP = L / (Rs × C)
        RP_calc = None
        if L_H and Rs and C_F and Rs > 0:
            RP_calc = L_H / (Rs * C_F)
        self.nt_rp_calc_var.set(format_res(RP_calc) if RP_calc else "")

        # RP values for validation
        rp_min_idx = RP_OPTIONS_LABELS.index(self.nt_rpmin_var.get())
        rp_max_idx = RP_OPTIONS_LABELS.index(self.nt_rpmax_var.get())
        rp_min_val = RP_OPTIONS_VALUES[rp_min_idx]
        rp_max_val = RP_OPTIONS_VALUES[rp_max_idx]

        # RP_MAX validation
        if RP_calc:
            if RP_calc > rp_max_val * 2:
                self._set_warning(self.nt_rpmax_warn, "⚠ Too Large", "red")
            elif rp_max_val < RP_calc:
                self._set_warning(self.nt_rpmax_warn, "⚠ Too Small", "orange")
            else:
                self._set_warning(self.nt_rpmax_warn, "", None)
        else:
            self._set_warning(self.nt_rpmax_warn, "", None)

        # RP_MIN validation
        if RP_calc:
            if rp_min_val >= 0.8 * RP_calc:
                self._set_warning(self.nt_rpmin_warn, "⚠ Too Large", "red")
            elif rp_min_val < self.RP_MIN_DROPDOWN:
                self._set_warning(self.nt_rpmin_warn, "⚠ Too Small", "orange")
            else:
                self._set_warning(self.nt_rpmin_warn, "", None)
        else:
            self._set_warning(self.nt_rpmin_warn, "", None)

        # ===== 3. Q_FACTOR CALCULATION AND VALIDATION =====
        # Q = RP × sqrt(C/L) = (1/Rs) × sqrt(L/C)
        q_val = None
        if L_H and C_F and Rs and Rs > 0:
            q_val = (1 / Rs) * (L_H / C_F) ** 0.5

        if q_val is not None:
            if q_val > self.Q_MAX:
                self._set_warning(self.nt_q_warn, "⚠ Too Large", "red")
            elif q_val < self.Q_MIN:
                self._set_warning(self.nt_q_warn, "⚠ Too Small", "orange")
            else:
                self._set_warning(self.nt_q_warn, "", None)
        else:
            self._set_warning(self.nt_q_warn, "", None)

        self.nt_qmin_var.set(f"{q_val:.2f}" if q_val else "")

        # ===== 4. R1 FORMULA AND VALIDATION =====
        # R1 = (√2 / (π × 0.6 × fSENSOR)) / C1
        c1_idx = C1_OPTIONS_LABELS.index(self.nt_c1_var.get())
        C1_val = C1_OPTIONS_VALUES[c1_idx]

        r1_calc = None
        if f_nt and C1_val:
            r1_calc = calc_r1(C1_val, f_nt)

        if r1_calc is not None:
            if r1_calc > self.R1_MAX:
                self._set_warning(self.nt_r1_warn, "⚠ Too Large", "red")
            elif r1_calc < self.R1_MIN:
                self._set_warning(self.nt_r1_warn, "⚠ Too Small", "orange")
            else:
                self._set_warning(self.nt_r1_warn, "", None)
        else:
            self._set_warning(self.nt_r1_warn, "", None)

        self.nt_r1_calc_var.set(format_res(r1_calc) if r1_calc else "")

        # Find nearest valid R1
        r1_idx = find_nearest_r1(r1_calc)
        if r1_idx is not None:
            self.nt_r1_var.set(R1_OPTIONS_LABELS[r1_idx])

        # ===== 5. R2 FORMULA AND VALIDATION =====
        # R2 = (2 × RP_MIN × Csensor) / C2
        c2_idx = C2_OPTIONS_LABELS.index(self.nt_c2_var.get())
        C2_val = C2_OPTIONS_VALUES[c2_idx]

        r2_calc = None
        if rp_min_val and C_F and C2_val:
            r2_calc = (2 * rp_min_val * C_F) / C2_val

        if r2_calc is not None:
            if r2_calc > self.R2_MAX:
                self._set_warning(self.nt_r2_warn, "⚠ Too Large", "red")
            elif r2_calc < self.R2_MIN:
                self._set_warning(self.nt_r2_warn, "⚠ Too Small", "orange")
            else:
                self._set_warning(self.nt_r2_warn, "", None)
        else:
            self._set_warning(self.nt_r2_warn, "", None)

        self.nt_r2_calc_var.set(format_res(r2_calc) if r2_calc else "")

        # Find nearest valid R2
        r2_idx = find_nearest_r2(r2_calc)
        if r2_idx is not None:
            self.nt_r2_var.set(R2_OPTIONS_LABELS[r2_idx])

        # ===== 6. MIN_FREQUENCY =====
        # Min_frequency = 16 - (8MHz / fSENSOR_MIN)
        if f_nt and f_nt > 0:
            min_freq = 16 - (8e6 / f_nt)
            self.nt_min_freq_var.set(f"{min_freq:.2f}")

            # ===== 7. CONV TIME =====
            # ConvTime = RESP_TIME / (3 × fSENSOR)
            # Get RESP_TIME from user input (default to 192 if not set)
            response_str = self.nt_response_var.get()
            resp_time = safe_float(response_str) if response_str else 192

            # fSENSOR is f_nt (in Hz)
            # ConvTime in microseconds
            if f_nt > 0:
                conv_time_us = (resp_time * 1e-6) / (3 * f_nt) * 1e6  # Convert to microseconds
                self.nt_convtime_var.set(f"{conv_time_us:.2f}")
            else:
                self.nt_convtime_var.set("")
        else:
            self.nt_min_freq_var.set("")
            self.nt_convtime_var.set("")

    def update_registers(self):
        """Calculate register values and push to register map."""
        # Get dropdown indices
        rp_min_idx = RP_OPTIONS_LABELS.index(self.nt_rpmin_var.get())
        rp_max_idx = RP_OPTIONS_LABELS.index(self.nt_rpmax_var.get())

        # RP_SET register (0x01)
        # bit7=HIGH_Q_SENSOR(0), bits 6:4=RP_MAX, bit3=RESERVED(0), bits 2:0=RP_MIN
        rp_set_val = (rp_max_idx << 4) | (rp_min_idx & 0x07)
        self.reg_live_values[0x01] = rp_set_val & 0xFF
        self.reg_lw[0x01] = f"0x{rp_set_val:02X}"

        # TC1 register (0x02)
        # bits 7:6 = C1, bit5 = RESERVED(0), bits 4:0 = R1_field
        c1_idx = C1_OPTIONS_LABELS.index(self.nt_c1_var.get())

        # Parse R1 calculated value
        r1_calc_str = self.nt_r1_calc_var.get()
        r1_calc = parse_sensor(r1_calc_str, {"kOhms": 1e3, "Ohms": 1, "k": 1e3, "kΩ": 1e3}) if r1_calc_str else None

        # Calculate R1_field: R1_field = round((417000 - R1) / 12770), clamped 0-31
        r1_field = 0
        if r1_calc and r1_calc > 0:
            r1_field = round((417000 - r1_calc) / 12770)
            r1_field = max(0, min(31, r1_field))

        tc1_val = (c1_idx << 6) | (r1_field & 0x1F)
        self.reg_live_values[0x02] = tc1_val
        self.reg_lw[0x02] = f"0x{tc1_val:02X}"

        # TC2 register (0x03)
        # bits 7:6 = C2, bits 5:0 = R2_field
        c2_idx = C2_OPTIONS_LABELS.index(self.nt_c2_var.get())

        # Parse R2 calculated value
        r2_calc_str = self.nt_r2_calc_var.get()
        r2_calc = parse_sensor(r2_calc_str, {"kOhms": 1e3, "Ohms": 1, "k": 1e3, "kΩ": 1e3}) if r2_calc_str else None

        # Calculate R2_field: R2_field = round((835000 - R2) / 12770), clamped 0-63
        r2_field = 0
        if r2_calc and r2_calc > 0:
            r2_field = round((835000 - r2_calc) / 12770)
            r2_field = max(0, min(63, r2_field))

        tc2_val = (c2_idx << 6) | (r2_field & 0x3F)
        self.reg_live_values[0x03] = tc2_val
        self.reg_lw[0x03] = f"0x{tc2_val:02X}"

        # DIG_CONF register (0x04)
        # bits 7:4 = MIN_FREQ, bit3 = RESERVED(0), bits 2:0 = RESP_TIME

        # Parse MIN_FREQ from calculated value
        min_freq_str = self.nt_min_freq_var.get()
        min_freq_val = safe_float(min_freq_str) if min_freq_str else 0

        # MIN_FREQ = round(16 - (8MHz / fSENSOR)), clamped 0-15
        # (Already calculated, just clamp)
        min_freq_field = max(0, min(15, round(min_freq_val)))

        # Parse response_time from user input
        response_str = self.nt_response_var.get()
        response_val = safe_float(response_str) if response_str else 192  # Default to 192

        # RESP_TIME encoding: b010=192, b011=384, b100=768, b101=1536, b110=3072, b111=6144
        # Map response time to bits 2:0
        resp_time_map = {192: 2, 384: 3, 768: 4, 1536: 5, 3072: 6, 6144: 7}
        resp_time_field = 2  # Default
        for val, bits in resp_time_map.items():
            if response_val <= val:
                resp_time_field = bits
                break
        if response_val > 6144:
            resp_time_field = 7

        dig_conf_val = (min_freq_field << 4) | (resp_time_field & 0x07)
        self.reg_live_values[0x04] = dig_conf_val
        self.reg_lw[0x04] = f"0x{dig_conf_val:02X}"

        self.set_status("Apps Calculator -> Registers updated.")
        messagebox.showinfo("Update Registers",
                           f"Register values updated from Apps Calculator!\n"
                           f"RP_SET  = 0x{rp_set_val:02X}\n"
                           f"TC1     = 0x{tc1_val:02X}\n"
                           f"TC2     = 0x{tc2_val:02X}\n"
                           f"DIG_CONF= 0x{dig_conf_val:02X}")

        # Notify main UI to update register map table
        if self.register_map_callback:
            self.register_map_callback()

    def bind_traces(self, recalculate_callback, sync_callback=None):
        """Bind trace callbacks - manual calculation via label clicks only."""
        # NO automatic recalculation on value changes
        # Only label clicks trigger calculation

        # Bind labels to click for manual calculation
        self._bind_label_clicks(self.frame, recalculate_callback)

    def _bind_label_clicks(self, widget, callback):
        """Bind all labels in widget to trigger callback on click."""
        if isinstance(widget, tk.Label):
            widget.configure(cursor="hand2")
            widget.bind("<Button-1>", lambda e: callback())
        for child in widget.winfo_children():
            self._bind_label_clicks(child, callback)