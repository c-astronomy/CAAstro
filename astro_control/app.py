"""Main application window with tab-based UI for AstroControl."""

import sys

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QProgressBar, QPushButton, QSlider, QSpinBox, QDoubleSpinBox,
    QCheckBox, QComboBox, QToolButton, QTreeWidget, QTreeWidgetItem,
    QTabWidget, QVBoxLayout, QWidget, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QFileDialog,
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QImage

from astro_control.devices import DeviceManager
from astro_control.planetarium import PlanetariumWidget
from astro_control.sequencer import Sequencer
from astro_control.imageviewer import ImageViewer
from astro_control.focus_widget import FocusWidget
from astro_control.guiding_widget import GuidingWidget
from astro_control.mount_widget import MountWidget
from astro_control.status_widget import StatusLogWidget
from astro_control.polar_align_widget import PolarAlignWidget


class MainWindow(QMainWindow):
    """Main window with tabs for Devices, Planetarium, Sequencer, and Viewer."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AstroControl")
        self.resize(1400, 900)

        # Core components
        self.device_manager = DeviceManager()
        self.sequencer = Sequencer(self.device_manager)
        self.image_viewer = ImageViewer(device_manager=self.device_manager)  # <-- Fixed here

        # Global dark theme
        self.setStyleSheet("""
            QWidget { background-color: #080808; color: #e0e0e0; }
            QLabel { color: #e8e8e8; }
            QPushButton { background-color: #1a1a1a; color: #00ff88; border: 1px solid #22aa44; padding: 4px; }
            QPushButton:hover { background-color: #222222; color: #55ffbb; }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QSlider { background-color: #111111; color: #e0e0e0; border: 1px solid #333333; }
            QGroupBox { border: 1px solid #22aa44; color: #00ff88; font-weight: bold; }
            QTreeWidget { background-color: #0a0a0a; color: #e8e8e8; border: 1px solid #22aa44; }
            QTabWidget::pane { border: 1px solid #22aa44; background: #080808; }
            QTabBar::tab { background: #111111; color: #00ff88; border: 1px solid #22aa44; padding: 6px; }
            QTabBar::tab:selected { background: #1a2a1a; color: #55ffbb; }
            QTextEdit { background-color: #0a0a0a; color: #e0e0e0; border: 1px solid #22aa44; }
            QProgressBar { background: #111; border: 1px solid #22aa44; color: #00ff88; }
            QProgressBar::chunk { background: #00aa44; }
        """)

        # Build UI
        self._build_ui()
        # Default theme after UI built
        if hasattr(self, 'theme_combo'):
            self.theme_combo.setCurrentIndex(1)
        self._build_ui()

        # Refresh timer for planetarium
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._update_planetarium)
        self._refresh_timer.start(500)

        # Connect signals
        self.device_manager.connection_status_changed.connect(
            self._update_connection_status
        )

    def _build_ui(self):
        """Build the main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # Left panel: split into device tree + settings/config
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Top: device tree
        left_layout.addWidget(QLabel("<b>Devices</b>"))
        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabel("Connected Equipment")
        self.device_tree.itemDoubleClicked.connect(self._on_device_double_click)
        left_layout.addWidget(self.device_tree, 2)

        # Bottom: device settings / config for selected gear
        settings_box = QGroupBox("Device Settings")
        settings_layout = QVBoxLayout(settings_box)
        settings_layout.addWidget(QLabel("Select a device above to configure."))
        # Placeholder config controls — extensible per device type
        self.lbl_config = QLabel("Device Type: —")
        settings_layout.addWidget(self.lbl_config)
        self.lbl_config.setStyleSheet("font-size: 10px; color: #aaa;")
        left_layout.addWidget(settings_box, 1)

        # Theme switcher (Light / Dark / Alt Red-Green)
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Alt Red-Green"])
        self.theme_combo.currentIndexChanged.connect(self._switch_theme)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        left_layout.addLayout(theme_layout)

        # Control buttons
        btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._refresh_devices)
        btn_layout.addWidget(self.btn_refresh)

        self.btn_connect = QPushButton("Connect All")
        self.btn_connect.clicked.connect(self._connect_all)
        btn_layout.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("Disconnect All")
        self.btn_disconnect.clicked.connect(self._disconnect_all)
        btn_layout.addWidget(self.btn_disconnect)

        btn_layout.addStretch()
        left_layout.addLayout(btn_layout)
        layout.addWidget(left_panel, 1)

        # Middle: tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 2)

        # Planetarium tab
        self.planetarium_widget = PlanetariumWidget(self.device_manager)
        self.tabs.addTab(self.planetarium_widget, "Planetarium")

        # Sequencer tab
        self.tabs.addTab(self.sequencer, "Sequencer")

        # Mount tab (new)
        self.mount_widget = MountWidget(self.device_manager)
        self.tabs.addTab(self.mount_widget, "Mount")

        # Focus tab (new)
        self.focus_widget = FocusWidget(self.device_manager)
        self.tabs.addTab(self.focus_widget, "Focus")

        # Guiding tab (new)
        self.guiding_widget = GuidingWidget(self.device_manager)
        self.tabs.addTab(self.guiding_widget, "Guiding")

        self.status_widget = StatusLogWidget(self.device_manager)
        self.tabs.addTab(self.status_widget, "Status")

        # Polar Alignment
        self.polar_widget = PolarAlignWidget(self.device_manager)
        self.tabs.addTab(self.polar_widget, "Polar Align")

        # Image viewer tab
        self.tabs.addTab(self.image_viewer, "Viewer")

        # Status bar
        self.status_bar = self.statusBar()
        self.conn_label = QLabel("Status: Disconnected")
        self.status_bar.addPermanentWidget(self.conn_label)
        self.device_label = QLabel("")
        self.status_bar.addPermanentWidget(self.device_label)

    def _refresh_devices(self):
        """Refresh device list from Alpaca discovery."""
        self.device_tree.clear()
        self.device_manager.discover_devices()

        # Populate tree
        for dev_type, devices in self.device_manager.devices_by_type.items():
            if not devices:
                continue
            item = QTreeWidgetItem([f"{dev_type} ({len(devices)})"])
            for dev in devices:
                child = QTreeWidgetItem([dev.name or "Unknown"])
                child.setData(0, Qt.UserRole, dev)
                item.addChild(child)
            self.device_tree.addTopLevelItem(item)

    @Slot()
    def _connect_all(self):
        """Attempt to connect all discovered devices."""
        self.device_manager.connect_all()

    @Slot()
    def _disconnect_all(self):
        """Disconnect all devices."""
        self.device_manager.disconnect_all()

    @Slot(object, int)
    def _on_device_double_click(self, item, column):
        """Handle device double-click: toggle single device connection."""
        dev = item.data(0, Qt.UserRole)
        if dev:
            if dev.is_connected():
                dev.disconnect()
                if self.device_manager.connection_status_changed:
                    self.device_manager.connection_status_changed.emit(dev.device_type, False)
            else:
                ok = dev.connect()
                if ok and self.device_manager.connection_status_changed:
                    self.device_manager.connection_status_changed.emit(dev.device_type, True)

    @Slot(str, bool)
    def _update_connection_status(self, device_type, connected):
        """Update status when device connection changes."""
        self.conn_label.setText(f"Status: {'Connected' if connected else 'Disconnected'}")
        self.conn_label.setStyleSheet(
            "color: green;" if connected else "color: red;"
        )

    def _update_planetarium(self):
        """Update planetarium with current time and mount position."""
        self.planetarium_widget.update_frame()


    def _switch_theme(self, idx):
        if idx == 0:  # Light
            self.setStyleSheet("QWidget { background-color: #f5f5f5; color: #111; } QPushButton { background-color: #ddd; color: #111; border: 1px solid #777; } QGroupBox { border: 1px solid #777; color: #333; } QTreeWidget { background: #fff; color: #111; border: 1px solid #777; }")
        elif idx == 1:  # Dark (default green)
            self.setStyleSheet("""
                QWidget { background-color: #080808; color: #e0e0e0; }
                QLabel { color: #e8e8e8; }
                QPushButton { background-color: #1a1a1a; color: #00ff88; border: 1px solid #22aa44; padding: 4px; }
                QPushButton:hover { background-color: #222222; color: #55ffbb; }
                QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QSlider { background-color: #111111; color: #e0e0e0; border: 1px solid #333333; }
                QGroupBox { border: 1px solid #22aa44; color: #00ff88; font-weight: bold; }
                QTreeWidget { background-color: #0a0a0a; color: #e8e8e8; border: 1px solid #22aa44; }
                QTabWidget::pane { border: 1px solid #22aa44; background: #080808; }
                QTabBar::tab { background: #111111; color: #00ff88; border: 1px solid #22aa44; padding: 6px; }
                QTabBar::tab:selected { background: #1a2a1a; color: #55ffbb; }
                QTextEdit { background-color: #0a0a0a; color: #e0e0e0; border: 1px solid #22aa44; }
                QProgressBar { background: #111; border: 1px solid #22aa44; color: #00ff88; }
                QProgressBar::chunk { background: #00aa44; }
            """)
        else:  # Alt Red-Green
            self.setStyleSheet("""
                QWidget { background-color: #0a0a0a; color: #ff5555; }
                QLabel { color: #ff8888; }
                QPushButton { background-color: #1a1a1a; color: #ffaa00; border: 1px solid #ff3333; padding: 4px; }
                QPushButton:hover { background-color: #220000; color: #ffeeee; }
                QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QSlider { background-color: #111111; color: #ff5555; border: 1px solid #aa2222; }
                QGroupBox { border: 1px solid #ff3333; color: #ff5555; font-weight: bold; }
                QTreeWidget { background-color: #0a0a0a; color: #ffeeee; border: 1px solid #ff3333; }
                QTabWidget::pane { border: 1px solid #ff3333; background: #0a0a0a; }
                QTabBar::tab { background: #111111; color: #ffaa00; border: 1px solid #ff3333; padding: 6px; }
                QTabBar::tab:selected { background: #2a1111; color: #ffeeee; }
                QTextEdit { background-color: #0a0a0a; color: #ff5555; border: 1px solid #ff3333; }
                QProgressBar { background: #111; border: 1px solid #ff3333; color: #ff5555; }
                QProgressBar::chunk { background: #cc2222; }
            """)


def create_app():
    """Factory function for testing."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    return MainWindow()
