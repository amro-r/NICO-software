#!/usr/bin/env python3
"""
Motor ID 36 - UNKNOWN (To be identified)
Full range test
"""

import sys
import time

sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')

from pypot.dynamixel.io.io_320 import Dxl320IO

MOTOR_ID = 36
JOINT_NAME = "UNKNOWN - Identify this joint"
PORT = "/dev/ttyUSB0"
BAUD = 1_000_000

def test_motor():
    print("=" * 50)
    print(f"MOTOR ID {MOTOR_ID} - {JOINT_NAME}")
    print("FULL RANGE TEST")
    print("=" * 50)
    
    dxl_io = Dxl320IO(PORT, baudrate=BAUD, timeout=0.5)
    
    print("Moving to 0°...")
    dxl_io.set_goal_position({MOTOR_ID: 0})
    time.sleep(2)
    
    # Full range test
    movements = [
        (0, "Starting at 0°"),
        (50, "Moving to +50°"),
        (100, "Moving to +100°"),
        (150, "Moving to +150°"),
        (0, "Back to 0°"),
        (-50, "Moving to -50°"),
        (-100, "Moving to -100°"),
        (-150, "Moving to -150°"),
        (0, "Back to 0°"),
    ]
    
    for pos, msg in movements:
        print(f"\n>>> {msg}")
        dxl_io.set_goal_position({MOTOR_ID: pos})
        time.sleep(1.5)
        input("Press Enter to continue...")
    
    print(f"\n✅ Full range test complete")
    print("What joint did this motor control?")
    print("  - Wrist Roll (left/right)?")
    print("  - Index Fingers?")
    print("  - Thumb?")
    print("  - Virtual Hand?")
    dxl_io.close()

if __name__ == "__main__":
    test_motor()
