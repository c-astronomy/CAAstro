"""Guide scope viewer widget.

Shows guide camera images with a simple star-detection overlay.
Used in the guiding tab to visualize which stars are being tracked.
"""

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QColor, QPainter, QPen

from astro_control.devices import DeviceManager


class GuideScopeWidget(QWidget):
    """Simple guide camera viewer with star overlay."""

    def __init__(self, device_manager: DeviceManager):
        super().__init__()
        self.device_manager = device_manager
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_image)
        self._timer.start(500)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Header info
        header = QHBoxLayout()
        self.lbl_guide_view_title = QLabel("Guide Scope View")
        self.lbl_guide_view_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(self.lbl_guide_view_title)
        self.lbl_guide_fps = QLabel("FPS: --")
        header.addWidget(self.lbl_guide_fps)
        header.addStretch()
        layout.addLayout(header)

        # Graphics view
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        layout.addWidget(self.view)

        # Controls row
        ctrl = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._update_image)
        ctrl.addWidget(self.btn_refresh)

        self.lbl_info = QLabel("Waiting for guide image...")
        ctrl.addWidget(self.lbl_info)
        ctrl.addStretch()
        layout.addLayout(ctrl)

    def _update_image(self):
        """Retrieve latest guide camera image and show stars."""
        camera = None
        cameras = self.device_manager.cameras
        if len(cameras) > 1:
            camera = cameras[1]  # second camera as guide
        elif cameras:
            camera = cameras[0]  # fallback

        if not camera or not camera.is_connected():
            self.lbl_info.setText("No guide camera connected")
            return

        try:
            arr = camera.get_property("ImageArray")
            if arr is None:
                # Try raw buffer for demo purposes
                self.lbl_info.setText("No image array available")
                return
            if not hasattr(arr, "shape"):
                return

            img = np.array(arr)
            # Normalize to 8-bit
            if img.dtype != np.uint8:
                lo, hi = img.min(), img.max()
                span = hi - lo
                if span == 0:
                    img = np.zeros_like(img, dtype=np.uint8)
                else:
                    img = ((img - lo) / span * 255).astype(np.uint8)

            # Ensure grayscale -> RGB for display
            if img.ndim == 2:
                img3 = np.stack([img, img, img], axis=-1)
                img = img3

            # Simple star overlay: detect bright spots by simple threshold
            stars = self._find_stars(img)

            h, w = img.shape[:2]
            data = img.tobytes()
            qimg = QImage(data, w, h, 3 * w, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)

            # Scale to view
            wv = self.view.width() - 20 or 600
            hv = self.view.height() - 80 or 400
            scaled = pixmap.scaled(wv, hv, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            self.scene.clear()
            pixmap_item = QGraphicsPixmapItem(scaled)
            self.scene.addItem(pixmap_item)

            # Draw stars overlay in red
            pen = QPen(QColor(255, 0, 0), 2)
            scale_x = wv / w
            scale_y = hv / h
            for (sx, sy) in stars:
                # Scale star coordinates to pixmap size
                cx = sx * scale_x
                cy = sy * scale_y
                circ = self.scene.addEllipse(cx - 4, cy - 4, 8, 8, pen, QColor(255, 200, 200, 100))
            self.lbl_info.setText(f"Stars detected: {len(stars)}")
        except Exception as exc:
            self.lbl_info.setText(f"Image error: {exc}")

    def _find_stars(self, img_array: np.ndarray) -> list:
        """Simple star detection via threshold."""
        stars = []
        # Work on grayscale
        gray = img_array[:, :, 0] if img_array.ndim == 3 else img_array
        # Simple threshold: pixels brighter than 70% of max
        threshold = gray.max() * 0.7 if gray.max() > 0 else 200
        h, w = gray.shape
        # Very simple: find bright spots every 20 pixels
        for y in range(10, h - 10, 15):
            for x in range(10, w - 10, 15):
                if gray[y, x] > threshold:
                    stars.append((x, y))
        return stars
