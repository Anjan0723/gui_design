# ═══════════════════════════════════════════════════════════════
#  APPS CALCULATOR UI - NO TARGET and MAX TARGET panels
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
    """Apps Calculator panel with NO TARGET and MAX TARGET sections."""

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

        # Build UI
        self._create_no_target_panel()
        self._create_max_target_panel()
        self._create_update_button()

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

        # MAX TARGET inputs
        self.mt_lvar_var = tk.StringVar()
        self.mt_lfinal_var = tk.StringVar()
        self.mt_fosc_var = tk.StringVar()
        self.mt_rpvar_var = tk.StringVar()
        self.mt_rp_var = tk.StringVar()
        self.mt_rp_calc_var = tk.StringVar()  # Calculated RP
        self.mt_rpmin_var = tk.StringVar(value=RP_OPTIONS_LABELS[0])
        self.mt_rpmax_var = tk.StringVar(value=RP_OPTIONS_LABELS[2])
        self.mt_qmin_var = tk.StringVar()
        self.mt_c1_var = tk.StringVar(value=C1_OPTIONS_LABELS[2])
        self.mt_r1_var = tk.StringVar()
        self.mt_r1_calc_var = tk.StringVar()  # Calculated R1
        self.mt_c2_var = tk.StringVar(value=C2_OPTIONS_LABELS[2])
        self.mt_r2_var = tk.StringVar()
        self.mt_r2_calc_var = tk.StringVar()  # Calculated R2
        self.mt_min_freq_var = tk.StringVar()  # Min_frequency
        self.mt_response_var = tk.StringVar()  # response_time

    def _create_no_target_panel(self):
        """Create NO TARGET panel."""
        self.no_tgt_outer = tk.LabelFrame(
            self.frame, text="NO TARGET (d=inf)",
            font=("Arial", 10, "bold"), fg=COLORS["fg_bold"],
            bg=COLORS["bg_main"], bd=2
        )
        self.no_tgt_outer.pack(side="left", fill="both", expand=True,
                               padx=(0, 6), pady=4)

        self.nt = tk.Frame(self.no_tgt_outer, bg=COLORS["bg_white"], bd=1, relief="solid")
        self.nt.pack(fill="both", expand=True, padx=4, pady=4)
        self.nt.columnconfigure(0, weight=1)
        self.nt.columnconfigure(1, weight=1)
        self.nt.columnconfigure(2, weight=1)

        # Row 0: Section header
        self._make_section_header(self.nt, 0, "Sensor Parameters :")

        # Row 1-5: Input fields
        self._make_row(self.nt, 1, "Csensor", self.nt_csensor_var)
        self._make_row(self.nt, 2, "Lsensor (No Target)", self.nt_lsensor_var)
        self._make_row(self.nt, 3, "Fsensor (No Target)", self.nt_fsensor_var, is_input=False, tooltip="Valid range: 500kHz - 10MHz", has_warning=True)
        self._make_row(self.nt, 4, "Rs_parasitic", self.nt_rs_var)
        self._make_row(self.nt, 5, "Rp_parasitic = L/(Rs×C)", self.nt_rp_calc_var, is_input=False)

        # Row 6: Section header
        self._make_section_header(self.nt, 6, "Loop Parameters :")

        # Row 7-8: Rp dropdowns with warning labels
        self._make_dropdown(self.nt, 7, "Rp_Min", self.nt_rpmin_var, RP_OPTIONS_LABELS, is_no_target=True, has_warning=True)
        self._make_dropdown(self.nt, 8, "Rp_Max", self.nt_rpmax_var, RP_OPTIONS_LABELS, is_no_target=True, has_warning=True)

        # Row 9: Q factor with warning label
        self._make_row(self.nt, 9, "Q_Factor", self.nt_qmin_var, is_input=False, tooltip="Valid range: 10 - 400", has_warning=True, name="nt_qmin")

        # Row 10-11: C1 and R1
        self._make_dropdown(self.nt, 10, "C1 (No Target)", self.nt_c1_var, C1_OPTIONS_LABELS)
        self._make_row(self.nt, 11, "R1 (calculated)", self.nt_r1_calc_var, is_input=False, tooltip="Valid range: 21.1kΩ - 417kΩ", has_warning=True)
        self.nt_r1_var.set(R1_OPTIONS_LABELS[0])  # Store selected R1

        # Row 12-13: C2 and R2
        self._make_dropdown(self.nt, 12, "C2 (No Target)", self.nt_c2_var, C2_OPTIONS_LABELS)
        self._make_row(self.nt, 13, "R2 (calculated)", self.nt_r2_calc_var, is_input=False, tooltip="Valid range: 30.5kΩ - 835kΩ", has_warning=True)
        self.nt_r2_var.set(R2_OPTIONS_LABELS[0])  # Store selected R2

        # Row 14: Min_frequency
        self._make_row(self.nt, 14, "Min_frequency", self.nt_min_freq_var, is_input=False)

        # Row 15: response_time (user input)
        self._make_row(self.nt, 15, "response time", self.nt_response_var, is_input=True)

        # Row 16: ConvTime (calculated)
        self.nt_convtime_var = tk.StringVar()
        self._make_row(self.nt, 16, "ConvTime (us)", self.nt_convtime_var, is_input=False)

    def _create_max_target_panel(self):
        """Create MAX TARGET panel."""
        self.mx_tgt_outer = tk.LabelFrame(
            self.frame, text="MAX TARGET (d=0)",
            font=("Arial", 10, "bold"), fg=COLORS["fg_bold"],
            bg=COLORS["bg_main"], bd=2
        )
        self.mx_tgt_outer.pack(side="left", fill="both", expand=True,
                               padx=(6, 0), pady=4)

        self.mt = tk.Frame(self.mx_tgt_outer, bg=COLORS["bg_white"], bd=1, relief="solid")
        self.mt.pack(fill="both", expand=True, padx=4, pady=4)
        self.mt.columnconfigure(0, weight=1)
        self.mt.columnconfigure(1, weight=1)
        self.mt.columnconfigure(2, weight=1)

        # Row 0: Section header
        self._make_section_header(self.mt, 0, "Sensor Parameters :")

        # Row 1-5: Input fields
        self._make_row(self.mt, 1, "Lvariation", self.mt_lvar_var)
        self._make_row(self.mt, 2, "Lsensor (Final)", self.mt_lfinal_var, is_input=False)
        self._make_row(self.mt, 3, "Fosc (Final)", self.mt_fosc_var, is_input=False, tooltip="Valid range: 500kHz - 10MHz", has_warning=True)
        self._make_row(self.mt, 4, "Rpvariation", self.mt_rpvar_var)
        self._make_row(self.mt, 5, "Rp_parasitic = L/(Rs×C)", self.mt_rp_calc_var, is_input=False)

        # Row 6: Section header
        self._make_section_header(self.mt, 6, "Loop Parameters :")

        # Row 7-8: Rp dropdowns with warning labels
        self._make_dropdown(self.mt, 7, "Rp_Min", self.mt_rpmin_var, RP_OPTIONS_LABELS, has_warning=True)
        self._make_dropdown(self.mt, 8, "Rp_Max", self.mt_rpmax_var, RP_OPTIONS_LABELS, has_warning=True)

        # Row 9: Q factor
        self._make_row(self.mt, 9, "Q_Factor", self.mt_qmin_var, is_input=False, tooltip="Valid range: 10 - 400", has_warning=True)

        # Row 10-11: C1 and R1
        self._make_dropdown(self.mt, 10, "C1 (Final)", self.mt_c1_var, C1_OPTIONS_LABELS)
        self._make_row(self.mt, 11, "R1 (calculated)", self.mt_r1_calc_var, is_input=False, tooltip="Valid range: 21.1kΩ - 417kΩ", has_warning=True)
        self.mt_r1_var.set(R1_OPTIONS_LABELS[0])

        # Row 12-13: C2 and R2
        self._make_dropdown(self.mt, 12, "C2 (Final)", self.mt_c2_var, C2_OPTIONS_LABELS)
        self._make_row(self.mt, 13, "R2 (calculated)", self.mt_r2_calc_var, is_input=False, tooltip="Valid range: 30.5kΩ - 835kΩ", has_warning=True)
        self.mt_r2_var.set(R2_OPTIONS_LABELS[0])

    def _create_update_button(self):
        """Create Update Registers button."""
        self.update_btn = tk.Button(
            self.frame, text="Update Registers",
            font=("Arial", 10, "bold"), bg="#1f7a1f", fg=COLORS["fg_white"],
            command=self.update_registers
        )
        self.update_btn.pack(side="bottom", pady=8, anchor="e", padx=10)

    def _make_section_header(self, parent, row_idx, text):
        """Create a section header."""
        lbl = tk.Label(parent, text=text, bg=COLORS["bg_white"],
                       font=FONTS["normal_bold"], fg=COLORS["fg_bold"],
                       anchor="w", padx=4, bd=1, relief="solid")
        lbl.grid(row=row_idx, column=0, columnspan=2, sticky="ew", ipady=4)

    def _make_row(self, parent, row_idx, label_text, var, is_input=True, tooltip=None, has_warning=False, fg_color=None, name=None):
        """Create a label + entry row."""
        tk.Label(parent, text=label_text, bg=COLORS["bg_white"], font=FONTS["normal"],
                anchor="w", bd=1, relief="solid", padx=4).grid(
                    row=row_idx, column=0, sticky="ew", ipady=2)

        state = "normal" if is_input else "readonly"
        e = tk.Entry(parent, textvariable=var, font=FONTS["normal"],
                      width=16, state=state, bg=COLORS["bg_white"],
                      relief="solid", bd=1)
        if fg_color:
            e.config(fg=fg_color)
        e.grid(row=row_idx, column=1, sticky="ew", padx=2, pady=0)

        # Store reference for named rows
        if name:
            setattr(self, f"{name}_entry", e)

        # Add tooltip if provided
        if tooltip:
            self._add_tooltip(e, tooltip)

        # Add warning label in column 2 if needed
        if has_warning:
            warn_lbl = tk.Label(parent, text="", bg=COLORS["bg_white"],
                              font=FONTS["small"], fg=COLORS["error"], anchor="w")
            warn_lbl.grid(row=row_idx, column=2, sticky="w", padx=2)
            # Store reference for later updates
            if parent == self.nt:
                if "Fsensor" in label_text:
                    self.nt_fsensor_warn = warn_lbl
                elif "Q_Factor" in label_text:
                    self.nt_q_warn = warn_lbl
                elif "R1" in label_text:
                    self.nt_r1_warn = warn_lbl
                elif "R2" in label_text:
                    self.nt_r2_warn = warn_lbl
            else:
                if "Fsensor" in label_text:
                    self.mt_fsensor_warn = warn_lbl
                elif "Q_Factor" in label_text:
                    self.mt_q_warn = warn_lbl
                elif "R1" in label_text:
                    self.mt_r1_warn = warn_lbl
                elif "R2" in label_text:
                    self.mt_r2_warn = warn_lbl

    def _make_dropdown(self, parent, row_idx, label_text, var, options, is_no_target=False, has_warning=False):
        """Create a labeled dropdown."""
        tk.Label(parent, text=label_text, bg=COLORS["bg_white"], font=FONTS["normal"],
                 anchor="w", bd=1, relief="solid", padx=4).grid(
                     row=row_idx, column=0, sticky="ew", ipady=2)

        frame = tk.Frame(parent, bg=COLORS["bg_white"])
        frame.grid(row=row_idx, column=1, sticky="ew", padx=2, pady=0)

        cb = ttk.Combobox(frame, textvariable=var, values=options,
                          state="readonly", font=FONTS["normal"], width=14)
        cb.pack(side="left")

        # Add warning label in column 2 if needed
        if has_warning:
            warn_lbl = tk.Label(parent, text="", bg=COLORS["bg_white"],
                              font=FONTS["small"], fg=COLORS["error"], anchor="w")
            warn_lbl.grid(row=row_idx, column=2, sticky="w", padx=2)
            if "Rp_Max" in label_text:
                if is_no_target:
                    self.nt_rpmax_warn = warn_lbl
                else:
                    self.mt_rpmax_warn = warn_lbl
            elif "Rp_Min" in label_text:
                if is_no_target:
                    self.nt_rpmin_warn = warn_lbl
                else:
                    self.mt_rpmin_warn = warn_lbl

        # Store reference to frame for Rp_Max warning label
        if "Rp_Max" in label_text:
            if is_no_target:
                self.nt_rpmax_frame = frame
                self.nt_rpmax_cb = cb
            else:
                self.mt_rpmax_frame = frame
                self.mt_rpmax_cb = cb

    def _add_tooltip(self, widget, text):
        """Add tooltip to a widget."""
        Tooltip(widget, text)

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
            label.config(fg=COLORS["bg_white"])  # Hide by matching bg

    def _set_defaults(self):
        """Set default values."""
        self.nt_csensor_var.set("330pF")
        self.nt_lsensor_var.set("9uH")
        self.nt_rs_var.set("5Ohms")
        self.mt_lvar_var.set("0.7")
        self.mt_rpvar_var.set("0.7")

    def get_frame(self):
        """Return the main frame."""
        return self.frame

    def recalculate(self, *args):
        """Main calculation function with all validations."""
        self._calculate_no_target()
        self._calculate_max_target()

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
                self._set_warning(self.nt_fsensor_warn, "too small", "orange")
            elif f_nt > self.FSENSOR_MAX:
                self._set_warning(self.nt_fsensor_warn, "too large", "red")
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

        # RP_MIN validation (show on Rp_Max label for simplicity)
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
                # Set Qmin value color to red (out of range)
                if hasattr(self, 'nt_qmin_entry'):
                    self.nt_qmin_entry.config(fg="#cc0000")
            elif q_val < self.Q_MIN:
                self._set_warning(self.nt_q_warn, "⚠ Too Small", "orange")
                # Set Qmin value color to red (out of range)
                if hasattr(self, 'nt_qmin_entry'):
                    self.nt_qmin_entry.config(fg="#cc0000")
            else:
                # Set Qmin value color to green (in range 10-400)
                self._set_warning(self.nt_q_warn, "", None)
                if hasattr(self, 'nt_qmin_entry'):
                    self.nt_qmin_entry.config(fg="#107c10")
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

        # ===== 7. MIN_FREQUENCY =====
        # Min_frequency = 16 - (8MHz / fSENSOR_MIN)
        if f_nt and f_nt > 0:
            min_freq = 16 - (8e6 / f_nt)
            self.nt_min_freq_var.set(f"{min_freq:.2f}")

            # ===== 8. CONV TIME =====
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

    def _calculate_max_target(self):
        """Calculate MAX TARGET panel values."""
        # Parse NO TARGET inputs first (needed for MAX TARGET calculations)
        csensor_str = self.nt_csensor_var.get()
        lsensor_str = self.nt_lsensor_var.get()
        rs_str = self.nt_rs_var.get()

        C_F, _ = parse_capacitance(csensor_str)
        if C_F is None:
            return

        L_H = parse_sensor(lsensor_str, {"uH": 1e-6, "mH": 1e-3, "nH": 1e-9,
                                          "u": 1e-6, "m": 1e-3, "n": 1e-9})
        Rs = parse_sensor(rs_str, {"kOhms": 1e3, "Ohms": 1, "k": 1e3})

        # Calculate NO TARGET Rp for MAX TARGET computation
        Rp_nt = (L_H / (Rs * C_F)) if (L_H and Rs and C_F and Rs > 0) else None

        # MAX TARGET inputs
        Lvar = safe_float(self.mt_lvar_var.get())
        RPvar = safe_float(self.mt_rpvar_var.get())

        # ===== 6. MAX TARGET COMPUTED FIELDS =====
        # Lsensor(final) = Lsensor(no target) × Lvariation
        L_final = (L_H * Lvar) if (L_H and Lvar) else None
        self.mt_lfinal_var.set(f"{L_final*1e6:.2f}uH" if L_final else "")

        # Fosc(final) = 1 / (2π × √(Lsensor(final) × Csensor))
        f_mt = calc_fsensor(L_final, C_F) if (L_final and C_F) else None
        self.mt_fosc_var.set(format_freq(f_mt) if f_mt else "")

        # Rp(final) = Rp(no target) × RPvariation
        Rp_final = (Rp_nt * RPvar) if (Rp_nt and RPvar) else None
        self.mt_rp_var.set(format_res(Rp_final) if Rp_final else "")

        # ===== RP for MAX TARGET =====
        if L_final and Rs and C_F and Rs > 0:
            RP_calc_mt = L_final / (Rs * C_F)
        else:
            RP_calc_mt = None
        self.mt_rp_calc_var.set(format_res(RP_calc_mt) if RP_calc_mt else "")

        # ===== MAX TARGET RP VALIDATION =====
        mt_rp_min_idx = RP_OPTIONS_LABELS.index(self.mt_rpmin_var.get())
        mt_rp_max_idx = RP_OPTIONS_LABELS.index(self.mt_rpmax_var.get())
        mt_rp_min_val = RP_OPTIONS_VALUES[mt_rp_min_idx]
        mt_rp_max_val = RP_OPTIONS_VALUES[mt_rp_max_idx]

        if RP_calc_mt:
            if RP_calc_mt > mt_rp_max_val * 2:
                self._set_warning(self.mt_rpmax_warn, "⚠ Too Large", "red")
            elif mt_rp_max_val < RP_calc_mt:
                self._set_warning(self.mt_rpmax_warn, "⚠ Too Small", "orange")
            else:
                self._set_warning(self.mt_rpmax_warn, "", None)

            if mt_rp_min_val >= 0.8 * RP_calc_mt:
                self._set_warning(self.mt_rpmin_warn, "⚠ Too Large", "red")
            elif mt_rp_min_val < self.RP_MIN_DROPDOWN:
                self._set_warning(self.mt_rpmin_warn, "⚠ Too Small", "orange")
            else:
                self._set_warning(self.mt_rpmin_warn, "", None)
        else:
            self._set_warning(self.mt_rpmax_warn, "", None)
            self._set_warning(self.mt_rpmin_warn, "", None)

        # ===== Q FACTOR FOR MAX TARGET =====
        q_mt = None
        if L_final and C_F and Rs and Rs > 0:
            q_mt = (1 / Rs) * (L_final / C_F) ** 0.5

        q_error_mt = None
        if q_mt is not None:
            if q_mt > self.Q_MAX:
                q_error_mt = "⚠ Too Large"
                self._set_warning(self.mt_q_warn, "⚠ Too Large", "red")
            elif q_mt < self.Q_MIN:
                q_error_mt = "⚠ Too Small"
                self._set_warning(self.mt_q_warn, "⚠ Too Small", "orange")
            else:
                self._set_warning(self.mt_q_warn, "", None)
        else:
            self._set_warning(self.mt_q_warn, "", None)

        self.mt_qmin_var.set(f"{q_mt:.2f}" if q_mt else "")

        # ===== R1 FOR MAX TARGET =====
        c1_mt_idx = C1_OPTIONS_LABELS.index(self.mt_c1_var.get())
        C1_mt = C1_OPTIONS_VALUES[c1_mt_idx]

        r1_mt = calc_r1(C1_mt, f_mt) if f_mt else None

        r1_error_mt = None
        if r1_mt is not None:
            if r1_mt > self.R1_MAX:
                self._set_warning(self.mt_r1_warn, "⚠ Too Large", "red")
            elif r1_mt < self.R1_MIN:
                self._set_warning(self.mt_r1_warn, "⚠ Too Small", "orange")
            else:
                self._set_warning(self.mt_r1_warn, "", None)
        else:
            self._set_warning(self.mt_r1_warn, "", None)

        self.mt_r1_calc_var.set(format_res(r1_mt) if r1_mt else "")

        r1_mt_idx = find_nearest_r1(r1_mt)
        if r1_mt_idx is not None:
            self.mt_r1_var.set(R1_OPTIONS_LABELS[r1_mt_idx])

        # ===== R2 FOR MAX TARGET =====
        c2_mt_idx = C2_OPTIONS_LABELS.index(self.mt_c2_var.get())
        C2_mt = C2_OPTIONS_VALUES[c2_mt_idx]

        r2_mt = None
        if mt_rp_min_val and C_F and C2_mt:
            r2_mt = (2 * mt_rp_min_val * C_F) / C2_mt

        r2_error_mt = None
        if r2_mt is not None:
            if r2_mt > self.R2_MAX:
                self._set_warning(self.mt_r2_warn, "⚠ Too Large", "red")
            elif r2_mt < self.R2_MIN:
                self._set_warning(self.mt_r2_warn, "⚠ Too Small", "orange")
            else:
                self._set_warning(self.mt_r2_warn, "", None)
        else:
            self._set_warning(self.mt_r2_warn, "", None)

        self.mt_r2_calc_var.set(format_res(r2_mt) if r2_mt else "")

        r2_mt_idx = find_nearest_r2(r2_mt)
        if r2_mt_idx is not None:
            self.mt_r2_var.set(R2_OPTIONS_LABELS[r2_mt_idx])

        # ===== MIN_FREQUENCY FOR MAX TARGET =====
        if f_mt and f_mt > 0:
            min_freq_mt = 16 - (8e6 / f_mt)
            self.mt_min_freq_var.set(f"{min_freq_mt:.2f}")
        else:
            self.mt_min_freq_var.set("")

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

    def bind_traces(self, recalculate_callback, sync_callback):
        """Bind trace callbacks - manual calculation via label clicks only."""
        # NO automatic recalculation on value changes
        # Only label clicks trigger calculation

        # Bind sync parameters (sync NO TARGET to MAX TARGET dropdowns)
        for var in [self.nt_rpmin_var, self.nt_rpmax_var, self.nt_c1_var, self.nt_r1_var,
                    self.nt_c2_var, self.nt_r2_var]:
            var.trace_add("write", sync_callback)

        # Bind labels to click for manual calculation
        self._bind_label_clicks(self.frame, recalculate_callback)

    def _bind_label_clicks(self, widget, callback):
        """Bind all labels in widget to trigger callback on click."""
        if isinstance(widget, tk.Label):
            widget.configure(cursor="hand2")
            widget.bind("<Button-1>", lambda e: callback())
        for child in widget.winfo_children():
            self._bind_label_clicks(child, callback)

    def sync_parameters(self, *args):
        """Sync NO TARGET params to MAX TARGET."""
        self.mt_rpmin_var.set(self.nt_rpmin_var.get())
        self.mt_rpmax_var.set(self.nt_rpmax_var.get())
        self.mt_qmin_var.set(self.nt_qmin_var.get())
        self.mt_c1_var.set(self.nt_c1_var.get())
        self.mt_c2_var.set(self.nt_c2_var.get())
        self.mt_r1_var.set(self.nt_r1_var.get())
        self.mt_r2_var.set(self.nt_r2_var.get())