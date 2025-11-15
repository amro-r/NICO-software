# Agents Catalogue

## Facial Display Controller — `scripts/nicoface/FaceExpression.py`
- **Role**: Generates and transmits facial expressions to the NICO head or a simulated image output.
- **Capabilities**:
  - Preset expressions (anger, happiness, neutral, etc.) with trained servo parameters.
  - Polynomial-based morph targets for brows and mouth allowing smooth interpolation.
  - Serial auto-discovery of Arduino-based face controller; simulation mode renders via PIL/OpenCV.
- **Key Behaviours**: Manages expression blending, polynomial generation, and command retries with error handling.

## Serial Connectivity — `scripts/nicoface/SerialConnectionManager.py`
- **Role**: Discovers and maintains serial links to subordinate microcontrollers.
- **Key Behaviours**: Provides `SerialDevice` abstraction with send/retry logic, device filtering by manufacturer for auto-detection.
- **Used By**: `FaceExpression`, `CapacitiveSensors`.

## Capacitive Sensing — `scripts/nicoface/CapacitiveSensors.py`
- **Role**: Interfaces with head-mounted capacitive touch sensors over serial.
- **Capabilities**: Scans ports for supported boards, reports touch states, debounces inputs, and supports calibration routines.

These agents coordinate to supply expressive facial output and touch feedback for NICO’s head, exposing higher-level APIs to ROS packages such as `nicoros`.
