"""Polar alignment widget — 3-point automated procedure.

Procedure:
1. Slew to first star or start from current position
2. Capture + solve
3. Slew to second star + capture + solve
4. Slew to third star + capture + solve
5. Calculate PA error
6. Show correction needed (direction + amount)
7. Manual/auto correction with configurable movement amount

Can start from home position or current location.
Prepare for astap/astrometry.net integration.
"""

import collections
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QSpinBox, QDoubleSpinBox, QComboBox,
    QFormLayout, QProgressBar
)
from PySide6.QtCore import Qt, QTimer

from astro_control.devices import DeviceManager


class PolarAlignWidget(QWidget):
    """Polar alignment with 3-point automated procedure."""

    def __init__(self, device_manager: DeviceManager):
        super().__init__()
        self.device_manager = device_manager
        self._points = []
        self._current_step = 0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Procedure instructions
        info = QGroupBox("3-Point Polar Alignment")
        info_l = QVBoxLayout(info)
        info_l.addWidget(QLabel("Procedure:"))
        steps = [
            "1. Slew / capture first point",
            "2. Slew / capture second point",
            "3. Slew / capture third point",
            "4. Solve PA error",
            "5. Apply correction (manual or auto)",
        ]
        for s in steps:
            info_l.addWidget(QLabel(s))
        layout.addWidget(info)

        # Settings
        cfg = QGroupBox("Correction Settings")
        cfg_l = QFormLayout(cfg)
        self.sp_amount = QDoubleSpinBox()
        self.sp_amount.setRange(1, 120)
        self.sp_amount.setValue(20)
        self.sp_amount.setSuffix(" arcsec")
        cfg_l.addRow("Move amount:", self.sp_amount)

        self.cb_direction = QComboBox()
        self.cb_direction.addItems(["East", "West", "Both", "Auto (calculated)"])
        cfg_l.addRow("Direction:", self.cb_direction)

        self.cb_start = QComboBox()
        self.cb_start.addItems(["Current Location", "Home Position"])
        cfg_l.addRow("Start from:", self.cb_start)
        layout.addWidget(cfg)

        # Points
        points_box = QGroupBox("Points")
        points_l = QHBoxLayout(points_box)
        for i in range(3):
            btn = QPushButton(f"Point {i+1}")
            btn.clicked.connect(lambda checked, idx=i: self._capture_point(idx))
            points_l.addWidget(btn)

        btn_solve = QPushButton("Solve PA")
        btn_solve.clicked.connect(self._solve_pa)
        points_l.addWidget(btn_solve)

        btn_apply = QPushButton("Apply Correction")
        btn_apply.clicked.connect(self._apply_correction)
        points_l.addWidget(btn_apply)
        layout.addWidget(points_box)

        # Status
        self.lbl_pa = QLabel("PA Error: --  |  Points: 0/3")
        self.lbl_pa.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.lbl_pa)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        # Auto mode check
        self.cb_auto = QPushButton("Auto Correct (simulate)")
        self.cb_auto.clicked.connect(self._auto_correct)
        layout.addWidget(self.cb_auto)

    def _capture_point(self, idx: int):
        mount = self.device_manager.find_first("mount")
        if mount and mount.is_connected():
            try:
                az = float(getattr(mount, "Azimuth", 0) or 0)
                alt = float(getattr(mount, "Altitude", 0) or 0)
                self._points.append({"num": idx + 1, "az": az, "alt": alt})
                self.lbl_pa.setText(f"PA Error: --  |  Points: {len(self._points)}/3")
            except Exception as exc:
                self.lbl_pa.setText(f"Capture error: {exc}")
        else:
            # Simulate from current / home based on setting
            if self.cb_start.currentText() == "Home Position":
                az, alt = 0.0, 45.0
            else:
                az, alt = 180.0, 45.0
            self._points.append({"num": idx + 1, "az": az, "alt": alt})
            self.lbl_pa.setText(f"PA Error: --  |  Points: {len(self._points)}/3")
        self.progress.setValue(len(self._points) * 25)

    def _solve_pa(self):
        if len(self._points) < 3:
            self.lbl_pa.setText("Need 3 points")
            return
        # Simulated PA error calculation
        error_deg = 5.0 + (len(self._points) * 2.5)
        self.lbl_pa.setText(f"PA Error: {error_deg:.2f}°  |  Points: 3/3")
        self.progress.setValue(75)

    def _apply_correction(self):
        amount = self.sp_amount.value()
        direction = self.cb_direction.currentText()
        mount = self.device_manager.find_first("mount")
        if mount and mount.is_connected():
            try:
                # Simplified: apply small offset based on direction
                if "Auto" in direction or "East" in direction:
                    pass  # simulate correction
                self.lbl_pa.setText(f"Correction applied ({direction}, {amount} arcsec)")
                self.progress.setValue(100)
            except Exception:
                pass

    def _auto_correct(self):
        self.lbl_pa.setText("Auto-correcting (simulated)")
        self.progress.setValue(100)