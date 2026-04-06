# ═══════════════════════════════════════════════════════════════
#  CALCULATIONS - Math functions for LDC1101
# ═══════════════════════════════════════════════════════════════

import math
from register_data import (
    RP_OPTIONS_VALUES, C1_OPTIONS_VALUES, C2_OPTIONS_VALUES,
    R1_OPTIONS_VALUES, R1_OPTIONS_LABELS, R2_OPTIONS_VALUES, R2_OPTIONS_LABELS
)


def safe_float(s):
    """Parse string with SI suffixes to float."""
    try:
        return float(str(s).strip()
                    .replace("k", "e3")
                    .replace("M", "e6")
                    .replace("p", "e-12")
                    .replace("n", "e-9")
                    .replace("u", "e-6"))
    except (ValueError, TypeError):
        return None


def format_freq(hz):
    """Format frequency in human-readable form."""
    if hz is None:
        return ""
    if hz >= 1e6:
        return f"{hz/1e6:.3f}MHz"
    if hz >= 1e3:
        return f"{hz/1e3:.3f}kHz"
    return f"{hz:.1f}Hz"


def format_res(ohm):
    """Format resistance in human-readable form."""
    if ohm is None:
        return ""
    if ohm >= 1e6:
        return f"{ohm/1e6:.2f}MOhms"
    if ohm >= 1e3:
        return f"{ohm/1e3:.2f}kOhms"
    return f"{ohm:.2f} Ohms"


def calc_fsensor(L_H, C_F):
    """Calculate sensor frequency: f = 1 / (2π√(L×C))"""
    try:
        return 1.0 / (2 * math.pi * math.sqrt(L_H * C_F))
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def calc_qmin(rp_min_ohm, C_F, L_H):
    """Calculate Qmin: Qmin = Rp_Min × √(C/L)"""
    try:
        return rp_min_ohm * math.sqrt(C_F / L_H)
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def calc_r1(C1_F, f_sensor_hz):
    """Calculate R1: R1 = √2 / (π×0.6×f×C1)"""
    try:
        return math.sqrt(2) / (math.pi * 0.6 * f_sensor_hz * C1_F)
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def calc_r2(C2_F, rp_min_ohm, C_sensor_F):
    """Calculate R2: R2 = 2×Rp_Min×Csensor / C2"""
    try:
        return 2 * rp_min_ohm * C_sensor_F / C2_F
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def find_nearest_r1(calc_r1_ohm):
    """Find the smallest valid R1 value >= calculated value."""
    if calc_r1_ohm is None or calc_r1_ohm <= 0:
        return None
    best_idx = None
    for i, val in enumerate(R1_OPTIONS_VALUES):
        if val >= calc_r1_ohm:
            best_idx = i
    return best_idx if best_idx is not None else 0


def find_nearest_r2(calc_r2_ohm):
    """Find the smallest valid R2 value >= calculated value."""
    if calc_r2_ohm is None or calc_r2_ohm <= 0:
        return None
    best_idx = None
    for i, val in enumerate(R2_OPTIONS_VALUES):
        if val >= calc_r2_ohm:
            best_idx = i
    return best_idx if best_idx is not None else 0


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


def parse_sensor(s, unit_map):
    """Parse sensor value with unit suffixes."""
    s = s.strip()
    # Sort suffixes by length (longest first) to avoid partial matches
    sorted_suffixes = sorted(unit_map.items(), key=lambda x: len(x[0]), reverse=True)
    # Check for unit suffix first
    for suffix, mult in sorted_suffixes:
        if s.endswith(suffix):
            try:
                return float(s[:-len(suffix)]) * mult
            except (ValueError, TypeError):
                return None
    # No suffix - treat as raw value
    try:
        return float(s)
    except (ValueError, TypeError):
        return None