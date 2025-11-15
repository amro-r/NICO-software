#!/usr/bin/env python3
"""
Direct Hand Motor Test using discovered configuration
Tests the 5 hand motors found on /dev/ttyUSB0
"""

import sys
import time
import traceback

# Add the nicomotion library path
sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')

try:
    from pypot.dynamixel.io import DxlIO
    print("✓ Successfully imported DxlIO")
except ImportError as e:
    print(f"✗ Failed to import DxlIO: {e}")
    sys.exit(1)

class DirectHandTest:
    def __init__(self):
        self.dxl_io = None
        self.port = '/dev/ttyUSB0'
        self.baudrate = 1000000
        
        # Hand motors found by port scanner
        self.hand_motors = {
            23: {'name': 'r_wrist_z', 'description': 'Right Wrist Rotation', 'type': 'SR-SEED56'},
            25: {'name': 'l_wrist_x', 'description': 'Left Wrist Bend', 'type': 'SR-SEED56'},
            27: {'name': 'l_indexfingers_x', 'description': 'Left Index Finger', 'type': 'SR-SEED56'},
            29: {'name': 'l_thumb_x', 'description': 'Left Thumb', 'type': 'SR-SEED56'},
            31: {'name': 'l_virtualhand_x', 'description': 'Left Virtual Hand', 'type': 'SR-EROSBRD'}
        }
    
    def connect(self):
        """Connect to the robot motors"""
        print("Connecting to hand motors...")
        try:
            self.dxl_io = DxlIO(self.port, baudrate=self.baudrate, timeout=1.0)
            print(f"✓ Connected to {self.port} at {self.baudrate} baud")
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False
    
    def test_motor_basic_info(self, motor_id):
        """Get basic motor information"""
        motor_info = self.hand_motors[motor_id]
        print(f"\n--- Testing {motor_info['description']} (ID: {motor_id}) ---")
        
        try:
            # Get current status
            position = self.dxl_io.get_present_position([motor_id])[0]
            voltage = self.dxl_io.get_present_voltage([motor_id])[0]
            temperature = self.dxl_io.get_present_temperature([motor_id])[0]
            
            print(f"  Type: {motor_info['type']}")
            print(f"  Current position: {position:.1f}°")
            print(f"  Voltage: {voltage:.1f}V")
            print(f"  Temperature: {temperature}°C")
            
            # Check if motor is moving
            moving = self.dxl_io.is_moving([motor_id])[0]
            print(f"  Currently moving: {moving}")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Failed to read motor info: {e}")
            return False
    
    def test_motor_movement(self, motor_id, test_angles=None):
        """Test motor movement with safe angles"""
        motor_info = self.hand_motors[motor_id]
        
        # Define safe test angles for each motor type
        if test_angles is None:
            if motor_id == 23:  # r_wrist_z
                test_angles = [120, 160, 140]  # Safe range for wrist rotation
            elif motor_id == 25:  # l_wrist_x  
                test_angles = [0, 20, 10]  # Safe range for wrist bend
            elif motor_id in [27, 29]:  # finger motors
                test_angles = [-120, -80, -100]  # Safe finger movement
            elif motor_id == 31:  # l_virtualhand_x
                test_angles = [-160, -120, -140]  # Safe virtual hand movement
            else:
                test_angles = [0, 10, 5]  # Conservative default
        
        print(f"\n  Testing movement with angles: {test_angles}")
        
        try:
            # Get initial position
            initial_pos = self.dxl_io.get_present_position([motor_id])[0]
            print(f"  Initial position: {initial_pos:.1f}°")
            
            # Test each angle
            for i, target_angle in enumerate(test_angles):
                print(f"  Step {i+1}: Moving to {target_angle}°...")
                
                # Set target position
                self.dxl_io.set_goal_position({motor_id: target_angle})
                
                # Wait for movement to complete
                time.sleep(1.5)
                
                # Check final position
                actual_pos = self.dxl_io.get_present_position([motor_id])[0]
                error = abs(actual_pos - target_angle)
                
                print(f"    Target: {target_angle}°, Actual: {actual_pos:.1f}°, Error: {error:.1f}°")
                
                if error > 10:
                    print(f"    ⚠️  Large position error!")
                else:
                    print(f"    ✓ Movement successful")
            
            # Return to initial position
            print(f"  Returning to initial position ({initial_pos:.1f}°)...")
            self.dxl_io.set_goal_position({motor_id: initial_pos})
            time.sleep(1.5)
            
            return True
            
        except Exception as e:
            print(f"  ✗ Movement test failed: {e}")
            return False
    
    def run_hand_tests(self):
        """Run comprehensive hand motor tests"""
        print("=" * 60)
        print("DIRECT HAND MOTOR TEST")
        print("=" * 60)
        print("Testing 5 hand motors found on /dev/ttyUSB0")
        print()
        
        if not self.connect():
            return False
        
        working_motors = []
        failed_motors = []
        
        try:
            for motor_id in sorted(self.hand_motors.keys()):
                motor_info = self.hand_motors[motor_id]
                
                print(f"\n{'='*50}")
                print(f"TESTING MOTOR {motor_id}: {motor_info['description']}")
                print(f"{'='*50}")
                
                # Test basic info
                if self.test_motor_basic_info(motor_id):
                    # Test movement
                    if self.test_motor_movement(motor_id):
                        working_motors.append(motor_id)
                        print(f"✓ Motor {motor_id} ({motor_info['description']}) - WORKING")
                    else:
                        failed_motors.append(motor_id)
                        print(f"✗ Motor {motor_id} ({motor_info['description']}) - MOVEMENT FAILED")
                else:
                    failed_motors.append(motor_id)
                    print(f"✗ Motor {motor_id} ({motor_info['description']}) - INFO READ FAILED")
            
            # Summary
            print("\n" + "=" * 60)
            print("HAND MOTOR TEST SUMMARY")
            print("=" * 60)
            
            print(f"\n✓ WORKING HAND MOTORS ({len(working_motors)}/5):")
            for motor_id in working_motors:
                motor_info = self.hand_motors[motor_id]
                print(f"  ID {motor_id}: {motor_info['description']} ({motor_info['name']})")
            
            print(f"\n✗ FAILED HAND MOTORS ({len(failed_motors)}/5):")
            for motor_id in failed_motors:
                motor_info = self.hand_motors[motor_id]
                print(f"  ID {motor_id}: {motor_info['description']} ({motor_info['name']})")
            
            success_rate = len(working_motors) / len(self.hand_motors) * 100
            print(f"\nSuccess rate: {success_rate:.0f}%")
            
            return len(working_motors) > 0
            
        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            traceback.print_exc()
            return False
        
        finally:
            self.disconnect()
    
    def disconnect(self):
        """Safely disconnect from motors"""
        print("\nDisconnecting from motors...")
        try:
            if self.dxl_io:
                self.dxl_io.close()
                print("✓ Disconnected safely")
        except Exception as e:
            print(f"Warning during disconnect: {e}")

def main():
    test = DirectHandTest()
    
    try:
        success = test.run_hand_tests()
        if success:
            print("\n🎉 Hand motor testing completed!")
        else:
            print("\n❌ Hand motor testing failed")
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()
    finally:
        test.disconnect()

if __name__ == "__main__":
    main()