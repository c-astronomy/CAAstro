"""Planetarium widget showing mount location and sky objects.

Uses ``ephem`` for coordinate calculations. Displays the mount position
(azimuth/altitude) on a proper sky map, plus constellations, Messier,
and NGC deep-sky objects.
"""

import math
from typing import List, Tuple

import ephem

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsLineItem, QWidget, QVBoxLayout, QLabel, QGroupBox,
    QDoubleSpinBox, QPushButton, QGraphicsTextItem, QHBoxLayout,
)
from PySide6.QtGui import QColor, QPen, QBrush

from astro_control.devices import DeviceManager
from astro_control.config import load_site as _load_site, save_site as _save_site


class PlanetariumWidget(QWidget):
    """Graphics view showing a proper azimuth/altitude sky map.

    The circular projection puts North at top, azimuth increasing clockwise,
    altitude 0 at the horizon (circle edge) and 90 at zenith (center).
    """

    # Messier objects: name, RA hours, Dec degrees (J2000 approximate)
    _MESSIER: List[Tuple[str, float, float]] = [
        ("M1",  5.58, 22.0),   ("M2", 21.31, -9.1),   ("M3", 13.61, 28.5),
        ("M4", 16.25, -26.3),  ("M5", 15.18, 2.0),    ("M6", 17.45, -32.2),
        ("M7", 17.52, -34.8),  ("M8", 18.03, -24.3),  ("M9", 17.15, -18.2),
        ("M10",16.95, -4.1),   ("M11",18.50, -6.2),   ("M12",16.45, -1.8),
        ("M13",16.69, 36.4),   ("M14",17.38, -3.3),   ("M15",21.30, 12.2),
        ("M16",18.17, -13.8),  ("M17",18.19, -16.1),  ("M18",18.10, -17.1),
        ("M19",16.32, -26.2),  ("M20",18.00, -23.0),  ("M21",18.05, -22.3),
        ("M22",18.36, -23.9),  ("M23",17.98, -19.0),  ("M24",18.15, -18.5),
        ("M25",18.30, -19.2),  ("M26",18.45, -9.2),   ("M27",19.95, 22.7),
        ("M28",18.24, -24.9),  ("M29",20.22, 38.3),   ("M30",21.40, -23.1),
        ("M31",0.68, 41.3),    ("M32",0.68, 40.8),    ("M33",1.46, 30.8),
        ("M34",2.11, 42.8),    ("M35",6.06, 24.3),    ("M36",5.58, 34.1),
        ("M37",5.59, 32.6),    ("M38",5.64, 35.9),    ("M39",21.32, 48.4),
        ("M40",12.40, 63.1),   ("M41",6.47, -20.8),   ("M42",5.58, -5.2),
        ("M43",5.58, -5.2),    ("M44",8.62, 19.7),    ("M45",5.67, 24.1),
        ("M46",7.65, -14.8),   ("M47",7.28, -11.5),   ("M48",8.16, -5.8),
        ("M49",12.30, 8.0),    ("M50",7.03, -8.2),    ("M51",13.30, 47.2),
        ("M52",23.22, 61.7),   ("M53",13.12, 18.3),   ("M54",18.54, -30.4),
        ("M55",19.39, -30.9),  ("M56",19.17, 30.1),   ("M57",18.85, 33.0),
        ("M58",12.44, 11.6),   ("M59",12.42, 11.6),   ("M60",12.42, 11.6),
        ("M61",12.48, 4.2),    ("M62",16.91, -30.1),  ("M63",13.12, 42.2),
        ("M64",12.52, 21.8),   ("M65",11.17, 13.2),   ("M66",11.19, 13.1),
        ("M67",8.51, 11.9),    ("M68",12.34, -26.8),  ("M69",18.31, -32.3),
        ("M70",18.42, -32.2),  ("M71",19.50, 18.8),   ("M72",20.55, -12.4),
        ("M73",20.45, -12.7),  ("M74",1.58, 15.8),    ("M75",20.04, -21.7),
        ("M76",1.55, 51.9),    ("M77",2.82, -0.2),    ("M78",5.44, 0.0),
        ("M79",5.22, -24.5),   ("M80",16.13, -22.7),  ("M81",9.92, 69.1),
        ("M82",9.94, 69.7),    ("M83",13.37, -29.9),  ("M84",12.22, 13.0),
        ("M85",12.34, 18.3),   ("M86",12.46, 13.1),   ("M87",12.50, 12.4),
        ("M88",12.40, 14.3),   ("M89",12.36, 12.9),   ("M90",12.36, 13.2),
        ("M91",12.34, 14.4),   ("M92",17.20, 43.2),   ("M93",7.45, -23.7),
        ("M94",12.52, 41.2),   ("M95",10.77, 11.7),   ("M96",10.76, 11.7),
        ("M97",11.15, 55.2),   ("M98",12.15, 14.8),   ("M99",12.27, 14.4),
        ("M100",12.29, 15.9),  ("M101",14.09, 54.6),  ("M102",15.10, 55.8),
        ("M103",1.48, 60.7),   ("M104",12.66, -11.7), ("M105",10.74, 12.6),
        ("M106",12.19, 47.4),  ("M107",16.31, -13.2), ("M108",11.20, 55.9),
        ("M109",11.17, 53.5),  ("M110",0.67, 41.7),
    ]

    # Common NGC objects
    _NGC: List[Tuple[str, float, float]] = [
        ("NGC 7000", 21.07, 44.2),   ("NGC 2237", 6.24, 4.9),   ("NGC 2244", 6.26, 4.9),
        ("NGC 2264", 6.39, 9.6),     ("NGC 2359", 6.60, -7.0),  ("NGC 2362", 6.76, -25.2),
        ("NGC 2467", 7.75, -26.2),   ("NGC 253", 0.73, -25.2),  ("NGC 457", 1.33, 58.2),
        ("NGC 650", 5.58, 22.0),     ("NGC 6514", 18.03, -23.0),("NGC 6523", 18.03, -24.2),
        ("NGC 6720", 18.85, 33.0),   ("NGC 7023", 21.03, 68.1), ("NGC 7293", 22.15, -20.9),
        ("NGC 7635", 23.21, 61.5),   ("NGC 869", 2.23, 57.1),   ("NGC 884", 2.25, 57.1),
        ("NGC 1499", 4.08, 36.4),    ("NGC 1976", 5.58, -5.2),  ("NGC 1982", 5.58, -5.2),
        ("NGC 2024", 5.58, -2.0),    ("NGC 2261", 6.71, 8.7),   ("NGC 3372", 10.70, -59.8),
    ]

    # Constellation lines: name, list of (ra_h, dec_deg) bright star points
    # Using approximate J2000 bright-star coordinates for clean lines
    _CONSTELLATIONS = {
        "Orion": [
            (5.92, 7.4),   # Betelgeuse
            (5.84, -8.2),  # Rigel
            (5.37, -1.9),  # Alnitak (belt)
            (5.60, -1.2),  # Alnilam (belt)
            (5.53, -0.3),  # Mintaka (belt)
            (5.92, 7.4),   # back to Betelgeuse
        ],
        "Ursa Major": [
            (11.07, 61.8),  # Dubhe
            (11.01, 56.4),  # Merak
            (11.88, 53.7),  # Phecda
            (12.25, 57.0),  # Megrez
            (12.90, 55.9),  # Alioth
            (13.40, 54.9),  # Mizar
            (13.80, 49.3),  # Alkaid
        ],
        "Cassiopeia": [
            (0.69, 60.2),   # Schedar
            (1.31, 59.2),   # Caph
            (1.91, 63.3),   # Gamma Cas
            (2.89, 61.8),   # Ruchbah
        ],
        "Scorpius": [
            (16.30, -26.3),  # Antares
            (16.89, -25.4),  # Graffias
            (17.45, -26.4),  # Dschubba
            (17.42, -34.3),  # Shaula
        ],
        "Cygnus": [
            (20.42, 45.2),   # Deneb
            (20.18, 36.6),   # Sadr
            (19.88, 27.8),   # Albireo
        ],
        "Lyra": [
            (18.74, 38.8),   # Vega (bright)
            (18.63, 33.0),   # Sheliak
            (18.91, 32.7),   # Sulafat
        ],
        "Andromeda": [
            (0.68, 41.3),     # Alpheratz
            (1.13, 45.5),     # Mirach
            (1.47, 36.0),     # Almach
        ],
        "Taurus": [
            (4.35, 16.2),     # Aldebaran
            (5.58, 22.0),     # El Nath (near M42)
        ],
        "Leo": [
            (10.74, 12.6),    # Regulus
            (11.17, 13.2),    # Algieba
            (11.49, 24.0),    # Denebola
        ],
        "Virgo": [
            (13.30, -11.0),   # Spica
        ],
        "Sagittarius": [
            (18.50, -28.0),   # Sagittarius star field
        ],
        "Polaris (NCP marker)": [
            (2.53, 89.3),     # Polaris — near North Celestial Pole
        ],
    }

    def __init__(self, device_manager: DeviceManager):
        super().__init__()
        self.device_manager = device_manager

        self.layout = QVBoxLayout(self)

        # Title
        self.layout.addWidget(QLabel("<b>Planetarium</b> — mount position and sky objects"))

        # Mount position controls (manual visual preview only — does not slew mount)
        ctrl = QGroupBox("Mount Position — Visual Preview")
        ctrl_layout = QHBoxLayout()
        ctrl.setLayout(ctrl_layout)

        self.sp_az = QDoubleSpinBox()
        self.sp_az.setRange(0, 359)
        self.sp_az.setDecimals(1)
        self.sp_az.setSuffix("\u00B0 Az")
        ctrl_layout.addWidget(QLabel("Az:"))
        ctrl_layout.addWidget(self.sp_az)

        self.sp_alt = QDoubleSpinBox()
        self.sp_alt.setRange(-90, 90)
        self.sp_alt.setDecimals(1)
        self.sp_alt.setSuffix("\u00B0 Alt")
        ctrl_layout.addWidget(QLabel("Alt:"))
        ctrl_layout.addWidget(self.sp_alt)

        btn_update = QPushButton("Update Mount")
        btn_update.clicked.connect(self._update_from_spinboxes)
        ctrl_layout.addWidget(btn_update)
        ctrl_layout.addStretch()

        self.layout.addWidget(ctrl)

        # Object type toggles
        obj_grp = QGroupBox("Show Objects")
        obj_layout = QHBoxLayout(obj_grp)
        self.chk_const = QCheckBox("Constellations")
        self.chk_const.setChecked(True)
        self.chk_const.stateChanged.connect(lambda _: self._render())
        obj_layout.addWidget(self.chk_const)
        self.chk_messier = QCheckBox("Messier")
        self.chk_messier.setChecked(True)
        self.chk_messier.stateChanged.connect(lambda _: self._render())
        obj_layout.addWidget(self.chk_messier)
        self.chk_ngc = QCheckBox("NGC")
        self.chk_ngc.setChecked(True)
        self.chk_ngc.stateChanged.connect(lambda _: self._render())
        obj_layout.addWidget(self.chk_ngc)
        obj_layout.addStretch()
        self.layout.addWidget(obj_grp)

        # Site / observer settings (affects sky-object projection)
        site_grp = QGroupBox("Observer Site")
        site_layout = QHBoxLayout(site_grp)
        self.sp_lat = QDoubleSpinBox()
        self.sp_lat.setRange(-90, 90)
        self.sp_lat.setDecimals(2)
        self.sp_lat.setSuffix("° Lat")
        self.sp_lat.setValue(0)
        site_layout.addWidget(QLabel("Lat:"))
        site_layout.addWidget(self.sp_lat)
        self.sp_lon = QDoubleSpinBox()
        self.sp_lon.setRange(-180, 180)
        self.sp_lon.setDecimals(2)
        self.sp_lon.setSuffix("° Lon")
        self.sp_lon.setValue(0)
        site_layout.addWidget(QLabel("Lon:"))
        site_layout.addWidget(self.sp_lon)
        btn_site = QPushButton("Apply Site")
        btn_site.clicked.connect(self._apply_site)
        site_layout.addWidget(btn_site)
        site_layout.addStretch()
        self.layout.addWidget(site_grp)

        # Graphics view
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.layout.addWidget(self.view)

        # Load saved site settings into spinboxes
        site = _load_site()
        self.sp_lat.setValue(site.get("lat", 0.0))
        self.sp_lon.setValue(site.get("lon", 0.0))

        # Current mount position (az, alt in degrees)
        self.mount_az = 0.0
        self.mount_alt = 0.0

        # Timer for periodic updates
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)
        self._timer.start(500)  # 2 Hz

        self._render()

    def update_frame(self):
        """Public method called by MainWindow timer to refresh."""
        self._update()

    def _update(self):
        """Recalculate mount position and redraw."""
        mount = self.device_manager.find_first("mount")
        if mount and mount.is_connected():
            try:
                self.mount_az = float(getattr(mount, "Azimuth", 0) or 0)
                self.mount_alt = float(getattr(mount, "Altitude", 0) or 0)
            except Exception:
                pass

        self._render()

    def _update_from_spinboxes(self):
        """Sync mount position from spinboxes."""
        self.mount_az = self.sp_az.value() % 360.0
        self.mount_alt = max(-90.0, min(90.0, self.sp_alt.value()))
        self.sp_az.setValue(self.mount_az)
        self.sp_alt.setValue(self.mount_alt)
        self._render()

    def _render(self):
        """Render the sky view onto the QGraphicsView."""
        self.scene.clear()

        w = self.view.width() or 600
        h = self.view.height() or 500

        # Dark sky background
        self.scene.addRect(0, 0, w, h, QPen(QColor(8, 8, 16)), QBrush(QColor(8, 8, 16)))

        cx = w / 2.0
        cy = h / 2.0
        radius = min(w, h) * 0.42

        # Horizon circle
        horizon_pen = QPen(QColor(60, 60, 90), 1)
        self.scene.addEllipse(cx - radius, cy - radius, 2 * radius, 2 * radius, horizon_pen)

        # Center crosshair (zenith marker)
        cross_pen = QPen(QColor(100, 100, 140), 1)
        self.scene.addLine(cx - radius, cy, cx + radius, cy, cross_pen)
        self.scene.addLine(cx, cy - radius, cx, cy + radius, cross_pen)

        # Cardinal labels
        label_pen = QColor(120, 120, 160)
        self.scene.addText("N").setDefaultTextColor(label_pen)
        n_txt = self.scene.addText("N")
        n_txt.setDefaultTextColor(label_pen)
        n_txt.setPos(cx - 6, cy - radius - 18)
        s_txt = self.scene.addText("S")
        s_txt.setDefaultTextColor(label_pen)
        s_txt.setPos(cx - 6, cy + radius + 4)
        e_txt = self.scene.addText("E")
        e_txt.setDefaultTextColor(label_pen)
        e_txt.setPos(cx + radius + 6, cy - 6)
        w_txt = self.scene.addText("W")
        w_txt.setDefaultTextColor(label_pen)
        w_txt.setPos(cx - radius - 16, cy - 6)

        # Mount position projection
        az = self.mount_az % 360.0
        alt = max(-90.0, min(90.0, self.mount_alt))

        if alt >= 0:
            r = radius * (90.0 - alt) / 90.0
        else:
            # Below horizon: still show but outside circle (clamped)
            r = radius * 1.05

        angle = math.radians(az)
        mx = cx + r * math.sin(angle)
        my = cy - r * math.cos(angle)

        cross = QPen(QColor(255, 60, 60), 3)
        self.scene.addLine(mx - 14, my, mx + 14, my, cross)
        self.scene.addLine(mx, my - 14, mx, my + 14, cross)

        mount_label = QGraphicsTextItem("MOUNT")
        mount_label.setPos(mx - 18, my + 16)
        mount_label.setDefaultTextColor(QColor(255, 80, 80))
        self.scene.addItem(mount_label)

        az_txt = QGraphicsTextItem(f"{az:.1f}\u00B0 Az / {alt:.1f}\u00B0 Alt")
        az_txt.setPos(mx - 30, my + 30)
        az_txt.setDefaultTextColor(QColor(200, 200, 200))
        self.scene.addItem(az_txt)

        # Observer location (from site settings)
        observer = ephem.Observer()
        observer.lat = str(self.sp_lat.value())
        observer.lon = str(self.sp_lon.value())
        observer.date = ephem.now()
        observer.pressure = 0
        observer.temp = 0

        # Draw constellation lines
        if self.chk_const.isChecked():
            for cname, stars in self._CONSTELLATIONS.items():
                points = []
                visible_any = False
                # Draw lines connecting consecutive bright stars
                for i in range(len(stars)):
                    (ra1, dec1) = stars[i]
                    (ra2, dec2) = stars[(i + 1) % len(stars)]
                    alt1, az1 = self._radec_to_altaz(ra1, dec1, observer)
                    alt2, az2 = self._radec_to_altaz(ra2, dec2, observer)
                    if alt1 > 5 and alt2 > 5:
                        visible_any = True
                        r1 = radius * (90.0 - alt1) / 90.0
                        r2 = radius * (90.0 - alt2) / 90.0
                        a1 = math.radians(az1)
                        a2 = math.radians(az2)
                        x1 = cx + r1 * math.sin(a1)
                        y1 = cy - r1 * math.cos(a1)
                        x2 = cx + r2 * math.sin(a2)
                        y2 = cy - r2 * math.cos(a2)
                        points.append((x1, y1, x2, y2))
                if visible_any:
                    line_pen = QPen(QColor(150, 150, 255), 1)
                    for (x1, y1, x2, y2) in points:
                        self.scene.addLine(x1, y1, x2, y2, line_pen)
                    # Label near first star
                    if points:
                        x1, y1, _, _ = points[0]
                        lbl = QGraphicsTextItem(cname)
                        lbl.setPos(x1 + 4, y1 - 4)
                        lbl.setDefaultTextColor(QColor(180, 180, 255))
                        self.scene.addItem(lbl)
                    # Draw bright star markers for constellations
                    star_pen = QPen(QColor(220, 220, 255), 2)
                    star_brush = QBrush(QColor(220, 230, 255, 120))
                    for (ra_s, dec_s) in stars:
                        alt_s, az_s = self._radec_to_altaz(ra_s, dec_s, observer)
                        if alt_s > 5:
                            rs = radius * (90.0 - alt_s) / 90.0
                            as_r = math.radians(az_s)
                            sx = cx + rs * math.sin(as_r)
                            sy = cy - rs * math.cos(as_r)
                            circ = QGraphicsEllipseItem(sx - 4, sy - 4, 8, 8)
                            circ.setPen(star_pen)
                            circ.setBrush(star_brush)
                            self.scene.addItem(circ)

        # Helper to draw a catalog object
        def draw_object(name, ra_h, dec_deg, color):
            try:
                alt_obj, az_obj = self._radec_to_altaz(ra_h, dec_deg, observer)
            except Exception:
                return
            if alt_obj <= 5:
                return
            r_obj = radius * (90.0 - alt_obj) / 90.0
            ang = math.radians(az_obj)
            ox = cx + r_obj * math.sin(ang)
            oy = cy - r_obj * math.cos(ang)

            circ = QGraphicsEllipseItem(ox - 5, oy - 5, 10, 10)
            circ.setPen(QPen(color, 1.5))
            circ.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 40)))
            self.scene.addItem(circ)

            txt = QGraphicsTextItem(name)
            txt.setPos(ox + 7, oy - 8)
            txt.setDefaultTextColor(color)
            self.scene.addItem(txt)

        # Draw Messier objects (green)
        if self.chk_messier.isChecked():
            for name, ra_h, dec_deg in self._MESSIER:
                draw_object(name, ra_h, dec_deg, QColor(80, 255, 80))

        # Draw NGC objects (cyan)
        if self.chk_ngc.isChecked():
            for name, ra_h, dec_deg in self._NGC:
                draw_object(name, ra_h, dec_deg, QColor(80, 200, 255))

    def _radec_to_altaz(self, ra_h: float, dec_deg: float, observer=None) -> Tuple[float, float]:
        """Convert RA/Dec to Altitude/Azimuth using observer location.
        
        If observer is None, creates a default equatorial observer.
        """
        # Create observer if not provided
        if observer is None:
            observer = ephem.Observer()
            observer.lat = "0"
            observer.lon = "0"
            observer.date = ephem.now()
            observer.pressure = 0
            observer.temp = 0

        obj = ephem.FixedBody()
        obj._ra = ephem.hours(ra_h)
        obj._dec = ephem.degrees(dec_deg)
        obj._epoch = ephem.J2000

        try:
            obj.compute(observer)
        except AttributeError:
            # Fallback for older ephem versions
            observer.compute(obj)
        except Exception:
            return 0.0, 0.0

        try:
            alt = math.degrees(obj.alt)
            az = math.degrees(obj.az)
        except (AttributeError, TypeError):
            return 0.0, 0.0

        return alt, az

    def _apply_site(self):
        """Apply observer site settings and persist them."""
        lat = self.sp_lat.value()
        lon = self.sp_lon.value()
        try:
            data = _load_site()
            data["lat"] = lat
            data["lon"] = lon
            _save_site(data)
        except Exception as e:
            print(f"[Planetarium] site save error: {e}")
        self._render()

    def set_mount_position(self, az: float, alt: float):
        """Directly set mount position (az, alt in degrees)."""
        self.mount_az = az % 360.0
        self.mount_alt = max(0.0, min(90.0, alt))
        self.sp_az.setValue(self.mount_az)
        self.sp_alt.setValue(self.mount_alt)
        self._render()
