#!/usr/bin/env python3
"""
Right-hand finger range-of-motion test (index, thumb, virtual hand)

- Targets only finger motors; wrist is excluded.
- Reads motor IDs and limits from hand configs; uses hardware limits if reachable.
- Sweeps each detected motor across its range in steps and reports achieved span.
"""

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')

try:
    from pypot.dynamixel.io import DxlIO
    print("✓ DxlIO imported")
except ImportError as exc:
    print(f"✗ Failed to import pypot DxlIO: {exc}")
    sys.exit(1)


RIGHT_HAND_MOTOR_NAMES = {
    "r_indexfingers_x": "Right Index Finger",
    "r_thumb_x": "Right Thumb",
    "r_virtualhand_x": "Right Virtual Hand / Coupled Fingers",
}

DEFAULT_CONFIGS = [
    "json/nico_humanoid_upper_body_control_general.json",   # IDs 27, 29, 32
    "json/nico_humanoid_upper_with_hands.json",            # IDs 28, 30, 32
    "json/nico_humanoid_upper_fixed.json",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_specs():
    root = _repo_root()
    for rel in DEFAULT_CONFIGS:
        cfg_path = root / rel
        if not cfg_path.exists():
            continue
        with cfg_path.open() as fh:
            data = json.load(fh)
        motors = data.get("motors", {})

        specs = {}
        for name, label in RIGHT_HAND_MOTOR_NAMES.items():
            if name not in motors:
                continue
            entry = motors[name]
            motor_id = int(entry["id"])
            limits = entry.get("angle_limit", [-150.0, 150.0])
            specs[motor_id] = {
                "name": name,
                "description": label,
                "expected_range": (float(limits[0]), float(limits[1])),
                "config": cfg_path.name,
            }
        if specs:
            return specs

    # Hard fallback
    return {
        27: {"name": "r_indexfingers_x", "description": "Right Index Finger", "expected_range": (-150.0, 150.0), "config": "hardcoded"},
        29: {"name": "r_thumb_x", "description": "Right Thumb", "expected_range": (-150.0, 150.0), "config": "hardcoded"},
        32: {"name": "r_virtualhand_x", "description": "Right Virtual Hand / Coupled Fingers", "expected_range": (-150.0, 150.0), "config": "hardcoded"},
    }


class FingerRangeTest:
    def __init__(self, port="/dev/ttyUSB0", baudrate=1_000_000, step_deg=12.0,
                 settle_time=0.9, tolerance_deg=7.0):
        self.port = port
        self.baudrate = baudrate
        self.step_deg = step_deg
        self.settle_time = settle_time
        self.tolerance_deg = tolerance_deg
        self.motors = load_specs()
        self.dxl = None

    def connect(self):
        print(f"Connecting to {self.port} @ {self.baudrate} baud …")
        try:
            self.dxl = DxlIO(self.port, baudrate=self.baudrate, timeout=0.25)
            print("✓ DxlIO connection established")
            return True
        except Exception as exc:
            print(f"✗ Failed to open port: {exc}")
            return False

    def close(self):
        if self.dxl:
            try:
                self.dxl.close()
                print("✓ Connection closed")
            except Exception:
                pass

    def build_targets(self, minimum, maximum):
        to_min, to_max = [], []
        current = 0.0
        while current - self.step_deg > minimum:
            current -= self.step_deg
            to_min.append(current)
        to_min.append(minimum)
        current = 0.0
        while current + self.step_deg < maximum:
            current += self.step_deg
            to_max.append(current)
        to_max.append(maximum)
        return to_min, to_max

    def move_and_measure(self, motor_id, target_deg):
        self.dxl.set_goal_position({motor_id: target_deg})
        time.sleep(self.settle_time)
        actual = self.dxl.get_present_position([motor_id])[0]
        error = abs(actual - target_deg)
        return actual, error

    def sweep_motor(self, motor_id, spec, available_ids):
        print("\n" + "-" * 60)
        print(f"Testing {spec['description']} (ID {motor_id}, {spec['name']})")
        print(f"Config source: {spec.get('config', 'unknown')}")
        print("-" * 60)

        if motor_id not in available_ids:
            print("❌ Motor not detected on bus – cannot test")
            return None

        # Prefer hardware limits when possible
        try:
            hw_min, hw_max = self.dxl.get_angle_limit([motor_id])[0]
            spec = dict(spec)
            spec["expected_range"] = (float(hw_min), float(hw_max))
            print(f"Using HW limits: {spec['expected_range']}")
        except Exception as exc:
            print(f"⚠️  Could not read HW limits: {exc}")

        try:
            init_pos = self.dxl.get_present_position([motor_id])[0]
            voltage = self.dxl.get_present_voltage([motor_id])[0]
            temperature = self.dxl.get_present_temperature([motor_id])[0]
            print(f"Current position: {init_pos:.1f}° | Voltage: {voltage:.1f}V | Temp: {temperature}°C")
        except Exception as exc:
            print(f"⚠️  Unable to read initial telemetry: {exc}")
            init_pos, voltage, temperature = None, None, None

        # Center then sweep
        try:
            neutral_actual, neutral_error = self.move_and_measure(motor_id, 0.0)
            print(f"Centered at 0° → actual {neutral_actual:.1f}° (err {neutral_error:.1f}°)")
        except Exception as exc:
            print(f"❌ Could not move to neutral: {exc}")
            return None

        expected_min, expected_max = spec["expected_range"]
        to_min, to_max = self.build_targets(expected_min, expected_max)

        reached_positions = [neutral_actual]
        limits_hit = {"min": None, "max": None}

        for idx, target in enumerate(to_min, start=1):
            actual, error = self.move_and_measure(motor_id, target)
            reached_positions.append(actual)
            stalled = error > self.tolerance_deg and abs(actual - reached_positions[-2]) < 2.0
            if stalled:
                limits_hit["min"] = f"stalled near {actual:.1f}° (err {error:.1f}°)"
                print(f"  Step {idx}: target {target:.1f}° → actual {actual:.1f}° (err {error:.1f}°) ⚠️ stalled")
                break
            print(f"  Step {idx}: target {target:.1f}° → actual {actual:.1f}° (err {error:.1f}°)")
            if error > self.tolerance_deg:
                limits_hit["min"] = f"large error at {actual:.1f}° (err {error:.1f}°)"
                break

        neutral_actual, _ = self.move_and_measure(motor_id, 0.0)
        reached_positions.append(neutral_actual)

        for idx, target in enumerate(to_max, start=1):
            actual, error = self.move_and_measure(motor_id, target)
            reached_positions.append(actual)
            stalled = error > self.tolerance_deg and abs(actual - reached_positions[-2]) < 2.0
            if stalled:
                limits_hit["max"] = f"stalled near {actual:.1f}° (err {error:.1f}°)"
                print(f"  Step +{idx}: target {target:.1f}° → actual {actual:.1f}° (err {error:.1f}°) ⚠️ stalled")
                break
            print(f"  Step +{idx}: target {target:.1f}° → actual {actual:.1f}° (err {error:.1f}°)")
            if error > self.tolerance_deg:
                limits_hit["max"] = f"large error at {actual:.1f}° (err {error:.1f}°)"
                break

        achieved_min = min(reached_positions)
        achieved_max = max(reached_positions)
        span = achieved_max - achieved_min
        expected_span = expected_max - expected_min
        coverage = max(0.0, min(1.0, span / expected_span)) if expected_span else 0.0
        status = "FULL" if coverage >= 0.9 else "PARTIAL" if coverage >= 0.5 else "FAILED"

        print(f"Reached span: {achieved_min:.1f}° → {achieved_max:.1f}° (coverage {coverage*100:.0f}% of expected)")
        if limits_hit["min"]:
            print(f"  Min-side limit: {limits_hit['min']}")
        if limits_hit["max"]:
            print(f"  Max-side limit: {limits_hit['max']}")
        print(f"Result: {status}\n")

        self.move_and_measure(motor_id, 0.0)

        return {
            "achieved_min": achieved_min,
            "achieved_max": achieved_max,
            "span": span,
            "coverage": coverage,
            "status": status,
            "limits_hit": limits_hit,
        }

    def run(self):
        print("=" * 60)
        print("RIGHT FINGER RANGE TEST (Index / Thumb / Virtual Hand)")
        print("=" * 60)

        if not self.connect():
            return False

        try:
            available = set(self.dxl.scan(list(self.motors.keys())))
            print(f"Detected IDs on bus: {sorted(available)}")
        except Exception as exc:
            print(f"⚠️  Bus scan failed: {exc}")
            available = set()

        summary = {}
        try:
            for motor_id, spec in self.motors.items():
                capability = self.sweep_motor(motor_id, spec, available)
                summary[motor_id] = capability
            self.report(summary)
        finally:
            self.close()

        return True

    def report(self, summary):
        print("\n" + "=" * 60)
        print("RIGHT FINGER RANGE REPORT")
        print("=" * 60)
        for motor_id, capability in summary.items():
            spec = self.motors[motor_id]
            if capability is None:
                print(f"ID {motor_id}: {spec['description']} → NOT REACHABLE")
                continue
            print(f"ID {motor_id}: {spec['description']}")
            print(f"  Achieved range : {capability['achieved_min']:.1f}° to {capability['achieved_max']:.1f}°")
            print(f"  Span / Expected: {capability['span']:.1f}° / {(spec['expected_range'][1] - spec['expected_range'][0]):.1f}° ({capability['coverage']*100:.0f}% )")
            if capability['limits_hit']['min']:
                print(f"  Min limit      : {capability['limits_hit']['min']}")
            if capability['limits_hit']['max']:
                print(f"  Max limit      : {capability['limits_hit']['max']}")
            print(f"  Status         : {capability['status']}\n")


def parse_args():
    p = argparse.ArgumentParser(description="Right-hand finger range test (index, thumb, virtual hand)")
    p.add_argument("--port", default="/dev/ttyUSB0", help="USB/serial port")
    p.add_argument("--baud", type=int, default=1_000_000, help="Baudrate")
    p.add_argument("--step", type=float, default=12.0, help="Step size in degrees")
    p.add_argument("--settle", type=float, default=0.9, help="Seconds to wait after each move")
    p.add_argument("--tolerance", type=float, default=7.0, help="Allowed position error before flagging limited motion")
    return p.parse_args()


def main():
    args = parse_args()
    test = FingerRangeTest(port=args.port, baudrate=args.baud, step_deg=args.step,
                           settle_time=args.settle, tolerance_deg=args.tolerance)
    try:
        ok = test.run()
        if not ok:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted – returning motors to neutral if possible…")
    except Exception as exc:
        print(f"\nUnexpected error: {exc}")
        traceback.print_exc()
    finally:
        test.close()


if __name__ == "__main__":
    main()
