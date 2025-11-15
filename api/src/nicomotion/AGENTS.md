# Agents Catalogue

## Core Robot Driver — `scripts/nicomotion/Motion.py`
- **Role**: Unified hardware/simulation controller for NICO actuators via pypot (Dynamixel) or V-REP/PyRep backends.
- **Capabilities**:
  - Loads motor configurations from JSON, initialises hand models (RH4D/RH5D/RH7D).
  - Supports real hardware with automatic retry/removal of missing motors and latency adjustments.
  - Provides torque, PID, speed, and safety utilities; publishes tracked objects when running in simulation.
- **Key Behaviours**: Abstracts communication errors, handles simulation switching, and exposes high-level joint group operations consumed by ROS layers.

## Motion Sequencing — `scripts/nicomotion/Mover.py`
- **Role**: Higher-level trajectory coordinator that sequences joint targets, respects velocity profiles, and synchronises limb movements.
- **Features**: Interpolates angles, enforces speed constraints, integrates with `Motion` for execution.

## Analytical Kinematics — `scripts/nicomotion/Kinematics.py`
- **Role**: Provides direct forward/inverse kinematics calculations for specific chains independent of MoveIt.
- **Usage**: Supports scripts and diagnostic tooling needing lightweight kinematics.

## Safety Utilities — `scripts/nicomotion/Freezer.py`
- **Role**: Locks selected joints to prevent unintended movement, useful for calibration and demos.

## Internal Tooling (`_nicomotion_internal`)
- Contains error handlers, hand kinematics, and support classes for the main driver.

Together these agents deliver the low-level motion control stack that `nicoros` and ELMiRA build upon for manipulation.
