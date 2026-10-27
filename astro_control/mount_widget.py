"""Mount control tab widget.

Provides mount status, tracking, slewing, and coordinate display.
- Connect mount device
- Manual directional controls (N/E/S/W) with speed settings
- GOTO RA/Dec
- Tracking on/off
- Park / Unpark
- Display current mount position (Alt/Az or RA/Dec) and tracking state
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QSpinBox, QDoubleSpinBox, QPushButton, QLabel, QComboBox,
    QCheckBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer

from astro_control.devices import DeviceManager


class MountWidget(QWidget):
    """Mount control widget with status, tracking, slewing, and GOTO."""

    def __init__(self, device_manager: DeviceManager):
        super().__init__()
        self.device_manager = device_manager
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_status)
        self._timer.start(500)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Connection
        conn_group = QGroupBox("Mount Connection")
        conn_layout = QHBoxLayout(conn_group)
        self.btn_connect_mount = QPushButton("Connect Mount")
        self.btn_connect_mount.clicked.connect(self._connect_mount)
        conn_layout.addWidget(self.btn_connect_mount)
        self.lbl_mount_status = QLabel("Not connected")
        conn_layout.addWidget(self.lbl_mount_status)
        conn_layout.addStretch()
        layout.addWidget(conn_group)

        # Status / Position display
        status_group = QGroupBox("Status")
        status_layout = QHBoxLayout(status_group)
        self.lbl_alt_az = QLabel("Alt/Az: -- / --")
        status_layout.addWidget(self.lbl_alt_az)
        self.lbl_ra_dec = QLabel("RA/Dec: -- / --")
        status_layout.addWidget(self.lbl_ra_dec)
        self.lbl_tracking = QLabel("Tracking: OFF")
        status_layout.addWidget(self.lbl_tracking)
        layout.addWidget(status_group)

        # Manual control
        control_group = QGroupBox("Manual Slew")
        control_layout = QHBoxLayout(control_group)

        # Direction buttons grid
        dir_group = QGroupBox("Direction")
        dir_layout = QHBoxLayout(dir_group)
        btn_grid = QWidget()
        btn_grid_layout = QHBoxLayout(btn_grid)

        self.btn_north = QPushButton("N")
        self.btn_north.clicked.connect(lambda: self._slew_dir("north"))
        btn_grid_layout.addWidget(self.btn_north)
        self.btn_south = QPushButton("S")
        self.btn_south.clicked.connect(lambda: self._slew_dir("south"))
        btn_grid_layout.addWidget(self.btn_south)
        self.btn_east = QPushButton("E")
        self.btn_east.clicked.connect(lambda: self._slew_dir("east"))
        btn_grid_layout.addWidget(self.btn_east)
        self.btn_west = QPushButton("W")
        self.btn_west.clicked.connect(lambda: self._slew_dir("west"))
        btn_grid_layout.addWidget(self.btn_west)
        btn_grid_layout.addStretch()
        dir_layout.addLayout(btn_grid_layout)
        control_layout.addWidget(dir_group)

        # Speed settings
        speed_group = QGroupBox("Speed")
        speed_layout = QFormLayout(speed_group)
        self.cb_speed = QComboBox()
        self.cb_speed.addItems(["Slow", "Medium", "Fast"])
        speed_layout.addRow("Slew speed:", self.cb_speed)
        control_layout.addWidget(speed_group)
        layout.addWidget(control_group)

        # Tracking / Park
        track_group = QGroupBox("Tracking")
        track_layout = QHBoxLayout(track_group)
        self.btn_tracking = QPushButton("Start Tracking")
        self.btn_tracking.setCheckable(True)
        self.btn_tracking.toggled.connect(self._toggle_tracking)
        track_layout.addWidget(self.btn_tracking)

        self.btn_park = QPushButton("Park")
        self.btn_park.clicked.connect(self._park)
        track_layout.addWidget(self.btn_park)

        self.btn_unpark = QPushButton("Unpark")
        self.btn_unpark.clicked.connect(self._unpark)
        track_layout.addWidget(self.btn_unpark)
        layout.addWidget(track_group)

        # GOTO
        goto_group = QGroupBox("GOTO")
        goto_layout = QFormLayout(goto_group)
        self.sb_ra = QDoubleSpinBox()
        self.sb_ra.setRange(0, 24)
        self.sb_ra.setSingleStep(0.1)
        goto_layout.addRow("RA (h):", self.sb_ra)
        self.sb_dec = QDoubleSpinBox()
        self.sb_dec.setRange(-90, 90)
        self.sb_dec.setSingleStep(0.1)
        goto_layout.addRow("Dec (deg):", self.sb_dec)

        self.btn_goto = QPushButton("GOTO")
        self.btn_goto.clicked.connect(self._goto)
        goto_layout.addRow(self.btn_goto)
        layout.addWidget(goto_group)

    def _get_mount(self):
        """Helper to find any valid mount or telescope device, avoiding bad index fallbacks."""
        mounts = self.device_manager.mounts
        if mounts:
            for m in mounts:
                if m.is_connected():
                    return m
            return mounts[0]
        return None

    def _connect_mount(self):
        mount = self._get_mount()
        if not mount:
            self.lbl_mount_status.setText("No mount found!")
            return
            
        if mount.is_connected():
            mount.disconnect()
            self.lbl_mount_status.setText("Not connected")
            self.btn_connect_mount.setText("Connect Mount")
        else:
            ok = mount.connect()
            if ok:
                self.lbl_mount_status.setText("Connected")
                self.btn_connect_mount.setText("Disconnect Mount")
            else:
                self.lbl_mount_status.setText("Connection Failed")

    def _slew_dir(self, direction: str):
        mount = self._get_mount()
        if not mount or not mount.is_connected():
            return
        try:
            handle = mount._get_handle()
            # Try common ASCOM/Alpaca slew methods by direction
            dir_map = {
                "north": (0, 1),
                "south": (0, -1),
                "east": (1, 0),
                "west": (-1, 0),
            }
            axis, rate = dir_map.get(direction, (0, 0))
            if axis == 0:
                # Try command fallback
                try:
                    mount.command_string(f"SLEW_{direction.upper()}")
                except Exception:
                    pass
            else:
                # Try MoveAxis if available
                if hasattr(handle, "MoveAxis") and callable(handle.MoveAxis):
                    try:
                        # ASCOM MoveAxis uses Primary/Secondary (RA=primary, Dec=secondary)
                        # Approximate: north/south is Dec, east/west is RA
                        if direction in ("north", "south"):
                            handle.MoveAxis(1, rate * 0.5)
                        else:
                            handle.MoveAxis(0, rate * 0.5)
                    except Exception:
                        pass
                else:
                    mount.command_string(f"SLEW_{direction.upper()}")
        except Exception as exc:
            print(f"[Mount] Slew error: {exc}")

    def _toggle_tracking(self, enabled: bool):
        mount = self._get_mount()
        if not mount or not mount.is_connected():
            return
        try:
            mount.set_property("Tracking", enabled)
        except Exception as exc:
            print(f"[Mount] Tracking error: {exc}")
        self.lbl_tracking.setText("Tracking: ON" if enabled else "Tracking: OFF")

    def _park(self):
        mount = self._get_mount()
        if not mount or not mount.is_connected():
            return
        try:
            handle = mount._get_handle()
            if hasattr(handle, "Park") and callable(handle.Park):
                handle.Park()
            else:
                print("[Mount] Park method not found on handle.")
        except Exception as exc:
            print(f"[Mount] Park error: {exc}")

    def _unpark(self):
        mount = self._get_mount()
        if not mount or not mount.is_connected():
            return
        try:
            handle = mount._get_handle()
            if hasattr(handle, "Unpark") and callable(handle.Unpark):
                handle.Unpark()
            else:
                print("[Mount] Unpark method not found on handle.")
        except Exception as exc:
            print(f"[Mount] Unpark error: {exc}")

    def _goto(self):
        mount = self._get_mount()
        if not mount or not mount.is_connected():
            return
        ra = self.sb_ra.value()
        dec = self.sb_dec.value()
        try:
            handle = mount._get_handle()
            if hasattr(handle, "SlewToCoordinatesAsync"):
                handle.SlewToCoordinatesAsync(ra, dec)
            elif hasattr(handle, "SlewToCoordinates"):
                handle.SlewToCoordinates(ra, dec)
            else:
                print("[Mount] Error: No GOTO method found on mount handle.")
        except Exception as exc:
            print(f"[Mount] GOTO error: {exc}")

    def _update_status(self):
        mount = self._get_mount()
        if not mount or not mount.is_connected():
            self.lbl_mount_status.setText("Not connected")
            self.btn_connect_mount.setText("Connect Mount")
            return
            
        self.lbl_mount_status.setText("Connected")
        self.btn_connect_mount.setText("Disconnect Mount")
        try:
            alt = float(mount.get_property("Altitude", 0) or 0)
            az = float(mount.get_property("Azimuth", 0) or 0)
            tracking = bool(mount.get_property("Tracking", False))
            ra = float(mount.get_property("RightAscension", 0) or 0)
            dec = float(mount.get_property("Declination", 0) or 0)
            
            self.lbl_alt_az.setText(f"Alt/Az: {alt:.1f}° / {az:.1f}°")
            self.lbl_ra_dec.setText(f"RA/Dec: {ra:.2f}h / {dec:.2f}°")
            self.lbl_tracking.setText(f"Tracking: {'ON' if tracking else 'OFF'}")
        except Exception as exc:
            pass
