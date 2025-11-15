# Folder Context: NICO Hardware Diagnostics

## My Role

You are an expert robotics software engineer. Your current task is to help me create a standalone Python script to directly test the hardware functionality of the NICO robot's head and arm motors. This is to diagnose whether a motion problem is due to a hardware failure or a software integration issue in the higher-level ROS stack.

## Primary Goal

Create a Python script named `hardware_test.py`. This script will **NOT** use ROS. Instead, it will directly import and use the low-level `nicomotion` library to command the robot's joints. The script should be simple, robust, and provide clear feedback in the terminal.

## Core Technologies for this Task

* **Primary Python Environment**: Python 3.8 in the virtual environment located at `~/.NICO-python3/`.
* **Target Library**: The `nicomotion` Python package located at `~/catkin_ws/src/NICO-software/api/src/nicomotion`. We need to use the classes within this library (likely a `Motion` or `NicoMotion` class) to control the motors.
* **Required Dependency**: `pypot`, which is the underlying library used by `nicomotion` to communicate with the Dynamixel motors.

## Script Logic and Requirements

Your task is to guide me in writing the `hardware_test.py` script. The script must perform the following steps:

1.  **Activate Environment**: The script must be run from within the `~/.NICO-python3/` virtual environment.
2.  **Import Necessary Class**: Import the main motion control class from the `nicomotion` library.
3.  **Initialize Connection**: Instantiate the motion class to establish a connection with the robot's motors. This may involve specifying a port or robot model.
4.  **Define Test Routine**: Create a sequence of simple, distinct movements to test the key joints. The routine should:
    * Print what it's about to do (e.g., "Testing Head Yaw...").
    * Move the `head_yaw` joint to the left, pause, then move it to the right, pause, then return to center.
    * Move the `head_pitch` joint up, pause, then down, pause, then return to center.
    * Move the `r_shoulder_pitch` joint up, pause, then down.
    * Move the `l_shoulder_pitch` joint up, pause, then down.
    * Move the `r_elbow` joint to bend, pause, then straighten.
    * Move the `l_elbow` joint to bend, pause, then straighten.
    * Ensure there are `time.sleep()` pauses between each distinct movement so we can observe it.
5.  **Graceful Shutdown**: Ensure the script has a `try...finally` block to properly close the connection to the motors, even if an error occurs. This is critical to avoid leaving the motors in a locked state.
6.  **Provide Commands**: Give me the exact commands to run the script from the terminal.

## Instructions for You (Claude)

Your primary goal is to help me write the `hardware_test.py` script. You will ask me for the contents of the `nicomotion` directory if needed to determine the correct class and method names. Guide me step-by-step to build the script logic as outlined above.