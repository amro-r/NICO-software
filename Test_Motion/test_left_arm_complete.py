#!/usr/bin/env python3
"""
NICO Robot Left Arm Complete Test
Tests all left arm components: shoulder, elbow, wrist, and fingers
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

class LeftArmTest:
    def __init__(self):
        self.motion = None
        self.dxl_io = None
        self.config_path = "/home/amr/catkin_ws/src/NICO-software/Test_Motion/test_config.json"
        
        # Left arm motor mapping based on NICO configuration
        self.left_arm_motors = {
            # Core arm motors (available via Motion class)
            2: {'name': 'l_shoulder_y', 'description': 'Left Shoulder Pitch', 'type': 'core', 'range': [-179, 180]},
            21: {'name': 'l_shoulder_z', 'description': 'Left Shoulder Roll', 'type': 'core', 'range': [-125, 100]},
            4: {'name': 'l_arm_x', 'description': 'Left Arm Twist', 'type': 'core', 'range': [-75, 140]},
            6: {'name': 'l_elbow_y', 'description': 'Left Elbow Pitch', 'type': 'core', 'range': [-100, 100]},
            
            # Hand motors (available via direct DxlIO)
            25: {'name': 'l_wrist_x', 'description': 'Left Wrist Pitch', 'type': 'hand', 'range': [-35, 50]},
            27: {'name': 'l_indexfinger_x', 'description': 'Left Index Finger', 'type': 'hand', 'range': [-160, 160]},
            # Assuming middle finger is grouped with index or separate
            29: {'name': 'l_thumb_x', 'description': 'Left Thumb', 'type': 'hand', 'range': [-160, 160]},
            31: {'name': 'l_virtualhand_x', 'description': 'Left Virtual Hand', 'type': 'hand', 'range': [-160, 160]},
            
            # Missing hand motor
            24: {'name': 'l_wrist_z', 'description': 'Left Wrist Roll', 'type': 'missing', 'range': None}
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
        motor_info = self.left_arm_motors[motor_id]
        motor_name = motor_info['name']
        
        print(f"\n--- Testing {motor_info['description']} ({motor_name}) ---")
        
        if test_angles is None:
            # Safe test angles for each motor
            if motor_id == 2:  # shoulder pitch
                test_angles = [0, 30, -30, 0]
            elif motor_id == 21:  # shoulder roll
                test_angles = [0, 30, -30, 0]
            elif motor_id == 4:  # arm twist
                test_angles = [0, 30, -30, 0]
            elif motor_id == 6:  # elbow
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
        motor_info = self.left_arm_motors[motor_id]
        
        print(f"\n--- Testing {motor_info['description']} ---")
        
        try:
            # Check if motor responds
            position = self.dxl_io.get_present_position([motor_id])[0]
            voltage = self.dxl_io.get_present_voltage([motor_id])[0]
            temperature = self.dxl_io.get_present_temperature([motor_id])[0]
            
            print(f"  Current position: {position:.1f}°")
            print(f"  Voltage: {voltage:.1f}V")
            print(f"  Temperature: {temperature}°C")
            
            # Define test angles based on motor type
            if motor_id == 25:  # l_wrist_x
                test_angles = [0, 20, -20, 10]
                initial_pos = position
            elif motor_id in [27, 29]:  # finger motors
                test_angles = [-120, -80, -140, -100]
                initial_pos = position
            elif motor_id == 31:  # virtual hand
                test_angles = [-160, -120, -180, -140]
                initial_pos = position
            else:
                test_angles = [position + 10, position - 10, position]
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
            elif success_rate >= 25:
                print(f"  ⚠️ Motor {motor_id} ({motor_info['description']}) - LIMITED")
                return 'limited'
            else:
                print(f"  ❌ Motor {motor_id} ({motor_info['description']}) - FAILED")
                return 'failed'
            
        except Exception as e:
            print(f"  ❌ Motor {motor_id} ({motor_info['description']}) - ERROR: {e}")
            return 'error'
    
    def test_missing_motor(self, motor_id):
        """Test for missing motor"""
        motor_info = self.left_arm_motors[motor_id]
        
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
        """Run comprehensive left arm test"""
        print("=" * 60)
        print("NICO LEFT ARM COMPREHENSIVE TEST")
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
            core_motors = [2, 21, 4, 6]  # shoulder_y, shoulder_z, arm_x, elbow_y
            for motor_id in core_motors:
                results[motor_id] = self.test_core_motor(motor_id)
            
            print("\n" + "="*50)
            print("TESTING HAND MOTORS")
            print("="*50)
            
            # Test available hand motors
            hand_motors = [25, 27, 29, 31]  # wrist_x, index, thumb, virtual
            for motor_id in hand_motors:
                results[motor_id] = self.test_hand_motor(motor_id)
            
            print("\n" + "="*50)
            print("CHECKING MISSING MOTORS")
            print("="*50)
            
            # Check missing motor
            results[24] = self.test_missing_motor(24)  # l_wrist_z
            
            # Generate report
            self.generate_report(results)
            
            return True
            
        except Exception as e:
            print(f"\n❌ Left arm test failed: {e}")
            traceback.print_exc()
            return False
        
        finally:
            self.shutdown()
    
    def generate_report(self, results):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("LEFT ARM TEST REPORT")
        print("="*60)
        
        # Categorize results
        working = []
        limited = []
        failed = []
        missing = []
        error = []
        
        for motor_id, status in results.items():
            motor_info = self.left_arm_motors[motor_id]
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
        total_expected = len([m for m in self.left_arm_motors.keys() if self.left_arm_motors[m]['type'] != 'missing'])
        functional = len(working) + len(limited)
        functionality_rate = functional / total_expected * 100 if total_expected > 0 else 0
        
        print(f"\nLEFT ARM FUNCTIONALITY: {functionality_rate:.0f}%")
        print(f"Functional motors: {functional}/{total_expected}")
        
        # Specific capabilities
        print(f"\nLEFT ARM CAPABILITIES:")
        print(f"  Shoulder movement: {'✅' if 2 in [m[0] for m in working] and 21 in [m[0] for m in working] else '❌'}")
        print(f"  Elbow movement: {'✅' if 6 in [m[0] for m in working] else '❌'}")
        print(f"  Arm twist: {'✅' if 4 in [m[0] for m in working] else '❌'}")
        print(f"  Wrist pitch: {'✅' if 25 in [m[0] for m in working] else '❌'}")
        print(f"  Wrist roll: {'❌ Missing hardware' if 24 in [m[0] for m in missing] else '❌'}")
        print(f"  Index finger: {'✅' if 27 in [m[0] for m in working] else '❌'}")
        print(f"  Thumb: {'✅' if 29 in [m[0] for m in working] else '❌'}")
        print(f"  Grasping capability: {'✅ Basic grasping available' if 27 in [m[0] for m in working] and 29 in [m[0] for m in working] else '❌'}")
    
    def shutdown(self):
        """Safely shutdown connections"""
        print("\nShutting down connections...")
        try:
            if self.motion:
                # Disable torque on left arm motors
                arm_motors = ['l_shoulder_y', 'l_shoulder_z', 'l_arm_x', 'l_elbow_y']
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
    test = LeftArmTest()
    
    try:
        success = test.run_complete_arm_test()
        if success:
            print("\n🎉 Left arm test completed!")
        else:
            print("\n❌ Left arm test failed")
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()
    finally:
        test.shutdown()

if __name__ == "__main__":
    main()