"""Sequencer widget for GOTO/Platesolve/Focus/Capture operations."""

import time
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox,
    QLabel, QFrame, QFormLayout, QGroupBox, QFileDialog,
    QProgressBar, QDialog, QDialogButtonBox, QRadioButton,
    QButtonGroup, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot

from astro_control.devices import DeviceManager
from astro_control.config import save_sequence, load_sequence, list_profiles


class Sequencer(QWidget):
    """Widget that provides GOTO / Platesolve / Focus / Capture / Exposure / Gain control."""

    def __init__(self, device_manager: DeviceManager):
        super().__init__()
        self.device_manager = device_manager
        self._stop_requested = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Queue area
        queue_box = QGroupBox("Queue")
        queue_layout = QVBoxLayout(queue_box)

        self.queue_list = QListWidget()
        queue_layout.addWidget(self.queue_list)

        self.queue_list.itemSelectionChanged.connect(self._update_selection_highlight)
        # Queue controls
        qc = QHBoxLayout()
        self.btn_add_step = QPushButton("Add Step")
        self.btn_add_step.clicked.connect(self._add_default_step)
        qc.addWidget(self.btn_add_step)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.queue_list.clear)
        qc.addWidget(self.btn_clear)

        qc.addStretch()

        self.btn_up = QPushButton("Up")
        self.btn_up.clicked.connect(self._move_up)
        qc.addWidget(self.btn_up)

        self.btn_down = QPushButton("Down")
        self.btn_down.clicked.connect(self._move_down)
        qc.addWidget(self.btn_down)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self._delete_step)
        qc.addWidget(self.btn_delete)

        self.btn_edit = QPushButton("Edit")
        self.btn_edit.clicked.connect(self._edit_step)
        qc.addWidget(self.btn_edit)

        queue_layout.addLayout(qc)
        layout.addWidget(queue_box)

        # Run controls
        run_box = QGroupBox("Execution")
        rb_layout = QHBoxLayout(run_box)
        self.btn_run = QPushButton("Run")
        self.btn_run.clicked.connect(self._run_sequence)
        rb_layout.addWidget(self.btn_run)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self._stop_sequence)
        rb_layout.addWidget(self.btn_stop)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        rb_layout.addWidget(self.progress)

        layout.addWidget(run_box)

        # Predefined step buttons
        step_box = QGroupBox("Quick Steps")
        sb_layout = QHBoxLayout(step_box)
        for step_name in ["GOTO", "Focus", "Capture", "PlateSolve", "Filter", "Track ON", "Track OFF"]:
            btn = QPushButton(step_name)
            btn.clicked.connect(lambda checked, s=step_name.lower(): self._quick_add(s))
            sb_layout.addWidget(btn)
        layout.addWidget(step_box)

        # Profile save/load
        profile_box = QGroupBox("Sequence Profile")
        profile_layout = QHBoxLayout(profile_box)
        btn_save_profile = QPushButton("Save Profile")
        btn_save_profile.clicked.connect(self._save_profile)
        profile_layout.addWidget(btn_save_profile)
        btn_load_profile = QPushButton("Load Profile")
        btn_load_profile.clicked.connect(self._load_profile)
        profile_layout.addWidget(btn_load_profile)
        layout.addWidget(profile_box)

    def _update_selection_highlight(self):
        """Highlight currently selected item card."""
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            card = self.queue_list.itemWidget(item)
            if card:
                card.setSelected(i == self.queue_list.currentRow())

    def _add_default_step(self):
        """Prompt for step type and add to queue."""
        dlg = StepDialog(self.device_manager, self)
        if dlg.exec() == QDialog.Accepted:
            self.add_step(dlg.step_type, dlg.params)

    def _quick_add(self, step_type: str):
        """Quick add a common step with defaults."""
        defaults = {
            "goto": {"ra": 0.0, "dec": 0.0},
            "platesolve": {},
            "focus": {"step": 50},
            "capture": {"exposure": 5.0, "gain": 100},
            "set_exposure": {"exposure": 5.0},
            "set_gain": {"gain": 100},
        }
        self.add_step(step_type, defaults.get(step_type, {}))

    def add_step(self, step_type: str, params: dict, active: bool = True):
        """Add a step to the queue as a card with toggle."""
        item = QListWidgetItem()
        item.setData(Qt.UserRole, (step_type, params, active))
        card = StepCard(step_type, params, active)
        item.setSizeHint(card.sizeHint())
        self.queue_list.addItem(item)
        self.queue_list.setItemWidget(item, card)

    def _move_up(self):
        row = self.queue_list.currentRow()
        if row > 0:
            item = self.queue_list.item(row)
            if item:
                step_type, params, active = item.data(Qt.UserRole)
                self.queue_list.takeItem(row)
                new_item = QListWidgetItem()
                new_item.setData(Qt.UserRole, (step_type, params, active))
                card = StepCard(step_type, params, active)
                new_item.setSizeHint(card.sizeHint())
                self.queue_list.insertItem(row - 1, new_item)
                self.queue_list.setItemWidget(new_item, card)
                self.queue_list.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.queue_list.currentRow()
        if row >= 0 and row < self.queue_list.count() - 1:
            item = self.queue_list.item(row)
            if item:
                step_type, params, active = item.data(Qt.UserRole)
                self.queue_list.takeItem(row)
                new_item = QListWidgetItem()
                new_item.setData(Qt.UserRole, (step_type, params, active))
                card = StepCard(step_type, params, active)
                new_item.setSizeHint(card.sizeHint())
                self.queue_list.insertItem(row + 1, new_item)
                self.queue_list.setItemWidget(new_item, card)
                self.queue_list.setCurrentRow(row + 1)

    def _delete_step(self):
        row = self.queue_list.currentRow()
        if row >= 0:
            self.queue_list.takeItem(row)

    def _edit_step(self):
        row = self.queue_list.currentRow()
        if row < 0:
            return
        item = self.queue_list.item(row)
        step_type, params, active = item.data(Qt.UserRole)
        dlg = StepDialog(self.device_manager, self)
        dlg.cb_step.setCurrentText({
            "goto": "Slew (GOTO)", "platesolve": "Plate Solve",
            "focus": "Focus Move", "capture": "Capture Image",
            "set_exposure": "Set Exposure", "set_gain": "Set Gain"
        }.get(step_type, step_type))
        # Pre-fill values
        dlg.ra_edit.setValue(params.get("ra", 0))
        dlg.dec_edit.setValue(params.get("dec", 0))
        dlg.exp_edit.setValue(params.get("exposure", 0))
        dlg.gain_edit.setValue(params.get("gain", 0))
        dlg.step_edit.setValue(params.get("step", 10))
        if dlg.exec() == QDialog.Accepted:
            new_type = dlg.step_type
            new_params = dlg.params
            # Rebuild item
            card = StepCard(new_type, new_params, active)
            item.setData(Qt.UserRole, (new_type, new_params, active))
            self.queue_list.setItemWidget(item, card)

    def _save_profile(self):
        """Save current queue to a named profile (JSON)."""
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:")
        if ok and name:
            steps = []
            for i in range(self.queue_list.count()):
                item = self.queue_list.item(i)
                step_type, params, active = item.data(Qt.UserRole)
                steps.append({"type": step_type, "params": params, "active": active})
            save_sequence(name, steps)
            print(f"[Sequencer] saved profile '{name}'")

    def _load_profile(self):
        """Load a saved profile into the queue."""
        profiles = list_profiles()
        if not profiles:
            print("[Sequencer] no saved profiles")
            return
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getItem(self, "Load Profile", "Select profile:", profiles, 0, False)
        if ok and name:
            steps = load_sequence(name)
            self.queue_list.clear()
            for s in steps:
                self.add_step(s.get("type", "goto"), s.get("params", {}), s.get("active", True))
            print(f"[Sequencer] loaded profile '{name}'")

    def _run_sequence(self):
        """Execute the queued steps."""
        if self.queue_list.count() == 0:
            return

        self._stop_requested = False
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress.setValue(0)

        for i in range(self.queue_list.count()):
            if self._stop_requested:
                break
            item = self.queue_list.item(i)
            card = self.queue_list.itemWidget(item)
            if card and not card.is_active():
                # Skip disabled steps
                continue
            step_type, params, _ = item.data(Qt.UserRole)
            success = self._execute_step(step_type, params)
            self.progress.setValue(int(100.0 * (i + 1) / self.queue_list.count()))
            if not success:
                break

        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress.setValue(0)

    def _stop_sequence(self):
        """Stop sequence execution."""
        self._stop_requested = True

    def _execute_step(self, step_type: str, params: dict) -> bool:
        """Execute a single step, return True for success."""
        try:
            if step_type == "goto":
                return self._do_goto(params)
            elif step_type == "platesolve":
                return self._do_platesolve(params)
            elif step_type == "focus":
                return self._do_focus(params)
            elif step_type == "capture":
                return self._do_capture(params)
            elif step_type == "select_filter":
                return self._do_select_filter(params)
            elif step_type == "set_exposure":
                return self._do_set_exposure(params)
            elif step_type == "set_gain":
                return self._do_set_gain(params)
        except Exception as e:
            print(f"[Sequencer] {step_type} error: {e}")
        return False

    def _do_goto(self, params: dict) -> bool:
        mount = self.device_manager.find_first("mount") or self.device_manager.find_first("telescope")
        if not mount or not mount.is_connected():
            print("[Sequencer] no mount connected")
            return False
        # Alpaca mount slew
        try:
            mount.set_property("SlewToCoordinatesAsync", True)
            mount.set_property("TargetRightAscension", params.get("ra", 0))
            mount.set_property("TargetDeclination", params.get("dec", 0))
        except Exception:
            pass
        time.sleep(0.5)
        return True

    def _do_platesolve(self, params: dict) -> bool:
        try:
            from astro_control.platesolve_wrapper import PlateSolver
            solver = PlateSolver()
            result = solver.solve("/tmp/guide_image.png")
            if result.get("status") == "solved":
                print(f"[Sequencer] platesolve solved via {result.get('solver')}")
            else:
                print("[Sequencer] platesolve failed (no solver or no match) — integrate astap locally")
        except Exception as exc:
            print(f"[Sequencer] platesolve error: {exc}")
        return True

    def _do_focus(self, params: dict) -> bool:
        focuser = self.device_manager.find_first("focuser")
        if not focuser or not focuser.is_connected():
            print("[Sequencer] no focuser connected")
            return False
        step = params.get("step", 10)
        position = focuser.get_property("Position") or 0
        focuser.set_property("Position", position + step)
        time.sleep(0.5)
        return True

    def _do_capture(self, params: dict) -> bool:
        camera = self.device_manager.find_first("camera")
        if not camera or not camera.is_connected():
            print("[Sequencer] no camera connected")
            return False
        exp = params.get("exposure", 1.0)
        gain = params.get("gain", 0)
        try:
            camera.set_property("ExposureDuration", exp)
            camera.set_property("Gain", gain)
            camera.set_property("StartExposure", True)
        except Exception:
            pass
        time.sleep(max(0.1, exp))
        return True

    def _do_set_exposure(self, params: dict) -> bool:
        exp = params.get("exposure", 1.0)
        camera = self.device_manager.find_first("camera")
        if camera and camera.is_connected():
            camera.set_property("ExposureDuration", exp)
        return True

    def _do_set_gain(self, params: dict) -> bool:
        gain = params.get("gain", 0)
        camera = self.device_manager.find_first("camera")
        if camera and camera.is_connected():
            camera.set_property("Gain", gain)
        return True

    def _do_select_filter(self, params: dict) -> bool:
        fw = self.device_manager.find_first("filterwheel")
        if fw and fw.is_connected():
            fw.set_property("Position", params.get("filter", 1))
        return True


class StepCard(QFrame):
    """Visual card for a sequence step with checkbox toggle."""

    def __init__(self, step_type: str, params: dict, active: bool = True):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setStyleSheet("QFrame { border: 1px solid #555; border-radius: 6px; padding: 6px; background: #1e1e2e; }")

        layout = QHBoxLayout(self)
        layout.setSpacing(8)

        # Toggle checkbox
        self.check = QCheckBox()
        self.check.setChecked(active)
        self.check.setStyleSheet("color: white;")
        layout.addWidget(self.check)

        # Friendly label
        label_text = self._friendly_text(step_type, params)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #eee; font-size: 11px;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        layout.addStretch()

    def _friendly_text(self, step_type: str, params: dict) -> str:
        friendly = {
            "goto": "Slew Mount",
            "platesolve": "Plate Solve",
            "focus": "Focus",
            "capture": "Capture Image",
            "set_exposure": "Set Exposure",
            "set_gain": "Set Gain",
        }
        name = friendly.get(step_type, step_type)
        parts = [f"<b>{name}</b>"]
        if step_type == "goto":
            ra = params.get("ra", 0)
            dec = params.get("dec", 0)
            parts.append(f"→ RA {ra}h / Dec {dec}°")
        elif step_type == "focus":
            parts.append(f"step {params.get('step', '?')}")
        elif step_type == "capture":
            parts.append(f"{params.get('exposure', '?')}s exp | gain {params.get('gain', '?')}")
        elif step_type == "set_exposure":
            parts.append(f"{params.get('exposure', '?')}s")
        elif step_type == "set_gain":
            parts.append(f"gain {params.get('gain', '?')}")
        return " | ".join(parts)

        # Highlight on selection
        self.setHighlight(False)

    def setHighlight(self, on: bool):
        if on:
            self.setStyleSheet("QFrame { border: 2px solid #ffcc00; border-radius: 6px; padding: 6px; background: #2a2a3e; }")
        else:
            self.setStyleSheet("QFrame { border: 1px solid #555; border-radius: 6px; padding: 6px; background: #1e1e2e; }")

    def setSelected(self, on: bool):
        self.setHighlight(on)

    def is_active(self) -> bool:
        return self.check.isChecked()


class StepDialog(QDialog):
    """Dialog for adding a new step."""

    def __init__(self, device_manager: DeviceManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Step")
        self.device_manager = device_manager
        self.step_type = None
        self.params = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.cb_step = QComboBox()
        self.cb_step.addItems([
            "Slew (GOTO)", "Plate Solve", "Focus Move",
            "Capture Image", "Set Exposure", "Set Gain",
            "Select Filter"
        ])
        self.cb_step.currentIndexChanged.connect(self._on_step_type_changed)
        form.addRow("Step Type:", self.cb_step)

        # Param fields
        self.ra_edit = QDoubleSpinBox()
        self.ra_edit.setRange(0, 24)
        self.ra_edit.setSingleStep(0.1)
        self.dec_edit = QDoubleSpinBox()
        self.dec_edit.setRange(-90, 90)
        self.dec_edit.setSingleStep(0.1)
        self.exp_edit = QDoubleSpinBox()
        self.exp_edit.setRange(0.01, 300)
        self.exp_edit.setSingleStep(0.1)
        self.gain_edit = QSpinBox()
        self.gain_edit.setRange(0, 1000)
        self.step_edit = QSpinBox()
        self.step_edit.setRange(1, 100)
        self.filter_edit = QComboBox()
        filters = [
            (1, "Luminance"), (2, "Red"), (3, "Green"), (4, "Blue"),
            (5, "Ha"), (6, "OIII"), (7, "SII"), (8, "UVIR")
        ]
        for slot, name in filters:
            self.filter_edit.addItem(f"Slot {slot} ({name})", slot)

        form.addRow("Target RA (hours):", self.ra_edit)
        form.addRow("Target Dec (degrees):", self.dec_edit)
        form.addRow("Exposure Time (seconds):", self.exp_edit)
        form.addRow("Camera Gain:", self.gain_edit)
        form.addRow("Focuser Move Size:", self.step_edit)
        form.addRow("Filter Slot:", self.filter_edit)
        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._on_step_type_changed(0)

    def _on_step_type_changed(self, idx):
        text = self.cb_step.currentText()
        self.ra_edit.setVisible("Slew" in text)
        self.dec_edit.setVisible("Slew" in text)
        self.exp_edit.setVisible("Exposure" in text or "Capture" in text or "Image" in text)
        self.gain_edit.setVisible("Gain" in text or "Capture" in text or "Image" in text)
        self.step_edit.setVisible("Focus" in text)

    def _accept(self):
        step = self.cb_step.currentText()
        friendly = {
            "Slew (GOTO)": "goto", "Plate Solve": "platesolve",
            "Focus Move": "focus", "Capture Image": "capture",
            "Set Exposure": "set_exposure", "Set Gain": "set_gain",
            "Select Filter": "select_filter"
        }
        self.step_type = friendly.get(step, step)
        params = {}
        if "Slew" in step:
            params["ra"] = self.ra_edit.value()
            params["dec"] = self.dec_edit.value()
        elif "Exposure" in step or "Image" in step or "Capture" in step:
            params["exposure"] = self.exp_edit.value()
        elif "Gain" in step:
            params["gain"] = self.gain_edit.value()
        elif "Filter" in step:
            params["filter"] = self.filter_edit.currentData() if hasattr(self, "filter_edit") and self.filter_edit.currentData() is not None else 1
        elif "Focus" in step:
            params["step"] = self.step_edit.value()
        self.params = params
        self.accept()