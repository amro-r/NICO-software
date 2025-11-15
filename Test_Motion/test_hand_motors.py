#!/usr/bin/env python3
"""
Test Hand Motors Only - Bypassing hand class initialization
"""

import sys
import time
import traceback

# Add the nicomotion library path
sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')

try:
    from nicomotion.Motion import Motion
    print("✓ Successfully imported Motion class")
except ImportError as e:
    print(f"✗ Failed to import Motion class: {e}")
    sys.exit(1)

def test_hand_motors():
    """Test hand motors directly without using Motion class"""
    print("\n" + "="*50)
    print("TESTING HAND MOTORS")
    print("="*50)
    
    try:
        # Initialize with hand motor config only
        motion = Motion(motorConfig="/home/amr/catkin_ws/src/NICO-software/Test_Motion/hand_config.json", 
                       vrep=False, ignoreMissing=True, monitorHandCurrents=False)
        
        print("✓ Hand motor connection established")
        
        # Test hand motors
        hand_motors = [
            ("r_wrist_z", [30, -30, 0], "Right Wrist Rotation"),
            ("l_wrist_x", [20, -20, 0], "Left Wrist Bend"),
            ("l_indexfingers_x", [60, -60, 0], "Left Index Finger"),
            ("l_thumb_x", [60, -60, 0], "Left Thumb"),
            ("l_virtualhand_x", [30, -30, 0], "Left Virtual Hand"),
        ]
        
        working_motors = []
        failed_motors = []
        
        for motor_name, angles, description in hand_motors:
            print(f"\nTesting {description} ({motor_name})...")
            try:
                current_pos = motion.getAngle(motor_name)
                print(f"  Current position: {current_pos:.1f}°")
                
                # Test first angle
                target_angle = angles[0]
                print(f"  Moving to {target_angle}°...")
                motion.setAngle(motor_name, target_angle, 0.2)
                time.sleep(1.5)
                
                # Check position
                actual_pos = motion.getAngle(motor_name)
                print(f"  Actual position: {actual_pos:.1f}°")
                
                # Return to center
                motion.setAngle(motor_name, 0.0, 0.2)
                time.sleep(1.0)
                
                working_motors.append((motor_name, description))
                print(f"  ✓ {description} working")
                
            except Exception as e:
                failed_motors.append((motor_name, description, str(e)))
                print(f"  ✗ {description} failed: {e}")
        
        # Report results
        print("\n" + "="*60)
        print("HAND MOTOR TEST RESULTS")
        print("="*60)
        
        print(f"\n✓ WORKING HAND MOTORS ({len(working_motors)}):")
        for motor_name, description in working_motors:
            print(f"  - {description} ({motor_name})")
        
        print(f"\n✗ FAILED HAND MOTORS ({len(failed_motors)}):")
        for motor_name, description, error in failed_motors:
            print(f"  - {description} ({motor_name}): {error}")
        
        return len(working_motors) > 0
        
    except Exception as e:
        print(f"✗ Failed to test hand motors: {e}")
        traceback.print_exc()
        return False

def main():
    try:
        success = test_hand_motors()
        if success:
            print("\n🎉 Hand motor testing completed!")
        else:
            print("\n❌ Hand motor testing failed")
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()