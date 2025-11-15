#!/usr/bin/env python3
"""
Shoulder Motor Diagnostic Script
Tests motor IDs 1 and 2 directly to identify which arm they control
"""

import sys
import time
import traceback

sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')

try:
    from pypot.dynamixel.io import DxlIO
    print("✓ DxlIO imported")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

def test_shoulder_motor_ids():
    print("=" * 60)
    print("SHOULDER MOTOR ID DIAGNOSTIC")
    print("=" * 60)
    print("This script will test motor IDs 1 and 2 directly")
    print("Please observe which arm moves for each test")
    print()
    
    # Initialize direct connection
    try:
        dxl_io = DxlIO('/dev/ttyUSB0', baudrate=1000000, timeout=1.0)
        print("✓ Direct connection established")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    # Test motor IDs for shoulder pitch
    test_motors = [1, 2]
    
    try:
        for motor_id in test_motors:
            print(f"\n{'='*50}")
            print(f"TESTING MOTOR ID {motor_id}")
            print(f"{'='*50}")
            
            # Check if motor responds
            try:
                response = dxl_io.ping(motor_id)
                if not response:
                    print(f"❌ Motor ID {motor_id} does not respond")
                    continue
                    
                print(f"✅ Motor ID {motor_id} responds")
                
                # Get current status
                position = dxl_io.get_present_position([motor_id])[0]
                voltage = dxl_io.get_present_voltage([motor_id])[0]
                print(f"Current position: {position:.1f}°")
                print(f"Voltage: {voltage:.1f}V")
                
                # Perform test movement
                print(f"\n🔄 TESTING MOVEMENT - OBSERVE WHICH ARM MOVES!")
                print(f"Motor ID {motor_id} will move in small increments")
                print("Please watch both arms carefully...")
                
                input("Press Enter to start the test movement...")
                
                # Small test movements
                initial_pos = position
                test_positions = [position + 10, position - 10, position + 15, position - 15]
                
                for i, target_pos in enumerate(test_positions):
                    print(f"\nMovement {i+1}/4: Moving to {target_pos:.1f}°")
                    dxl_io.set_goal_position({motor_id: target_pos})
                    time.sleep(2.0)
                    
                    actual_pos = dxl_io.get_present_position([motor_id])[0]
                    print(f"Actual position: {actual_pos:.1f}°")
                    
                    # Ask user which arm moved
                    while True:
                        arm_moved = input("Which arm moved? (L)eft, (R)ight, (N)one, (B)oth: ").upper()
                        if arm_moved in ['L', 'R', 'N', 'B']:
                            break
                        print("Please enter L, R, N, or B")
                    
                    if i == 0:  # Store result from first movement
                        if arm_moved == 'L':
                            arm_result = "LEFT ARM"
                        elif arm_moved == 'R':
                            arm_result = "RIGHT ARM"
                        elif arm_moved == 'N':
                            arm_result = "NO MOVEMENT"
                        elif arm_moved == 'B':
                            arm_result = "BOTH ARMS"
                
                # Return to original position
                print(f"\nReturning to original position...")
                dxl_io.set_goal_position({motor_id: initial_pos})
                time.sleep(2.0)
                
                # Record result
                print(f"\n📋 RESULT: Motor ID {motor_id} controls {arm_result}")
                
                # Based on configuration, this should be:
                expected_arm = "LEFT ARM" if motor_id == 2 else "RIGHT ARM"
                expected_name = "l_shoulder_y" if motor_id == 2 else "r_shoulder_y"
                
                print(f"📖 Expected (from config): {expected_name} -> {expected_arm}")
                
                if arm_result == expected_arm:
                    print("✅ Configuration matches reality")
                else:
                    print("❌ Configuration does NOT match reality!")
                    print("    This explains the cross-arm interference!")
                
            except Exception as e:
                print(f"❌ Error testing motor ID {motor_id}: {e}")
                traceback.print_exc()
        
        print(f"\n{'='*60}")
        print("DIAGNOSTIC SUMMARY")
        print(f"{'='*60}")
        print("Based on the test results above:")
        print("1. Note which motor ID controls which arm")
        print("2. Compare with the expected configuration")
        print("3. If they don't match, we need to update the configuration")
        print()
        print("Expected configuration:")
        print("  Motor ID 1 -> r_shoulder_y -> RIGHT ARM")
        print("  Motor ID 2 -> l_shoulder_y -> LEFT ARM")
        
    except Exception as e:
        print(f"✗ Diagnostic failed: {e}")
        traceback.print_exc()
    
    finally:
        try:
            dxl_io.close()
            print("\n✓ Connection closed")
        except:
            pass

if __name__ == "__main__":
    test_shoulder_motor_ids()