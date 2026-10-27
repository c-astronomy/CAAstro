"""Status and log tab widget.

Shows a simple event log and device status overview.
All actions (connect, disconnect, sequence steps, guiding, focus) log here.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Qt

from astro_control.devices import DeviceManager


class StatusLogWidget(QWidget):
    """Status overview with event log and device table."""

    def __init__(self, device_manager: DeviceManager):
        super().__init__()
        self.device_manager = device_manager
        self._build_ui()
        self.log("Status widget initialized")

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Device status table
        info_group = QGroupBox("Device Status")
        info_layout = QVBoxLayout(info_group)
        self.status_table = QTableWidget()
        self.status_table.setColumnCount(3)
        self.status_table.setHorizontalHeaderLabels(["Device", "Type", "Status"])
        self.status_table.horizontalHeader().setStretchLastSection(True)
        info_layout.addWidget(self.status_table)
        layout.addWidget(info_group)

        # Event log
        log_group = QGroupBox("Event Log")
        log_layout = QVBoxLayout(log_group)
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setMaximumHeight(200)
        log_layout.addWidget(self.event_log)
        layout.addWidget(log_group)

    def log(self, message: str):
        """Add a message to the event log."""
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        self.event_log.insertPlainText(line)
        self.event_log.ensureCursorVisible()

    def refresh_table(self):
        """Refresh the device status table from the manager."""
        self.status_table.setRowCount(0)
        row = 0
        for dev_type, devices in self.device_manager.devices_by_type.items():
            for dev in devices:
                connected = "Connected" if dev.is_connected() else "Disconnected"
                self.status_table.insertRow(row)
                self.status_table.setItem(row, 0, QTableWidgetItem(dev.name or "Unknown"))
                self.status_table.setItem(row, 1, QTableWidgetItem(dev.device_type))
                self.status_table.setItem(row, 2, QTableWidgetItem(connected))
                row += 1
        self.status_table.resizeColumnsToContents()
