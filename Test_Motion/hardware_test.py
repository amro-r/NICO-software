#!/usr/bin/env python3
"""
NICO Robot Hardware Test Script
Direct hardware testing without ROS using nicomotion library
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
    print("Make sure you're running this from the ~/.NICO-python3/ virtual environment")
    sys.exit(1)

class NicoHardwareTest:
    def __init__(self):
        self.motion = None
        self.config_path = "/home/amr/catkin_ws/src/NICO-software/json/nico_humanoid_upper_with_hands.json"
        
    def initialize_robot(self):
        """Initialize connection to the robot hardware"""
        print("Initializing robot connection...")
        try:
            # Initialize Motion class with hardware config (vrep=False for direct hardware)
            # ignoreMissing=True allows the robot to work with missing motors
            self.motion = Motion(motorConfig=self.config_path, vrep=False, ignoreMissing=True)
            print("✓ Robot connection established successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to initialize robot: {e}")
            print("Check that:")
            print("  - Robot is powered on")
            print("  - USB cable is connected")
            print("  - No other programs are using the robot")
            return False
    
    def test_joint_movement(self, joint_name, angles, joint_description):
        """Test a specific joint with given angles"""
        print(f"\n--- Testing {joint_description} ({joint_name}) ---")
        
        try:
            # Get current position
            current_pos = self.motion.getAngle(joint_name)
            print(f"Current position: {current_pos:.1f}°")
            
            # Test each angle
            for i, angle in enumerate(angles):
                print(f"Moving to {angle}°...")
                self.motion.setAngle(joint_name, angle, 0.3)  # 30% speed
                time.sleep(2.0)  # Wait for movement to complete
                
                # Verify position
                actual_pos = self.motion.getAngle(joint_name)
                print(f"  Target: {angle}°, Actual: {actual_pos:.1f}°")
                
                # Check if movement was successful (within 5 degrees tolerance)
                if abs(actual_pos - angle) > 5:
                    print(f"  ⚠️  Large position error detected!")
                else:
                    print(f"  ✓ Movement successful")
            
            # Return to starting position
            print("Returning to center...")
            self.motion.setAngle(joint_name, 0.0, 0.3)
            time.sleep(2.0)
            
            print(f"✓ {joint_description} test completed")
            
        except Exception as e:
            print(f"✗ Error testing {joint_description}: {e}")
            traceback.print_exc()
    
    def run_hardware_tests(self):
        """Run comprehensive hardware tests"""
        print("=" * 60)
        print("NICO ROBOT HARDWARE TEST")
        print("=" * 60)
        print("This script will test the robot's head and arm motors")
        print("Make sure the robot has clear space to move!")
        print()
        
        # Auto-start in non-interactive mode
        print("Starting automated hardware test...")
        
        if not self.initialize_robot():
            return False
        
        try:
            # Test Head Motors
            print("\n" + "="*50)
            print("TESTING HEAD MOTORS")
            print("="*50)
            
            # Head Yaw (head_z) - left/right rotation
            self.test_joint_movement("head_z", [-45, 45, 0], "Head Yaw (Left/Right)")
            
            # Head Pitch (head_y) - up/down movement  
            self.test_joint_movement("head_y", [30, -30, 0], "Head Pitch (Up/Down)")
            
            # Test Right Arm Motors
            print("\n" + "="*50)
            print("TESTING RIGHT ARM MOTORS")
            print("="*50)
            
            # Right Shoulder Pitch (r_shoulder_y) - forward/backward
            self.test_joint_movement("r_shoulder_y", [45, -45, 0], "Right Shoulder Pitch")
            
            # Right Shoulder Roll (r_shoulder_z) - up/down
            self.test_joint_movement("r_shoulder_z", [60, -60, 0], "Right Shoulder Roll")
            
            # Right Elbow (r_elbow_y) - bend/straighten
            self.test_joint_movement("r_elbow_y", [60, -60, 0], "Right Elbow")
            
            # Test Left Arm Motors
            print("\n" + "="*50)
            print("TESTING LEFT ARM MOTORS")
            print("="*50)
            
            # Left Shoulder Pitch (l_shoulder_y) - forward/backward
            self.test_joint_movement("l_shoulder_y", [45, -45, 0], "Left Shoulder Pitch")
            
            # Left Shoulder Roll (l_shoulder_z) - up/down
            self.test_joint_movement("l_shoulder_z", [60, -60, 0], "Left Shoulder Roll")
            
            # Left Elbow (l_elbow_y) - bend/straighten
            self.test_joint_movement("l_elbow_y", [60, -60, 0], "Left Elbow")
            
            # Test Basic Hand Movement (if available)
            print("\n" + "="*50)
            print("TESTING BASIC HAND MOVEMENT")
            print("="*50)
            
            try:
                # Test right wrist (available)
                self.test_joint_movement("r_wrist_z", [30, -30, 0], "Right Wrist Rotation")
                
                # Test left wrist (available)
                self.test_joint_movement("l_wrist_x", [30, -30, 0], "Left Wrist Rotation")
                
                # Test available finger motors
                self.test_joint_movement("l_indexfingers_x", [60, -60, 0], "Left Index Finger")
                self.test_joint_movement("l_thumb_x", [60, -60, 0], "Left Thumb")
                
            except Exception as e:
                print(f"Hand testing skipped: {e}")
            
            print("\n" + "="*60)
            print("HARDWARE TEST COMPLETED SUCCESSFULLY")
            print("="*60)
            print("If you noticed any unusual movements, sounds, or errors,")
            print("please check the hardware connections and motor health.")
            
            return True
            
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            return False
        except Exception as e:
            print(f"\n✗ Hardware test failed: {e}")
            traceback.print_exc()
            return False
    
    def shutdown(self):
        """Safely shutdown the robot connection"""
        print("\nShutting down robot connection...")
        try:
            if self.motion:
                # Disable torque on all motors to prevent overheating
                joints = ["head_z", "head_y", "r_shoulder_y", "r_shoulder_z", 
                         "r_elbow_y", "l_shoulder_y", "l_shoulder_z", "l_elbow_y",
                         "r_wrist_z", "l_wrist_x", "l_indexfingers_x", "l_thumb_x",
                         "l_arm_x", "r_arm_x", "l_virtualhand_x"]
                
                for joint in joints:
                    try:
                        self.motion.disableTorque(joint)
                    except:
                        pass  # Ignore errors during shutdown
                
                print("✓ Robot connection closed safely")
        except Exception as e:
            print(f"Warning during shutdown: {e}")

def main():
    test = NicoHardwareTest()
    
    try:
        success = test.run_hardware_tests()
        if success:
            print("\n🎉 All hardware tests completed!")
        else:
            print("\n❌ Hardware tests failed or incomplete")
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()
    finally:
        test.shutdown()

if __name__ == "__main__":
    main()