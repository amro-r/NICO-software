# Agents Catalogue

## OptoForce Multi-Finger Interface — `scripts/nicotouch/OptoforceMultichannel.py`
- **Role**: Connects to multi-channel OptoForce controllers to read fingertip force vectors.
- **Capabilities**: Auto-detects sensors by serial number, applies per-finger calibration scales, supports cached polling threads, and exposes force readings keyed by finger labels.

## Single-Sensor Driver — `scripts/nicotouch/optoforcesensors.py`
- **Role**: Accesses single OptoForce probes, converting raw hex packets to signed Newton readings.
- **Key Behaviours**: Scans serial ports, handles byte decoding, caches latest readings, provides helper methods for string/tuple outputs.

## Internal Driver Bindings (`_nicotouch_internal/optoforce.py`)
- Wraps the low-level communication protocol used by both agents above, including packet parsing and checksum management.

These agents underpin tactile perception for the NICO hands and arms and can be surfaced through ROS via `nicoros` bridge nodes.
