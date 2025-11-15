# Agents Overview – `srv/`
- Custom ROS service definitions consumed across the stack.
- Cover object detection, coordinate transfer, inverse kinematics, LLM prompting, and visibility verification.
- Service contracts are generated during `catkin_make` and referenced by the corresponding server/client nodes in `scripts/`.

