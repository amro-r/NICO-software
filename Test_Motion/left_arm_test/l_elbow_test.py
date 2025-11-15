#!/usr/bin/env python3
"""
Left elbow comprehensive test.

This script sweeps the l_elbow_y joint through its full configured range
(minus a small mechanical safety margin) to verify that the motor can reach
each waypoint consistently.
"""

import json
import sys
import time
import traceback

sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')

try:
    from nicomotion.Motion import Motion
    print("✓ Motion class imported")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

CONFIG_PATH = "/home/amr/catkin_ws/src/NICO-software/Test_Motion/test_config.json"
JOINT_NAME = "l_elbow_y"
MOTOR_ID = 6
SAFE_MARGIN_DEG = 5.0  # avoid slamming hard-stops
PROFILE_STEPS = 6      # number of points between the min/max limits
MOVE_SPEED = 0.25
DWELL_SECONDS = 2.0


def load_joint_limits(config_path, joint_name):
    """Read the joint's angle limits from the JSON config."""
    try:
        with open(config_path, "r") as cfg:
            config = json.load(cfg)
        limits = config["motors"][joint_name]["angle_limit"]
        return float(limits[0]), float(limits[1])
    except Exception as exc:  # pragma: no cover - defensive for runtime issues
        print(f"⚠️  Failed to load limits from {config_path}: {exc}")
        return -100.0, 100.0


def build_full_range_profile(angle_min, angle_max, steps):
    """Create a symmetric sweep profile from min to max and back."""
    safe_min = angle_min + SAFE_MARGIN_DEG
    safe_max = angle_max - SAFE_MARGIN_DEG
    if safe_min >= safe_max:  # fallback if the configured range is too tight
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


def move_and_measure(motion, angle):
    """Command the joint and capture the resulting position/error."""
    motion.setAngle(JOINT_NAME, angle, MOVE_SPEED)
    time.sleep(DWELL_SECONDS)
    actual = motion.getAngle(JOINT_NAME)
    error = actual - angle
    return actual, error


def test_left_elbow():
    print("=" * 60)
    print("LEFT ELBOW FULL-RANGE TEST")
    print("=" * 60)

    # Initialize robot
    try:
        motion = Motion(
            motorConfig=CONFIG_PATH,
            vrep=False,
            ignoreMissing=True,
            monitorHandCurrents=False,
        )
        print("✓ Robot connected")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return

    try:
        angle_min, angle_max = load_joint_limits(CONFIG_PATH, JOINT_NAME)
        print(f"Configured limits: [{angle_min}°, {angle_max}°]")
        profile = build_full_range_profile(angle_min, angle_max, PROFILE_STEPS)

        print(f"Motor: {JOINT_NAME} (ID: {MOTOR_ID})")
        print(f"Test waypoints ({len(profile)} steps): {profile}")

        results = []
        for idx, target in enumerate(profile, start=1):
            print(f"\nStep {idx}/{len(profile)}: Moving to {target}° ...")
            actual, error = move_and_measure(motion, target)
            abs_err = abs(error)
            results.append(abs_err)
            print(f"  Target: {target:.1f}° | Actual: {actual:.1f}° | Error: {error:.1f}°")
            if abs_err <= 3.0:
                print("  ✓ Within tolerance")
            else:
                print("  ⚠️  Exceeds tolerance (3°)")

        max_error = max(results) if results else 0.0
        avg_error = sum(results) / len(results) if results else 0.0
        print("\n--- Summary ---")
        print(f"Max absolute error: {max_error:.1f}°")
        print(f"Average absolute error: {avg_error:.1f}°")
        print("✅ Left elbow full-range test completed")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        traceback.print_exc()

    finally:
        try:
            motion.disableTorque(JOINT_NAME)
            print("✓ Elbow motor disabled")
        except Exception:
            pass


if __name__ == "__main__":
    test_left_elbow()
