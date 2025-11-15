#!/usr/bin/env python3
"""
Left wrist roll comprehensive test.

This script drives the l_wrist_z motor (left wrist roll) through the safe
portion of its configured range to ensure the correct motor ID is mapped and
to check whether the joint can reach each waypoint without large errors.
"""

import json
import sys
import time
import traceback

sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')

try:
    from pypot.dynamixel.io import DxlIO
    print("✓ DxlIO imported")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

CONFIG_PATH = "/home/amr/catkin_ws/src/NICO-software/json/nico_humanoid_upper.json"
PORT = "/dev/ttyUSB0"
BAUDRATE = 1000000
JOINT_NAME = "l_wrist_z"
SAFE_MARGIN_DEG = 10.0
PROFILE_STEPS = 6
MOVE_SPEED = 40  # Dynamixel speed units (approx. RPM)
DWELL_SECONDS = 1.8
ERROR_TOLERANCE = 5.0


def load_joint_specs(config_path, joint_name):
    """Load the motor ID and limits for the joint from the canonical config."""
    with open(config_path, "r") as cfg:
        config = json.load(cfg)

    if "motors" not in config or joint_name not in config["motors"]:
        raise KeyError(f"{joint_name} not found in {config_path}")

    joint_cfg = config["motors"][joint_name]
    angle_min, angle_max = joint_cfg["angle_limit"]
    return int(joint_cfg["id"]), float(angle_min), float(angle_max)


def build_profile(angle_min, angle_max, steps):
    """Create an out-and-back sweep profile with a small safety margin."""
    safe_min = angle_min + SAFE_MARGIN_DEG
    safe_max = angle_max - SAFE_MARGIN_DEG
    if safe_min >= safe_max:
        safe_min, safe_max = angle_min, angle_max

    steps = max(steps, 2)
    ascending = [
        round(safe_min + (safe_max - safe_min) * (i / (steps - 1)), 2)
        for i in range(steps)
    ]
    profile = [0.0]
    profile.extend(ascending)
    profile.extend(reversed(ascending))
    profile.append(0.0)
    return profile


def connect_io():
    """Open a DxlIO connection on the default bus."""
    return DxlIO(PORT, baudrate=BAUDRATE, timeout=1.0)


def test_left_wrist():
    print("=" * 60)
    print("LEFT WRIST ROLL FULL-RANGE TEST")
    print("=" * 60)

    try:
        motor_id, angle_min, angle_max = load_joint_specs(CONFIG_PATH, JOINT_NAME)
    except Exception as exc:
        print(f"✗ Failed to read joint specs: {exc}")
        return

    print(f"Motor: {JOINT_NAME} (ID: {motor_id})")
    print(f"Configured limits: [{angle_min}°, {angle_max}°]")

    profile = build_profile(angle_min, angle_max, PROFILE_STEPS)
    print(f"Test waypoints ({len(profile)} steps): {profile}")

    dxl_io = None
    try:
        dxl_io = connect_io()
        print(f"✓ Connected to {PORT} at {BAUDRATE} baud")

        # Use a conservative moving speed if supported by the motor.
        try:
            dxl_io.set_moving_speed({motor_id: MOVE_SPEED})
        except Exception:
            pass

        results = []
        for idx, target in enumerate(profile, start=1):
            print(f"\nStep {idx}/{len(profile)}: Moving to {target}° ...")
            dxl_io.set_goal_position({motor_id: target})
            time.sleep(DWELL_SECONDS)
            actual = dxl_io.get_present_position([motor_id])[0]
            error = actual - target
            abs_error = abs(error)
            results.append(abs_error)
            print(f"  Target: {target:.1f}° | Actual: {actual:.1f}° | Error: {error:.1f}°")
            if abs_error <= ERROR_TOLERANCE:
                print("  ✓ Within tolerance")
            else:
                print(f"  ⚠️  Exceeds tolerance ({ERROR_TOLERANCE}°)")

        max_error = max(results) if results else 0.0
        avg_error = sum(results) / len(results) if results else 0.0
        print("\n--- Summary ---")
        print(f"Max absolute error: {max_error:.1f}°")
        print(f"Average absolute error: {avg_error:.1f}°")
        print("✅ Left wrist roll test completed")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        traceback.print_exc()
    finally:
        try:
            if dxl_io:
                dxl_io.disable_torque([motor_id])
                dxl_io.close()
                print("✓ Connection closed")
        except Exception:
            pass


if __name__ == "__main__":
    test_left_wrist()
