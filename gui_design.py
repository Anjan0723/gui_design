import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import math
import serial.tools.list_ports

# ═══════════════════════════════════════════════════════════════
#  REGISTER DATABASE  (mirrors real LDC1101 datasheet)
# ═══════════════════════════════════════════════════════════════
REGISTERS = [
    {
        "name": "RP_SET",      "address": 0x01, "default": 0x07, "mode": "R/W", "size": 8,
        "description": (
            "RPMAX_DIS[7:7]\nRP_MAX Disable\n\n"
            "This setting improves the RP measurement accuracy for very high Q coils "
            "by driving 0A as the RPMAX current drive.\n\n"
            "b0: Programmed RP_MAX is driven (default value)\n"
            "b1: RP_MAX current is ignored; current drive is off.\n\n"
            "RP_MAX[6:4]\nRP_MAX Setting\n\n"
            "RP_MIN[2:0]\nRP_MIN Setting"
        ),
        "fields": [
            {"name": "RPMAX_DIS[0]", "bit": 7},
            {"name": "RP_MAX[2]",    "bit": 6},
            {"name": "RP_MAX[1]",    "bit": 5},
            {"name": "RP_MAX[0]",    "bit": 4},
            {"name": "UNUSED",       "bit": 3},
            {"name": "RP_MIN[2]",    "bit": 2},
            {"name": "RP_MIN[1]",    "bit": 1},
            {"name": "RP_MIN[0]",    "bit": 0},
        ],
        "readonly_bits": [],
    },
    {
        "name": "TC1",         "address": 0x02, "default": 0x90, "mode": "R/W", "size": 8,
        "description": (
            "C1[7:6]\nCapacitance factor 1\n\nR1[5:3]\nResistance factor 1\n\nTC1_FREQ[2:0]\nTime constant frequency select"
        ),
        "fields": [
            {"name": "C1[1]",      "bit": 7},
            {"name": "C1[0]",      "bit": 6},
            {"name": "R1[2]",      "bit": 5},
            {"name": "R1[1]",      "bit": 4},
            {"name": "R1[0]",      "bit": 3},
            {"name": "FREQ[2]",    "bit": 2},
            {"name": "FREQ[1]",    "bit": 1},
            {"name": "FREQ[0]",    "bit": 0},
        ],
        "readonly_bits": [],
    },
    {
        "name": "TC2",         "address": 0x03, "default": 0xA0, "mode": "R/W", "size": 8,
        "description": "C2[7:6]\nCapacitance factor 2\n\nR2[5:3]\nResistance factor 2\n\nTC2_FREQ[2:0]\nTime constant 2 freq select",
        "fields": [
            {"name": "C2[1]",   "bit": 7}, {"name": "C2[0]",   "bit": 6},
            {"name": "R2[2]",   "bit": 5}, {"name": "R2[1]",   "bit": 4},
            {"name": "R2[0]",   "bit": 3}, {"name": "FREQ[2]", "bit": 2},
            {"name": "FREQ[1]", "bit": 1}, {"name": "FREQ[0]", "bit": 0},
        ],
        "readonly_bits": [],
    },
    {
        "name": "DIG_CONF",    "address": 0x04, "default": 0x03, "mode": "R/W", "size": 8,
        "description": "RESERVED[7:3]\nReserved bits — do not modify\n\nSENSOR_ACT[2]\nSensor activation bit\n\nCONV_MODE[1:0]\nConversion mode select",
        "fields": [
            {"name": "RSV[4]",     "bit": 7}, {"name": "RSV[3]",     "bit": 6},
            {"name": "RSV[2]",     "bit": 5}, {"name": "RSV[1]",     "bit": 4},
            {"name": "RSV[0]",     "bit": 3}, {"name": "SENS_ACT",   "bit": 2},
            {"name": "CONV[1]",    "bit": 1}, {"name": "CONV[0]",    "bit": 0},
        ],
        "readonly_bits": [7, 6, 5, 4, 3],
    },
    {
        "name": "ALT_CONFIG",  "address": 0x05, "default": 0x00, "mode": "R/W", "size": 8,
        "description": "RESERVED[7:5]\nReserved\n\nAUTO_AMP_DIS[4]\nDisable auto amplitude control\n\nDRIVE_CURRENT[3:0]\nSensor drive current setting",
        "fields": [
            {"name": "RSV[2]",   "bit": 7}, {"name": "RSV[1]",   "bit": 6},
            {"name": "RSV[0]",   "bit": 5}, {"name": "AMP_DIS",  "bit": 4},
            {"name": "DRV[3]",   "bit": 3}, {"name": "DRV[2]",   "bit": 2},
            {"name": "DRV[1]",   "bit": 1}, {"name": "DRV[0]",   "bit": 0},
        ],
        "readonly_bits": [7, 6, 5],
    },
    {
        "name": "RP_THRESH_HI_LSB", "address": 0x06, "default": 0x00, "mode": "R/W", "size": 8,
        "description": "RP_THRESH_HI_LSB[7:0]\nLow byte of upper Rp threshold",
        "fields": [{"name": f"D[{i}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [],
    },
    {
        "name": "RP_THRESH_HI_MSB", "address": 0x07, "default": 0x00, "mode": "R/W", "size": 8,
        "description": "RP_THRESH_HI_MSB[7:0]\nHigh byte of upper Rp threshold",
        "fields": [{"name": f"D[{i}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [],
    },
    {
        "name": "RP_THRESH_LO_LSB", "address": 0x08, "default": 0x00, "mode": "R/W", "size": 8,
        "description": "RP_THRESH_LO_LSB[7:0]\nLow byte of lower Rp threshold",
        "fields": [{"name": f"D[{i}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [],
    },
    {
        "name": "RP_THRESH_LO_MSB", "address": 0x09, "default": 0x00, "mode": "R/W", "size": 8,
        "description": "RP_THRESH_LO_MSB[7:0]\nHigh byte of lower Rp threshold",
        "fields": [{"name": f"D[{i}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [],
    },
    {
        "name": "INTB_MODE",   "address": 0x0A, "default": 0x00, "mode": "R/W", "size": 8,
        "description": "INTB_MODE[7:0]\nInterrupt pin mode configuration",
        "fields": [{"name": f"M[{i}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [],
    },
    {
        "name": "START_CONFIG","address": 0x0B, "default": 0x01, "mode": "R/W", "size": 8,
        "description": "RESERVED[7:2]\nReserved\n\nFUNC_MODE[1:0]\nFunctional mode select\nb00: Active conversion mode\nb01: Sleep mode",
        "fields": [
            {"name": "RSV[5]", "bit": 7}, {"name": "RSV[4]", "bit": 6},
            {"name": "RSV[3]", "bit": 5}, {"name": "RSV[2]", "bit": 4},
            {"name": "RSV[1]", "bit": 3}, {"name": "RSV[0]", "bit": 2},
            {"name": "FNC[1]", "bit": 1}, {"name": "FNC[0]", "bit": 0},
        ],
        "readonly_bits": [7, 6, 5, 4, 3, 2],
    },
    {
        "name": "D_CONFIG",    "address": 0x0C, "default": 0x00, "mode": "R/W", "size": 8,
        "description": "D_CONFIG[7:0]\nADC digital configuration register",
        "fields": [{"name": f"D[{i}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [],
    },
    {
        "name": "L_THRESH_HI_LSB", "address": 0x16, "default": 0x00, "mode": "R/W", "size": 8,
        "description": "L_THRESH_HI_LSB[7:0]\nLow byte of upper L threshold",
        "fields": [{"name": f"D[{i}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [],
    },
    {
        "name": "L_THRESH_HI_MSB", "address": 0x17, "default": 0x00, "mode": "R/W", "size": 8,
        "description": "L_THRESH_HI_MSB[7:0]\nHigh byte of upper L threshold",
        "fields": [{"name": f"D[{i}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [],
    },
    {
        "name": "L_THRESH_LO_LSB", "address": 0x18, "default": 0x00, "mode": "R/W", "size": 8,
        "description": "L_THRESH_LO_LSB[7:0]\nLow byte of lower L threshold",
        "fields": [{"name": f"D[{i}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [],
    },
    {
        "name": "L_THRESH_LO_MSB", "address": 0x19, "default": 0x00, "mode": "R/W", "size": 8,
        "description": "L_THRESH_LO_MSB[7:0]\nHigh byte of lower L threshold",
        "fields": [{"name": f"D[{i}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [],
    },
]

# RP_MIN / RP_MAX lookup tables (Ohms)
RP_OPTIONS_LABELS = ["96k (Ohms)", "48k (Ohms)", "24k (Ohms)", "12k (Ohms)",
                     "6k (Ohms)",  "3k (Ohms)",  "1.5k (Ohms)", "0.75k (Ohms)"]
RP_OPTIONS_VALUES = [96000, 48000, 24000, 12000, 6000, 3000, 1500, 750]

# C1 options (Farads) for TC1
C1_OPTIONS_LABELS = ["0.75p (F)", "1.5p (F)", "3p (F)", "6p (F)"]
C1_OPTIONS_VALUES = [0.75e-12, 1.5e-12, 3e-12, 6e-12]

# C2 options (Farads) for TC2
C2_OPTIONS_LABELS = ["3p (F)", "6p (F)", "12p (F)", "24p (F)"]
C2_OPTIONS_VALUES = [3e-12, 6e-12, 12e-12, 24e-12]

# R1 options (Ohms): 417kΩ down to 21.1kΩ, step -12.77kΩ, n=0 to 31
# Formula: R1(Ω) = -12.77kΩ × n + 417kΩ
R1_OPTIONS_VALUES = [417000 - 12770 * n for n in range(32)]
R1_OPTIONS_LABELS = [f"{r/1000:.2f}kOhms" for r in R1_OPTIONS_VALUES]

# R2 options (Ohms): 835kΩ down to 30.5kΩ, step -12.77kΩ, n=0 to 63
# Formula: R2(Ω) = -12.77kΩ × n + 835kΩ
R2_OPTIONS_VALUES = [835000 - 12770 * n for n in range(64)]
R2_OPTIONS_LABELS = [f"{r/1000:.2f}kOhms" for r in R2_OPTIONS_VALUES]

# ═══════════════════════════════════════════════════════════════
#  STATE
# ═══════════════════════════════════════════════════════════════
reg_live_values = {r["address"]: r["default"] for r in REGISTERS}
reg_lw          = {r["address"]: "0x00" for r in REGISTERS}
reg_lr          = {r["address"]: "0x00" for r in REGISTERS}
selected_reg    = [REGISTERS[0]]
temp_bit_state  = None
write_buffer    = {}

# ═══════════════════════════════════════════════════════════════
#  WINDOW
# ═══════════════════════════════════════════════════════════════
root = tk.Tk()
root.title("LDC1101 EVM GUI")
root.geometry("1280x780")
root.configure(bg="#f0f0f0")
root.resizable(True, True)

style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview",
    background="white", foreground="black",
    fieldbackground="white", rowheight=22,
    font=("Arial", 9))
style.configure("Treeview.Heading",
    background="#dce6f1", foreground="#1f3864",
    font=("Arial", 9, "bold"), relief="groove")
style.map("Treeview",
    background=[("selected", "#0078d7")],
    foreground=[("selected", "white")])
style.configure("TLabelframe",       background="#f0f0f0")
style.configure("TLabelframe.Label", background="#f0f0f0",
                font=("Arial", 9, "bold"), foreground="#1f3864")
style.configure("TButton",           font=("Arial", 9))
style.configure("TCombobox",         font=("Arial", 9))

# ═══════════════════════════════════════════════════════════════
#  MENU BAR
# ═══════════════════════════════════════════════════════════════
menubar = tk.Menu(root)
for menu_name in ["File", "Script", "Debug", "Help"]:
    m = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label=menu_name, menu=m)
root.config(menu=menubar)

# ═══════════════════════════════════════════════════════════════
#  TITLE BAR
# ═══════════════════════════════════════════════════════════════
title_bar = tk.Frame(root, bg="#1f3864", height=48)
title_bar.pack(fill="x")
title_bar.pack_propagate(False)
tk.Label(title_bar, text="LDC1101 EVM GUI",
         bg="#1f3864", fg="white",
         font=("Arial", 18, "bold")).pack(side="left", padx=20, pady=8)
sim_var = tk.BooleanVar(value=False)
tk.Checkbutton(title_bar, text="Simulate Communication",
               variable=sim_var, bg="#1f3864", fg="white",
               selectcolor="#1f3864", activebackground="#1f3864",
               font=("Arial", 9)).pack(side="right", padx=16)

# ═══════════════════════════════════════════════════════════════
#  COM + SAVE/LOAD BAR
# ═══════════════════════════════════════════════════════════════
top_bar = tk.Frame(root, bg="#e8e8e8", pady=5, bd=1, relief="groove")
top_bar.pack(fill="x", padx=0)
tk.Label(top_bar, text="COM Port", bg="#e8e8e8",
         font=("Arial", 9)).pack(side="left", padx=(12, 4))
port_var = tk.StringVar()
port_cb  = ttk.Combobox(top_bar, textvariable=port_var, width=18,
                         state="readonly", font=("Arial", 9))
port_cb.pack(side="left", padx=4)

def refresh_ports():
    ports = [p.device for p in serial.tools.list_ports.comports()]
    if not ports:
        ports = ["COM3 (Mock)", "COM4 (Mock)"]
        port_cb["values"] = ports
        port_var.set(ports[0])
        conn_lbl.config(text="  NOT CONNECTED  ", bg="#cc0000")
    else:
        port_cb["values"] = ports
        port_var.set(ports[0])
        conn_lbl.config(text="  CONNECTED  ", bg="#107c10")

tk.Button(top_bar, text="⟳", command=refresh_ports,
          font=("Arial", 9), width=2).pack(side="left", padx=2)
tk.Button(top_bar, text="💾  Save Config",
          font=("Arial", 9), command=lambda: save_config()).pack(side="right", padx=8)
tk.Button(top_bar, text="📂  Load Config",
          font=("Arial", 9), command=lambda: load_config()).pack(side="right", padx=4)

# ═══════════════════════════════════════════════════════════════
#  MAIN BODY
# ═══════════════════════════════════════════════════════════════
body = tk.Frame(root, bg="#f0f0f0")
body.pack(fill="both", expand=True, padx=4, pady=4)

# ── LEFT SIDEBAR ─────────────────────────────────────────────
left_sb = ttk.LabelFrame(body, text="Selection", width=140)
left_sb.pack(side="left", fill="y", padx=(0, 4), pady=0)
left_sb.pack_propagate(False)

sel_items = ["LHR", "Apps Calculator", "Register Configuration", "About"]
sel_var   = tk.StringVar(value="Register Configuration")

# ── CONTENT AREA (center + right) ────────────────────────────
content_area = tk.Frame(body, bg="#f0f0f0")
content_area.pack(side="left", fill="both", expand=True)

# ── CENTER ───────────────────────────────────────────────────
center = tk.Frame(content_area, bg="#f0f0f0")
center.pack(side="left", fill="both", expand=True, padx=(0, 4))

# ── RIGHT PANEL ──────────────────────────────────────────────
right_panel = tk.Frame(content_area, bg="#f0f0f0", width=260)
right_panel.pack(side="right", fill="y")
right_panel.pack_propagate(False)

# ═══════════════════════════════════════════════════════════════
#  APPS CALCULATOR PANEL (hidden by default)
# ═══════════════════════════════════════════════════════════════
apps_frame = tk.Frame(content_area, bg="#f0f0f0")
# Not packed yet — shown when Apps Calculator is selected

# ── Helper to make a labeled input row ───────────────────────
def make_row(parent, row_idx, label_text, is_input=True, dropdown_opts=None):
    """Creates a label + entry or dropdown in a grid parent. Returns the widget."""
    tk.Label(parent, text=label_text, bg="white", font=("Arial", 9),
             anchor="w", bd=1, relief="solid",
             padx=4).grid(row=row_idx, column=0, sticky="ew", ipady=3)
    if dropdown_opts:
        var = tk.StringVar(value=dropdown_opts[0])
        cb = ttk.Combobox(parent, textvariable=var, values=dropdown_opts,
                          state="readonly", font=("Arial", 9), width=14)
        cb.grid(row=row_idx, column=1, sticky="ew", padx=2, pady=1)
        return var, cb
    else:
        var = tk.StringVar()
        state = "normal" if is_input else "readonly"
        bg    = "white"
        e = tk.Entry(parent, textvariable=var, font=("Arial", 9),
                     width=16, state=state, bg=bg,
                     relief="solid", bd=1)
        e.grid(row=row_idx, column=1, sticky="ew", padx=2, pady=1)
        return var, e

def make_section_header(parent, row_idx, text):
    lbl = tk.Label(parent, text=text, bg="white",
                   font=("Arial", 9, "bold"), fg="#1f3864",
                   anchor="w", padx=4, bd=1, relief="solid")
    lbl.grid(row=row_idx, column=0, columnspan=2, sticky="ew", ipady=4)

# ── NO TARGET panel ──────────────────────────────────────────
no_tgt_outer = tk.LabelFrame(apps_frame, text="NO TARGET (d=inf)",
                              font=("Arial", 10, "bold"), fg="#1f3864",
                              bg="#f0f0f0", bd=2)
no_tgt_outer.pack(side="left", fill="both", expand=True, padx=(0,6), pady=4)

nt = tk.Frame(no_tgt_outer, bg="white", bd=1, relief="solid")
nt.pack(fill="both", expand=True, padx=4, pady=4)
nt.columnconfigure(0, weight=1)
nt.columnconfigure(1, weight=1)

make_section_header(nt, 0, "Sensor Parameters :")
nt_csensor_var,   nt_csensor_entry = make_row(nt, 1,  "Csensor",            is_input=True)
nt_lsensor_var,   nt_lsensor_entry = make_row(nt, 2,  "Lsensor (No Target)", is_input=True)
nt_fsensor_var,   _ = make_row(nt, 3,  "Fsensor (No Target)", is_input=False)
nt_rs_var,        nt_rs_entry = make_row(nt, 4,  "Rs_parasitic",        is_input=True)
nt_rp_var,        nt_rp_entry = make_row(nt, 5,  "Rp_parasitic",        is_input=True)



# Rp_Min dropdown + Too Large warning
tk.Label(nt, text="Rp_Min", bg="white", font=("Arial", 9),
         anchor="w", bd=1, relief="solid", padx=4).grid(row=9, column=0, sticky="ew", ipady=3)
nt_rpmin_frame = tk.Frame(nt, bg="white")
nt_rpmin_frame.grid(row=9, column=1, sticky="ew", padx=2, pady=1)
nt_rpmin_var = tk.StringVar(value=RP_OPTIONS_LABELS[5])  # default 3k
nt_rpmin_cb  = ttk.Combobox(nt_rpmin_frame, textvariable=nt_rpmin_var,
                              values=RP_OPTIONS_LABELS, state="readonly",
                              font=("Arial", 9), width=14)
nt_rpmin_cb.pack(side="left")

tk.Label(nt, text="Rp_Max", bg="white", font=("Arial", 9),
         anchor="w", bd=1, relief="solid", padx=4).grid(row=10, column=0, sticky="ew", ipady=3)
nt_rpmax_frame = tk.Frame(nt, bg="white")
nt_rpmax_frame.grid(row=10, column=1, sticky="ew", padx=2, pady=1)
nt_rpmax_var = tk.StringVar(value=RP_OPTIONS_LABELS[2])  # default 24k
nt_rpmax_cb  = ttk.Combobox(nt_rpmax_frame, textvariable=nt_rpmax_var,
                              values=RP_OPTIONS_LABELS, state="readonly",
                              font=("Arial", 9), width=14)
nt_rpmax_cb.pack(side="left")
nt_toolarge_lbl = tk.Label(nt_rpmax_frame, text="Too Large", bg="#ff4444",
                            fg="white", font=("Arial", 8, "bold"), padx=4)

nt_qmin_var,_ = make_row(nt, 11,  "Qmin", is_input=True)

tk.Label(nt, text="C1 (No Target)", bg="white", font=("Arial", 9),
         anchor="w", bd=1, relief="solid", padx=4).grid(row=12, column=0, sticky="ew", ipady=3)
nt_c1_var = tk.StringVar(value=C1_OPTIONS_LABELS[2])  # default 3p
nt_c1_cb  = ttk.Combobox(nt, textvariable=nt_c1_var, values=C1_OPTIONS_LABELS,
                           state="readonly", font=("Arial", 9), width=14)
nt_c1_cb.grid(row=12, column=1, sticky="ew", padx=2, pady=1)

# R1 (No Target) dropdown
tk.Label(nt, text="R1 (No Target)", bg="white", font=("Arial", 9),
         anchor="w", bd=1, relief="solid", padx=4).grid(row=13, column=0, sticky="ew", ipady=3)
nt_r1_var = tk.StringVar(value=R1_OPTIONS_LABELS[0])
nt_r1_cb = ttk.Combobox(nt, textvariable=nt_r1_var, values=R1_OPTIONS_LABELS,
                        state="readonly", font=("Arial", 9), width=14)
nt_r1_cb.grid(row=13, column=1, sticky="ew", padx=2, pady=1)

tk.Label(nt, text="C2 (No Target)", bg="white", font=("Arial", 9),
         anchor="w", bd=1, relief="solid", padx=4).grid(row=14, column=0, sticky="ew", ipady=3)
nt_c2_var = tk.StringVar(value=C2_OPTIONS_LABELS[2])  # default 12p
nt_c2_cb  = ttk.Combobox(nt, textvariable=nt_c2_var, values=C2_OPTIONS_LABELS,
                           state="readonly", font=("Arial", 9), width=14)
nt_c2_cb.grid(row=14, column=1, sticky="ew", padx=2, pady=1)

# R2 (No Target) dropdown
tk.Label(nt, text="R2 (No Target)", bg="white", font=("Arial", 9),
         anchor="w", bd=1, relief="solid", padx=4).grid(row=15, column=0, sticky="ew", ipady=3)
nt_r2_var = tk.StringVar(value=R2_OPTIONS_LABELS[0])
nt_r2_cb = ttk.Combobox(nt, textvariable=nt_r2_var, values=R2_OPTIONS_LABELS,
                        state="readonly", font=("Arial", 9), width=14)
nt_r2_cb.grid(row=15, column=1, sticky="ew", padx=2, pady=1)

# ── MAX TARGET panel ─────────────────────────────────────────
mx_tgt_outer = tk.LabelFrame(apps_frame, text="MAX TARGET (d=0)",
                              font=("Arial", 10, "bold"), fg="#1f3864",
                              bg="#f0f0f0", bd=2)
mx_tgt_outer.pack(side="left", fill="both", expand=True, padx=(6,0), pady=4)

mt = tk.Frame(mx_tgt_outer, bg="white", bd=1, relief="solid")
mt.pack(fill="both", expand=True, padx=4, pady=4)
mt.columnconfigure(0, weight=1)
mt.columnconfigure(1, weight=1)

make_section_header(mt, 0, "Sensor Parameters :")
mt_lvar_var,   mt_lvar_entry = make_row(mt, 1,  "Lvariation",         is_input=True)
mt_lfinal_var, _ = make_row(mt, 2,  "Lsensor (Final)",    is_input=False)
mt_fosc_var,   _ = make_row(mt, 3,  "Fosc (Final)",       is_input=False)
mt_rpvar_var,  mt_rpvar_entry = make_row(mt, 4,  "Rpvariation",        is_input=True)
mt_rp_var,     _ = make_row(mt, 5,  "Rp_parasitic",       is_input=False)

make_section_header(mt, 6, "Loop Parameters :")

tk.Label(mt, text="Rp_Min", bg="white", font=("Arial", 9),
         anchor="w", bd=1, relief="solid", padx=4).grid(row=7, column=0, sticky="ew", ipady=3)
mt_rpmin_frame = tk.Frame(mt, bg="white")
mt_rpmin_frame.grid(row=7, column=1, sticky="ew", padx=2, pady=1)
mt_rpmin_var = tk.StringVar(value=RP_OPTIONS_LABELS[5])
mt_rpmin_cb  = ttk.Combobox(mt_rpmin_frame, textvariable=mt_rpmin_var,
                              values=RP_OPTIONS_LABELS, state="readonly",
                              font=("Arial", 9), width=14)
mt_rpmin_cb.pack(side="left")

tk.Label(mt, text="Rp_Max", bg="white", font=("Arial", 9),
         anchor="w", bd=1, relief="solid", padx=4).grid(row=8, column=0, sticky="ew", ipady=3)
mt_rpmax_frame = tk.Frame(mt, bg="white")
mt_rpmax_frame.grid(row=8, column=1, sticky="ew", padx=2, pady=1)
mt_rpmax_var = tk.StringVar(value=RP_OPTIONS_LABELS[2])
mt_rpmax_cb  = ttk.Combobox(mt_rpmax_frame, textvariable=mt_rpmax_var,
                              values=RP_OPTIONS_LABELS, state="readonly",
                              font=("Arial", 9), width=14)
mt_rpmax_cb.pack(side="left")
mt_toolarge_lbl = tk.Label(mt_rpmax_frame, text="Too Large", bg="#ff4444",
                            fg="white", font=("Arial", 8, "bold"), padx=4)

mt_qmin_var,   _ = make_row(mt, 9,  "Qmin",               is_input=True)

tk.Label(mt, text="C1 (Final)", bg="white", font=("Arial", 9),
         anchor="w", bd=1, relief="solid", padx=4).grid(row=10, column=0, sticky="ew", ipady=3)
mt_c1_var = tk.StringVar(value=C1_OPTIONS_LABELS[2])
mt_c1_cb  = ttk.Combobox(mt, textvariable=mt_c1_var, values=C1_OPTIONS_LABELS,
                           state="readonly", font=("Arial", 9), width=14)
mt_c1_cb.grid(row=10, column=1, sticky="ew", padx=2, pady=1)

# R1 (Final) dropdown
tk.Label(mt, text="R1 (Final)", bg="white", font=("Arial", 9),
         anchor="w", bd=1, relief="solid", padx=4).grid(row=11, column=0, sticky="ew", ipady=3)
mt_r1_var = tk.StringVar(value=R1_OPTIONS_LABELS[0])
mt_r1_cb = ttk.Combobox(mt, textvariable=mt_r1_var, values=R1_OPTIONS_LABELS,
                        state="readonly", font=("Arial", 9), width=14)
mt_r1_cb.grid(row=11, column=1, sticky="ew", padx=2, pady=1)

tk.Label(mt, text="C2 (Final)", bg="white", font=("Arial", 9),
         anchor="w", bd=1, relief="solid", padx=4).grid(row=12, column=0, sticky="ew", ipady=3)
mt_c2_var = tk.StringVar(value=C2_OPTIONS_LABELS[2])
mt_c2_cb  = ttk.Combobox(mt, textvariable=mt_c2_var, values=C2_OPTIONS_LABELS,
                           state="readonly", font=("Arial", 9), width=14)
mt_c2_cb.grid(row=12, column=1, sticky="ew", padx=2, pady=1)

# R2 (Final) dropdown
tk.Label(mt, text="R2 (Final)", bg="white", font=("Arial", 9),
         anchor="w", bd=1, relief="solid", padx=4).grid(row=13, column=0, sticky="ew", ipady=3)
mt_r2_var = tk.StringVar(value=R2_OPTIONS_LABELS[0])
mt_r2_cb = ttk.Combobox(mt, textvariable=mt_r2_var, values=R2_OPTIONS_LABELS,
                        state="readonly", font=("Arial", 9), width=14)
mt_r2_cb.grid(row=13, column=1, sticky="ew", padx=2, pady=1)

# ── Update Registers button ───────────────────────────────────
tk.Button(apps_frame, text="✔  Update Registers",
          font=("Arial", 10, "bold"), bg="#1f7a1f", fg="white",
          command=lambda: apps_update_registers()).pack(
          side="bottom", pady=8, anchor="e", padx=10)

# ═══════════════════════════════════════════════════════════════
#  APPS CALCULATOR — CALCULATION ENGINE
# ═══════════════════════════════════════════════════════════════

def safe_float(s):
    try:
        return float(str(s).strip().replace("k","e3").replace("M","e6")
                     .replace("p","e-12").replace("n","e-9").replace("u","e-6"))
    except:
        return None

def format_freq(hz):
    if hz is None: return ""
    if hz >= 1e6:  return f"{hz/1e6:.3f}MHz"
    if hz >= 1e3:  return f"{hz/1e3:.3f}kHz"
    return f"{hz:.1f}Hz"

def format_res(ohm):
    if ohm is None: return ""
    if ohm >= 1e6:  return f"{ohm/1e6:.2f}MOhms"
    if ohm >= 1e3:  return f"{ohm/1e3:.2f}kOhms"
    return f"{ohm:.2f} Ohms"

def calc_fsensor(L_H, C_F):
    """f = 1 / (2π√(L×C))"""
    try:
        return 1.0 / (2 * math.pi * math.sqrt(L_H * C_F))
    except:
        return None

def calc_qmin(rp_min_ohm, C_F, L_H):
    """Qmin = Rp_Min × √(C/L)"""
    try:
        return rp_min_ohm * math.sqrt(C_F / L_H)
    except:
        return None

def calc_r1(C1_F, f_sensor_hz):
    """R1×C1 = √2 / (π × 0.6 × f_sensor)  →  R1 = √2 / (π×0.6×f×C1)"""
    try:
        r1 = math.sqrt(2) / (math.pi * 0.6 * f_sensor_hz * C1_F)
        return r1
    except:
        return None

def calc_r2(C2_F, rp_min_ohm, C_sensor_F):
    """R2×C2 = 2×Rp_Min×Csensor  →  R2 = 2×Rp_Min×Csensor / C2"""
    try:
        return 2 * rp_min_ohm * C_sensor_F / C2_F
    except:
        return None

def find_nearest_r1(calc_r1_ohm):
    """Find the smallest valid R1 value >= calculated value."""
    if calc_r1_ohm is None or calc_r1_ohm <= 0:
        return None
    # Find the smallest value >= calc_r1_ohm (search from low to high values)
    # R1_OPTIONS_VALUES is descending: [417k, 404k, 391k, ..., 21k]
    # We want the closest value that is >= calc_r1 (should be near the end for small calc_r1)
    best_idx = None
    for i, val in enumerate(R1_OPTIONS_VALUES):
        if val >= calc_r1_ohm:
            best_idx = i  # Keep updating to get the last (smallest) valid one
    return best_idx if best_idx is not None else 0

def find_nearest_r2(calc_r2_ohm):
    """Find the smallest valid R2 value >= calculated value."""
    if calc_r2_ohm is None or calc_r2_ohm <= 0:
        return None
    # Find the smallest value >= calc_r2_ohm
    best_idx = None
    for i, val in enumerate(R2_OPTIONS_VALUES):
        if val >= calc_r2_ohm:
            best_idx = i
    return best_idx if best_idx is not None else 0

def sync_no_target_to_max_target(*args):
    """Sync NO TARGET loop parameters to MAX TARGET."""
    # Copy values from NO TARGET to MAX TARGET
    mt_rpmin_var.set(nt_rpmin_var.get())
    mt_rpmax_var.set(nt_rpmax_var.get())
    mt_qmin_var.set(nt_qmin_var.get())
    mt_c1_var.set(nt_c1_var.get())
    mt_c2_var.set(nt_c2_var.get())
    mt_r1_var.set(nt_r1_var.get())
    mt_r2_var.set(nt_r2_var.get())

def parse_capacitance(value_str):
    """
    Parse capacitance value and return (numeric_SI_value, display_string).
    
    User types    →  SI value used    →  Field displays
    330           →  330 F            →  '330 F'
    330p          →  330e-12 F        →  '330 pF'
    330pF         →  330e-12 F        →  '330 pF'
    330n          →  330e-9 F         →  '330 nF'
    330nF         →  330e-9 F         →  '330 nF'
    330u          →  330e-6 F         →  '330 uF'
    330uF         →  330e-6 F         →  '330 uF'
    
    Returns (None, '') if invalid input.
    """
    s = value_str.strip()
    if not s:
        return (None, '')
    
    try:
        # Check suffixes (longest first to avoid partial matches)
        if s.endswith("pF"):
            val = float(s[:-2])
            return (val * 1e-12, f"{val:.0f} pF")
        if s.endswith("nF"):
            val = float(s[:-2])
            return (val * 1e-9, f"{val:.0f} nF")
        if s.endswith("uF"):
            val = float(s[:-2])
            return (val * 1e-6, f"{val:.0f} uF")
        if s.endswith("p"):
            val = float(s[:-1])
            return (val * 1e-12, f"{val:.0f} pF")
        if s.endswith("n"):
            val = float(s[:-1])
            return (val * 1e-9, f"{val:.0f} nF")
        if s.endswith("u"):
            val = float(s[:-1])
            return (val * 1e-6, f"{val:.0f} uF")
        if s.endswith("F"):
            val = float(s[:-1])
            return (val, f"{val:.0f} F")
        # No suffix - treat as raw Farads
        val = float(s)
        return (val, f"{val:.0f} F")
    except (ValueError, TypeError):
        return (None, '')

def apps_recalculate(*args):
    """Main calculation function — called whenever any input changes."""
    print(f"DEBUG: apps_recalculate called with args={args}")

    # ── Parse NO TARGET inputs ──
    csensor_str = nt_csensor_var.get()   # e.g. "330pF" or "330"
    lsensor_str = nt_lsensor_var.get()   # e.g. "9uH"
    rs_str      = nt_rs_var.get()
    rp_str      = nt_rp_var.get()

    # Parse Csensor with smart formatting
    C_F, c_display = parse_capacitance(csensor_str)
    if C_F is None:
        set_status("Error: Invalid Csensor value")
        return
    nt_csensor_var.set(c_display)  # Update field with formatted value

    # Normalise unit strings for other sensors
    def parse_sensor(s, unit_map):
        s = s.strip()
        # Check for unit suffix first
        for suffix, mult in unit_map.items():
            if s.endswith(suffix):
                try: return float(s[:-len(suffix)]) * mult
                except: return None
        # No suffix - treat as raw Farads
        try: return float(s)
        except: return None

    L_H   = parse_sensor(lsensor_str, {"uH":1e-6,"mH":1e-3,"nH":1e-9,"u":1e-6,"m":1e-3,"n":1e-9})
    Rs    = parse_sensor(rs_str,      {"kOhms":1e3,"Ohms":1,"k":1e3})
    Rp_nt = parse_sensor(rp_str,      {"kOhms":1e3,"kΩ":1e3,"k":1e3,"Ohms":1})

    # ── NO TARGET Fsensor ──
    f_nt = calc_fsensor(L_H, C_F)
    nt_fsensor_var.set(format_freq(f_nt) if f_nt else "")

    # ── NO TARGET Rp_Min / Rp_Max ──
    rp_min_idx = RP_OPTIONS_LABELS.index(nt_rpmin_var.get())
    rp_max_idx = RP_OPTIONS_LABELS.index(nt_rpmax_var.get())
    rp_min_val = RP_OPTIONS_VALUES[rp_min_idx]
    rp_max_val = RP_OPTIONS_VALUES[rp_max_idx]

    # Too Large check for NO TARGET
    if Rp_nt and Rp_nt > rp_max_val:
        nt_toolarge_lbl.pack(side="left", padx=4)
    else:
        nt_toolarge_lbl.pack_forget()

    # ── NO TARGET Qmin ──
    q_nt = calc_qmin(rp_min_val, C_F, L_H) if (C_F and L_H) else None
    nt_qmin_var.set(f"{q_nt:.2f}" if q_nt else "")

    # ── NO TARGET C1/R1 ──
    c1_nt_label = nt_c1_var.get()
    print(f"DEBUG: nt_c1_var.get() = '{c1_nt_label}'")
    c1_nt_idx = C1_OPTIONS_LABELS.index(c1_nt_label)
    C1_nt     = C1_OPTIONS_VALUES[c1_nt_idx]
    r1_nt     = calc_r1(C1_nt, f_nt) if f_nt else None
    r1_nt_idx = find_nearest_r1(r1_nt)
    print(f"DEBUG: C1={C1_nt*1e12:.1f}pF, f={f_nt/1e6:.2f}MHz, calc_R1={r1_nt/1000:.2f}k, idx={r1_nt_idx}")
    if r1_nt_idx is not None:
        new_r1_label = R1_OPTIONS_LABELS[r1_nt_idx]
        nt_r1_var.set(new_r1_label)
        nt_r1_cb.set(new_r1_label)  # Force combobox to update display
        print(f"DEBUG: R1 (No Target) set to: {new_r1_label}")

    # ── NO TARGET C2/R2 ──
    c2_nt_idx = C2_OPTIONS_LABELS.index(nt_c2_var.get())
    C2_nt     = C2_OPTIONS_VALUES[c2_nt_idx]
    r2_nt     = calc_r2(C2_nt, rp_min_val, C_F) if C_F else None
    r2_nt_idx = find_nearest_r2(r2_nt)
    if r2_nt_idx is not None:
        nt_r2_var.set(R2_OPTIONS_LABELS[r2_nt_idx])

    # ── MAX TARGET inputs ──
    lvar_str  = mt_lvar_var.get()
    rpvar_str = mt_rpvar_var.get()
    Lvar  = safe_float(lvar_str)
    RPvar = safe_float(rpvar_str)

    # ── MAX TARGET derived sensor params ──
    L_final  = (L_H  * Lvar)  if (L_H  and Lvar)  else None
    Rp_final = (Rp_nt * RPvar) if (Rp_nt and RPvar) else None
    f_mt     = calc_fsensor(L_final, C_F) if (L_final and C_F) else None

    mt_lfinal_var.set(f"{L_final*1e6:.2f}uH" if L_final else "")
    mt_fosc_var.set(format_freq(f_mt) if f_mt else "")
    mt_rp_var.set(format_res(Rp_final) if Rp_final else "")

    # ── MAX TARGET Rp_Min / Rp_Max ──
    mt_rp_min_idx = RP_OPTIONS_LABELS.index(mt_rpmin_var.get())
    mt_rp_max_idx = RP_OPTIONS_LABELS.index(mt_rpmax_var.get())
    mt_rp_min_val = RP_OPTIONS_VALUES[mt_rp_min_idx]
    mt_rp_max_val = RP_OPTIONS_VALUES[mt_rp_max_idx]

    if Rp_final and Rp_final > mt_rp_max_val:
        mt_toolarge_lbl.pack(side="left", padx=4)
    else:
        mt_toolarge_lbl.pack_forget()

    # ── MAX TARGET Qmin ──
    q_mt = calc_qmin(mt_rp_min_val, C_F, L_final) if (C_F and L_final) else None
    mt_qmin_var.set(f"{q_mt:.2f}" if q_mt else "")

    # ── MAX TARGET R1 ──
    c1_mt_idx = C1_OPTIONS_LABELS.index(mt_c1_var.get())
    C1_mt     = C1_OPTIONS_VALUES[c1_mt_idx]
    r1_mt     = calc_r1(C1_mt, f_mt) if f_mt else None
    r1_mt_idx = find_nearest_r1(r1_mt)
    if r1_mt_idx is not None:
        new_r1_mt_label = R1_OPTIONS_LABELS[r1_mt_idx]
        mt_r1_var.set(new_r1_mt_label)
        mt_r1_cb.set(new_r1_mt_label)
        print(f"DEBUG: R1 (Final) set to: {new_r1_mt_label}")

    # ── MAX TARGET R2 ──
    c2_mt_idx = C2_OPTIONS_LABELS.index(mt_c2_var.get())
    C2_mt     = C2_OPTIONS_VALUES[c2_mt_idx]
    r2_mt     = calc_r2(C2_mt, mt_rp_min_val, C_F) if C_F else None
    r2_mt_idx = find_nearest_r2(r2_mt)
    if r2_mt_idx is not None:
        new_r2_mt_label = R2_OPTIONS_LABELS[r2_mt_idx]
        mt_r2_var.set(new_r2_mt_label)
        mt_r2_cb.set(new_r2_mt_label)

# ── Calculate Button removed per user request ────────────────────────
# Calculation is now triggered by clicking the labels

def apps_update_registers():
    """Calculate register values from Apps Calculator and push to register map."""
    # Get Rp_Min / Rp_Max bit codes (index maps to register bits b000..b111)
    rp_min_idx = RP_OPTIONS_LABELS.index(nt_rpmin_var.get())
    rp_max_idx = RP_OPTIONS_LABELS.index(nt_rpmax_var.get())

    # RP_SET register: bit7=0, bits[6:4]=RP_MAX, bit3=0, bits[2:0]=RP_MIN
    rp_set_val = (rp_max_idx << 4) | (rp_min_idx & 0x07)
    reg_live_values[0x01] = rp_set_val & 0xFF
    reg_lw[0x01] = f"0x{rp_set_val:02X}"

    # TC1: C1 bits[7:6], R1 bits[4:0] (simplified — just encode C1 index)
    c1_idx = C1_OPTIONS_LABELS.index(nt_c1_var.get())
    tc1_val = (c1_idx << 6) & 0xFF
    reg_live_values[0x02] = tc1_val
    reg_lw[0x02] = f"0x{tc1_val:02X}"

    # TC2: C2 bits[7:6]
    c2_idx = C2_OPTIONS_LABELS.index(nt_c2_var.get())
    tc2_val = (c2_idx << 6) & 0xFF
    reg_live_values[0x03] = tc2_val
    reg_lw[0x03] = f"0x{tc2_val:02X}"

    # Update all table rows
    for reg in REGISTERS:
        update_table_row(reg)

    set_status("Apps Calculator → Registers updated.")
    messagebox.showinfo("Update Registers",
                        "Register values updated from Apps Calculator!\n"
                        f"RP_SET = 0x{rp_set_val:02X}\n"
                        f"TC1    = 0x{tc1_val:02X}\n"
                        f"TC2    = 0x{tc2_val:02X}")

# Bind all Apps Calculator inputs to recalculate
def _bind_apps():
    print("DEBUG: _bind_apps() called")
    # Entry widgets: NO automatic triggers — only manual Calculate button
    # (No bindings for nt_csensor_entry, nt_lsensor_entry, nt_rs_entry, nt_rp_entry,
    #  mt_lvar_entry, mt_rpvar_entry)
    
    def bind_labels(widget):
        if isinstance(widget, tk.Label):
            widget.configure(cursor="hand2")
            widget.bind("<Button-1>", apps_recalculate)
        for child in widget.winfo_children():
            bind_labels(child)

    bind_labels(apps_frame)

    # Combobox widgets: keep trace_add for immediate response on dropdown changes
    for var in [nt_rpmin_var, nt_rpmax_var, nt_c1_var, nt_c2_var,
                mt_rpmin_var, mt_rpmax_var, mt_c1_var, mt_c2_var]:
        var.trace_add("write", apps_recalculate)
    
    # Sync NO TARGET loop parameters to MAX TARGET (dropdowns only)
    for var in [nt_rpmin_var, nt_rpmax_var, nt_c1_var, nt_r1_var, nt_c2_var, nt_r2_var]:
        var.trace_add("write", sync_no_target_to_max_target)
    print("DEBUG: All bindings set successfully")

# Set defaults and run once
def _set_apps_defaults():
    nt_csensor_var.set("330pF")
    nt_lsensor_var.set("9uH")
    nt_rs_var.set("5Ohms")
    nt_rp_var.set("5.45kOhms")
    mt_lvar_var.set("0.7")
    mt_rpvar_var.set("0.7")

# ═══════════════════════════════════════════════════════════════
#  CENTER — Register Map Table
# ═══════════════════════════════════════════════════════════════
reg_map_frame = ttk.LabelFrame(center, text="Register Map")
reg_map_frame.pack(fill="both", expand=True)

cols = ("Block / Register Name", "Address", "Default", "Mode", "Size", "LW*", "LR*")
tree = ttk.Treeview(reg_map_frame, columns=cols, show="headings", selectmode="browse")

col_widths = [170, 70, 70, 50, 45, 70, 70]
for col, w in zip(cols, col_widths):
    tree.heading(col, text=col)
    anchor = "w" if col == "Block / Register Name" else "center"
    tree.column(col, width=w, anchor=anchor, minwidth=w)

tree.insert("", "end", iid="group_hdr",
            values=("  LDC1101 EVM Registers", "", "", "", "", "", ""),
            tags=("group",))
tree.tag_configure("group", background="#dce6f1", font=("Arial", 9, "bold"))
tree.tag_configure("even",  background="white")
tree.tag_configure("odd",   background="#f5f8ff")

iid_to_reg = {}
for i, reg in enumerate(REGISTERS):
    lw  = reg_lw[reg["address"]]
    lr  = reg_lr[reg["address"]]
    iid = f"reg_{reg['address']}"
    tag = "even" if i % 2 == 0 else "odd"
    tree.insert("", "end", iid=iid,
                values=(f"    {reg['name']}",
                        f"0x{reg['address']:02X}",
                        f"0x{reg['default']:02X}",
                        reg["mode"], reg["size"], lw, lr),
                tags=(tag,))
    iid_to_reg[iid] = reg

sb_tree = ttk.Scrollbar(reg_map_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=sb_tree.set)
sb_tree.pack(side="right", fill="y")
tree.pack(fill="both", expand=True)

tree.insert("", "end", values=("", "", "", "", "", "*LW→ Last Write", "*LR→ Last Read"),
            tags=("note",))
tree.tag_configure("note", foreground="#888888", font=("Arial", 7, "italic"))

# ── Register Description ─────────────────────────────────────
desc_frame = ttk.LabelFrame(center, text="Register Description")
desc_frame.pack(fill="x", pady=(4, 0))

desc_text = tk.Text(desc_frame, height=7, font=("Courier New", 9),
                    bg="white", relief="sunken", bd=1,
                    wrap="word", state="disabled")
desc_sb = ttk.Scrollbar(desc_frame, orient="vertical", command=desc_text.yview)
desc_text.configure(yscrollcommand=desc_sb.set)
desc_sb.pack(side="right", fill="y")
desc_text.pack(fill="both", expand=True, padx=4, pady=4)

# ═══════════════════════════════════════════════════════════════
#  RIGHT PANEL — Write / Read / Bit checkboxes
# ═══════════════════════════════════════════════════════════════
tk.Button(right_panel, text="Tx R to W", font=("Arial", 9), width=14,
          command=lambda: tx_r_to_w()).pack(pady=(4, 8))

wd_frame = ttk.LabelFrame(right_panel, text="Write Data")
wd_frame.pack(fill="x", padx=4, pady=2)
wd_inner = tk.Frame(wd_frame, bg="#f0f0f0")
wd_inner.pack(fill="x", padx=4, pady=4)
tk.Label(wd_inner, text="x", bg="#f0f0f0", font=("Arial", 9)).pack(side="left")
write_var = tk.StringVar(value=str(REGISTERS[0]["default"]))
write_entry = tk.Entry(wd_inner, textvariable=write_var, width=8,
                       font=("Courier New", 10), relief="sunken", bd=2)
write_entry.pack(side="left", padx=4)

def btn(parent, text, cmd, w=14):
    return tk.Button(parent, text=text, command=cmd,
                     font=("Arial", 9), width=w, relief="groove")

btn(wd_frame, "Write Register", lambda: write_register_cmd(), 16).pack(pady=2)
btn(wd_frame, "Write All",      lambda: write_all_cmd(),      16).pack(pady=2)

rd_frame = ttk.LabelFrame(right_panel, text="Read Data")
rd_frame.pack(fill="x", padx=4, pady=6)
rd_inner = tk.Frame(rd_frame, bg="#f0f0f0")
rd_inner.pack(fill="x", padx=4, pady=4)
tk.Label(rd_inner, text="x", bg="#f0f0f0", font=("Arial", 9)).pack(side="left")
read_val_var = tk.StringVar(value="0")
tk.Entry(rd_inner, textvariable=read_val_var, width=8,
         font=("Courier New", 10), relief="sunken", bd=2,
         state="readonly").pack(side="left", padx=4)
btn(rd_frame, "Read Register", lambda: read_register_cmd(), 16).pack(pady=2)
btn(rd_frame, "Read All",      lambda: read_all_cmd(),      16).pack(pady=2)

ca_frame = ttk.LabelFrame(right_panel, text="Current Address")
ca_frame.pack(fill="x", padx=4, pady=4)
ca_inner = tk.Frame(ca_frame, bg="#f0f0f0")
ca_inner.pack(fill="x", padx=4, pady=4)
tk.Label(ca_inner, text="x", bg="#f0f0f0", font=("Arial", 9)).pack(side="left")
addr_var = tk.StringVar(value="1")
tk.Entry(ca_inner, textvariable=addr_var, width=8,
         font=("Courier New", 10), relief="sunken", bd=2,
         state="readonly").pack(side="left", padx=4)

rd_bits_frame = ttk.LabelFrame(right_panel, text="Register Data")
rd_bits_frame.pack(fill="both", expand=True, padx=4, pady=4)

bit_vars     = []
bit_cb_wgts  = []
bit_lbl_wgts = []

for i in range(8):
    bit_num = 7 - i
    row = tk.Frame(rd_bits_frame, bg="#f0f0f0")
    row.pack(fill="x", padx=6, pady=1)
    tk.Label(row, text=str(bit_num), bg="#f0f0f0",
             font=("Arial", 9, "bold"), width=2, anchor="e").pack(side="left", padx=(0, 2))
    bv = tk.BooleanVar(value=False)
    cb = tk.Checkbutton(row, variable=bv, bg="#f0f0f0", activebackground="#f0f0f0",
                        command=lambda: on_bit_changed())
    cb.pack(side="left")
    fl = tk.Label(row, text="", bg="#f0f0f0", font=("Arial", 8), anchor="w", fg="#333333")
    fl.pack(side="left", padx=4)
    bit_vars.append(bv)
    bit_cb_wgts.append(cb)
    bit_lbl_wgts.append(fl)

tk.Button(right_panel, text="Load Config", font=("Arial", 9), width=14,
          command=lambda: load_config()).pack(pady=(4, 2))
tk.Button(right_panel, text="Save Config", font=("Arial", 9), width=14,
          command=lambda: save_config()).pack(pady=2)

# ── Status bar ───────────────────────────────────────────────
status_bar = tk.Frame(root, bg="#333333", height=24)
status_bar.pack(fill="x", side="bottom")
status_bar.pack_propagate(False)
status_lbl = tk.Label(status_bar, text="idle", bg="#333333", fg="white",
                       font=("Arial", 8), anchor="w")
status_lbl.pack(side="left", padx=8)
tk.Label(status_bar, text="Version: 1.0.0.7", bg="#333333", fg="#aaaaaa",
         font=("Arial", 8)).pack(side="left", padx=20)
conn_lbl = tk.Label(status_bar, text="  NOT CONNECTED  ",
                     bg="#cc0000", fg="white", font=("Arial", 8, "bold"))
conn_lbl.pack(side="right", padx=4, pady=2)

# ═══════════════════════════════════════════════════════════════
#  SIDEBAR SELECTION — show/hide panels
# ═══════════════════════════════════════════════════════════════
def on_selection_change():
    sel = sel_var.get()
    if sel == "Apps Calculator":
        # Hide register UI, show apps calculator
        center.pack_forget()
        right_panel.pack_forget()
        apps_frame.pack(fill="both", expand=True)
    else:
        # Hide apps calculator, show register UI
        apps_frame.pack_forget()
        center.pack(side="left", fill="both", expand=True, padx=(0, 4))
        right_panel.pack(side="right", fill="y")

for item in sel_items:
    rb = tk.Radiobutton(left_sb, text=item, variable=sel_var, value=item,
                        bg="#f0f0f0", font=("Arial", 9),
                        anchor="w", indicatoron=True,
                        command=on_selection_change)
    rb.pack(fill="x", padx=6, pady=2)

# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════
def set_status(msg):
    status_lbl.config(text=msg)

def update_bit_panel(reg, value):
    addr_var.set(str(reg["address"]))
    for i, field in enumerate(reg["fields"]):
        bit_num = field["bit"]
        bit_on  = bool((value >> bit_num) & 1)
        bit_vars[i].set(bit_on)
        bit_lbl_wgts[i].config(text=field["name"])
        if bit_num in reg.get("readonly_bits", []):
            bit_cb_wgts[i].config(state="disabled")
        else:
            bit_cb_wgts[i].config(state="normal")

def get_value_from_bits(reg):
    val = 0
    for i, field in enumerate(reg["fields"]):
        if bit_vars[i].get():
            val |= (1 << field["bit"])
    return val

def update_description(reg):
    desc_text.config(state="normal")
    desc_text.delete("1.0", "end")
    desc_text.insert("end", reg["description"])
    desc_text.config(state="disabled")

def update_table_row(reg, lw_val=None, lr_val=None):
    iid = f"reg_{reg['address']}"
    if lw_val is not None:
        reg_lw[reg["address"]] = f"0x{lw_val:02X}"
    if lr_val is not None:
        reg_lr[reg["address"]] = f"0x{lr_val:02X}"
    lw = reg_lw[reg["address"]]
    lr = reg_lr[reg["address"]]
    tree.item(iid, values=(
        f"    {reg['name']}",
        f"0x{reg['address']:02X}",
        f"0x{reg['default']:02X}",
        reg["mode"], reg["size"], lw, lr
    ))

def load_reg_into_ui(reg):
    global temp_bit_state
    addr = reg["address"]
    temp_bit_state = None
    wval = write_buffer.get(addr)
    if wval is None:
        wval = reg_live_values.get(addr, reg.get("default", 0))
    addr_var.set(str(addr))
    try:
        lr_int = int(reg_lr[addr], 16) & 0xFF
    except (ValueError, TypeError):
        lr_int = 0
    read_val_var.set(str(lr_int))
    write_var.set(str(wval))
    update_bit_panel(reg, wval)
    update_description(reg)

def save_current_reg_state():
    global temp_bit_state
    current = selected_reg[0]
    if not current:
        return
    addr = current["address"]
    if temp_bit_state is not None:
        val = temp_bit_state
    else:
        try:
            val = int(write_var.get()) & 0xFF
        except ValueError:
            val = write_buffer.get(addr, reg_live_values.get(addr, current.get("default", 0)))
    write_buffer[addr] = val
    temp_bit_state = None

# ═══════════════════════════════════════════════════════════════
#  COMMAND FUNCTIONS
# ═══════════════════════════════════════════════════════════════
def write_register_cmd():
    global temp_bit_state
    reg = selected_reg[0]
    if not reg: return
    addr = reg["address"]
    if temp_bit_state is not None:
        val = temp_bit_state
    else:
        try:
            val = int(write_var.get() or 0) & 0xFF
        except ValueError:
            val = 0
    reg_live_values[addr] = val
    reg_lw[addr] = f"0x{val:02X}"
    write_buffer[addr] = val
    temp_bit_state = None
    update_table_row(reg)
    update_bit_panel(reg, val)
    set_status(f"Written 0x{val:02X} → {reg['name']} (0x{addr:02X})")

def write_all_cmd():
    for reg in REGISTERS:
        try:
            val = int(write_var.get().strip()) & 0xFF
        except ValueError:
            val = reg["default"]
        reg_live_values[reg["address"]] = val
        update_table_row(reg, lw_val=val)
    set_status("Write All complete.")

def read_register_cmd():
    reg = selected_reg[0]
    if not reg: return
    addr = reg["address"]
    val  = reg_live_values.get(addr, reg.get("default", 0))
    read_val_var.set(str(val))
    reg_lr[addr] = f"0x{val:02X}"
    update_table_row(reg)
    set_status(f"Read 0x{val:02X} ← {reg['name']} (0x{addr:02X})")

def read_all_cmd():
    for reg in REGISTERS:
        val = reg_live_values[reg["address"]]
        update_table_row(reg, lr_val=val)
    reg = selected_reg[0]
    val = reg_live_values[reg["address"]]
    read_val_var.set(str(val))
    set_status("Read All complete.")

def tx_r_to_w():
    write_var.set(read_val_var.get())
    set_status("Transferred Read → Write.")

def save_config():
    path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON Config", "*.json")],
        title="Save Config")
    if not path: return
    data = {f"0x{addr:02X}": val for addr, val in reg_live_values.items()}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    set_status(f"Config saved → {path}")

def load_config():
    path = filedialog.askopenfilename(
        filetypes=[("JSON Config", "*.json")],
        title="Load Config")
    if not path: return
    with open(path) as f:
        data = json.load(f)
    for addr_str, val in data.items():
        addr = int(addr_str, 16)
        if addr in reg_live_values:
            reg_live_values[addr] = val & 0xFF
            for reg in REGISTERS:
                if reg["address"] == addr:
                    update_table_row(reg)
    write_buffer.clear()
    load_reg_into_ui(selected_reg[0])
    set_status(f"Config loaded ← {path}")

# ═══════════════════════════════════════════════════════════════
#  CALLBACKS
# ═══════════════════════════════════════════════════════════════
def on_bit_changed():
    global temp_bit_state
    reg = selected_reg[0]
    if not reg: return
    value = get_value_from_bits(reg)
    temp_bit_state = value
    write_var.set(str(value))

def on_tree_select(event):
    global temp_bit_state
    sel = tree.selection()
    if not sel or sel[0] not in iid_to_reg: return
    new_reg = iid_to_reg[sel[0]]
    if new_reg is selected_reg[0]: return
    save_current_reg_state()
    selected_reg[0] = new_reg
    load_reg_into_ui(new_reg)

tree.bind("<<TreeviewSelect>>", on_tree_select)

# ═══════════════════════════════════════════════════════════════
#  AUTO PORT DETECTION
# ═══════════════════════════════════════════════════════════════
def auto_refresh_ports():
    refresh_ports()
    root.after(3000, auto_refresh_ports)

# ═══════════════════════════════════════════════════════════════
#  INITIAL LOAD
# ═══════════════════════════════════════════════════════════════
def initial_load():
    first_iid = f"reg_{REGISTERS[0]['address']}"
    tree.selection_set(first_iid)
    tree.focus(first_iid)
    tree.see(first_iid)
    load_reg_into_ui(REGISTERS[0])
    auto_refresh_ports()
    # Setup Apps Calculator
    _bind_apps()
    _set_apps_defaults()

root.after(100, initial_load)
root.mainloop()