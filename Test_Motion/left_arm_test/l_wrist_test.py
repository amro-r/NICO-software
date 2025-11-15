#!/usr/bin/env python3
"""
Simple Left Wrist Test
Tests the left wrist motor using direct DxlIO (only roll available)
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

def test_left_wrist():
    print("=" * 50)
    print("LEFT WRIST TEST")
    print("=" * 50)
    
    # Initialize direct connection
    try:
        dxl_io = DxlIO('/dev/ttyUSB0', baudrate=1000000, timeout=1.0)
        print("✓ Direct connection established")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    try:
        # Test Left Wrist (motor ID 25) - Note: l_wrist_x, not roll
        motor_id = 25
        print(f"\n--- Left Wrist Test ---")
        print(f"Motor ID: {motor_id} (l_wrist_x)")
        
        # Check if motor responds
        try:
            position = dxl_io.get_present_position([motor_id])[0]
            voltage = dxl_io.get_present_voltage([motor_id])[0]
            temp = dxl_io.get_present_temperature([motor_id])[0]
            
            print(f"Current position: {position:.1f}°")
            print(f"Voltage: {voltage:.1f}V")
            print(f"Temperature: {temp}°C")
            
            # Simple movement test (safe range for wrist)
            initial_pos = position
            test_angles = [0, 15, -15, 10]
            
            for i, angle in enumerate(test_angles):
                print(f"Step {i+1}: Moving to {angle}°...")
                dxl_io.set_goal_position({motor_id: angle})
                time.sleep(2.0)
                actual = dxl_io.get_present_position([motor_id])[0]
                error = abs(actual - angle)
                print(f"  Target: {angle}°, Actual: {actual:.1f}°, Error: {error:.1f}°")
                if error < 5:
                    print("  ✓ Good movement")
                else:
                    print("  ⚠️ Position error")
            
            # Return to initial position
            print(f"Returning to initial position ({initial_pos:.1f}°)...")
            dxl_io.set_goal_position({motor_id: initial_pos})
            time.sleep(2.0)
            
            print("\n✅ Left wrist test completed")
            
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
    test_left_wrist()