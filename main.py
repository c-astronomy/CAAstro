#!/usr/bin/env python3
"""AstroControl — Astrophotography control application.

A simple, clean, cross-platform Python GUI for controlling ASCOM/INDI/Alpaca
astronomy equipment: camera, guide camera, mount, focuser, filter wheel, etc.

Features
--------
- Alpaca-based device discovery and connection (runs INDIGO / ASCOM drivers).
- Connect camera, guide camera, mount, focuser, filter wheel.
- Basic planetarium showing mount location and common deep-sky objects.
- Sequencer: goto / platesolve / focus / capture / exposure / gain.
- Image viewer with live-view.
- Simple live-stack (mean/median) of captured frames.

Run
---
    python main.py
"""

import sys
from PySide6.QtWidgets import QApplication
from astro_control.app import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AstroControl")
    app.setOrganizationName("AstroControl")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
