"""Guiding tab widget.

Provides autoguiding control and graph:
- Connect guide camera
- Calibration settings
- Guide parameters (aggressiveness, min move, exposure)
- Start/stop guiding
- Live graph of guide errors (RA/Dec)
"""

import collections
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QDoubleSpinBox, QSpinBox, QPushButton, QLabel, QProgressBar,
    QCheckBox, QComboBox, QGraphicsView, QGraphicsScene,
    QScrollArea,
)
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPen, QColor, QPainter, QBrush

from astro_control.devices import DeviceManager
from astro_control.guidescope_widget import GuideScopeWidget


class GuidingWidget(QWidget):
    """Autoguiding control widget with live error graph."""

    def __init__(self, device_manager: DeviceManager):
        super().__init__()
        self.device_manager = device_manager
        self._is_guiding = False
        self._calibrated = False

        # Error history for graph (max 200 points)
        self._ra_errors = collections.deque(maxlen=200)
        self._dec_errors = collections.deque(maxlen=200)

        self._build_ui()
        self._setup_graph()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Scrollable top controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setLayout(QVBoxLayout())
        scroll.setWidget(scroll_content)

        # Connection section
        conn_group = QGroupBox("Guide Camera")
        conn_layout = QVBoxLayout(conn_group)

        self.btn_connect_guide = QPushButton("Connect Guide Camera")
        self.btn_connect_guide.clicked.connect(self._connect_guide_camera)
        conn_layout.addWidget(self.btn_connect_guide)

        self.lbl_guide_status = QLabel("Not connected")
        conn_layout.addWidget(self.lbl_guide_status)

        # Exposure control
        form = QFormLayout()
        self.sb_guide_exp = QDoubleSpinBox()
        self.sb_guide_exp.setRange(0.1, 10.0)
        self.sb_guide_exp.setValue(1.0)
        self.sb_guide_exp.setSingleStep(0.1)
        form.addRow("Guide exposure (s):", self.sb_guide_exp)

        self.sb_guide_gain = QSpinBox()
        self.sb_guide_gain.setRange(0, 500)
        self.sb_guide_gain.setValue(50)
        form.addRow("Guide gain:", self.sb_guide_gain)

        conn_layout.addLayout(form)
        layout.addWidget(conn_group)

        # Calibration section
        cal_group = QGroupBox("Calibration")
        cal_layout = QVBoxLayout(cal_group)

        self.btn_calibrate = QPushButton("Calibrate")
        self.btn_calibrate.clicked.connect(self._calibrate)
        cal_layout.addWidget(self.btn_calibrate)

        self.lbl_cal_status = QLabel("Not calibrated")
        cal_layout.addWidget(self.lbl_cal_status)

        # Calibration parameters
        cal_form = QFormLayout()
        self.sb_cal_step = QSpinBox()
        self.sb_cal_step.setRange(50, 1000)
        self.sb_cal_step.setValue(500)
        cal_form.addRow("Cal step (ms):", self.sb_cal_step)

        self.sb_cal_iter = QSpinBox()
        self.sb_cal_iter.setRange(1, 10)
        self.sb_cal_iter.setValue(3)
        cal_form.addRow("Iterations:", self.sb_cal_iter)

        cal_layout.addLayout(cal_form)
        layout.addWidget(cal_group)

        # Guide parameters (compact grid)
        guide_group = QGroupBox("Guide Settings")
        guide_layout = QFormLayout(guide_group)
        guide_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.sb_aggressiveness = QDoubleSpinBox()
        self.sb_aggressiveness.setRange(0.1, 3.0)
        self.sb_aggressiveness.setValue(1.0)
        self.sb_aggressiveness.setSingleStep(0.1)
        guide_layout.addRow("Aggressiveness:", self.sb_aggressiveness)

        self.sb_min_move = QDoubleSpinBox()
        self.sb_min_move.setRange(0.0, 10.0)
        self.sb_min_move.setValue(0.5)
        self.sb_min_move.setSingleStep(0.1)
        guide_layout.addRow("Min move (px):", self.sb_min_move)

        self.sb_max_move = QDoubleSpinBox()
        self.sb_max_move.setRange(1.0, 50.0)
        self.sb_max_move.setValue(10.0)
        self.sb_max_move.setSingleStep(0.5)
        guide_layout.addRow("Max move (px):", self.sb_max_move)

        self.cb_guide_mode = QComboBox()
        self.cb_guide_mode.addItems(["Both", "RA only", "Dec only"])
        guide_layout.addRow("Guide mode:", self.cb_guide_mode)

        layout.addWidget(guide_group)

        # Start/stop guiding
        guide_btn_layout = QHBoxLayout()
        self.btn_start_guide = QPushButton("Start Guiding")
        self.btn_start_guide.clicked.connect(self._start_guiding)
        guide_btn_layout.addWidget(self.btn_start_guide)

        self.btn_stop_guide = QPushButton("Stop Guiding")
        self.btn_stop_guide.clicked.connect(self._stop_guiding)
        self.btn_stop_guide.setEnabled(False)
        guide_btn_layout.addWidget(self.btn_stop_guide)

        layout.addLayout(guide_btn_layout)

        # Status
        self.lbl_guiding_status = QLabel("Guiding: Stopped")
        self.lbl_guiding_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_guiding_status)

        # Guide scope view
        self.guide_scope = GuideScopeWidget(self.device_manager)
        layout.addWidget(self.guide_scope)

        # Live graph
        graph_group = QGroupBox("Guide Error Graph")
        graph_layout = QVBoxLayout(graph_group)

        self.graph_view = QGraphicsView()
        self.graph_view.setMinimumHeight(200)
        self.graph_view.setRenderHint(QPainter.Antialiasing)
        graph_layout.addWidget(self.graph_view)

        layout.addWidget(graph_group)

        # Timer for graph updates and guiding loop
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_loop)
        self._update_timer.start(200)  # 5 Hz

    def _setup_graph(self):
        """Setup the graph scene."""
        self.graph_scene = QGraphicsScene()
        self.graph_view.setScene(self.graph_scene)

        # Initial empty scene
        self.graph_scene.setSceneRect(0, 0, 600, 200)

    def _connect_guide_camera(self):
        """Connect to the guide camera."""
        # Guide camera is typically a second camera device
        # For simplicity, we'll try to find a second camera or the same camera
        guide_cam = None
        cameras = self.device_manager.cameras
        if len(cameras) > 1:
            guide_cam = cameras[1]
        elif cameras:
            guide_cam = cameras[0]

        if not guide_cam:
            print("[GuidingWidget] no guide camera device found")
            return

        if guide_cam.is_connected():
            guide_cam.disconnect()
            self.lbl_guide_status.setText("Not connected")
            self.btn_connect_guide.setText("Connect Guide Camera")
        else:
            ok = guide_cam.connect()
            if ok:
                self.lbl_guide_status.setText("Connected")
                self.btn_connect_guide.setText("Disconnect Guide Camera")

    def _calibrate(self):
        """Run calibration routine."""
        if not self._calibrated:
            print("[GuidingWidget] Starting calibration...")
            self.lbl_cal_status.setText("Calibrating...")
            # Simulate calibration
            import threading
            threading.Timer(2.0, self._calibration_done).start()
        else:
            self._calibrated = False
            self.lbl_cal_status.setText("Not calibrated")
            self.btn_calibrate.setText("Calibrate")

    def _calibration_done(self):
        """Called when calibration completes."""
        self._calibrated = True
        self.lbl_cal_status.setText("Calibrated")
        self.btn_calibrate.setText("Re-calibrate")
        print("[GuidingWidget] Calibration complete")

    def _start_guiding(self):
        """Start autoguiding loop."""
        if not self._calibrated:
            print("[GuidingWidget] Need to calibrate first")
            return

        guide_cam = self._get_guide_camera()
        if not guide_cam or not guide_cam.is_connected():
            print("[GuidingWidget] No guide camera connected")
            return

        mount = self.device_manager.find_first("mount")
        if not mount or not mount.is_connected():
            print("[GuidingWidget] No mount connected")
            return

        self._is_guiding = True
        self.btn_start_guide.setEnabled(False)
        self.btn_stop_guide.setEnabled(True)
        self.lbl_guiding_status.setText("Guiding: Active")

        # Set guide camera properties
        try:
            exp = self.sb_guide_exp.value()
            gain = self.sb_guide_gain.value()
            guide_cam.set_property("ExposureDuration", exp)
            guide_cam.set_property("Gain", gain)
            guide_cam.set_property("StartExposure", True)
        except Exception as e:
            print(f"[GuidingWidget] camera setup error: {e}")

    def _stop_guiding(self):
        """Stop autoguiding loop."""
        self._is_guiding = False
        self.btn_start_guide.setEnabled(True)
        self.btn_stop_guide.setEnabled(False)
        self.lbl_guiding_status.setText("Guiding: Stopped")

        # Clear error history
        self._ra_errors.clear()
        self._dec_errors.clear()
        self._redraw_graph()

    def _update_loop(self):
        """Periodic update for guiding and graph."""
        if self._is_guiding:
            self._guiding_step()

        # Update graph display
        self._redraw_graph()

    def _guiding_step(self):
        """One iteration of the guiding loop."""
        # In a real implementation, this would:
        # 1. Capture a guide frame
        # 2. Detect star centroid
        # 3. Calculate error from reference position
        # 4. Send correction to mount
        # For demo, we simulate some errors
        import random

        # Simulate small random errors
        ra_err = random.uniform(-2.0, 2.0)
        dec_err = random.uniform(-2.0, 2.0)

        # Apply aggressiveness
        agg = self.sb_aggressiveness.value()
        ra_err *= agg
        dec_err *= agg

        # Apply min/max move limits
        min_move = self.sb_min_move.value()
        max_move = self.sb_max_move.value()

        if abs(ra_err) < min_move:
            ra_err = 0.0
        elif abs(ra_err) > max_move:
            ra_err = math.copysign(max_move, ra_err)

        if abs(dec_err) < min_move:
            dec_err = 0.0
        elif abs(dec_err) > max_move:
            dec_err = math.copysign(max_move, dec_err)

        # Store errors for graph
        self._ra_errors.append(ra_err)
        self._dec_errors.append(dec_err)

        # Send corrections to mount (simplified)
        mount = self.device_manager.find_first("mount")
        if mount and mount.is_connected() and (ra_err != 0 or dec_err != 0):
            mode = self.cb_guide_mode.currentText()
            try:
                if mode in ("Both", "RA only") and ra_err != 0:
                    # Send RA correction
                    pass
                if mode in ("Both", "Dec only") and dec_err != 0:
                    # Send Dec correction
                    pass
            except Exception as e:
                print(f"[GuidingWidget] mount correction error: {e}")

    def _redraw_graph(self):
        """Redraw the error graph."""
        self.graph_scene.clear()

        w = self.graph_view.width() or 600
        h = self.graph_view.height() or 200
        self.graph_scene.setSceneRect(0, 0, w, h)

        # Background
        self.graph_scene.addRect(0, 0, w, h, QPen(QColor(20, 20, 30)), QBrush(QColor(20, 20, 30)))

        # Center line
        center_y = h / 2
        pen_center = QPen(QColor(60, 60, 80), 1)
        self.graph_scene.addLine(0, center_y, w, center_y, pen_center)

        # Grid lines
        pen_grid = QPen(QColor(40, 40, 60), 1)
        for i in range(1, 5):
            y = center_y + (i * h / 8)
            self.graph_scene.addLine(0, y, w, y, pen_grid)
            self.graph_scene.addLine(0, center_y - (i * h / 8), w, center_y - (i * h / 8), pen_grid)

        # Labels for scale
        # +5, -5 pixel scale markers
        for label, offset in [("+5px", -5), ("-5px", 5)]:
            y = center_y + offset * (h / 40)  # 5 px per 1/8 height
            txt = self.graph_scene.addText(label)
            txt.setDefaultTextColor(QColor(100, 100, 120))
            txt.setPos(5, y - 8)

        # Plot RA errors (red)
        if self._ra_errors:
            pen_ra = QPen(QColor(255, 100, 100), 2)
            self._plot_series(self._ra_errors, w, h, center_y, pen_ra)

        # Plot Dec errors (cyan)
        if self._dec_errors:
            pen_dec = QPen(QColor(100, 255, 255), 2)
            self._plot_series(self._dec_errors, w, h, center_y, pen_dec)

        # Legend
        self._add_legend(w, h)

    def _plot_series(self, data, w, h, center_y, pen):
        """Plot a series of error values as a line."""
        n = len(data)
        if n < 2:
            return

        # Scale: 1 pixel = 1/40 of height
        scale = h / 40.0  # 5 pixels per division

        points = []
        for i, val in enumerate(data):
            x = (i / max(1, n - 1)) * w
            y = center_y - val * scale
            points.append(QPointF(x, y))

        # Draw lines between points
        for i in range(len(points) - 1):
            self.graph_scene.addLine(
                points[i].x(), points[i].y(),
                points[i+1].x(), points[i+1].y(),
                pen
            )

    def _add_legend(self, w, h):
        """Add a simple legend to the graph."""
        # RA legend
        ra_pen = QPen(QColor(255, 100, 100), 2)
        self.graph_scene.addLine(10, 10, 30, 10, ra_pen)
        ra_txt = self.graph_scene.addText("RA")
        ra_txt.setDefaultTextColor(QColor(255, 100, 100))
        ra_txt.setPos(35, 5)

        # Dec legend
        dec_pen = QPen(QColor(100, 255, 255), 2)
        self.graph_scene.addLine(10, 30, 30, 30, dec_pen)
        dec_txt = self.graph_scene.addText("Dec")
        dec_txt.setDefaultTextColor(QColor(100, 255, 255))
        dec_txt.setPos(35, 25)

    def _get_guide_camera(self):
        """Get the guide camera device."""
        cameras = self.device_manager.cameras
        if len(cameras) > 1:
            return cameras[1]
        elif cameras:
            return cameras[0]
        return None