# Agents Catalogue

## MoveIt Wrapper — `moveitwrapper/scripts/nicomoveit/moveitWrapper.py`
- **Role**: High-level helper (`groupHandle`) that boots MoveIt!, connects to `nicoros` motion services, and executes Cartesian/ joint plans.
- **Key Behaviours**:
  - Auto-launches appropriate MoveIt launch files (simulation vs. hardware, visualization toggles).
  - Maintains publishers/service proxies for `/nico/motion` topics to mirror plans on the robot.
  - Provides pre-defined wrist orientations (`sideGrasp`, `topGrasp`) and tolerance configuration.

## Kinematics Services — `kinematics/src/kinematics_server.cpp`
- **Role**: ROS node exposing forward/inverse kinematics and collision checks for MoveIt groups.
- **Interfaces**: Services `FK_request`, `IK_request`, and `collision_check`; publishes `FloatList` messages for solutions.
- **Support Files**: Launch scripts, experiment setups, and regression tests under `kinematics/`.

## Configuration Generators
- `createMoveitUrdf.py`: Produces URDF variants tailored for MoveIt planning by combining base URDF and additional meshes.
- `setJointConstraints.py` & `setKinematicsSolver.py`: Utilities to tune MoveIt joint limits and solver plugins programmatically.

## Assets
- `moveitgenerated/`: Pre-built MoveIt configuration packages.
- `moveitmeshes/`, `moveiturdf/`: Mesh and URDF resources consumed by MoveIt pipelines.

Collectively, these agents equip the project with planning and kinematics infrastructure that complements the ELMiRA manipulation stack.
