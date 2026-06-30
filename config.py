# ═══════════════════════════════════════════════════════════════
#  CONFIGURATION - Colors, Fonts, Constants
# ═══════════════════════════════════════════════════════════════

# Modern Professional Engineering Color Palette
COLORS = {
    # Primary Colors
    "primary":          "#1A73E8",
    "primary_dark":     "#1557B0",
    "primary_light":    "#4A90E2",

    # Accent Colors
    "accent":           "#1A73E8",
    "accent_hover":     "#1557B0",
    "accent_light":     "#E8F0FE",
    "accent_blue":      "#34A853",

    # Status Colors
    "success":          "#34A853",
    "success_bg":       "#E6F4EA",
    "success_light":    "#1E8E3E",
    "warning":          "#FBBC04",
    "warning_bg":       "#FEF7E0",
    "warning_light":    "#F9A825",
    "error":            "#EA4335",
    "error_bg":         "#FCE8E6",
    "error_light":      "#D93025",
    "info":             "#1A73E8",
    "info_bg":          "#E8F0FE",

    # Background Colors
    "bg_main":          "#FFFFFF",
    "bg_white":         "#F5F7FA",
    "bg_section":       "#F5F7FA",
    "bg_card":          "#FFFFFF",
    "bg_input":         "#FFFFFF",
    "bg_output":        "#F5F7FA",
    "bg_hover":         "#E8F0FE",

    # Text Colors
    "text_primary":     "#212121",
    "text_secondary":   "#5F6368",
    "text_muted":       "#757575",
    "text_on_primary":  "#FFFFFF",

    # Border Colors
    "border":           "#DADCE0",
    "border_focus":     "#1A73E8",
    "border_hover":     "#B9B9B9",

    # LED/Status Indicator Colors
    "led_green":        "#34A853",
    "led_red":          "#EA4335",
    "led_amber":        "#FBBC04",
    "led_inactive":     "#DADCE0",

    # Legacy keys — required for compatibility, do not remove
    "bg_dark":          "#F5F7FA",
    "bg_header":        "#E8F0FE",
    "bg_even":          "#FFFFFF",
    "bg_odd":           "#F5F7FA",
    "bg_group":         "#F5F7FA",
    "bg_top_bar":       "#E8F0FE",
    "fg_normal":        "#212121",
    "fg_bold":          "#1A73E8",
    "fg_white":         "#FFFFFF",
    "fg_gray":          "#5F6368",
    "fg_light_gray":    "#757575",
    "fg_label":         "#212121",
    "ti_red":           "#EA4335",
    "header":           "#1A73E8",
    "header_text":      "#FFFFFF",
}

# Modern Typography System - 2026 Engineering Tool Standards
FONTS = {
    # Page Titles - 20px Bold
    "page_title":       ("Segoe UI", 20, "bold"),

    # Section Headers - 14-16px Bold
    "section_title":    ("Segoe UI", 14, "bold"),
    "section_subtitle": ("Segoe UI", 12, "bold"),

    # Labels - 11-12px Regular
    "label":            ("Segoe UI", 11),
    "label_bold":       ("Segoe UI", 11, "bold"),
    "label_small":      ("Segoe UI", 10),

    # Measurement Values - 18-24px Bold - KPI Display
    "value":           ("Consolas", 14, "bold"),
    "value_lg":        ("Consolas", 18, "bold"),
    "value_xl":        ("Consolas", 24, "bold"),

    # KPI Display - Large prominent values
    "kpi_value":       ("Consolas", 22, "bold"),
    "kpi_label":       ("Segoe UI", 10, "bold"),
    "kpi_unit":        ("Segoe UI", 10),

    # Navigation
    "nav_item":        ("Segoe UI", 11, "bold"),
    "nav_item_small":  ("Segoe UI", 10),

    # General
    "normal":          ("Segoe UI", 11),
    "normal_bold":     ("Segoe UI", 11, "bold"),
    "small":           ("Segoe UI", 10),
    "small_bold":      ("Segoe UI", 10, "bold"),
    "mono":            ("Consolas", 11),
    "courier":         ("Consolas", 10),
    "tiny_italic":     ("Segoe UI", 9, "italic"),

    # Legacy keys
    "title":           ("Segoe UI", 18, "bold"),
    "heading":         ("Segoe UI", 12, "bold"),
    "heading_bold":    ("Segoe UI", 12, "bold"),
}

# Spacing System (8px base) - Professional spacing
SPACING = {
    "xs":   4,      # Extra small - 4px
    "sm":   8,      # Small - 8px
    "md":   16,     # Medium - 16px
    "lg":   24,     # Large - 24px
    "xl":   32,     # Extra large - 32px
    "xxl":  48,     # Extra extra large - 48px
}

# Corner Radius - Modern rounded corners
RADIUS = {
    "sm":   4,      # Small - 4px
    "md":   6,      # Medium - 6px
    "lg":   8,      # Large - 8px
    "xl":   12,     # Extra large - 12px
}

# Shadow definitions for cards
SHADOWS = {
    "sm": "0 1px 2px rgba(0,0,0,0.05)",
    "md": "0 2px 4px rgba(0,0,0,0.1)",
    "lg": "0 4px 8px rgba(0,0,0,0.15)",
}

# Version
VERSION = "1.0.0.8"

# Navigation Icons (Engineering tool style)
NAV_ICONS = {
    "RP+L": "📈",
    "LHR": "📊",
    "Apps Calc": "🧮",
    "Registers": "⚙",
    "About": "ℹ"
}

# Window settings
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 1100
WINDOW_TITLE = "Eddy Current Displacement Measurement"

# Table column widths
TABLE_COL_WIDTHS = [200, 80, 80, 60, 55, 80, 80]
TABLE_COLUMNS = (
    "Block / Register Name", "Address", "Default", "Mode", "Size", "LW*", "LR*"
)

# Sidebar items with icons (modern engineering tool style)
SIDEBAR_ITEMS = [
    ("RP+L", "📈"),
    ("LHR", "📊"),
    ("Apps Calc", "🧮"),
    ("Registers", "⚙"),
    ("About", "ℹ"),
]
SIDEBAR_LABELS = ["RP+L", "LHR", "Apps Calc", "Registers", "About"]
DEFAULT_SIDEBAR = "Registers"

# Menu bar
MENU_ITEMS = ["File", "Script", "Debug", "Help"]

# R1/R2 calculation constants
R1_MAX_OHMS = 417000
R1_STEP_OHMS = 12770
R1_OPTIONS_COUNT = 32

R2_MAX_OHMS = 835000
R2_STEP_OHMS = 12770
R2_OPTIONS_COUNT = 64

# Debug flag
DEBUG = True

# Logging configuration
import logging
import os

LOG_DIR = os.path.join(os.getcwd(), "logs")
LOG_FILE = os.path.join(LOG_DIR, "ldc1101_gui.log")
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO

def setup_logging():
    """Initialize logging for the application."""
    os.makedirs(LOG_DIR, exist_ok=True)

    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, mode="a"),
            logging.StreamHandler()
        ]
    )

    # Suppress verbose third-party debug logs
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)

    return logging.getLogger("LDC1101_GUI")

logger = setup_logging()