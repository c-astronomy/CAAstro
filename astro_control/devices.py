"""Alpaca device management layer.

Wraps ``alpaca`` for ASCOM/INDI/Alpaca device discovery and connection
(Camera, Guide Camera, Mount, Focuser, Filter Wheel, Rotator, Dome).

Alpaca is a REST-style protocol that lets a Python host control
ASCOM/INDI drivers running on a server. The server can be
- ASCOM Alpaca server (Windows)
- INDIGO Alpaca server (Linux/macOS/Windows)
- Any Alpaca-compatible server implementation.
"""

import threading
import time
import ipaddress
import socket
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from PySide6.QtCore import QObject, Signal

try:
    from alpaca.camera import Camera
    from alpaca.telescope import Telescope as Mount  # alpaca uses 'telescope' for mounts
    from alpaca.focuser import Focuser
    from alpaca.filterwheel import FilterWheel
except Exception as exc:
    print(f"[Import Warning] Failed to load alpaca classes: {exc}")
    Camera = None
    Mount = None
    Focuser = None
    FilterWheel = None


@dataclass
class AlpacaDevice:
    """Wrapper around an Alpaca device handle."""

    address: str
    port: int
    name: str
    device_type: str
    device_number: int = 0
    client_id: int = 0
    client_tx_id: int = 0
    _handle: Any = None

    def connect(self) -> bool:
        """Connect the device. Returns success."""
        try:
            handle = self._get_handle()
            handle.Connected = True
            self._handle = handle
            return True
        except Exception as exc:
            print(f"[Device] connect error for {self.name} (type={self.device_type}, index={self.device_number}): {exc}")
            return False

    def _get_handle(self):
        if self._handle:
            return self._handle
            
        endpoint = f"{self.address}:{self.port}"
        
        # Correct alpyca signature: Device(endpoint, device_number)
        if self.device_type == "camera":
            if Camera is None:
                raise ImportError("alpaca.camera failed to load.")
            dev = Camera(endpoint, self.device_number)
        elif self.device_type in ("mount", "telescope"):
            if Mount is None:
                raise ImportError("alpaca.telescope failed to load.")
            dev = Mount(endpoint, self.device_number)
        elif self.device_type == "focuser":
            if Focuser is None:
                raise ImportError("alpaca.focuser failed to load.")
            dev = Focuser(endpoint, self.device_number)
        elif self.device_type == "filterwheel":
            if FilterWheel is None:
                raise ImportError("alpaca.filterwheel failed to load.")
            dev = FilterWheel(endpoint, self.device_number)
        else:
            raise ValueError(f"Unknown device type: {self.device_type}")
            
        if self.name:
            dev.device_name = self.name
        return dev

    def is_connected(self) -> bool:
        try:
            return bool(self._get_handle().Connected)
        except Exception:
            return False

    def disconnect(self):
        try:
            self._get_handle().Connected = False
        except Exception as exc:
            print(f"[Device] disconnect error: {exc}")

    def command_string(self, command: str) -> str:
        """Send a raw command string to the device."""
        try:
            return self._get_handle().CommandString(command)
        except Exception as exc:
            print(f"[Device] command error: {exc}")
            return ""

    def get_property(self, prop: str, default=None):
        try:
            return getattr(self._get_handle(), prop)
        except Exception as exc:
            # Suppress noisy logs for idle ImageArray polls or unimplemented features (0x400)
            if prop != "ImageArray" and "0x400" not in str(exc):
                print(f"[Device] get {prop} error: {exc}")
            return default

    def set_property(self, prop: str, value) -> bool:
        try:
            setattr(self._get_handle(), prop, value)
            return True
        except Exception as exc:
            if "0x400" in str(exc) or "not implemented" in str(exc).lower():
                print(f"[Device] Note: Property '{prop}' not supported by {self.name}")
            else:
                print(f"[Device] set {prop} error: {exc}")
            return False

    def show_connection_dialog(self):
        """Placeholder for a connection configuration dialog."""
        print(f"Connect device: {self.name} ({self.device_type})")
        self.connect()

    @property
    def ClientNumber(self) -> int:
        try:
            return self._get_handle().ClientNumber
        except Exception:
            return 0


class DeviceManager(QObject):
    """Discovers and manages Alpaca ASCOM/INDI devices."""

    connection_status_changed = Signal(str, bool)

    DEVICE_TYPES = {
        "camera", "guidecamera", "mount", "telescope",
        "focuser", "filterwheel", "rotator", "dome",
        "switch", "sensor", "video",
    }

    def __init__(self):
        super().__init__()
        self.devices_by_type: Dict[str, List[AlpacaDevice]] = {
            t: [] for t in self.DEVICE_TYPES
        }
        self.all_devices: List[AlpacaDevice] = []
        self._by_name: Dict[str, AlpacaDevice] = {}

    @property
    def cameras(self) -> List[AlpacaDevice]:
        return self.devices_by_type["camera"] + self.devices_by_type["guidecamera"]

    @property
    def mounts(self) -> List[AlpacaDevice]:
        return self.devices_by_type["mount"] + self.devices_by_type["telescope"]

    @property
    def focusers(self) -> List[AlpacaDevice]:
        return self.devices_by_type["focuser"]

    @property
    def filter_wheels(self) -> List[AlpacaDevice]:
        return self.devices_by_type["filterwheel"]

    def clear(self):
        """Clear all registered devices to prevent duplicates on refresh."""
        self.all_devices.clear()
        for t in self.DEVICE_TYPES:
            self.devices_by_type[t].clear()
        self._by_name.clear()

    def discover_devices(self, timeout: float = 2.0):
        """Use Alpaca discovery protocol and query management API on LAN."""
        self.clear()
        self._udp_discover(timeout)

    def _register_device(self, addr, port, device_type, device_name, device_number=0):
        raw_type = device_type.lower() if device_type else "unknown"
        
        if raw_type in ("telescope", "mount"):
            norm_type = "mount"
        elif raw_type in ("camera", "guidecamera", "dslr"):
            norm_type = "camera"
        elif raw_type == "focuser":
            norm_type = "focuser"
        elif raw_type == "filterwheel":
            norm_type = "filterwheel"
        else:
            norm_type = raw_type

        if norm_type not in self.devices_by_type:
            print(f"[Discovery Warning] Unrecognized device type '{raw_type}', defaulting to camera")
            norm_type = "camera"

        dev = AlpacaDevice(
            address=addr,
            port=port,
            name=device_name or f"{norm_type}@{addr}:{port}",
            device_type=norm_type,
            device_number=device_number,
        )
        self.all_devices.append(dev)
        self.devices_by_type[norm_type].append(dev)
        self._by_name[dev.name] = dev

    def _udp_discover(self, timeout: float = 2.0):
        try:
            import urllib.request
        except ImportError:
            urllib.request = None

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        
        probe = b"alpacadiscovery1"
        discovered_servers = set()

        try:
            sock.sendto(probe, ("<broadcast>", 32227))
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, (addr, _) = sock.recvfrom(1024)
                    if data:
                        try:
                            response_json = json.loads(data.decode('utf-8', errors='ignore'))
                            alpaca_port = response_json.get("AlpacaPort")
                            if alpaca_port:
                                discovered_servers.add((addr, alpaca_port))
                        except Exception:
                            discovered_servers.add((addr, 10000))
                except socket.timeout:
                    break
        except Exception as exc:
            print(f"[Discovery] UDP broadcast error: {exc}")
        finally:
            sock.close()

        if urllib.request:
            for addr, port in discovered_servers:
                try:
                    url = f"http://{addr}:{port}/management/v1/configureddevices"
                    req = urllib.request.Request(url, headers={'User-Agent': 'CustomAstronomyClient'})
                    with urllib.request.urlopen(req, timeout=1.0) as response:
                        body = json.loads(response.read().decode('utf-8'))
                        devices = body.get("Value", [])
                        for dev_info in devices:
                            dev_type = dev_info.get("DeviceType", "").lower()
                            dev_name = dev_info.get("DeviceName", f"{dev_type}@{addr}")
                            dev_number = dev_info.get("DeviceNumber", 0)
                            self._register_device(addr, port, dev_type, dev_name, dev_number)
                except Exception as exc:
                    print(f"[Discovery] Failed to query management API for {addr}:{port} -> {exc}")

    def connect_device(self, device_type: str, name: Optional[str] = None) -> bool:
        devices = self.devices_by_type.get(device_type, [])
        if name:
            dev = self._by_name.get(name)
            if dev and dev.connect():
                self._notify_status(dev.device_type, True)
                return True
            return False
        if devices:
            dev = devices[0]
            ok = dev.connect()
            if ok and self.connection_status_changed:
                self.connection_status_changed.emit(dev.device_type, True)
            return ok
        return False

    def connect_all(self):
        for dev in self.all_devices:
            if not dev.is_connected():
                dev.connect()
                if self.connection_status_changed:
                    self.connection_status_changed.emit(dev.device_type, True)

    def disconnect_all(self):
        for dev in self.all_devices:
            dev.disconnect()
            if self.connection_status_changed:
                self.connection_status_changed.emit(dev.device_type, False)

    def _notify_status(self, device_type, connected):
        if self.connection_status_changed:
            self.connection_status_changed.emit(device_type, connected)

    def is_connected(self, device_type: str) -> bool:
        return any(d.is_connected() for d in self.devices_by_type.get(device_type, []))

    def find_first(self, device_type: str) -> Optional[AlpacaDevice]:
        for d in self.devices_by_type.get(device_type, []):
            if d.is_connected():
                return d
        devices = self.devices_by_type.get(device_type, [])
        return devices[0] if devices else None


def emit_status(manager: DeviceManager, device_type: str, connected: bool):
    """Helper to emit via a real Signal from outside Qt."""
    if manager.connection_status_changed:
        manager.connection_status_changed.emit(device_type, connected)
