# Agents Catalogue

## Device Abstractions
- **`VideoDevice.py`**: Low-level V4L2 camera wrapper that discovers NICO eye cameras, manages zoom/pan/tilt, loads camera setting presets, and spawns capture threads delivering frames via callbacks.
- **`PyrepDevice.py`**: Virtual camera device sourcing frames from PyRep simulations.

## Recording & Streaming
- **`MultiCamRecorder.py`**: Coordinates synchronous acquisition from multiple `VideoDevice` instances, delivering RGB frames to registered callbacks (used by `nicoros/Vision.py`).
- **`VideoRecorder.py` / `ImageRecorder.py` / `MultiCamRecorder`**: Utilities for saving continuous video or image sequences with timestamping.
- **`Display.py`**: Preview window helper with optional keyboard interaction.

## Processing Utilities
- **`Colorspace.py`**: Conversion helpers between OpenCV colour spaces.
- **`Barrier.py`**: Threading primitive to coordinate frame consumers.
- **`NumpyEncoder.py`**: JSON encoder for numpy datatypes (used by calibration/output storage).

Collectively, these agents provide flexible camera handling that underpins ROS streaming (`nicoros/Vision.py`) and higher-level perception modules such as ELMiRA’s object localisation.
