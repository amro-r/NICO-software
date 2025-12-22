#!/usr/bin/env python3
"""
Right-hand finger presence & quick motion check

- Avoids the pypot ping bug by using a single bus scan
- Uses motor IDs and limits from the first available hand config under ../json
- Exercises each detected motor with a small in-place wiggle to confirm movement
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

RIGHT_HAND_MOTOR_NAMES = {
    "r_indexfingers_x": "Right Index Finger",
    "r_thumb_x": "Right Thumb",
    "r_virtualhand_x": "Right Virtual Hand / Coupled Fingers",
}

DEFAULT_CONFIGS = [
    "json/nico_humanoid_upper_body_control_general.json",   # IDs 27, 29, 32 (matches current bus scan)
    "json/nico_humanoid_upper_with_hands.json",            # IDs 28, 30, 32
    "json/nico_humanoid_upper_fixed.json",                  # fallback
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_right_hand_specs():
    root = _repo_root()
    for rel in DEFAULT_CONFIGS:
        cfg = root / rel
        if not cfg.exists():
            continue
        with cfg.open() as fh:
            data = json.load(fh)
        motors = data.get("motors", {})

        specs = {}
        for name, label in RIGHT_HAND_MOTOR_NAMES.items():
            if name not in motors:
                continue
            entry = motors[name]
            specs[int(entry["id"])] = {
                "description": label,
                "angle_limit": entry.get("angle_limit", [-150.0, 150.0]),
                "config": cfg.name,
            }
        if specs:
            return specs

    # Hard fallback
    return {
        27: {"description": "Right Index Finger", "angle_limit": [-150.0, 150.0], "config": "hardcoded"},
        29: {"description": "Right Thumb", "angle_limit": [-150.0, 150.0], "config": "hardcoded"},
        32: {"description": "Right Virtual Hand / Coupled Fingers", "angle_limit": [-150.0, 150.0], "config": "hardcoded"},
    }


def test_right_fingers(port="/dev/ttyUSB0", baud=1_000_000):
    print("=" * 50)
    print("RIGHT FINGERS TEST")
    print("=" * 50)

    specs = load_right_hand_specs()
    print(f"Using config: {', '.join({v['config'] for v in specs.values()})}")

    # Initialize direct connection
    try:
        dxl_io = DxlIO(port, baudrate=baud, timeout=1.0)
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
        found_motors = []
        missing_motors = []

        for motor_id, info in specs.items():
            desc = info["description"]
            print(f"\nChecking {desc} (ID: {motor_id})...")

            if motor_id not in available_ids:
                print("  ❌ Motor not detected on bus")
                missing_motors.append((motor_id, desc))
                continue

            try:
                position = dxl_io.get_present_position([motor_id])[0]
                voltage = dxl_io.get_present_voltage([motor_id])[0]
                temp = dxl_io.get_present_temperature([motor_id])[0]

                print(f"  Position: {position:.1f}° | Voltage: {voltage:.1f}V | Temperature: {temp}°C")

                # Small wiggle to confirm motion capability (stay well inside limits)
                amin, amax = info["angle_limit"]
                wiggle = 12.0
                down = max(amin + 5, position - wiggle)
                up = min(amax - 5, position + wiggle)
                for target in (down, up, position):
                    dxl_io.set_goal_position({motor_id: target})
                    time.sleep(0.8)
                    actual = dxl_io.get_present_position([motor_id])[0]
                    print(f"    Target {target:.1f}° → actual {actual:.1f}°")

                found_motors.append((motor_id, desc))

            except Exception as e:
                print(f"  ⚠️ Communication error: {e}")
                missing_motors.append((motor_id, f"{desc} (comm error)"))

        # Summary
        print("\n" + "=" * 50)
        print("RIGHT HAND SUMMARY")
        print("=" * 50)

        if found_motors:
            print(f"\n✅ FOUND MOTORS ({len(found_motors)}):")
            for motor_id, description in found_motors:
                print(f"  ID {motor_id}: {description}")
        else:
            print(f"\n❌ NO MOTORS FOUND")

        if missing_motors:
            print(f"\n🔌 MISSING/ERROR MOTORS ({len(missing_motors)}):")
            for motor_id, description in missing_motors:
                print(f"  ID {motor_id}: {description}")

        print(f"\nRIGHT HAND STATUS: {'✅ Functional' if found_motors else '❌ No finger control available'}")

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
    test_right_fingers()
