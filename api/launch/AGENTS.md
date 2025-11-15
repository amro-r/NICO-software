# Agents Overview – `launch/`
- ROS launch files that bootstrap the full ELMiRA stack.
- `camera.launch` sets up the NICO vision pipeline with camera parameters.
- `init_nodes.launch` starts perception/action nodes alongside supporting `nicoros` processes; typically run via `roslaunch elmira init_nodes.launch`.

