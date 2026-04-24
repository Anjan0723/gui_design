# ═══════════════════════════════════════════════════════════════
#  CONFIGURATION - Colors, Fonts, Constants
# ═══════════════════════════════════════════════════════════════

# Colors
COLORS = {
    "bg_main": "#f0f0f0",
    "bg_dark": "#1f3864",
    "bg_white": "white",
    "bg_header": "#dce6f1",
    "bg_even": "white",
    "bg_odd": "#f5f8ff",
    "bg_group": "#dce6f1",
    "bg_top_bar": "#e8e8e8",
    "fg_normal": "black",
    "fg_bold": "#1f3864",
    "fg_white": "white",
    "fg_gray": "#888888",
    "fg_light_gray": "#aaaaaa",
    "fg_label": "#333333",
    "accent_blue": "#0078d7",
    "accent": "#0078d7",
    "success": "#107c10",
    "error": "#cc0000",
    "warning": "#ff4444",
    "ti_red": "#c8102e",
    "border": "#cccccc",
}

# Fonts
FONTS = {
    "title": ("Arial", 18, "bold"),
    "heading": ("Arial", 9, "bold"),
    "normal": ("Arial", 9),
    "normal_bold": ("Arial", 9, "bold"),
    "courier": ("Courier New", 10),
    "small": ("Arial", 8),
    "small_bold": ("Arial", 8, "bold"),
    "tiny_italic": ("Arial", 7, "italic"),
}

# Version
VERSION = "1.0.0.7"

# Window settings
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 780
WINDOW_TITLE = "LDC1101 EVM GUI"

# Table column widths
TABLE_COL_WIDTHS = [170, 70, 70, 50, 45, 70, 70]
TABLE_COLUMNS = (
    "Block / Register Name", "Address", "Default", "Mode", "Size", "LW*", "LR*"
)

# Sidebar items
SIDEBAR_ITEMS = [
    "LHR",
    "Apps Calculator",
    "Register Configuration",
    "About"
]
DEFAULT_SIDEBAR = "Register Configuration"

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
DEBUG = False

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
    return logging.getLogger("LDC1101_GUI")

logger = setup_logging()