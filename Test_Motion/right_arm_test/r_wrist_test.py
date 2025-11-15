#!/usr/bin/env python3
"""
Simple Right Wrist Test
Tests the right wrist motor using direct DxlIO
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

def test_right_wrist():
    print("=" * 50)
    print("RIGHT WRIST TEST")
    print("=" * 50)
    
    # Initialize direct connection
    try:
        dxl_io = DxlIO('/dev/ttyUSB0', baudrate=1000000, timeout=1.0)
        print("✓ Direct connection established")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    try:
        # Test Right Wrist Roll (motor ID 23)
        motor_id = 23
        print(f"\n--- Right Wrist Roll Test ---")
        print(f"Motor ID: {motor_id}")
        
        # Check if motor responds
        try:
            position = dxl_io.get_present_position([motor_id])[0]
            voltage = dxl_io.get_present_voltage([motor_id])[0]
            temp = dxl_io.get_present_temperature([motor_id])[0]
            
            print(f"Current position: {position:.1f}°")
            print(f"Voltage: {voltage:.1f}V")
            print(f"Temperature: {temp}°C")
            
            # Simple movement test
            initial_pos = position
            test_angles = [130, 150, 140]
            
            for i, angle in enumerate(test_angles):
                print(f"Step {i+1}: Moving to {angle}°...")
                dxl_io.set_goal_position({motor_id: angle})
                time.sleep(2.0)
                actual = dxl_io.get_present_position([motor_id])[0]
                error = abs(actual - angle)
                print(f"  Target: {angle}°, Actual: {actual:.1f}°, Error: {error:.1f}°")
                if error < 10:
                    print("  ✓ Good movement")
                else:
                    print("  ⚠️ Position error")
            
            # Return to initial position
            print(f"Returning to initial position ({initial_pos:.1f}°)...")
            dxl_io.set_goal_position({motor_id: initial_pos})
            time.sleep(2.0)
            
            print("\n✅ Right wrist test completed")
            
        except Exception as e:
            print(f"✗ Motor {motor_id} communication failed: {e}")
            print("Motor may not be responding properly")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        traceback.print_exc()
    
    finally:
        try:
            dxl_io.close()
            print("✓ Connection closed")
        except:
            pass

if __name__ == "__main__":
    test_right_wrist()