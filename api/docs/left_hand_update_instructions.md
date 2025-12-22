# Left Hand Hardware Update - ELMiRA Integration Instructions

**Date:** December 16, 2024  
**Status:** Hardware tested and configuration updated

---

## Summary

The malfunctioning left arm has been replaced with a new SEED Robotics hand. The new left hand is now fully operational and the JSON configuration has been updated. ELMiRA needs to be modified to use **both hands** for manipulation tasks.

---

## Hardware Changes

### New Left Hand Motor Mapping

The new left hand uses **XL-320/SEED Robotics protocol** (different from Protocol 1.0 used by arm motors).

| Motor ID | Joint Name | Description | Angle Limits |
|----------|------------|-------------|--------------|
| **31** | `l_wrist_z` | Wrist Roll (L/R rotation) | [-90°, 90°] |
| **33** | `l_wrist_x` | Wrist Pitch (Up/Down) | [-45°, 45°] |
| **34** | `l_thumb_z` | Thumb Roll (L/R) - **NEW!** | [-150°, 150°] |
| **35** | `l_thumb_x` | Thumb Pitch (Grabbing) | [-150°, 150°] |
| **36** | `l_indexfingers_x` | Index Finger | [-150°, 150°] |
| **37** | `l_middlefingers_x` | Middle Finger | [-150°, 150°] |

### Key Differences from Right Hand

1. **2-DOF Thumb**: The new left hand has a thumb with both Roll (ID 34) AND Pitch (ID 35), unlike the old hand
2. **Different Protocol**: Uses XL-320/SEED protocol (requires `Dxl320IO` instead of `DxlIO`)
3. **No Virtual Hand Motor**: The new hand has separate index and middle finger motors instead of a coupled "virtual hand"

### Configuration File Updated

**File:** `json/nico_humanoid_upper_fixed.json`

The `l_hand` motor group is now populated with the new motor definitions.

---

## Required ELMiRA Changes

### 1. Enable Left Arm for Manipulation

**File:** `api/src/ELMiRA/scripts/states/action_planner.py`

Currently, the arm selection logic may be biased toward the right arm or skip the left arm entirely. Update the `ActionTrajectory` class to:

- Use left arm (`l_arm`) when target object is on the robot's left side (`real_y > 0`)
- Use right arm (`r_arm`) when target object is on the right side (`real_y < 0`)

✅ **IMPLEMENTED** - Arm selection in `ActionTrajectory` (action_planner.py line 127):
```python
is_right = userdata.target_y < 0  # Right arm if Y is negative
userdata.planning_group = "r_arm" if is_right else "l_arm"
```

### 2. Add Left Arm IK Support

**File:** `api/src/ELMiRA/scripts/ik_solver.py`

✅ **VERIFIED** - IK solver already supports both arms:
- `urdf/nico_left_arm.urdf` is properly configured
- Joint names match the configuration

### 3. Update Motion Execution for Left Arm

**File:** `api/src/ELMiRA/scripts/states/move_robot.py`

✅ **VERIFIED** - `MoveRobotPart` correctly handles left arm movements:
- Left arm service: `/left/open_manipulator_p/goal_joint_space_path`
- Left arm state feedback: `/left/open_manipulator_p/joint_states`

### 4. Handle Protocol Difference (Important!)

The new left hand motors use **XL-320 protocol** while the arm motors use Protocol 1.0. If position reading is needed for the left hand specifically, use `Dxl320IO` instead of `DxlIO`:

```python
from pypot.dynamixel.io.io_320 import Dxl320IO  # For left hand
from pypot.dynamixel.io import DxlIO  # For arm motors
```

✅ **IMPLEMENTED** - `hand_control.py` handles protocol differences automatically:
- Left hand uses `Dxl320IO` for XL-320 motors
- Right hand uses `DxlIO` for Protocol 1.0 motors
- Timeout-based completion (no position feedback) for SEED servos

**Note:** Position reading from SEED servos returns incorrect values due to register mapping differences. Commands ARE sent correctly - only position feedback is unreliable.

---

## Testing Recommendations

1. **Test left arm reach**: Verify IK solutions for objects on the left side of the workspace
2. **Test arm selection**: Place objects on both sides and verify correct arm is chosen
3. **Test left hand grasping**: Verify finger motors respond to grasp commands
4. **Test bimanual tasks**: If implemented, test coordinated two-arm movements

---

## File References

- **Config:** `json/nico_humanoid_upper_fixed.json` - Updated with left hand motors
- **Left arm URDF:** `api/src/ELMiRA/urdf/nico_left_arm.urdf`
- **IK Solver:** `api/src/ELMiRA/scripts/ik_solver.py`
- **Action Planner:** `api/src/ELMiRA/scripts/states/action_planner.py`
- **Motion Executor:** `api/src/ELMiRA/scripts/states/move_robot.py`
- **Data flow doc:** `api/docs/ELMiRA_data_flow.md`

---

## Quick Reference: Motor ID Summary

### Left Side (New Hand)
- Arm: 2, 4, 6, 22 (Protocol 1.0)
- Hand: 31, 33, 34, 35, 36, 37 (XL-320 protocol)

### Right Side (Existing)
- Arm: 1, 3, 5, 21 (Protocol 1.0)
- Hand: 23, 25, 27, 29, 32 (Protocol 1.0)

### Head
- 19, 20 (Protocol 1.0)
