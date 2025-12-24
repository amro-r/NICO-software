# Interfaces Catalogue

This package provides the standard ROS interfaces from ROBOTIS' OpenManipulator project, reused by NICO for head/arm joint control.

## Messages (`msg/`)
- **`JointPosition.msg`**: Names and target positions for a joint chain.
- **`KinematicsPose.msg`**: Pose representation combining position and orientation vectors.
- **`OpenManipulatorState.msg`**: Encodes operating modes and actuator states for manipulator groups.

## Services (`srv/`)
- **`SetJointPosition.srv` / `GetJointPosition.srv`**: Set or query joint positions for a named planning group; consumed by ELMiRA’s motion executors.
- **`SetKinematicsPose.srv` / `GetKinematicsPose.srv`**: Manipulate Cartesian end-effector poses.
- **`SetActuatorState.srv`**: Toggle actuators on or off.
- **`SetDrawingTrajectory.srv`**: Command predefined drawing trajectories.

These interface definitions enable cross-compatibility between custom planners (EvoIK, MoveIt) and the actuator controllers used throughout the NICO software stack.
