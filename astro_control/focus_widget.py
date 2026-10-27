"""Focus routine tab widget.

Provides focus control and settings:
- Connect to focuser device
- Move focuser in/out
- Set focus step size
- Run focus routine (inhale/exhale, single direction)
- Display current position
"""

import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QDoubleSpinBox, QSpinBox, QPushButton, QLabel, QProgressBar,
    QCheckBox, QSlider, QComboBox,
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer

from astro_control.devices import DeviceManager


class FocusWidget(QWidget):
    """Focus control widget with routine and settings."""

    # Signal emitted when focus routine starts/stops
    routine_started = Signal()
    routine_stopped = Signal()

    def __init__(self, device_manager: DeviceManager):
        super().__init__()
        self.device_manager = device_manager
        self._is_focusing = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Connection section
        conn_group = QGroupBox("Connection")
        conn_layout = QVBoxLayout(conn_group)

        self.btn_connect_focuser = QPushButton("Connect Focuser")
        self.btn_connect_focuser.clicked.connect(self._connect_focuser)
        conn_layout.addWidget(self.btn_connect_focuser)

        self.lbl_focuser_status = QLabel("Not connected")
        conn_layout.addWidget(self.lbl_focuser_status)

        layout.addWidget(conn_group)

        # Controls section
        controls_group = QGroupBox("Focus Controls")
        controls_layout = QFormLayout(controls_group)

        # Step size
        self.sb_step = QSpinBox()
        self.sb_step.setRange(1, 200)
        self.sb_step.setValue(10)
        self.sb_step.setSingleStep(1)
        controls_layout.addRow("Step size:", self.sb_step)

        # Speed slider
        self.sb_speed = QSlider(Qt.Horizontal)
        self.sb_speed.setRange(1, 100)
        self.sb_speed.setValue(50)
        controls_layout.addRow("Speed:", self.sb_speed)

        # Current position
        self.lbl_position = QLabel("Position: --")
        controls_layout.addRow("Current position:", self.lbl_position)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_move_in = QPushButton("Move In")
        self.btn_move_in.clicked.connect(self._move_in)
        btn_layout.addWidget(self.btn_move_in)

        self.btn_move_out = QPushButton("Move Out")
        self.btn_move_out.clicked.connect(self._move_out)
        btn_layout.addWidget(self.btn_move_out)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self._stop_focus)
        btn_layout.addWidget(self.btn_stop)

        controls_layout.addRow(btn_layout)

        layout.addWidget(controls_group)

        # Routine section
        routine_group = QGroupBox("Focus Routine")
        routine_layout = QVBoxLayout(routine_group)

        # Routine type
        form = QFormLayout()
        self.cb_routine = QComboBox()
        self.cb_routine.addItems(["Inhale/Exhale", "Single Direction", "Bahtinov"])
        form.addRow("Routine type:", self.cb_routine)

        # Number of iterations
        self.sb_iterations = QSpinBox()
        self.sb_iterations.setRange(1, 100)
        self.sb_iterations.setValue(5)
        form.addRow("Iterations:", self.sb_iterations)

        # Step delay
        self.sb_delay = QDoubleSpinBox()
        self.sb_delay.setRange(0.1, 60.0)
        self.sb_delay.setValue(1.0)
        self.sb_delay.setSingleStep(0.5)
        form.addRow("Step delay (s):", self.sb_delay)

        routine_layout.addLayout(form)

        # Routine buttons
        routine_btn_layout = QHBoxLayout()
        self.btn_start_routine = QPushButton("Start Routine")
        self.btn_start_routine.clicked.connect(self._start_routine)
        routine_btn_layout.addWidget(self.btn_start_routine)

        self.btn_stop_routine = QPushButton("Stop Routine")
        self.btn_stop_routine.clicked.connect(self._stop_routine)
        self.btn_stop_routine.setEnabled(False)
        routine_btn_layout.addWidget(self.btn_stop_routine)

        routine_layout.addLayout(routine_btn_layout)

        layout.addWidget(routine_group)

        # Status/progress
        self.progress_focus = QProgressBar()
        self.progress_focus.setRange(0, 100)
        layout.addWidget(self.progress_focus)

        return layout

    def _connect_focuser(self):
        """Connect to the focuser device."""
        focuser = self.device_manager.find_first("focuser")
        if not focuser:
            print("[FocusWidget] no focuser device found")
            return

        if focuser.is_connected():
            focuser.disconnect()
            self.lbl_focuser_status.setText("Not connected")
            self.btn_connect_focuser.setText("Connect Focuser")
        else:
            ok = focuser.connect()
            if ok:
                self.lbl_focuser_status.setText("Connected")
                self.btn_connect_focuser.setText("Disconnect Focuser")
                try:
                    pos = focuser.get_property("Position") or 0
                    self.lbl_position.setText(f"Position: {pos}")
                except Exception:
                    pass

    def _move_in(self):
        """Move focuser inward."""
        focuser = self.device_manager.find_first("focuser")
        if not focuser or not focuser.is_connected():
            return

        step = self.sb_step.value()
        try:
            pos = focuser.get_property("Position") or 0
            focuser.set_property("Position", pos - step)
            try:
                new_pos = focuser.get_property("Position") or 0
                self.lbl_position.setText(f"Position: {new_pos}")
            except Exception:
                pass
        except Exception as e:
            print(f"[FocusWidget] move in error: {e}")

    def _move_out(self):
        """Move focuser outward."""
        focuser = self.device_manager.find_first("focuser")
        if not focuser or not focuser.is_connected():
            return

        step = self.sb_step.value()
        try:
            pos = focuser.get_property("Position") or 0
            focuser.set_property("Position", pos + step)
            try:
                new_pos = focuser.get_property("Position") or 0
                self.lbl_position.setText(f"Position: {new_pos}")
            except Exception:
                pass
        except Exception as e:
            print(f"[FocusWidget] move out error: {e}")

    def _stop_focus(self):
        """Stop focus movement (sends Halt/Abort if supported)."""
        focuser = self.device_manager.find_first("focuser")
        if focuser and focuser.is_connected():
            try:
                handle = focuser._get_handle()
                if hasattr(handle, "Halt") and callable(handle.Halt):
                    handle.Halt()
                elif hasattr(handle, "Abort") and callable(handle.Abort):
                    handle.Abort()
                else:
                    # Fallback: try setting current position
                    pos = focuser.get_property("Position") or 0
                    focuser.set_property("Position", pos)
            except Exception as e:
                print(f"[FocusWidget] stop error: {e}")

    def _start_routine(self):
        """Start the focus routine."""
        focuser = self.device_manager.find_first("focuser")
        if not focuser or not focuser.is_connected():
            print("[FocusWidget] no focuser connected")
            return

        self._is_focusing = True
        self.btn_start_routine.setEnabled(False)
        self.btn_stop_routine.setEnabled(True)
        self.progress_focus.setValue(0)
        self.routine_started.emit()

        # Simple one-shot demo: run a few steps via timer
        self._routine_timer = QTimer(self)
        self._routine_timer.timeout.connect(self._routine_step)
        self._routine_timer.start(100)  # 10 Hz

    def _stop_routine(self):
        """Stop the focus routine."""
        self._is_focusing = False
        self.btn_start_routine.setEnabled(True)
        self.btn_stop_routine.setEnabled(False)
        self.routine_stopped.emit()

        if hasattr(self, "_routine_timer"):
            self._routine_timer.stop()

    def _routine_step(self):
        """One step of the focus routine."""
        focuser = self.device_manager.find_first("focuser")
        if not focuser or not focuser.is_connected() or not self._is_focusing:
            self._stop_routine()
            return

        routine_type = self.cb_routine.currentText()
        step = self.sb_step.value()
        delay = self.sb_delay.value()

        try:
            pos = focuser.get_property("Position") or 0

            if routine_type == "Inhale/Exhale":
                focuser.set_property("Position", pos - step)
                self._update_position(focuser)
                time.sleep(min(delay, 0.05))  # scaled down for demo
                focuser.set_property("Position", pos + step)
                self._update_position(focuser)

            elif routine_type == "Single Direction":
                focuser.set_property("Position", pos + step)
                self._update_position(focuser)

            # Increment progress
            self.progress_focus.setValue(min(100, self.progress_focus.value() + 1))

        except Exception as e:
            print(f"[FocusWidget] routine error: {e}")

    def _update_position(self, focuser):
        """Refresh the position label from the focuser."""
        try:
            new_pos = focuser.get_property("Position") or 0
            self.lbl_position.setText(f"Position: {new_pos}")
        except Exception:
            pass
