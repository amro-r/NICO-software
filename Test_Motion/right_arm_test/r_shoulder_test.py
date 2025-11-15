#!/usr/bin/env python3
"""
Simple Right Shoulder Test
Tests right shoulder motors (pitch, roll, and arm twist/yaw)
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

def test_right_shoulder():
    print("=" * 50)
    print("RIGHT SHOULDER TEST")
    print("=" * 50)
    print("Testing: Pitch, Roll, and Arm Twist (Yaw)")
    print("Note: This test should ONLY move the RIGHT arm")
    
    # Initialize robot
    try:
        config_path = "/home/amr/catkin_ws/src/NICO-software/Test_Motion/test_config.json"
        motion = Motion(motorConfig=config_path, vrep=False, ignoreMissing=True, monitorHandCurrents=False)
        print("✓ Robot connected")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    try:
        # Test Right Shoulder Pitch (r_shoulder_y)
        print("\n--- Right Shoulder Pitch Test ---")
        print("Motor: r_shoulder_y (ID: 1)")
        current = motion.getAngle("r_shoulder_y")
        print(f"Current position: {current:.1f}°")
        
        test_angles = [0, 20, -20, 0]
        for angle in test_angles:
            print(f"Moving to {angle}°...")
            motion.setAngle("r_shoulder_y", angle, 0.15)
            time.sleep(2.0)
            actual = motion.getAngle("r_shoulder_y")
            error = abs(actual - angle)
            print(f"  Target: {angle}°, Actual: {actual:.1f}°, Error: {error:.1f}°")
            if error < 3:
                print("  ✓ Good")
            else:
                print("  ⚠️ Error")
        
        # Test Right Shoulder Roll (r_shoulder_z)
        print("\n--- Right Shoulder Roll Test ---")
        print("Motor: r_shoulder_z (ID: 21)")
        current = motion.getAngle("r_shoulder_z")
        print(f"Current position: {current:.1f}°")
        
        test_angles = [0, 25, -25, 0]
        for angle in test_angles:
            print(f"Moving to {angle}°...")
            motion.setAngle("r_shoulder_z", angle, 0.15)
            time.sleep(2.0)
            actual = motion.getAngle("r_shoulder_z")
            error = abs(actual - angle)
            print(f"  Target: {angle}°, Actual: {actual:.1f}°, Error: {error:.1f}°")
            if error < 3:
                print("  ✓ Good")
            else:
                print("  ⚠️ Error")
        
        # Test Right Arm Twist/Yaw (r_arm_x)
        print("\n--- Right Arm Twist/Yaw Test ---")
        print("Motor: r_arm_x (ID: 3)")
        current = motion.getAngle("r_arm_x")
        print(f"Current position: {current:.1f}°")
        
        test_angles = [0, 20, -20, 0]
        for angle in test_angles:
            print(f"Moving to {angle}°...")
            motion.setAngle("r_arm_x", angle, 0.15)
            time.sleep(2.0)
            actual = motion.getAngle("r_arm_x")
            error = abs(actual - angle)
            print(f"  Target: {angle}°, Actual: {actual:.1f}°, Error: {error:.1f}°")
            if error < 3:
                print("  ✓ Good")
            else:
                print("  ⚠️ Error")
        
        print("\n✅ Right shoulder test completed")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        traceback.print_exc()
    
    finally:
        try:
            motion.disableTorque("r_shoulder_y")
            motion.disableTorque("r_shoulder_z")
            motion.disableTorque("r_arm_x")
            print("✓ Motors disabled")
        except:
            pass

if __name__ == "__main__":
    test_right_shoulder()
