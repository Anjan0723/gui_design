# ═══════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT - LDC1101 EVM GUI
# ═══════════════════════════════════════════════════════════════

from gui_main import MainGUI


def main():
    """Run the application."""
    app = MainGUI()
    app.run()


if __name__ == "__main__":
    main()