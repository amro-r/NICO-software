#!/usr/bin/env python3
import sys, time
sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')
from nicomotion.Motion import Motion

def main():
    m = Motion(motorConfig='/home/amr/catkin_ws/src/NICO-software/json/nico_humanoid_upper_with_hands.json',
               vrep=False, ignoreMissing=True, monitorHandCurrents=False)
    time.sleep(1.0)
    joints = [
        'r_elbow_y', 'r_shoulder_y', 'r_shoulder_z',
        'l_elbow_y', 'l_shoulder_y', 'l_shoulder_z'
    ]
    for j in joints:
        if hasattr(m._robot, j):
            motor = getattr(m._robot, j)
            print(f"{j}: pos={motor.present_position:.1f}°, compliant={motor.compliant}, torque_limit={getattr(motor, 'torque_limit', None)}, lims=({getattr(motor, 'lower_limit', None)},{getattr(motor, 'upper_limit', None)})")
        else:
            print(f"{j}: MISSING")

if __name__ == '__main__':
    main()
