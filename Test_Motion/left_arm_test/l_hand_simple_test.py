#!/usr/bin/env python3
"""
Left Hand Simple Movement Test

Since position reading doesn't work correctly with SEED Robotics servos,
this test just sends movement commands without verifying position.

Watch the motors visually to confirm they're working.
"""

import sys
import time

sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')

from pypot.dynamixel.io.io_320 import Dxl320IO

# Correct motor mapping
MOTORS = {
    31: "Wrist Roll (L/R)",
    33: "Wrist Pitch (Up/Down)",
    34: "Thumb Roll (L/R)",
    35: "Thumb Pitch (Grab)",
    36: "Index Finger",
    37: "Middle Finger",
}

def main():
    print("=" * 60)
    print("LEFT HAND MOVEMENT TEST (Visual verification)")
    print("=" * 60)
    print("\n⚠️ Position reading is broken for SEED servos")
    print("   Watch the motors move visually to verify\n")
    
    dxl_io = Dxl320IO("/dev/ttyUSB0", baudrate=1_000_000, timeout=0.5)
    print("✓ Connected\n")
    
    # Reset all to 0
    print("Resetting all motors to 0°...")
    for mid in MOTORS:
        dxl_io.set_goal_position({mid: 0})
        time.sleep(0.2)
    time.sleep(2)
    
    # Test each motor
    for mid, name in MOTORS.items():
        print(f"\n{'='*50}")
        print(f"Testing: {name} (ID {mid})")
        print("=" * 50)
        
        input("Press Enter to move to +100°...")
        dxl_io.set_goal_position({mid: 100})
        time.sleep(1)
        
        input("Press Enter to move to -100°...")
        dxl_io.set_goal_position({mid: -100})
        time.sleep(1)
        
        input("Press Enter to return to 0°...")
        dxl_io.set_goal_position({mid: 0})
        time.sleep(1)
        
        response = input("Did this motor move correctly? (y/n): ")
        if response.lower() == 'y':
            print(f"✅ {name} WORKING")
        else:
            print(f"❌ {name} ISSUE DETECTED")
    
    # Return all to 0
    print("\nReturning all to 0°...")
    for mid in MOTORS:
        dxl_io.set_goal_position({mid: 0})
    time.sleep(1)
    
    dxl_io.close()
    print("\n✓ Test complete!")

if __name__ == "__main__":
    main()
