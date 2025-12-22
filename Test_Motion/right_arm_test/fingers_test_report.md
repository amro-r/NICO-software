# Right Hand Fingers Range Test Report

**Run command:** `python3 Test_Motion/right_arm_test/r_fingers_range_test.py`  
**Port/Baud:** `/dev/ttyUSB0` @ 1,000,000 baud  
**Config referenced:** `json/nico_humanoid_upper_body_control_general.json` (hardware angle limits read from each detected motor)

## Test Method
- Scan only the right-hand finger IDs defined in the config (27 index, 29 thumb, 32 virtual hand).
- For each detected motor:
  - Read hardware angle limits.
  - Center to 0°, then sweep in 12° steps to both limits with 0.9 s settle time.
  - Record achieved positions, span, and errors.
- Report achieved min/max, coverage vs expected span, and any stall/large-error notes.

## Results
- **ID 27 – Right Index Finger (r_indexfingers_x)**
  - Achieved range: **-180.0° → 167.1°**
  - Span / Expected: **347.1° / 320.0° (96%)**
  - Note: Larger error near +167°; otherwise tracks targets closely.
  - Status: **FULL**

- **ID 29 – Right Thumb (r_thumb_x)**
  - Achieved range: **-180.0° → 53.0°**
  - Span / Expected: **233.0° / 320.0° (65%)**
  - Note: Positive side stops near +53° with rising error; negative side fully reachable.
  - Status: **PARTIAL**

- **ID 32 – Right Virtual Hand / Coupled Fingers (r_virtualhand_x)**
  - Not detected on bus; no motion tested.
  - Status: **NOT REACHABLE**

## Recommendation
- Remove the virtual hand motor (ID 32) from the right-hand configuration and test targets, as it is not present on the bus. Continue range testing only IDs **27** (index) and **29** (thumb).
