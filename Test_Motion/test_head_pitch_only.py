#!/usr/bin/env python3
"""
NICO Robot Head Pitch Only Test
Tests only the head_y motor (ID 20) for pitch movement
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
    sys.exit(1)

class HeadPitchTest:
    def __init__(self):
        self.motion = None
        self.config_path = "/home/amr/catkin_ws/src/NICO-software/Test_Motion/test_config.json"
        
    def initialize_robot(self):
        """Initialize connection to the robot hardware"""
        print("Initializing robot connection...")
        try:
            self.motion = Motion(motorConfig=self.config_path, vrep=False, 
                               ignoreMissing=True, monitorHandCurrents=False)
            print("✓ Robot connection established successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to initialize robot: {e}")
            return False
    
    def test_head_pitch(self):
        """Test head pitch motor with comprehensive movement sequence"""
        print("\n" + "="*50)
        print("HEAD PITCH (UP/DOWN) MOVEMENT TEST")
        print("="*50)
        print("Motor: head_y (ID: 20)")
        print("Range: -89° to +79° (down to up)")
        print()
        
        try:
            # Get current position
            current_pos = self.motion.getAngle("head_y")
            print(f"Current head pitch position: {current_pos:.1f}°")
            
            # Test sequence: center -> up -> down -> center
            test_sequence = [
                (0, "Center position"),
                (30, "Look up"),
                (-30, "Look down"), 
                (15, "Slight up"),
                (-15, "Slight down"),
                (0, "Return to center")
            ]
            
            print(f"\nStarting movement sequence...")
            print("(Positive angles = look up, Negative angles = look down)")
            
            for i, (target_angle, description) in enumerate(test_sequence):
                print(f"\nStep {i+1}: {description} ({target_angle}°)")
                
                # Move to target position
                print(f"  Moving to {target_angle}°...")
                self.motion.setAngle("head_y", target_angle, 0.2)  # 20% speed for smooth movement
                
                # Wait for movement to complete
                time.sleep(2.0)
                
                # Check actual position
                actual_pos = self.motion.getAngle("head_y")
                error = abs(actual_pos - target_angle)
                
                print(f"  Target: {target_angle}°, Actual: {actual_pos:.1f}°, Error: {error:.1f}°")
                
                if error > 5:
                    print(f"  ⚠️  Large position error detected!")
                else:
                    print(f"  ✓ Movement successful")
                
                # Brief pause between movements
                time.sleep(0.5)
            
            # Test extreme positions (within safe limits)
            print(f"\n--- Testing Range Limits ---")
            
            # Test upper limit
            print("Testing upper limit (60°)...")
            self.motion.setAngle("head_y", 60, 0.15)
            time.sleep(2.5)
            actual_pos = self.motion.getAngle("head_y")
            print(f"  Upper limit test: Target 60°, Actual: {actual_pos:.1f}°")
            
            # Test lower limit  
            print("Testing lower limit (-60°)...")
            self.motion.setAngle("head_y", -60, 0.15)
            time.sleep(2.5)
            actual_pos = self.motion.getAngle("head_y")
            print(f"  Lower limit test: Target -60°, Actual: {actual_pos:.1f}°")
            
            # Return to center
            print("Returning to center...")
            self.motion.setAngle("head_y", 0, 0.2)
            time.sleep(2.0)
            final_pos = self.motion.getAngle("head_y")
            print(f"  Final position: {final_pos:.1f}°")
            
            print(f"\n✓ Head pitch test completed successfully")
            return True
            
        except Exception as e:
            print(f"\n✗ Head pitch test failed: {e}")
            traceback.print_exc()
            return False
    
    def shutdown(self):
        """Safely shutdown the robot connection"""
        print("\nShutting down robot connection...")
        try:
            if self.motion:
                # Disable torque on head pitch motor
                self.motion.disableTorque("head_y")
                print("✓ Head pitch motor torque disabled")
                print("✓ Robot connection closed safely")
        except Exception as e:
            print(f"Warning during shutdown: {e}")

def main():
    test = HeadPitchTest()
    
    try:
        print("=" * 60)
        print("NICO ROBOT HEAD PITCH ONLY TEST")
        print("=" * 60)
        print("This test will move only the head pitch motor (up/down)")
        print("Make sure the robot head has clear space to move!")
        print()
        
        if test.initialize_robot():
            success = test.test_head_pitch()
            if success:
                print("\n🎉 Head pitch test completed successfully!")
            else:
                print("\n❌ Head pitch test failed")
        else:
            print("\n❌ Failed to initialize robot")
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()
    finally:
        test.shutdown()

if __name__ == "__main__":
    main()