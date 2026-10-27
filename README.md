# AstroControl — Cross-Platform Astrophotography Control

A minimal, clean, fully functional Python application for controlling ASCOM/INDI/Alpaca astronomy equipment. Built with PySide6, the app provides a graphical interface to connect and control cameras, guide cameras, mounts, focusers, filter wheels, and autoguiding with live error graphs.

---

## Features

### Device Control (Alpaca-based)
- **Camera Control**: Connect, set exposure time, gain, capture images, read ImageArray
- **Guide Camera**: Same Alpaca interface for autoguiding
- **Mount Control**: GOTO coordinates, slew, track, set park position
- **Focuser**: Move in/out, set position, read current position
- **Filter Wheel**: Select filters, change filter positions
- **Alpaca Discovery**: Auto-discovery of Alpaca devices on the local network via UDP broadcast (port 11160)
- **Cross-Platform**: Works with INDI servers (Linux/macOS) and ASCOM Alpaca servers (Windows)

### Planetarium View
- Displays current mount position in alt/az coordinates
- Shows selected Messier objects (M1, M31, M42, M57, M81, M82, M13, M27, M33, M104)
- Interactive coordinate display
- Updates periodically to reflect mount movement

### Sequencer
- Queue-based operation executor
- Supported step types: `goto`, `platesolve`, `focus`, `capture`, `set_exposure`, `set_gain`
- Move steps up/down in the queue
- Progress bar during execution
- Stop execution at any time

### Focus Tab (New)
- **Connection**: Connect focuser device
- **Manual controls**: Move In / Out with configurable step size
- **Routine settings**: Inhale/Exhale, Single Direction, Bahtinov types
- **Routine parameters**: Iterations, step delay, step size, speed
- **Live position display**: Real-time focuser position
- **Progress bar**: Shows routine progress

### Guiding Tab (New)
- **Guide Camera Connection**: Connect second camera or use primary camera
- **Calibration**: Calibrate tracking with configurable steps and iterations
- **Guide Settings**: Aggressiveness (0.1–3.0), Min/Max move limits, Guide mode (Both/RA/Dec)
- **Guide Exposure**: Configurable exposure and gain
- **Live Error Graph**: Real-time RA/Dec error plot (red for RA, cyan for Dec), scales automatically, shows 200-point history
- **Start/Stop**: Begin/stop autoguiding loop with simulated corrections

### Image Viewer
- Real-time display of camera images
- Exposure time control via slider
- Save images as PNG, TIFF, or FITS
- **Live-stack mode**: Accumulate frames and display mean or median stack
- Adjustable stack size (2–500 frames)
- Stack mode toggle (Mean vs Median)

---

## Installation

```bash
pip install -r requirements.txt
python main.py
```

---

## Usage — Focus
1. Go to **Focus** tab
2. Click **Connect Focuser**
3. Adjust **Step size** and click **Move In / Out**
4. For routine: select type, set iterations/delay, click **Start Routine**
5. Monitor progress bar and current position

## Usage — Guiding
1. Go to **Guiding** tab
2. Click **Connect Guide Camera**
3. Set exposure/gain for guide camera
4. Click **Calibrate** (wait for completion)
5. Configure **Aggressiveness**, **Min/Max move**, and **Guide mode**
6. Click **Start Guiding** — live error graph updates in real time
7. Click **Stop Guiding** to halt

---

## Architecture

| Module | Description |
|--------|-------------|
| `main.py` | Entry point |
| `astro_control/app.py` | Main window: device tree + 6 tabs |
| `astro_control/devices.py` | Alpaca discovery / connection |
| `astro_control/planetarium.py` | Sky map |
| `astro_control/sequencer.py` | Queue execution |
| `astro_control/focus_widget.py` | Focus tab |
| `astro_control/guiding_widget.py` | Guiding tab + error graph |
| `astro_control/imageviewer.py` | Image viewer + livestack |

---

## Cross-Platform
- Linux: INDI + Alpaca server
- macOS: INDI Nightly / `indiserver`
- Windows: ASCOM + Alpaca bridge
