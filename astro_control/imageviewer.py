"""Image viewer widget with live-view and simple live-stack functionality.

Uses numpy/PIL/PySide6 to display FITS/raw images from the camera.
Live-stack averages the last N frames (mean or median).
"""

import numpy as np

from PySide6.QtCore import Qt, QTimer, QElapsedTimer, Slot
from PySide6.QtGui import QImage, QPixmap, QBrush, QPen, QColor
from PySide6.QtWidgets import (
    QWidget, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGroupBox, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QCheckBox,
    QSpinBox, QDoubleSpinBox, QSlider, QFileDialog, QProgressBar,
    QComboBox,
)

from astro_control.devices import DeviceManager


class ImageViewer(QWidget):
    """Image viewer widget with live-view and live-stack."""

    def __init__(self, live_stack: bool = False, device_manager: DeviceManager = None):
        super().__init__()
        self.live_stack_mode = live_stack
        self.device_manager = device_manager
        self.setWindowTitle("Image Viewer")
        self.resize(800, 600)

        # Graphics view embedded inside widget
        self.view = QGraphicsView(self)
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        # Build toolbar
        self._setup_ui()

        # Periodic refresh timer (every 100ms for ~10 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_display)
        self._timer.start(100)

        # Live stack buffer
        self._frame_buffer: list = []
        self.stack_mode = "mean"
        self.stack_size = 10

        # Capture-retrieve state
        self._capture_timer = QTimer(self)
        self._capture_timer.timeout.connect(self._on_capture_timeout)
        self._capture_elapsed = QElapsedTimer()
        self._exposure_duration = 0.0

    def _setup_ui(self):
        toolbar = QGroupBox("Controls")
        tb_layout = QHBoxLayout(toolbar)

        self.btn_capture = QPushButton("Capture")
        self.btn_capture.clicked.connect(self._on_capture)
        tb_layout.addWidget(self.btn_capture)

        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self._on_save)
        tb_layout.addWidget(self.btn_save)

        self.btn_stack_toggle = QPushButton("Stack: OFF")
        self.btn_stack_toggle.setCheckable(True)
        self.btn_stack_toggle.toggled.connect(self._on_stack_toggle)
        tb_layout.addWidget(self.btn_stack_toggle)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        tb_layout.addWidget(self.progress)

        self.stack_label = QLabel("Stack: 0")
        tb_layout.addWidget(self.stack_label)

        # Exposure slider (seconds, range 0.1 - 30)
        self.exp_slider = QSlider(Qt.Horizontal)
        self.exp_slider.setRange(10, 300)
        self.exp_slider.setValue(50)  # 5.0 s
        tb_layout.addWidget(QLabel("Exp (s):"))
        tb_layout.addWidget(self.exp_slider)

        # Stack size spinner
        self.stack_size_spin = QSpinBox()
        self.stack_size_spin.setRange(2, 500)
        self.stack_size_spin.setValue(10)
        tb_layout.addWidget(QLabel("Stack N:"))
        tb_layout.addWidget(self.stack_size_spin)

        # Stack mode combo
        self.stack_mode_combo = QComboBox()
        self.stack_mode_combo.addItems(["Mean", "Median"])
        tb_layout.addWidget(self.stack_mode_combo)

        toolbar.setLayout(tb_layout)

        # Main layout: toolbar at top, view fills rest
        main_layout = QHBoxLayout(self)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(toolbar)
        left_layout.addStretch()
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(self.view, 3)

    def _on_capture(self):
        """Trigger a capture from the connected camera."""
        if not self.device_manager:
            print("[ImageViewer] no device manager configured")
            return
        camera = self.device_manager.find_first("camera")
        if not camera or not camera.is_connected():
            print("[ImageViewer] no camera connected")
            return

        exposure = self.exp_slider.value() / 10.0  # slider value = tenths of seconds

        try:
            camera.set_property("ExposureDuration", exposure)
            camera.set_property("StartExposure", True)
        except Exception as exc:
            print(f"[ImageViewer] capture error: {exc}")
            return

        self.progress.setVisible(True)
        self._exposure_duration = exposure
        self._capture_elapsed.start()
        # One-shot timer to retrieve image after exposure time
        self._capture_timer.start(int(exposure * 1000 + 500))

    @Slot()
    def _on_capture_timeout(self):
        """Timer handler: retrieve image after exposure timeout."""
        self._capture_timer.stop()
        retrieve_time = self._exposure_duration * 1000  # ms
        # We already waited enough; just try retrieval
        self._retrieve_and_display()

    def _retrieve_and_display(self):
        """Fetch the image array and display it."""
        if not self.device_manager:
            return
        camera = self.device_manager.find_first("camera")
        if not camera or not camera.is_connected():
            return

        # Try standard ImageArray first, then fall back to raw buffer
        arr = None
        try:
            arr = camera.get_property("ImageArray")
        except Exception:
            pass

        # If no ImageArray, try to trigger a retrieval-friendly property
        if arr is None:
            try:
                # Some DSLR/USB cameras expose image data via raw buffer or other means
                # Fall back to getting whatever image data is available
                raw = camera.get_property("ImageArray")  # retry
            except Exception:
                raw = None

        if arr is None:
            # Last resort: some cameras have a "Image" or "LastImage" property
            try:
                arr = camera.get_property("Image")
            except Exception:
                arr = None

        if arr is None:
            print("[ImageViewer] no image data found on camera")
            return

        if not hasattr(arr, "shape"):
            print("[ImageViewer] expected ndarray, got:", type(arr))
            return

        self._process_image(arr)

    def _process_image(self, img_array: np.ndarray):
        """Convert numpy array to QImage and display."""
        img = np.array(img_array)
        if img.dtype != np.uint8:
            lo, hi = img.min(), img.max()
            span = hi - lo
            if span == 0:
                img = np.zeros_like(img, dtype=np.uint8)
            else:
                img = ((img - lo) / span * 255).astype(np.uint8)

        if img.ndim == 2:
            img3 = np.stack([img, img, img], axis=-1)
            img = img3

        h, w = img.shape[:2]
        data = img.tobytes()
        qimg = QImage(data, w, h, 3 * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        self._fit_pixmap(pixmap)

        # Live stack
        if self.live_stack_mode:
            self._frame_buffer.append(img.copy())
            if len(self._frame_buffer) > self.stack_size:
                self._frame_buffer.pop(0)
            self._update_stack_display()

    def _fit_pixmap(self, pixmap):
        """Scale pixmap to fit view, keeping aspect ratio."""
        wv = self.width() - 20
        hv = self.height() - 60
        if wv <= 0 or hv <= 0:
            wv, hv = 400, 300
        scaled = pixmap.scaled(wv, hv, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.pixmap_item.setPixmap(scaled)

    def _update_stack_display(self):
        """If stack is non-empty, render mean or median of accumulated frames."""
        n = len(self._frame_buffer)
        self.stack_label.setText(f"Stack: {n}")
        if n == 0:
            return

        frames = [f.copy() for f in self._frame_buffer]
        if not frames:
            return

        arr = np.stack(frames, axis=0)
        label = self.stack_mode_combo.currentText().lower()
        self.stack_mode = label
        agg = np.mean(arr, axis=0) if label == "mean" else np.median(arr, axis=0)
        agg = agg.astype(np.uint8)

        if agg.ndim == 2:
            agg3 = np.stack([agg, agg, agg], axis=-1)
            agg = agg3

        h, w = agg.shape[:2]
        qimg = QImage(agg.tobytes(), w, h, 3 * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        self._fit_pixmap(pixmap)

    def _on_stack_toggle(self, enabled: bool):
        self.btn_stack_toggle.setText("Stack: ON" if enabled else "Stack: OFF")
        if enabled:
            self._frame_buffer.clear()
            self.stack_size = self.stack_size_spin.value()
            self._update_stack_display()

    def _on_save(self):
        fname, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "",
            "PNG (*.png);;TIFF (*.tiff);;FITS (*.fits)"
        )
        if fname:
            pix = self.pixmap_item.pixmap()
            if pix and pix.save(fname):
                print(f"[ImageViewer] saved to {fname}")
            else:
                print(f"[ImageViewer] failed to save {fname}")

    def _update_display(self):
        """Periodic check for new images from the camera.

        Tries to retrieve the latest frame from the connected camera.
        """
        if not self.device_manager:
            return
        camera = self.device_manager.find_first("camera")
        if camera and camera.is_connected():
            # Best-effort: poll for latest image
            try:
                arr = camera.get_property("ImageArray")
                if arr is not None and hasattr(arr, "shape"):
                    self._process_image(arr)
            except Exception:
                pass
            # Also try fallback property names
            try:
                arr2 = camera.get_property("Image")
                if arr2 is not None and hasattr(arr2, "shape") and arr2 is not arr:
                    self._process_image(arr2)
            except Exception:
                pass

    def set_device_manager(self, dm: DeviceManager):
        self.device_manager = dm
        self._timer.stop()
        self._timer.start(100)
