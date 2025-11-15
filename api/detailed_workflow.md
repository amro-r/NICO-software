# NICO Software Workflow Deep Dive

This document summarises how every package under `api/src/` collaborates to give the NICO humanoid conversational, perceptual, and manipulation capabilities. The stack runs on ROS Noetic (Ubuntu 20.04, Python 3.8) and combines learned components (LLMs, neural coordinate mapping) with classical robotics subsystems (MoveIt, Dynamixel control, OptoForce tactile sensing).

## 1. System Overview

- **Core runtime**: ROS nodes written in Python/C++, orchestrated by launch files in `src/ELMiRA/launch` and `src/nicoros/launch`.
- **Primary behaviour**: ELMiRA’s SMACH state machine (`src/ELMiRA/scripts/state_machine.py`) turns spoken instructions into speech responses, scene descriptions, and arm motions.
- **Supporting packages**:  
  - `nicoaudio`, `nicoros/TextToSpeech.py` → speech synthesis and audio IO.  
  - `nicovision`, `nicoros/Vision.py` → stereo camera streaming.  
  - `nicomotion`, `nicoros/Motion.py` → joint control for real robot or simulators.  
  - `nicomoveit` → MoveIt configuration and extra kinematics services.  
  - `nicotouch`, `nicoface`, `nicoemotionrecognition` → tactile, facial display, and emotion perception add-ons.  
  - `open_manipulator_msgs`, `nicomsg` → shared ROS interface definitions.

The remainder of this document drills into each subsystem and highlights key data paths.

## 2. Runtime Topology

| Package | Key Nodes/Services | Responsibilities |
| --- | --- | --- |
| `ELMiRA` | `speech_asr`, `llm_api`, `object_localiser`, `coordinate_transfer`, `ik_solver`, `state_machine` | Conversational loop, perception-to-action planning, LLM integration |
| `nicoros` | `Motion.py`, `TrajectoryServer.py`, `Vision.py`, `TextToSpeech.py`, OptoForce bridges | ROS façade over motion, vision, TTS, tactile hardware |
| `nicomotion` | Python motor driver (`Motion`, `Mover`, `Kinematics`) | Direct Dynamixel & simulation control |
| `nicomoveit` | `moveitWrapper.py`, C++ kinematics server | MoveIt-based planning, FK/IK services |
| `nicoaudio` | `AudioPlayer`, `TextToSpeech`, `AudioRecorder` | Audio playback, TTS backends, microphone capture |
| `nicovision` | `VideoDevice`, `MultiCamRecorder` | Camera discovery, frame acquisition utilities |
| `nicotouch` | OptoForce drivers | Tactile force sensing |
| `nicoface` | `FaceExpression`, `CapacitiveSensors` | Facial expression control, head touch sensors |
| `nicoemotionrecognition` | `EmotionRecognition` | CNN-based affect inference plus optional robot mirroring |
| `nicomsg`, `open_manipulator_msgs` | Message/service definitions | Shared ROS contracts for the entire stack |

## 3. Conversational Perception-to-Action Loop (ELMiRA)

### 3.1 Initialization

- Launch file `src/ELMiRA/launch/init_nodes.launch` bundles:  
  - Camera streaming via `nicoros/Vision.py`.  
  - Joint control (`nicoros/launch/joint_controller.launch`).  
  - ELMiRA support nodes: ASR, LLM gateway, object localiser, coordinate transfer, IK solver.  
  - ROS TTS (`nicoros/TextToSpeech.py`).
- `rosrun elmira state_machine.py` starts the SMACH executive once all services are live.

### 3.2 Speech Recognition (`src/ELMiRA/scripts/speech_asr.py`)

- Multi-client action server (`speech_asr`) built on `MultiActionServer`.  
- Captures audio with PyAudio/sounddevice, uses adaptive energy thresholds to detect speech, and plays beeps when the microphone toggles.  
- Transcribes buffered speech with Whisper (CUDA when available) and returns text plus metadata (stop reason, durations) in the `PerformASRAction` result.

### 3.3 LLM Mediation (`src/ELMiRA/scripts/llm_api.py`)

- Requires `OPENAI_API_KEY`; initialises GPT‑4o assistant with a prompt describing NICO’s abilities.  
- Services:  
  - `llm_chat` → textual planning (returns JSON `{ "actions": [...] }`).  
  - `llm_vision` → fetches `/nico/vision/right` frame, uploads to OpenAI, and yields updated action lists.  
  - `llm_object_visibility` → verifies whether the requested object appears in the current scene; returns boolean plus optional system message.

### 3.4 Action Interpretation (`src/ELMiRA/scripts/states/action_parser.py`)

- Iterates over LLM-provided action list. Supported verbs: `speak`, `act`, `describe`, `initial_pose`, `quit`.  
- Stores additional userdata (speech text, target objects, joint trajectories) for downstream states.

### 3.5 Planning & Verification (`src/ELMiRA/scripts/states/action_planner.py`)

1. **Detect objects** via `object_localiser` service.  
2. **Select candidate** (`ObjectSelector`): ranks detections, enforces workspace polygon to stay within reachable table area.  
3. **Map coordinates**: `coordinate_transfer` service runs an implicit neural field (loaded from `model_checkpoints/implicit_model_weights.pth`) to translate image bottom points to table-frame `(x, y)` (table height from userdata).  
4. **Generate poses** (`ActionTrajectory`): constructs sequences based on action type (touch, show, push, push_left/right) with orientation heuristics and offsets, deciding which arm (left vs. right) to use.  
5. **Solve IK** (`ik_solver` service): EvoIK initialises per-arm URDFs (`src/ELMiRA/urdf/`), sorts seed joints, and iteratively solves each target pose, chaining results for smoothness.  
6. Append the nominal initial pose so that execution ends safely.

### 3.6 Concurrency Guard (`ConcurrentPlanAndVerify`)

- Runs the planner alongside `llm_object_visibility`.  
- If GPT‑4 vision deems the object absent, the planner branch is pre-empted and a system message is injected into the LLM context for recovery.

### 3.7 Motion Execution (`src/ELMiRA/scripts/states/move_robot.py`)

- `JointTrajectoryIterator` iterates over planner-produced joint dictionaries (head/left/right).  
- `MoveRobotPart` calls `open_manipulator_msgs/SetJointPosition` for each chain and monitors `sensor_msgs/JointState` until within tolerance (≈3°) and velocities settle.  
- Head motions accompany both act and describe actions (look-down posture).  
- Shutdown path returns to safe poses and publishes `/nico/motion/disableTorqueAll`.

### 3.8 Dialogue Loop

- After each action batch, control yields back to ASR unless `quit` requested.  
- Failures from any branch become `"SYSTEM: …"` messages stored in userdata and fed back into the next LLM prompt (`sm.userdata.llm_input`).

## 4. Perception & Reasoning Support

- **Object Localisation** (`src/ELMiRA/scripts/object_localiser.py`): wraps OWLv2 zero-shot detector. Publishes annotated debug frames (`owlv2_server/result_image`) and returns `elmira/DetectedObject` (label, score, centre, size).  
- **Implicit Coordinate Transfer** (`src/ELMiRA/scripts/coordinate_transfer.py`): neural field sampling (`coordinate_transfer_net.py`) for image-to-table mapping.  
- **EvoIK Solver** (`src/ELMiRA/scripts/ik_solver.py`): GPU-capable IK using EvoIK library with URDFs per arm.  
- **State Machine Introspection**: `smach_ros.IntrospectionServer` exposes live state transitions for monitoring (e.g., SMACH viewer).

## 5. Motion & Control Infrastructure

### 5.1 `nicoros` Motion Bridge (`src/nicoros/scripts/Motion.py`)

- Launch-time config toggles between real hardware and V-REP/PyRep simulation.  
- Posts `/nico/motion` topics for joint commands (`setAngle`, `enableTorque`, hand open/close) and exposes complementary services (`getAngle`, `getJointNames`, `getConfig`, etc.).  
- Publishes joint states for TF updates and interacts with MoveIt when enabled.

### 5.2 Trajectory Execution (`src/nicoros/scripts/TrajectoryServer.py`)

- Implements `FollowJointTrajectoryAction` per planning group (e.g., `/l_arm/trajectory`).  
- Reads tolerances from ROS params, forwards points to `/nico/motion/setAngle`, and verifies execution by reading back joint states.

### 5.3 Low-Level Driver (`src/nicomotion/scripts/nicomotion/Motion.py`)

- Abstracts Dynamixel communication (via `pypot.dynamixel`), optionally remaps missing IDs, and manages hand-specific logic (`RH4D`, `RH5D`, `RH7D`).  
- Supports V-REP or PyRep simulation with remote API configuration.  
- Additional helpers (`Mover.py`, `Kinematics.py`, `Freezer.py`) provide trajectory sequencing, analytical kinematics, and joint locking.

### 5.4 MoveIt Tooling (`src/nicomoveit`)

- `moveitwrapper/scripts/nicomoveit/moveitWrapper.py`: `groupHandle` class launches MoveIt, syncs with `/nico/motion`, and exposes planning utilities with preset gripper orientations.  
- `kinematics/src/kinematics_server.cpp`: C++ services for FK, IK, and collision checking used by MoveIt pipelines or external clients.  
- Auxiliary scripts (`createMoveitUrdf.py`, `setJointConstraints.py`, `setKinematicsSolver.py`) automate configuration generation.

### 5.5 Manipulator Interfaces (`src/open_manipulator_msgs`)

- Provides `SetJointPosition`, `SetKinematicsPose`, and related services used by ELMiRA’s motion states to talk to the low-level controllers.

## 6. Audio Subsystem

- **`nicoaudio/TextToSpeech.py`**: Implements multi-backend TTS with caching (`gTTS`, Mozilla TTS server, `pico2wave` fallback), returning playback duration.  
- **`nicoaudio/AudioPlayer.py`**: Handles asynchronous playback with pitch/speed adjustments via phase vocoder.  
- **`nicoros/TextToSpeech.py`**: Wraps TTS as ROS service `nico/text_to_speech/say` used by ELMiRA’s speak actions.  
- **`nicoaudio/AudioRecorder.py`** and `_nicoaudio_internal` modules provide microphone recording utilities consumed by demo scripts.

## 7. Vision Subsystem

- **`nicovision/VideoDevice.py`**: Detects camera devices, manipulates zoom/pan/tilt, and streams frames via callback threads.  
- **`nicovision/MultiCamRecorder.py`**: Coordinates multi-camera acquisition (stereo).  
- **`nicoros/Vision.py`**: Exposes frames on `/nico/vision/{left,right}` topics, with services for runtime camera control.  
- **Integration with ELMiRA**: `llm_vision` and `object_localiser` subscribe to the right-eye stream for perception tasks.

## 8. Tactile & Facial Expression Subsystems

- **Tactile** (`src/nicotouch` & `src/nicoros/scripts/Optoforce*.py`): Drivers for single and multi-channel OptoForce sensors, offering raw force readings and Newton conversions.  
- **Facial Expression** (`src/nicoface/scripts/nicoface/FaceExpression.py`): Controls LED matrix/servo-based expressions via serial; includes simulation mode that renders expressions with PIL/OpenCV.  
- **Capacitive Sensors** (`src/nicoface/scripts/nicoface/CapacitiveSensors.py`): Reads head touch sensors for interaction cues.  
- **Emotion Recognition** (`src/nicoemotionrecognition/scripts/nicoemotionrecognition/EmotionRecognition.py`): Uses TensorFlow models to classify user expressions, optionally drives TTS responses and mirrors the emotion on the robot face.

## 9. Messaging & Interfaces

- **`src/nicomsg`**: Defines reusable ROS messages (e.g., `sff`, `polynomial_face`, `hs`) and services (`SayText`, `GetAngle`, `LoadAudio`, etc.) that glue the subsystems together.  
- **`src/ELMiRA/msg` & `src/ELMiRA/srv`**: Custom types for detected objects, joint positions, ASR actions, and LLM services.  
- **`src/open_manipulator_msgs`**: Imported ROBOTIS definitions for joint/pose manipulation.

## 10. Launch & Configuration Artifacts

- **Camera launch** (`src/ELMiRA/launch/camera.launch`): Passes resolution, framerate, and zoom defaults to `nicoros/Vision.py`.  
- **Robot launch suites** (`src/nicoros/launch/*.launch`): Provide variants for real robot vs. simulation, with or without MoveIt visualisation.  
- **JSON configs** (`json/` in project root, reused by `nicomotion` and `nicomoveit`): Servo mappings, joint groups, speed limits.  
- **URDF meshes** (`src/ELMiRA/urdf`, `src/nicomoveit/moveiturdf`, `src/nicomoveit/moveitmeshes`): Used by EvoIK and MoveIt for accurate kinematics.  
- **Model checkpoints** (`src/ELMiRA/model_checkpoints/implicit_model_weights.pth`): Learned coordinate transfer weights.

## 11. Typical Execution Flow

1. **Bring-up**: `roslaunch elmira init_nodes.launch` starts camera stream, joint controllers, ASR, object localisation, coordinate transfer, IK, LLM gateway, and TTS.  
2. **Start interaction**: `rosrun elmira state_machine.py`.  
3. **User speaks**: `speech_asr` detects and transcribes.  
4. **LLM plans**: `llm_chat` produces actions (speak/describe/act/quit).  
5. **Perception**: If needed, `llm_vision` obtains image/generate new plan; `object_detector` + implicit mapper compute object pose.  
6. **Motion**: `inverse_kinematics` generates trajectories; `MoveRobotPart` sends them via OpenManipulator services; nicoros/nicomotion execute them on hardware or simulation.  
7. **Feedback**: Failures or visibility warnings become `SYSTEM:` prompts for next LLM cycle.  
8. **Shutdown**: On `quit`, robot returns to safe pose and torques are disabled.

## 12. Extensibility Notes

- New dialogue behaviours can be added by extending the action schema parsed in `ActionParser` and implementing corresponding SMACH states.  
- Alternative perception models can replace OWLv2 by reimplementing the `object_detector` service while keeping the same `elmira/DetectedObject` output.  
- Coordination with MoveIt is possible via `nicomoveit/moveitwrapper` should EvoIK or implicit mapping need augmentation.  
- Additional sensors (touch, emotion recognition) can feed into the LLM context by publishing `SYSTEM:` messages or extending userdata in `state_machine.py`.

Together, these components create a tightly-integrated system where high-level language understanding drives low-level robot control, augmented with modular sensory subsystems that can be enabled as the scenario demands.
