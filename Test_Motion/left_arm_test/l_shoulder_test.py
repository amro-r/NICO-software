#!/usr/bin/env python3
"""
Simple Left Shoulder Test
Tests left shoulder motors (pitch, roll, and arm twist/yaw)
"""

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

def test_left_shoulder():
    print("=" * 50)
    print("LEFT SHOULDER TEST")
    print("=" * 50)
    print("Testing: Pitch, Roll, and Arm Twist (Yaw)")
    print("Note: This test should ONLY move the LEFT arm")
    
    # Initialize robot
    try:
        config_path = "/home/amr/catkin_ws/src/NICO-software/Test_Motion/test_config.json"
        motion = Motion(motorConfig=config_path, vrep=False, ignoreMissing=True, monitorHandCurrents=False)
        print("✓ Robot connected")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    try:
        # Test Left Shoulder Pitch (l_shoulder_y)
        print("\n--- Left Shoulder Pitch Test ---")
        print("Motor: l_shoulder_y (ID: 2)")
        current = motion.getAngle("l_shoulder_y")
        print(f"Current position: {current:.1f}°")
        
        test_angles = [0, 20, -20, 0]
        for angle in test_angles:
            print(f"Moving to {angle}°...")
            motion.setAngle("l_shoulder_y", angle, 0.15)
            time.sleep(2.0)
            actual = motion.getAngle("l_shoulder_y")
            error = abs(actual - angle)
            print(f"  Target: {angle}°, Actual: {actual:.1f}°, Error: {error:.1f}°")
            if error < 3:
                print("  ✓ Good")
            else:
                print("  ⚠️ Error")
        
        # Test Left Shoulder Roll (l_shoulder_z)
        print("\n--- Left Shoulder Roll Test ---")
        print("Motor: l_shoulder_z (ID: 22)")
        current = motion.getAngle("l_shoulder_z")
        print(f"Current position: {current:.1f}°")
        
        test_angles = [0, 25, -25, 0]
        for angle in test_angles:
            print(f"Moving to {angle}°...")
            motion.setAngle("l_shoulder_z", angle, 0.15)
            time.sleep(2.0)
            actual = motion.getAngle("l_shoulder_z")
            error = abs(actual - angle)
            print(f"  Target: {angle}°, Actual: {actual:.1f}°, Error: {error:.1f}°")
            if error < 3:
                print("  ✓ Good")
            else:
                print("  ⚠️ Error")
        
        # Test Left Arm Twist/Yaw (l_arm_x)
        print("\n--- Left Arm Twist/Yaw Test ---")
        print("Motor: l_arm_x (ID: 4)")
        current = motion.getAngle("l_arm_x")
        print(f"Current position: {current:.1f}°")
        
        test_angles = [0, 20, -20, 0]
        for angle in test_angles:
            print(f"Moving to {angle}°...")
            motion.setAngle("l_arm_x", angle, 0.15)
            time.sleep(2.0)
            actual = motion.getAngle("l_arm_x")
            error = abs(actual - angle)
            print(f"  Target: {angle}°, Actual: {actual:.1f}°, Error: {error:.1f}°")
            if error < 3:
                print("  ✓ Good")
            else:
                print("  ⚠️ Error")
        
        print("\n✅ Left shoulder test completed")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        traceback.print_exc()
    
    finally:
        try:
            motion.disableTorque("l_shoulder_y")
            motion.disableTorque("l_shoulder_z")
            motion.disableTorque("l_arm_x")
            print("✓ Motors disabled")
        except:
            pass

if __name__ == "__main__":
    test_left_shoulder()
