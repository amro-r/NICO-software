#!/usr/bin/env python3
"""
NICO Robot Right Arm Complete Test
Tests all right arm components: shoulder, elbow, wrist, and fingers
"""

import sys
import time
import traceback

# Add the nicomotion library path
sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')

try:
    from nicomotion.Motion import Motion
    from pypot.dynamixel.io import DxlIO
    print("✓ Successfully imported required modules")
except ImportError as e:
    print(f"✗ Failed to import modules: {e}")
    sys.exit(1)

class RightArmTest:
    def __init__(self):
        self.motion = None
        self.dxl_io = None
        self.config_path = "/home/amr/catkin_ws/src/NICO-software/Test_Motion/test_config.json"
        
        # Right arm motor mapping based on NICO configuration
        self.right_arm_motors = {
            # Core arm motors (available via Motion class)
            1: {'name': 'r_shoulder_y', 'description': 'Right Shoulder Pitch', 'type': 'core', 'range': [-180, 179]},
            21: {'name': 'r_shoulder_z', 'description': 'Right Shoulder Roll', 'type': 'core', 'range': [-100, 125]},
            3: {'name': 'r_arm_x', 'description': 'Right Arm Twist', 'type': 'core', 'range': [-140, 75]},
            5: {'name': 'r_elbow_y', 'description': 'Right Elbow Pitch', 'type': 'core', 'range': [-100, 100]},
            
            # Hand motors (available via direct DxlIO)
            23: {'name': 'r_wrist_z', 'description': 'Right Wrist Roll', 'type': 'hand', 'range': [-90, 90]},
            
            # Missing hand motors
            26: {'name': 'r_wrist_x', 'description': 'Right Wrist Pitch', 'type': 'missing', 'range': None},
            28: {'name': 'r_indexfinger_x', 'description': 'Right Index Finger', 'type': 'missing', 'range': None},
            # Note: Assuming middle finger would be a separate motor if present
            30: {'name': 'r_thumb_x', 'description': 'Right Thumb', 'type': 'missing', 'range': None},
            32: {'name': 'r_virtualhand_x', 'description': 'Right Virtual Hand', 'type': 'missing', 'range': None}
        }
        
    def initialize_connections(self):
        """Initialize both Motion class and direct DxlIO connections"""
        print("Initializing robot connections...")
        
        # Initialize Motion class for core motors
        try:
            self.motion = Motion(motorConfig=self.config_path, vrep=False, 
                               ignoreMissing=True, monitorHandCurrents=False)
            print("✓ Motion class connection established")
        except Exception as e:
            print(f"✗ Failed to initialize Motion class: {e}")
            return False
        
        # Initialize DxlIO for hand motors
        try:
            self.dxl_io = DxlIO('/dev/ttyUSB0', baudrate=1000000, timeout=1.0)
            print("✓ Direct DxlIO connection established")
        except Exception as e:
            print(f"✗ Failed to initialize DxlIO: {e}")
            return False
        
        return True
    
    def test_core_motor(self, motor_id, test_angles=None):
        """Test a core arm motor using Motion class"""
        motor_info = self.right_arm_motors[motor_id]
        motor_name = motor_info['name']
        
        print(f"\n--- Testing {motor_info['description']} ({motor_name}) ---")
        
        if test_angles is None:
            # Safe test angles for each motor
            if motor_id == 1:  # shoulder pitch
                test_angles = [0, 30, -30, 0]
            elif motor_id == 21:  # shoulder roll
                test_angles = [0, 30, -30, 0]
            elif motor_id == 3:  # arm twist
                test_angles = [0, 30, -30, 0]
            elif motor_id == 5:  # elbow
                test_angles = [0, 45, -45, 0]
            else:
                test_angles = [0, 15, -15, 0]
        
        try:
            # Get current position
            current_pos = self.motion.getAngle(motor_name)
            print(f"  Current position: {current_pos:.1f}°")
            print(f"  Configured range: {motor_info['range']}")
            
            results = []
            
            for i, target_angle in enumerate(test_angles):
                print(f"  Step {i+1}: Moving to {target_angle}°...")
                
                # Move to target
                self.motion.setAngle(motor_name, target_angle, 0.2)
                time.sleep(2.0)
                
                # Check position
                actual_pos = self.motion.getAngle(motor_name)
                error = abs(actual_pos - target_angle)
                
                print(f"    Target: {target_angle}°, Actual: {actual_pos:.1f}°, Error: {error:.1f}°")
                
                if error > 5:
                    print(f"    ⚠️  Large position error!")
                    results.append('error')
                else:
                    print(f"    ✓ Movement successful")
                    results.append('success')
                
                time.sleep(0.5)
            
            # Analyze results
            success_rate = results.count('success') / len(results) * 100
            print(f"  Success rate: {success_rate:.0f}%")
            
            if success_rate >= 75:
                print(f"  ✅ Motor {motor_id} ({motor_info['description']}) - WORKING")
                return 'working'
            elif success_rate >= 25:
                print(f"  ⚠️ Motor {motor_id} ({motor_info['description']}) - LIMITED")
                return 'limited'
            else:
                print(f"  ❌ Motor {motor_id} ({motor_info['description']}) - FAILED")
                return 'failed'
                
        except Exception as e:
            print(f"  ❌ Motor {motor_id} ({motor_info['description']}) - ERROR: {e}")
            return 'error'
    
    def test_hand_motor(self, motor_id):
        """Test a hand motor using direct DxlIO"""
        motor_info = self.right_arm_motors[motor_id]
        
        print(f"\n--- Testing {motor_info['description']} ---")
        
        try:
            # Check if motor responds
            position = self.dxl_io.get_present_position([motor_id])[0]
            voltage = self.dxl_io.get_present_voltage([motor_id])[0]
            temperature = self.dxl_io.get_present_temperature([motor_id])[0]
            
            print(f"  Current position: {position:.1f}°")
            print(f"  Voltage: {voltage:.1f}V")
            print(f"  Temperature: {temperature}°C")
            
            # Test movement for wrist motor
            if motor_id == 23:  # r_wrist_z
                test_angles = [120, 160, 140]
                initial_pos = position
                
                results = []
                for i, target_angle in enumerate(test_angles):
                    print(f"  Step {i+1}: Moving to {target_angle}°...")
                    
                    self.dxl_io.set_goal_position({motor_id: target_angle})
                    time.sleep(1.5)
                    
                    actual_pos = self.dxl_io.get_present_position([motor_id])[0]
                    error = abs(actual_pos - target_angle)
                    
                    print(f"    Target: {target_angle}°, Actual: {actual_pos:.1f}°, Error: {error:.1f}°")
                    
                    if error > 10:
                        print(f"    ⚠️  Large position error!")
                        results.append('error')
                    else:
                        print(f"    ✓ Movement successful")
                        results.append('success')
                
                # Return to initial position
                self.dxl_io.set_goal_position({motor_id: initial_pos})
                time.sleep(1.5)
                
                success_rate = results.count('success') / len(results) * 100
                print(f"  Success rate: {success_rate:.0f}%")
                
                if success_rate >= 75:
                    print(f"  ✅ Motor {motor_id} ({motor_info['description']}) - WORKING")
                    return 'working'
                else:
                    print(f"  ⚠️ Motor {motor_id} ({motor_info['description']}) - LIMITED")
                    return 'limited'
            
        except Exception as e:
            print(f"  ❌ Motor {motor_id} ({motor_info['description']}) - ERROR: {e}")
            return 'error'
    
    def test_missing_motor(self, motor_id):
        """Test for missing motor"""
        motor_info = self.right_arm_motors[motor_id]
        
        print(f"\n--- Checking {motor_info['description']} ---")
        
        try:
            # Try to ping the motor
            response = self.dxl_io.ping([motor_id])
            if response:
                print(f"  🎉 Motor {motor_id} found! (Unexpected)")
                return self.test_hand_motor(motor_id)
            else:
                print(f"  ❌ Motor {motor_id} not connected (as expected)")
                return 'missing'
                
        except Exception as e:
            print(f"  ❌ Motor {motor_id} not connected: {e}")
            return 'missing'
    
    def run_complete_arm_test(self):
        """Run comprehensive right arm test"""
        print("=" * 60)
        print("NICO RIGHT ARM COMPREHENSIVE TEST")
        print("=" * 60)
        print("Testing: Shoulder, Elbow, Wrist, and Fingers")
        print()
        
        if not self.initialize_connections():
            return False
        
        results = {}
        
        try:
            print("\n" + "="*50)
            print("TESTING CORE ARM MOTORS")
            print("="*50)
            
            # Test core motors
            core_motors = [1, 22, 3, 5]  # shoulder_y, shoulder_z, arm_x, elbow_y
            for motor_id in core_motors:
                results[motor_id] = self.test_core_motor(motor_id)
            
            print("\n" + "="*50)
            print("TESTING HAND MOTORS")
            print("="*50)
            
            # Test available hand motor
            results[23] = self.test_hand_motor(23)  # r_wrist_z
            
            print("\n" + "="*50)
            print("CHECKING MISSING MOTORS")
            print("="*50)
            
            # Check missing motors
            missing_motors = [26, 28, 30, 32]
            for motor_id in missing_motors:
                results[motor_id] = self.test_missing_motor(motor_id)
            
            # Generate report
            self.generate_report(results)
            
            return True
            
        except Exception as e:
            print(f"\n❌ Right arm test failed: {e}")
            traceback.print_exc()
            return False
        
        finally:
            self.shutdown()
    
    def generate_report(self, results):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("RIGHT ARM TEST REPORT")
        print("="*60)
        
        # Categorize results
        working = []
        limited = []
        failed = []
        missing = []
        error = []
        
        for motor_id, status in results.items():
            motor_info = self.right_arm_motors[motor_id]
            motor_entry = (motor_id, motor_info['description'])
            
            if status == 'working':
                working.append(motor_entry)
            elif status == 'limited':
                limited.append(motor_entry)
            elif status == 'failed':
                failed.append(motor_entry)
            elif status == 'missing':
                missing.append(motor_entry)
            elif status == 'error':
                error.append(motor_entry)
        
        print(f"\n✅ WORKING MOTORS ({len(working)}):")
        for motor_id, description in working:
            print(f"  ID {motor_id:2d}: {description}")
        
        print(f"\n⚠️ LIMITED FUNCTION MOTORS ({len(limited)}):")
        for motor_id, description in limited:
            print(f"  ID {motor_id:2d}: {description}")
        
        print(f"\n❌ FAILED MOTORS ({len(failed)}):")
        for motor_id, description in failed:
            print(f"  ID {motor_id:2d}: {description}")
        
        print(f"\n🔌 MISSING MOTORS ({len(missing)}):")
        for motor_id, description in missing:
            print(f"  ID {motor_id:2d}: {description}")
        
        print(f"\n⚡ ERROR MOTORS ({len(error)}):")
        for motor_id, description in error:
            print(f"  ID {motor_id:2d}: {description}")
        
        # Calculate arm functionality
        total_expected = len([m for m in self.right_arm_motors.keys() if self.right_arm_motors[m]['type'] != 'missing'])
        functional = len(working) + len(limited)
        functionality_rate = functional / total_expected * 100 if total_expected > 0 else 0
        
        print(f"\nRIGHT ARM FUNCTIONALITY: {functionality_rate:.0f}%")
        print(f"Functional motors: {functional}/{total_expected}")
        
        # Specific capabilities
        print(f"\nRIGHT ARM CAPABILITIES:")
        print(f"  Shoulder movement: {'✅' if 1 in [m[0] for m in working] and 22 in [m[0] for m in working] else '❌'}")
        print(f"  Elbow movement: {'✅' if 5 in [m[0] for m in working] else '❌'}")
        print(f"  Arm twist: {'✅' if 3 in [m[0] for m in working] else '❌'}")
        print(f"  Wrist roll: {'✅' if 23 in [m[0] for m in working] else '❌'}")
        print(f"  Wrist pitch: {'❌ Missing hardware'}")
        print(f"  Finger control: {'❌ Missing hardware'}")
        print(f"  Grasping capability: {'❌ No fingers available'}")
    
    def shutdown(self):
        """Safely shutdown connections"""
        print("\nShutting down connections...")
        try:
            if self.motion:
                # Disable torque on right arm motors
                arm_motors = ['r_shoulder_y', 'r_shoulder_z', 'r_arm_x', 'r_elbow_y']
                for motor in arm_motors:
                    try:
                        self.motion.disableTorque(motor)
                    except:
                        pass
            
            if self.dxl_io:
                self.dxl_io.close()
            
            print("✓ Connections closed safely")
        except Exception as e:
            print(f"Warning during shutdown: {e}")

def main():
    test = RightArmTest()
    
    try:
        success = test.run_complete_arm_test()
        if success:
            print("\n🎉 Right arm test completed!")
        else:
            print("\n❌ Right arm test failed")
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()
    finally:
        test.shutdown()

if __name__ == "__main__":
    main()
