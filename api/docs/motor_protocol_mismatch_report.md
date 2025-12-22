# NICO Robot Motor Protocol Mismatch Report

**Date:** December 16, 2024  
**Author:** Hardware Diagnostics Analysis  
**Status:** ✅ RESOLVED (December 17, 2024)

---

## Executive Summary

The NICO robot's new left hand uses **SEED Robotics servos with XL-320 protocol**, while the rest of the robot uses **Dynamixel Protocol 1.0**. This creates a protocol mismatch that prevents the standard motion controller from communicating with both systems simultaneously.

**Resolution:** Left hand motors have been completely removed from the main motor config (`nico_humanoid_upper_fixed.json`). The Motion node now only initializes Protocol 1.0 motors, avoiding any protocol conflicts.

---

## Current Configuration

### Motors in Main Config (Protocol 1.0)
- Head: IDs 19, 20
- Right arm: IDs 1, 3, 5, 21
- Left arm: IDs 2, 4, 6, 22
- Right hand: IDs 23, 25, 29, 32

### Motors NOT in Main Config (XL-320 - Excluded)
- Left hand: IDs 31, 33, 34, 35, 36, 37

---

## Hardware Scan Results

### Clean Scan ✅

All motors are physically connected and responding. No missing hardware.

### Protocol 1.0 Motors (18 detected)

| ID | Component | Status |
|----|-----------|--------|
| 1, 2 | Shoulder Pitch (L/R) | ✅ |
| 3, 4 | Arm X (L/R) | ✅ |
| 5, 6 | Elbow (L/R) | ✅ |
| 19, 20 | Head Z/Y | ✅ |
| 21, 22 | Shoulder Z (L/R) | ✅ |
| 23, 25 | Right Wrist Z/X | ✅ |
| 27, 29 | Right Index/Thumb | ✅ |
| 30 | Unknown (dual-protocol) | ⚠️ |

### XL-320 Protocol Motors (7 detected)

| ID | Component | Note |
|----|-----------|------|
| 30 | Unknown | Also responds to P1.0 |
| 31 | Left Wrist Roll | Also responds to P1.0 |
| 33 | Left Wrist Pitch | XL-320 only |
| 34 | Left Thumb Roll | XL-320 only |
| 35 | Left Thumb Pitch | Also responds to P1.0 |
| 36 | Left Index Finger | Also responds to P1.0 |
| 37 | Left Middle Finger | Also responds to P1.0 |

### Key Finding: Dual-Protocol Responses

Motors **30, 31, 35, 36, 37** respond to BOTH protocols. This is abnormal behavior indicating:
- SEED servos have some Protocol 1.0 compatibility layer
- Response parsing differs between protocols
- Position/command registers are NOT compatible

---

## Problem Manifestation

### Symptom
```
OSError: No valid port found
could not parse received data bytearray(b'Unkn')
```

### Cause Chain
```
Motion.py initializes
    → Loads nico_humanoid_upper_fixed.json
    → Scans ALL motor IDs with Protocol 1.0
    → Left hand motors (XL-320) respond with incompatible packet format
    → Parser fails on malformed response
    → Port marked as invalid
    → No ports remaining → OSError
```

---

## Solutions Analysis

### Solution 1: Disable Left Hand in Motion.py ⭐ RECOMMENDED

**Complexity:** Low  
**Risk:** Low  
**Implementation Time:** 5 minutes

Add left hand motor IDs to `disabledMotorIds` in JSON config:
```json
"disabledMotorIds": [31, 33, 34, 35, 36, 37]
```

| Pros | Cons |
|------|------|
| Minimal code changes | Left hand not in Motion.py joint states |
| Uses existing mechanism | Requires separate hand controller |
| Already tested pattern | Two control paths for hands |

**Status:** `hand_control.py` already handles left hand with correct protocol.

---

### Solution 2: Dual-Protocol Motion Controller

**Complexity:** High  
**Risk:** Medium  
**Implementation Time:** 2-3 days

Modify `nicomotion.Motion` to:
1. Detect motor protocol during scan
2. Maintain separate IO handlers for each protocol
3. Route commands based on motor-to-protocol mapping

| Pros | Cons |
|------|------|
| Unified control interface | Major code refactor |
| Full position feedback | Testing complexity |
| Cleaner architecture | May break existing code |

---

### Solution 3: Bridge Protocol Translator

**Complexity:** Very High  
**Risk:** High  
**Implementation Time:** 1-2 weeks

Create hardware/software bridge that:
1. Intercepts Protocol 1.0 commands for left hand
2. Translates to XL-320 protocol
3. Translates responses back

| Pros | Cons |
|------|------|
| Transparent to existing code | Significant development |
| No software changes needed | Potential latency issues |
| Reusable for other robots | Complex debugging |

---

### Solution 4: Reprogram Motor Protocols

**Complexity:** Medium  
**Risk:** Very High  
**Implementation Time:** N/A (usually impossible)

Flash SEED servos with Protocol 1.0 firmware.

| Pros | Cons |
|------|------|
| Simplest long-term solution | May not be possible |
| Unified protocol | Could brick motors |
| No software changes | Warranty void |

**Status:** NOT recommended - SEED servos likely don't support this.

---

## Recommendation

**Implement Solution 1** (disabledMotorIds) for immediate resolution:

1. Already have `hand_control.py` handling left hand correctly
2. Minimal risk to existing functionality  
3. Can migrate to Solution 2 later if needed

### Immediate Action
Add to `nico_humanoid_upper_fixed.json`:
```json
{
  "controllers": {
    "all_controller": {
      "disabledMotorIds": [31, 33, 34, 35, 36, 37],
      ...
    }
  }
}
```

---

## Appendix: Raw Scan Data Interpretation

The garbled responses like `ffff1f0200deffff1f02409e...` show:
- `ffff` = Standard Dynamixel header
- `1f` = ID 31 response embedded
- `02409e` = XL-320 status packet format

This confirms the motors ARE responding but with XL-320 packet structure that Protocol 1.0 parser cannot decode.
