# Agents Catalogue

## Motion Bridge — `scripts/Motion.py`
- **Role**: Wraps `nicomotion.Motion` and exposes it over ROS topics/services under `/nico/motion`.
- **Interfaces**:
  - Subscribers for commands (`setAngle`, `enableTorque`, hand open/close, force control toggles, etc.).
  - Services for getting joint angles, names, poses, configuration, and toggling V-REP/pyrep options.
  - Publishes `sensor_msgs/JointState` and diagnostic information.
- **Key Behaviours**: Applies launch-time parameters (real vs. simulation), periodically pushes joint state updates, and cleans shutdown torque.

## Trajectory Action Server — `scripts/TrajectoryServer.py`
- **Role**: Provides `FollowJointTrajectoryAction` endpoints (per planning group) that forward waypoints to `/nico/motion`.
- **Key Behaviours**: Validates joint names, enforces path tolerances, checks goal completion by reading back joint states, supports fake execution mode.

## Vision Bridge — `scripts/Vision.py`
- **Role**: Streams camera frames from `nicovision.MultiCamRecorder` into ROS image topics (`/nico/vision/{left,right}`).
- **Interfaces**: Services to adjust zoom/pan/tilt at runtime; publishers for mono/stereo topics configured via CLI args.

## Text-to-Speech Node — `scripts/TextToSpeech.py`
- **Role**: Exposes `nicoaudio.TextToSpeech` as the ROS service `nico/text_to_speech/say`.
- **Features**: Accepts cache directory and backend URL overrides; delegates synthesis to `nicoaudio`.

## Audio Streaming — `scripts/AudioStream.py`
- **Role**: Records or streams audio input over ROS topics/services, pairing with `nicoaudio` primitives.

## Force/Tactile Bridges
- `scripts/Optoforce*.py`: Nodes that expose OptoForce single and multi-channel tactile sensors, publishing force readings and offering management services.

## Launch Suites — `launch/`
- Pre-defined launch files for simulated vs. real robot setups, MoveIt-integrated stacks, and camera configurations. These compose the agents above into turnkey runtime graphs.

Nicoros forms the ROS-layer glue that connects low-level hardware APIs (`nicomotion`, `nicovision`, `nicoaudio`, `nicotouch`) with higher-level behaviour packages such as ELMiRA.
