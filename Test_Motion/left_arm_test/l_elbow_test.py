#!/usr/bin/env python3
"""
Simple Left Elbow Test
Tests only the left elbow motor
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

def test_left_elbow():
    print("=" * 50)
    print("LEFT ELBOW TEST")
    print("=" * 50)
    
    # Initialize robot
    try:
        config_path = "/home/amr/catkin_ws/src/NICO-software/Test_Motion/test_config.json"
        motion = Motion(motorConfig=config_path, vrep=False, ignoreMissing=True, monitorHandCurrents=False)
        print("✓ Robot connected")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    try:
        # Test Left Elbow (l_elbow_y)
        print("\n--- Left Elbow Pitch Test ---")
        print("Motor: l_elbow_y (ID: 6)")
        
        current = motion.getAngle("l_elbow_y")
        print(f"Current position: {current:.1f}°")
        
        # Simple bend test
        test_angles = [0, 30, 60, 30, 0]
        for i, angle in enumerate(test_angles):
            print(f"Step {i+1}: Moving to {angle}°...")
            motion.setAngle("l_elbow_y", angle, 0.2)
            time.sleep(2.5)
            actual = motion.getAngle("l_elbow_y")
            error = abs(actual - angle)
            print(f"  Target: {angle}°, Actual: {actual:.1f}°, Error: {error:.1f}°")
            if error < 5:
                print("  ✓ Good movement")
            else:
                print("  ⚠️ Position error")
            time.sleep(0.5)
        
        print("\n✅ Left elbow test completed")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        traceback.print_exc()
    
    finally:
        try:
            motion.disableTorque("l_elbow_y")
            print("✓ Elbow motor disabled")
        except:
            pass

if __name__ == "__main__":
    test_left_elbow()