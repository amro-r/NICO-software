#!/usr/bin/env python3
"""
Direct pypot test for remaining hand motors
"""

import sys
import time
import traceback

# Add the nicomotion library path
sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')

try:
    import pypot.robot
    print("✓ Successfully imported pypot")
except ImportError as e:
    print(f"✗ Failed to import pypot: {e}")
    sys.exit(1)

def test_remaining_motors():
    """Test remaining motors using pypot directly"""
    print("\n" + "="*50)
    print("TESTING REMAINING MOTORS WITH PYPOT")
    print("="*50)
    
    try:
        # Create a direct pypot robot config for the remaining motors
        config = {
            'controllers': {
                'hand_controller': {
                    'port': '/dev/ttyUSB0',
                    'sync_read': False,
                    'protocol': 2,
                    'attached_motors': ['r_wrist_z', 'l_wrist_x', 'l_indexfingers_x', 'l_thumb_x', 'l_virtualhand_x'],
                    'models': {
                        'r_wrist_z': 'MX-28',
                        'l_wrist_x': 'MX-28',
                        'l_indexfingers_x': 'MX-28',
                        'l_thumb_x': 'MX-28',
                        'l_virtualhand_x': 'MX-28'
                    }
                }
            },
            'motorgroups': {
                'hand_motors': ['r_wrist_z', 'l_wrist_x', 'l_indexfingers_x', 'l_thumb_x', 'l_virtualhand_x']
            },
            'motors': {
                'r_wrist_z': {
                    'id': 23,
                    'type': 'MX-28',
                    'angle_limit': [-90, 90],
                    'offset': 0.0,
                    'orientation': 'direct'
                },
                'l_wrist_x': {
                    'id': 25,
                    'type': 'MX-28',
                    'angle_limit': [-35, 50],
                    'offset': 0.0,
                    'orientation': 'indirect'
                },
                'l_indexfingers_x': {
                    'id': 27,
                    'type': 'MX-28',
                    'angle_limit': [-160, 160],
                    'offset': 0.0,
                    'orientation': 'direct'
                },
                'l_thumb_x': {
                    'id': 29,
                    'type': 'MX-28',
                    'angle_limit': [-160, 160],
                    'offset': 0.0,
                    'orientation': 'direct'
                },
                'l_virtualhand_x': {
                    'id': 31,
                    'type': 'MX-28',
                    'angle_limit': [-160, 160],
                    'offset': 0.0,
                    'orientation': 'direct'
                }
            }
        }
        
        print("Initializing pypot robot...")
        robot = pypot.robot.from_config(config)
        print("✓ Robot initialized successfully")
        
        # Test each motor
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
                motor = getattr(robot, motor_name)
                current_pos = motor.present_position
                print(f"  Current position: {current_pos:.1f}°")
                
                # Test first angle
                target_angle = angles[0]
                print(f"  Moving to {target_angle}°...")
                motor.goal_position = target_angle
                time.sleep(1.5)
                
                # Check position
                actual_pos = motor.present_position
                print(f"  Actual position: {actual_pos:.1f}°")
                
                # Return to center
                motor.goal_position = 0.0
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
        
        # Close robot connection
        robot.close()
        
        return len(working_motors) > 0
        
    except Exception as e:
        print(f"✗ Failed to test hand motors: {e}")
        traceback.print_exc()
        return False

def main():
    try:
        success = test_remaining_motors()
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