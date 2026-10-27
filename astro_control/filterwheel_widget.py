"""Filter wheel setup widget.

Allows mapping filter names to slots and selecting filters.
Can be added to the sequencer."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QPushButton, QLabel, QComboBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt

from astro_control.devices import DeviceManager


class FilterWheelWidget(QWidget):
    """Filter wheel slot mapping and selection."""

    def __init__(self, device_manager: DeviceManager):
        super().__init__()
        self.device_manager = device_manager
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Connection
        conn = QGroupBox("Filter Wheel")
        conn_layout = QHBoxLayout(conn)
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self._connect)
        conn_layout.addWidget(self.btn_connect)
        self.lbl_status = QLabel("Not connected")
        conn_layout.addWidget(self.lbl_status)
        layout.addWidget(conn)

        # Slot mapping table
        map_group = QGroupBox("Slot Mapping")
        map_layout = QVBoxLayout(map_group)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Slot", "Filter Name"])
        self.table.horizontalHeader().setStretchLastSection(True)
        # Pre-fill with common filters
        filters = [
            (1, "Luminance"), (2, "Red"), (3, "Green"), (4, "Blue"),
            (5, "Ha"), (6, "OIII"), (7, "SII"), (8, "UVIR")
        ]
        self.table.setRowCount(len(filters))
        for i, (slot, name) in enumerate(filters):
            self.table.setItem(i, 0, QTableWidgetItem(str(slot)))
            self.table.setItem(i, 1, QTableWidgetItem(name))
        map_layout.addWidget(self.table)
        layout.addWidget(map_group)

        # Quick select
        sel_group = QGroupBox("Select Filter")
        sel_layout = QHBoxLayout(sel_group)
        self.cb_filter = QComboBox()
        for _, name in filters:
            self.cb_filter.addItem(name)
        sel_layout.addWidget(QLabel("Filter:"))
        sel_layout.addWidget(self.cb_filter)
        self.btn_select = QPushButton("Select")
        self.btn_select.clicked.connect(self._select_filter)
        sel_layout.addWidget(self.btn_select)
        layout.addWidget(sel_group)

    def _connect(self):
        fw = self.device_manager.find_first("filterwheel")
        if not fw:
            return
        if fw.is_connected():
            fw.disconnect(); self.lbl_status.setText("Disconnected")
        else:
            fw.connect(); self.lbl_status.setText("Connected")

    def _select_filter(self):
        fw = self.device_manager.find_first("filterwheel")
        if not fw or not fw.is_connected():
            return
        name = self.cb_filter.currentText()
        # Find slot from mapping
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1) and self.table.item(row, 1).text() == name:
                slot = int(self.table.item(row, 0).text())
                try:
                    fw.set_property("Position", slot)
                except Exception:
                    pass
                return
