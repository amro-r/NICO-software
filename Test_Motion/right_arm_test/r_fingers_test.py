#!/usr/bin/env python3
"""
Simple Right Fingers Test
Checks for right hand finger motors
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

def test_right_fingers():
    print("=" * 50)
    print("RIGHT FINGERS TEST")
    print("=" * 50)
    
    # Initialize direct connection
    try:
        dxl_io = DxlIO('/dev/ttyUSB0', baudrate=1000000, timeout=1.0)
        print("✓ Direct connection established")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    # Right hand finger motor IDs (corrected - no wrist pitch)
    finger_motors = {
        28: "Right Index Finger", 
        30: "Right Thumb",
        32: "Right Virtual Hand"
    }
    
    try:
        print("\n--- Checking Right Hand Motors ---")
        
        found_motors = []
        missing_motors = []
        
        for motor_id, description in finger_motors.items():
            print(f"\nChecking {description} (ID: {motor_id})...")
            try:
                # Try to ping the motor
                response = dxl_io.ping([motor_id])
                if response and len(response) > 0:
                    print(f"  🎉 Motor {motor_id} found!")
                    
                    # Try to get basic info
                    try:
                        position = dxl_io.get_present_position([motor_id])[0]
                        voltage = dxl_io.get_present_voltage([motor_id])[0] 
                        temp = dxl_io.get_present_temperature([motor_id])[0]
                        
                        print(f"    Position: {position:.1f}°")
                        print(f"    Voltage: {voltage:.1f}V")
                        print(f"    Temperature: {temp}°C")
                        
                        found_motors.append((motor_id, description))
                        
                    except Exception as e:
                        print(f"    ⚠️ Found but communication error: {e}")
                        found_motors.append((motor_id, f"{description} (comm error)"))
                        
                else:
                    print(f"  ❌ Motor {motor_id} not found")
                    missing_motors.append((motor_id, description))
                    
            except Exception as e:
                print(f"  ❌ Motor {motor_id} not found: {e}")
                missing_motors.append((motor_id, description))
        
        # Summary
        print("\n" + "="*50)
        print("RIGHT HAND SUMMARY")
        print("="*50)
        
        if found_motors:
            print(f"\n✅ FOUND MOTORS ({len(found_motors)}):")
            for motor_id, description in found_motors:
                print(f"  ID {motor_id}: {description}")
        else:
            print(f"\n❌ NO MOTORS FOUND")
        
        if missing_motors:
            print(f"\n🔌 MISSING MOTORS ({len(missing_motors)}):")
            for motor_id, description in missing_motors:
                print(f"  ID {motor_id}: {description}")
        
        print(f"\nRIGHT HAND STATUS: {'✅ Functional' if found_motors else '❌ No finger control available'}")
        
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
    test_right_fingers()