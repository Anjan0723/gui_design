# ═══════════════════════════════════════════════════════════════
#  REGISTER DATABASE - LDC1101 register definitions
# ═══════════════════════════════════════════════════════════════

REGISTERS = [
    # ═══════════════════════════════════════════════════════════════
    # Sub-group: "11 configuration reg (write)"
    # ═══════════════════════════════════════════════════════════════
    {
        "name": "RP_SET",      "address": 0x01, "default": 0x07, "mode": "R/W", "size": 8,
        "description": (
            "RP_MAX[6:4]\nRP_MAX Setting\n\n"
            "RP_MIN[2:0]\nRP_MIN Setting\n\n"
            "HIGH_Q_SENSOR\nHigh-Q sensor mode enable"
        ),
        "fields": [
            {"name": "HIGH_Q_SENSOR", "bit": 7},
            {"name": "RP_MAX[2]",     "bit": 6},
            {"name": "RP_MAX[1]",     "bit": 5},
            {"name": "RP_MAX[0]",     "bit": 4},
            {"name": "RESERVED",      "bit": 3},
            {"name": "RP_MIN[2]",     "bit": 2},
            {"name": "RP_MIN[1]",     "bit": 1},
            {"name": "RP_MIN[0]",     "bit": 0},
        ],
        "readonly_bits": [],
    },
    {
        "name": "TC1",         "address": 0x02, "default": 0x90, "mode": "R/W", "size": 8,
        "description": (
            "C1[1:0]\nCapacitance factor 1\n\nR1[4:0]\nResistance factor 1\n\nR1(Ω) = -12770 × R1_field + 417000"
        ),
        "fields": [
            {"name": "C1[1]",      "bit": 7},
            {"name": "C1[0]",      "bit": 6},
            {"name": "RESERVED",   "bit": 5},
            {"name": "R1[4]",      "bit": 4},
            {"name": "R1[3]",      "bit": 3},
            {"name": "R1[2]",      "bit": 2},
            {"name": "R1[1]",      "bit": 1},
            {"name": "R1[0]",      "bit": 0},
        ],
        "readonly_bits": [],
    },
    {
        "name": "TC2",         "address": 0x03, "default": 0xA0, "mode": "R/W", "size": 8,
        "description": (
            "C2[1:0]\nCapacitance factor 2\n\nR2[5:0]\nResistance factor 2\n\nR2(Ω) = -12770 × R2_field + 835000"
        ),
        "fields": [
            {"name": "C2[1]",   "bit": 7}, {"name": "C2[0]",   "bit": 6},
            {"name": "R2[5]",   "bit": 5}, {"name": "R2[4]",   "bit": 4},
            {"name": "R2[3]",   "bit": 3}, {"name": "R2[2]",   "bit": 2},
            {"name": "R2[1]",   "bit": 1}, {"name": "R2[0]",   "bit": 0},
        ],
        "readonly_bits": [],
    },
    {
        "name": "DIG_CONF",    "address": 0x04, "default": 0x03, "mode": "R/W", "size": 8,
        "description": (
            "MIN_FREQ[3:0]\nMinimum frequency setting\n\n"
            "RESP_TIME[2:0]\nResponse time setting\n\n"
            "MIN_FREQ = 16 - (8MHz / fSENSOR_MIN)\n"
            "RESP_TIME: b010=192us, b011=384us, b100=768us, b101=1536us, b110=3072us, b111=6144us"
        ),
        "fields": [
            {"name": "MIN_FREQ[3]", "bit": 7}, {"name": "MIN_FREQ[2]", "bit": 6},
            {"name": "MIN_FREQ[1]", "bit": 5}, {"name": "MIN_FREQ[0]", "bit": 4},
            {"name": "RESERVED",    "bit": 3}, {"name": "RESP_TIME[2]", "bit": 2},
            {"name": "RESP_TIME[1]", "bit": 1}, {"name": "RESP_TIME[0]", "bit": 0},
        ],
        "readonly_bits": [],
    },
    {
        "name": "ALT_CONFIG",  "address": 0x05, "default": 0x00, "mode": "R/W", "size": 8,
        "description": (
            "RESERVED[5:0]\nReserved bits - do not modify\n\n"
            "SHUTDOWN_EN\nShutdown enable\n\n"
            "LOPTIMAL\nL optimal mode"
        ),
        "fields": [
            {"name": "RESERVED[5]", "bit": 7}, {"name": "RESERVED[4]", "bit": 6},
            {"name": "RESERVED[3]", "bit": 5}, {"name": "RESERVED[2]", "bit": 4},
            {"name": "RESERVED[1]", "bit": 3}, {"name": "RESERVED[0]", "bit": 2},
            {"name": "SHUTDOWN_EN", "bit": 1}, {"name": "LOPTIMAL",     "bit": 0},
        ],
        "readonly_bits": [7, 6, 5, 4, 3, 2],
    },
    {
        "name": "START_CONFIG","address": 0x0B, "default": 0x01, "mode": "R/W", "size": 8,
        "description": (
            "RESERVED[5:0]\nReserved bits - do not modify\n\n"
            "FUNC_MODE[1:0]\nFunctional mode select\nb00: Active conversion mode\nb01: Sleep mode"
        ),
        "fields": [
            {"name": "RESERVED[5]", "bit": 7}, {"name": "RESERVED[4]", "bit": 6},
            {"name": "RESERVED[3]", "bit": 5}, {"name": "RESERVED[2]", "bit": 4},
            {"name": "RESERVED[1]", "bit": 3}, {"name": "RESERVED[0]", "bit": 2},
            {"name": "FUNC_MODE[1]", "bit": 1}, {"name": "FUNC_MODE[0]", "bit": 0},
        ],
        "readonly_bits": [7, 6, 5, 4, 3, 2],
    },
    {
        "name": "D_CONFIG",    "address": 0x0C, "default": 0x00, "mode": "R/W", "size": 8,
        "description": (
            "RESERVED[6:1]\nReserved bits - do not modify\n\n"
            "DOK_REPORT\nData OK report enable"
        ),
        "fields": [
            {"name": "RESERVED[6]", "bit": 7}, {"name": "RESERVED[5]", "bit": 6},
            {"name": "RESERVED[4]", "bit": 5}, {"name": "RESERVED[3]", "bit": 4},
            {"name": "RESERVED[2]", "bit": 3}, {"name": "RESERVED[1]", "bit": 2},
            {"name": "RESERVED[0]", "bit": 1}, {"name": "DOK_REPORT",    "bit": 0},
        ],
        "readonly_bits": [],
    },
    {
        "name": "LHR_RCOUNT_LSB", "address": 0x30, "default": 0xFF, "mode": "R/W", "size": 8,
        "description": (
            "LHR_RCOUNT[7:0]\nLHR Conversion Counter LSB\n"
            "Sets the number of conversion clock cycles for LHR measurement"
        ),
        "fields": [{"name": f"LHR_RCOUNT[{i}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [],
    },
    {
        "name": "LHR_RCOUNT_MSB", "address": 0x31, "default": 0x0F, "mode": "R/W", "size": 8,
        "description": (
            "LHR_RCOUNT[15:8]\nLHR Conversion Counter MSB\n"
            "Sets the number of conversion clock cycles for LHR measurement"
        ),
        "fields": [{"name": f"LHR_RCOUNT[{i+8}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [],
    },
    {
        "name": "LHR_OFFSET_LSB", "address": 0x32, "default": 0x00, "mode": "R/W", "size": 8,
        "description": (
            "LHR_OFFSET[7:0]\nLHR Offset LSB\n"
            "Offset value subtracted from LHR measurement result"
        ),
        "fields": [{"name": f"LHR_OFFSET[{i}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [],
    },
    {
        "name": "LHR_OFFSET_MSB", "address": 0x33, "default": 0x00, "mode": "R/W", "size": 8,
        "description": (
            "LHR_OFFSET[15:8]\nLHR Offset MSB\n"
            "Offset value subtracted from LHR measurement result"
        ),
        "fields": [{"name": f"LHR_OFFSET[{i+8}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [],
    },
    {
        "name": "LHR_CONFIG",   "address": 0x34, "default": 0x00, "mode": "R/W", "size": 8,
        "description": (
            "RESERVED[7:3]\nReserved bits\n\n"
            "LHR_EN\nLHR mode enable\n\n"
            "LHR_FREQ[2:0]\nLHR conversion frequency"
        ),
        "fields": [
            {"name": "RESERVED[2]", "bit": 7}, {"name": "RESERVED[1]", "bit": 6},
            {"name": "RESERVED[0]", "bit": 5}, {"name": "LHR_EN",       "bit": 4},
            {"name": "LHR_FREQ[2]", "bit": 3}, {"name": "LHR_FREQ[1]", "bit": 2},
            {"name": "LHR_FREQ[0]", "bit": 1},
        ],
        "readonly_bits": [7, 6, 5],
    },
    # ═══════════════════════════════════════════════════════════════
    # Sub-group: "3 data registers (read)"
    # ═══════════════════════════════════════════════════════════════
    {
        "name": "LHR_DATA_LSB", "address": 0x38, "default": 0x00, "mode": "R", "size": 8,
        "description": (
            "LHR_DATA[7:0]\nLHR Measurement Result LSB\n"
            "Least significant byte of 24-bit LHR measurement"
        ),
        "fields": [{"name": f"LHR_DATA[{i}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [7, 6, 5, 4, 3, 2, 1, 0],
    },
    {
        "name": "LHR_DATA_MID", "address": 0x39, "default": 0x00, "mode": "R", "size": 8,
        "description": (
            "LHR_DATA[15:8]\nLHR Measurement Result MID\n"
            "Middle byte of 24-bit LHR measurement"
        ),
        "fields": [{"name": f"LHR_DATA[{i+8}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [7, 6, 5, 4, 3, 2, 1, 0],
    },
    {
        "name": "LHR_DATA_MSB", "address": 0x3A, "default": 0x00, "mode": "R", "size": 8,
        "description": (
            "LHR_DATA[23:16]\nLHR Measurement Result MSB\n"
            "Most significant byte of 24-bit LHR measurement"
        ),
        "fields": [{"name": f"LHR_DATA[{i+16}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [7, 6, 5, 4, 3, 2, 1, 0],
    },
    # ═══════════════════════════════════════════════════════════════
    # Sub-group: "3 status registers (read)"
    # ═══════════════════════════════════════════════════════════════
    {
        "name": "STATUS",       "address": 0x20, "default": 0x00, "mode": "R", "size": 8,
        "description": (
            "RP_OK\nRP measurement within thresholds\n\n"
            "L_OK\nL measurement within thresholds\n\n"
            "DRDY\nData ready flag\n\n"
            "LHR_RDY\nLHR conversion complete"
        ),
        "fields": [
            {"name": "RESERVED[4]", "bit": 7}, {"name": "RESERVED[3]", "bit": 6},
            {"name": "LHR_RDY",     "bit": 5}, {"name": "RESERVED[2]", "bit": 4},
            {"name": "DRDY",        "bit": 3}, {"name": "L_OK",         "bit": 2},
            {"name": "RP_OK",       "bit": 1}, {"name": "RESERVED[0]", "bit": 0},
        ],
        "readonly_bits": [7, 6, 5, 4, 3, 2, 1, 0],
    },
    {
        "name": "LHR_STATUS",   "address": 0x3B, "default": 0x00, "mode": "R", "size": 8,
        "description": (
            "LHR_ERROR\nLHR measurement error\n\n"
            "LHR_RDY\nLHR data ready\n\n"
            "LHR_OFFSET_OK\nOffset calibration valid"
        ),
        "fields": [
            {"name": "RESERVED[4]", "bit": 7}, {"name": "RESERVED[3]", "bit": 6},
            {"name": "LHR_ERROR",   "bit": 5}, {"name": "LHR_OFFSET_OK", "bit": 4},
            {"name": "RESERVED[2]", "bit": 3}, {"name": "RESERVED[1]", "bit": 2},
            {"name": "RESERVED[0]", "bit": 1},
        ],
        "readonly_bits": [7, 6, 5, 4, 3, 2, 1, 0],
    },
    {
        "name": "CHIP_ID",      "address": 0x3F, "default": 0x0D, "mode": "R", "size": 8,
        "description": (
            "CHIP_ID[7:0]\nDevice identification\n"
            "LDC1101: 0x0D"
        ),
        "fields": [{"name": f"CHIP_ID[{i}]", "bit": i} for i in range(7, -1, -1)],
        "readonly_bits": [7, 6, 5, 4, 3, 2, 1, 0],
    },
]

# ═══════════════════════════════════════════════════════════════
#  LOOKUP TABLES
# ═══════════════════════════════════════════════════════════════

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