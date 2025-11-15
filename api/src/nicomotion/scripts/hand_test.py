
import time
import pypot.robot
from nicomotion._nicomotion_internal.RH7D_hand import RH7DHand

# Connect to the robot
robot = pypot.robot.from_config({
    'controllers': {
        'my_dxl_controller': {
            'port': '/dev/ttyACM0',
            'sync_read': False,
            'protocol': 2,
            'models': {
                'left_hand': 'RH-7D',
            }
        }
    }
})

# Initialize the left hand
left_hand = RH7DHand(robot, isLeft=True)

# Test the hand
print("Opening hand...")
left_hand.openHand(1.0, 1.0)
time.sleep(2)

print("Closing hand...")
left_hand.closeHand(1.0, 1.0)
time.sleep(2)

print("Test complete.")

# Close the robot connection
robot.close()
