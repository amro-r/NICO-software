#!/usr/bin/env python3
"""
Right arm range test (shoulder, elbow, wrist; fingers excluded)

- Verifies shoulder pitch/roll, elbow flex, and wrist roll/pitch against their configured limits.
- Reads IDs/limits from available upper-body/hand configs under ../json.
- Excludes finger motors; finger range is covered by r_fingers_range_test.py.
"""

import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')

try:
    from pypot.dynamixel.io import DxlIO
    print("✓ DxlIO imported")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Candidate configs ordered by likelihood for this robot
DEFAULT_CONFIGS = [
    "json/nico_humanoid_upper_body_control_general.json",
    "json/nico_humanoid_upper_with_hands.json",
    "json/nico_humanoid_upper_fixed.json",
    "json/rh7d_hands.json",  # wrist variants
    "json/rh5d_hands.json",
]

JOINT_SPECS = {
    "r_shoulder_y": {"description": "Shoulder Pitch", "desired_span": (-120, 120)},
    "r_shoulder_z": {"description": "Shoulder Roll", "desired_span": (-90, 90)},
    "r_arm_x":      {"description": "Upper Arm Twist", "desired_span": (-140, 75)},  # matches config default
    "r_elbow_y":    {"description": "Elbow Flex", "desired_span": (-100, 100)},
    "r_wrist_z":    {"description": "Wrist Roll (left/right)", "desired_span": (-90, 90)},
    "r_wrist_y":    {"description": "Wrist Pitch (up/down)", "desired_span": (-40, 40)},
    "r_wrist_x":    {"description": "Wrist Pitch (up/down)", "desired_span": (-50, 35)},
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_joint_specs():
    root = _repo_root()
    for rel in DEFAULT_CONFIGS:
        cfg = root / rel
        if not cfg.exists():
            continue
        with cfg.open() as fh:
            data = json.load(fh)
        motors = data.get("motors", {})

        specs = {}
        for name, meta in JOINT_SPECS.items():
            if name not in motors:
                continue
            entry = motors[name]
            specs[int(entry["id"])] = {
                "name": name,
                "description": meta["description"],
                "desired_span": meta["desired_span"],
                "angle_limit": entry.get("angle_limit", meta["desired_span"]),
                "config": cfg.name,
            }
        if specs:
            return specs

    # Hard fallback (right arm common IDs)
    return {
        1: {"name": "r_shoulder_y", "description": "Shoulder Pitch", "desired_span": (-120, 120), "angle_limit": (-180, 179), "config": "hardcoded"},
        21: {"name": "r_shoulder_z", "description": "Shoulder Roll", "desired_span": (-90, 90), "angle_limit": (-100, 125), "config": "hardcoded"},
        3: {"name": "r_arm_x", "description": "Upper Arm Twist", "desired_span": (-140, 75), "angle_limit": (-140, 75), "config": "hardcoded"},
        5: {"name": "r_elbow_y", "description": "Elbow Flex", "desired_span": (-100, 100), "angle_limit": (-100, 100), "config": "hardcoded"},
        23: {"name": "r_wrist_z", "description": "Wrist Roll (left/right)", "desired_span": (-90, 90), "angle_limit": (-90, 90), "config": "hardcoded"},
        25: {"name": "r_wrist_x", "description": "Wrist Pitch (up/down)", "desired_span": (-50, 35), "angle_limit": (-50, 35), "config": "hardcoded"},
    }


def safe_targets(angle_limit, desired_span):
    amin, amax = angle_limit
    m = 3.0
    tmin = max(amin + m, desired_span[0])
    tmax = min(amax - m, desired_span[1])
    return [0.0, tmin, 0.0, tmax, 0.0]


def test_arm(port="/dev/ttyUSB0", baud=1_000_000):
    print("=" * 60)
    print("RIGHT ARM RANGE TEST (Shoulder / Elbow / Wrist)")
    print("=" * 60)

    specs = load_joint_specs()
    print(f"Using config: {', '.join({v['config'] for v in specs.values()})}")

    try:
        dxl_io = DxlIO(port, baudrate=baud, timeout=0.25)
        print("✓ Direct connection established")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return

    candidate_ids = list(specs.keys())
    try:
        available_ids = set(dxl_io.scan(candidate_ids))
        print(f"Detected IDs on bus (limited to {candidate_ids}): {sorted(available_ids)}")
    except Exception as e:
        print(f"✗ Scan failed: {e}")
        available_ids = set()

    try:
        for motor_id, info in specs.items():
            desc = info["description"]
            limits = info["angle_limit"]
            desired_span = info["desired_span"]

            print("\n------------------------------------------------------------")
            print(f"{desc} (ID {motor_id}, {info['name']})")
            print(f"Config source: {info.get('config','unknown')}")
            print(f"Config limits: {limits}")
            print("------------------------------------------------------------")

            if motor_id not in available_ids:
                print("❌ Motor not detected on bus – skipping")
                continue

            # Prefer hardware angle limits
            try:
                hw_min, hw_max = dxl_io.get_angle_limit([motor_id])[0]
                limits = (float(hw_min), float(hw_max))
                print(f"Using HW limits: {limits}")
            except Exception as e:
                print(f"⚠️ Could not read HW limits: {e}")

            waypoints = safe_targets(limits, desired_span)
            reached = []

            try:
                pos = dxl_io.get_present_position([motor_id])[0]
                volt = dxl_io.get_present_voltage([motor_id])[0]
                temp = dxl_io.get_present_temperature([motor_id])[0]
                print(f"Current: {pos:.1f}° | {volt:.1f}V | {temp}°C")
            except Exception as e:
                print(f"⚠️ Telemetry read failed: {e}")

            for idx, target in enumerate(waypoints, 1):
                try:
                    dxl_io.set_goal_position({motor_id: target})
                    time.sleep(1.0)
                    actual = dxl_io.get_present_position([motor_id])[0]
                    err = abs(actual - target)
                    reached.append(actual)
                    print(f"  Step {idx}: target {target:.1f}° → actual {actual:.1f}° (err {err:.1f}°)")
                except Exception as e:
                    print(f"  ❌ Move/read failed at step {idx}: {e}")
                    break

            if reached:
                span = max(reached) - min(reached)
                print(f"  Achieved span: {span:.1f}° (min {min(reached):.1f}°, max {max(reached):.1f}°)")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        traceback.print_exc()
    finally:
        try:
            dxl_io.close()
            print("\n✓ Connection closed")
        except Exception:
            pass


if __name__ == "__main__":
    test_arm()
