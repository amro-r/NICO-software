#!/usr/bin/env python3
"""
Simple Left Fingers Test
Tests the left hand: index finger, middle finger, and thumb
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

def test_left_fingers():
    print("=" * 50)
    print("LEFT FINGERS TEST")
    print("=" * 50)
    print("Testing: Index Finger, Middle Finger, Thumb")
    
    # Initialize direct connection
    try:
        dxl_io = DxlIO('/dev/ttyUSB0', baudrate=1000000, timeout=1.0)
        print("✓ Direct connection established")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    # Left hand finger motor IDs (3 fingers only)
    finger_motors = {
        27: "Left Index Finger", 
        # Middle finger motor ID needs to be determined - might be grouped with index
        29: "Left Thumb"
    }
    
    # Check if there's a separate middle finger motor or if it's grouped
    potential_middle_finger_ids = [28, 31]  # Check these IDs for middle finger
    
    try:
        print("\n--- Testing Left Hand Fingers ---")
        
        working_motors = []
        error_motors = []
        
        # Test known finger motors
        for motor_id, description in finger_motors.items():
            print(f"\n--- {description} (ID: {motor_id}) ---")
            try:
                # Get motor status
                position = dxl_io.get_present_position([motor_id])[0]
                voltage = dxl_io.get_present_voltage([motor_id])[0] 
                temp = dxl_io.get_present_temperature([motor_id])[0]
                
                print(f"  Position: {position:.1f}°")
                print(f"  Voltage: {voltage:.1f}V")
                print(f"  Temperature: {temp}°C")
                
                # Test movement (safe angles for finger motors)
                initial_pos = position
                if motor_id == 27:  # index finger
                    test_angles = [-100, -120, -110]
                elif motor_id == 29:  # thumb
                    test_angles = [-100, -120, -110]
                
                print(f"  Testing movement...")
                for angle in test_angles:
                    dxl_io.set_goal_position({motor_id: angle})
                    time.sleep(1.5)
                    actual = dxl_io.get_present_position([motor_id])[0]
                    error = abs(actual - angle)
                    print(f"    Target: {angle}°, Actual: {actual:.1f}°, Error: {error:.1f}°")
                
                # Return to initial position
                dxl_io.set_goal_position({motor_id: initial_pos})
                time.sleep(1.5)
                
                working_motors.append((motor_id, description))
                print(f"  ✅ {description} working")
                        
            except Exception as e:
                print(f"  ❌ {description} error: {e}")
                error_motors.append((motor_id, description))
        
        # Check for middle finger motor
        print(f"\n--- Searching for Middle Finger ---")
        middle_finger_found = False
        for potential_id in potential_middle_finger_ids:
            print(f"Checking ID {potential_id} for middle finger...")
            try:
                response = dxl_io.ping([potential_id])
                if response:
                    position = dxl_io.get_present_position([potential_id])[0]
                    print(f"  🎉 Found motor at ID {potential_id}!")
                    print(f"    Position: {position:.1f}°")
                    working_motors.append((potential_id, "Left Middle Finger"))
                    middle_finger_found = True
                    break
                else:
                    print(f"  ❌ No motor at ID {potential_id}")
            except Exception as e:
                print(f"  ❌ No motor at ID {potential_id}: {e}")
        
        if not middle_finger_found:
            print("  ❓ Middle finger motor not found - may be grouped with index finger")
        
        # Summary
        print("\n" + "="*50)
        print("LEFT HAND FINGERS SUMMARY")
        print("="*50)
        
        if working_motors:
            print(f"\n✅ WORKING FINGERS ({len(working_motors)}):")
            for motor_id, description in working_motors:
                print(f"  ID {motor_id}: {description}")
        
        if error_motors:
            print(f"\n❌ ERROR FINGERS ({len(error_motors)}):")
            for motor_id, description in error_motors:
                print(f"  ID {motor_id}: {description}")
        
        # Grasping capability assessment
        has_index = any("Index" in desc for _, desc in working_motors)
        has_thumb = any("Thumb" in desc for _, desc in working_motors)
        has_middle = any("Middle" in desc for _, desc in working_motors)
        
        print(f"\nFINGER AVAILABILITY:")
        print(f"  Index Finger: {'✅' if has_index else '❌'}")
        print(f"  Middle Finger: {'✅' if has_middle else '❓ Unknown/Grouped'}")
        print(f"  Thumb: {'✅' if has_thumb else '❌'}")
        
        grasping_available = has_index and has_thumb
        print(f"\nGRASPING CAPABILITY: {'✅ Basic grasping possible' if grasping_available else '❌ Insufficient for grasping'}")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        traceback.print_exc()
    
    finally:
        try:
            dxl_io.close()
            print("\n✓ Connection closed")
        except:
            pass

if __name__ == "__main__":
    test_left_fingers()