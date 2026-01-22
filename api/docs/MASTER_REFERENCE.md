# NICO Software Master Reference Document

## 1. System Overview

The NICO software architecture is a modular, ROS-based framework designed to enable multimodal interaction and developmental robotics research. It integrates low-level hardware control with high-level cognitive processing, leveraging a hybrid approach of local real-time processing and cloud-based reasoning.

### 1.1 Architecture
The system follows a distributed **Service-Oriented Architecture (SOA)** built upon **ROS (Robot Operating System)**. It is organized into specialized packages that handle distinct modalities:

*   **Core Modules:**
    *   `nicomotion`: Handles motor control, kinematics, and trajectory generation for the head and arms (OpenManipulator).
    *   `nicovision`: Manages camera interfaces, recording, and image processing pipelines.
    *   `nicoaudio`: Provides interfaces for audio capture, speech recognition (ASR), and text-to-speech (TTS).
    *   `nicotouch`: Interfaces with tactile sensors and skin technology.
*   **Cognitive Layer (ELMiRA):**
    *   Acts as the high-level orchestrator, bridging perception and action through Large Language Models (LLMs).
    *   Operates as a collection of ROS nodes coordinating via a central State Machine.

### 1.2 Design Patterns
The codebase utilizes several key software design patterns to ensure scalability and maintainability:

*   **Publisher/Subscriber:** Used for continuous data streams, such as joint states (`/NICOL/joint_states`), camera feeds (`/nico/vision/right`), and sensor readings.
*   **Service/Client:** Employed for synchronous, blocking operations requiring immediate results, such as Inverse Kinematics calculations (`InverseKinematics.srv`), coordinate mapping, and LLM queries.
*   **Action Server:** Utilized for long-running, preemptable tasks like Automatic Speech Recognition (`PerformASR.action`), allowing the system to provide feedback or cancel operations.
*   **State Machine:** **SMACH** is used to orchestrate complex behaviors, managing the flow between listening, reasoning, planning, and execution states.
*   **Provider Pattern (v2):** The updated ELMiRA architecture uses a provider abstraction to dynamically switch between different Multimodal LLM backends (e.g., OpenAI, Google) without altering core logic.

### 1.3 Technology Stack
*   **Operating System:** Ubuntu 20.04 LTS
*   **Middleware:** ROS Noetic
*   **Languages:** Python 3.8 (primary), C++ (performance-critical nodes)
*   **Simulation:** CoppeliaSim with **PyRep** for Python bindings.
*   **AI & Machine Learning:**
    *   **Frameworks:** PyTorch, NumPy.
    *   **Perception:** OpenAI Whisper (ASR), OWLv2 (Object Detection), OpenCV.
    *   **Reasoning:** GPT-4o, Gemini 3 Flash (via API).
*   **Kinematics & Control:**
    *   **Libraries:** `gaikpy`, `math3d`, `transforms3d`.
    *   **Solvers:** **EvoIK** (GPU-accelerated evolutionary inverse kinematics).
    *   **Hardware Interface:** `open_manipulator_msgs`, `dynamixel_sdk`.

### 1.4 Data Flow (ELMiRA Pipeline)
Data moves through the system in a closed perception-action loop:

1.  **Perception:**
    *   **Audio:** Captured via `nicoaudio`, processed by **Whisper** to generate text transcripts.
    *   **Vision:** Raw images are captured from the right eye camera (`/nico/vision/right`).
2.  **Reasoning (LLM Gateway):**
    *   Transcribed text and current visual frames are sent to the **Multimodal LLM**.
    *   The LLM returns a structured **JSON Action Plan** (e.g., `{"action": "act", "object": "orange", "type": "push_right"}`).
3.  **Planning & Grounding:**
    *   **Object Detection:** The target object is located using either the MLLM's grounding capabilities or a local **OWLv2** model.
    *   **Coordinate Transfer:** 2D pixel coordinates are mapped to 3D table coordinates using a trained MLP network (`coordinate_transfer_net.py`).
    *   **Trajectory Generation:** The **Action Planner** converts abstract actions into Cartesian poses.
    *   **Inverse Kinematics:** **EvoIK** solves for the joint angles required to reach these poses.
4.  **Execution:**
    *   Joint trajectories are published to the robot controllers.
    *   The system monitors joint states to ensure convergence before proceeding to the next action or returning to the listening state.

---

## 2. Directory Structure

```markdown
api/
├── action/
├── docs/
│   ├── static/ ...
│   ├── ELMiRA_data_flow.md
│   ├── ELMiRA_mllm_upgrade_plan.md
│   ├── ELMiRA_v2_implementation_status.md
│   ├── ELMiRA_v2_upgrade_plan.md
│   └── new_multimodal_module_plan.md
├── examples/
│   ├── mixed-modules/ ...
│   ├── multimodal_recording/ ...
│   ├── nicoaudio/ ...
│   ├── nicoemotionrecognition/ ...
│   ├── nicoface/ ...
│   ├── nicomotion/ ...
│   ├── nicomoveit/ ...
│   ├── nicotouch/ ...
│   └── nicovision/ ...
├── launch/
├── model_checkpoints/
├── msg/
├── scripts/
├── src/
│   ├── ELMiRA/
│   │   ├── action/
│   │   │   └── PerformASR.action
│   │   ├── config/
│   │   │   └── mllm_config.yaml
│   │   ├── docs/ ...
│   │   ├── json/
│   │   ├── launch/
│   │   │   ├── init_nodes.launch
│   │   │   ├── init_nodes_v2.launch
│   │   │   └── mllm_only.launch
│   │   ├── model_checkpoints/
│   │   ├── msg/
│   │   │   ├── DetectedObject.msg
│   │   │   └── JointPosition.msg
│   │   ├── scripts/
│   │   │   ├── states/
│   │   │   │   ├── action_parser.py
│   │   │   │   ├── action_planner.py
│   │   │   │   └── move_robot.py
│   │   │   ├── ui/
│   │   │   │   ├── elmira_v2_dashboard.py
│   │   │   │   ├── run_elmira_v2_dashboard.sh
│   │   │   │   ├── requirements_ui.txt
│   │   │   │   └── README.md
│   │   │   ├── v2/
│   │   │   │   ├── config/
│   │   │   │   ├── providers/
│   │   │   │   │   ├── google_provider.py
│   │   │   │   │   └── openai_provider.py
│   │   │   │   ├── schemas/
│   │   │   │   │   ├── actions.py
│   │   │   │   │   └── detections.py
│   │   │   │   ├── utils/
│   │   │   │   │   └── image_cache.py
│   │   │   │   └── llm_api_v2.py
│   │   │   ├── coordinate_transfer.py
│   │   │   ├── coordinate_transfer_net.py
│   │   │   ├── ik_solver.py
│   │   │   ├── llm_api.py
│   │   │   ├── multi_action_server.py
│   │   │   ├── object_localiser.py
│   │   │   ├── speech_asr.py
│   │   │   └── state_machine.py
│   │   ├── srv/
│   │   │   ├── DetectWithMLLM.srv
│   │   │   ├── PromptMLLM.srv
│   │   │   ├── PromptMLLMWithGrounding.srv
│   │   │   └── ...
│   │   ├── urdf/
│   │   ├── CMakeLists.txt
│   │   ├── package.xml
│   │   └── requirements.txt
│   ├── nicoaudio/
│   │   ├── scripts/nicoaudio/
│   │   │   ├── _nicoaudio_internal/
│   │   │   ├── AudioPlayer.py
│   │   │   ├── AudioRecorder.py
│   │   │   ├── pulse_audio_recorder.py
│   │   │   └── TextToSpeech.py
│   │   ├── tests/
│   │   └── setup.py
│   ├── nicoemotionrecognition/
│   │   ├── scripts/nicoemotionrecognition/
│   │   │   ├── _nicoemotionrecognition_internal/ ...
│   │   │   ├── EmotionRecognition.py
│   │   │   └── EmotionRecognitionServer.py
│   │   └── setup.py
│   ├── nicoface/
│   │   ├── scripts/nicoface/
│   │   │   ├── CapacitiveSensors.py
│   │   │   ├── FaceExpression.py
│   │   │   └── SerialConnectionManager.py
│   │   ├── tests/
│   │   └── setup.py
│   ├── nicomotion/
│   │   ├── scripts/nicomotion/
│   │   │   ├── _nicomotion_internal/ ...
│   │   │   ├── urdf/
│   │   │   ├── Freezer.py
│   │   │   ├── Kinematics.py
│   │   │   ├── Motion.py
│   │   │   ├── Mover.py
│   │   │   └── Visualizer.py
│   │   ├── tests/
│   │   └── setup.py
│   └── nicomoveit/
│       ├── kinematics/ ...
│       ├── moveitgenerated/ ...
│       ├── createMoveitUrdf.py
│       ├── setJointConstraints.py
│       └── setKinematicsSolver.py
├── install_apt.sh
├── NICO-python3.bash
├── NICO-setup.bash
├── NICO-test.bash
├── pyrep_env.bash
└── readme.md
```

---

## 3. Component-Level Analysis

### 3.1 ELMiRA Module (`api/src/ELMiRA`)

#### `scripts/state_machine.py`
*   **Primary Responsibility:** Orchestrates the high-level behavior of the robot by integrating speech recognition (ASR), LLM planning, and action execution.
*   **Key Components:**
    *   `main()`: Initializes the SMACH state machine.
    *   `ActionParser`: Parses LLM JSON responses into executable states.
    *   `JointTrajectoryIterator`: Manages the execution of physical movements.
    *   States: `SPEECH_ASR`, `LLM_SPEECH_PROCESSOR`, `EXECUTE_ACTIONS`, `TEXT_TO_SPEECH`.
*   **Internal Logic:**
    1.  **Wait for Input:** Uses `PerformASRAction` to listen for user speech.
    2.  **Plan:** Sends transcribed text to the LLM service to generate a list of actions (JSON).
    3.  **Iterate:** Enters an iterator to process each action in the list sequentially.
    4.  **Execute:** Triggers `ConcurrentPlanAndVerify` to check object visibility and plan trajectories.
*   **Dependencies:** `smach`, `smach_ros`, `rospy`, `json`.
*   **Integration Points:** Services: `llm_chat`, `llm_vision`, `nico/text_to_speech/say`.

#### `scripts/ik_solver.py`
*   **Primary Responsibility:** Provides an Inverse Kinematics (IK) service to calculate joint angles for the robot's arms.
*   **Key Components:**
    *   `KinematicsServer`: The ROS node class.
    *   `EvoIK`: A PyTorch-based IK solver library.
*   **Internal Logic:**
    1.  Loads URDF models: `nico_right_arm.urdf` (6 joints) and `nico_left_arm_no_wrist.urdf` (4 joints).
    2.  Uses `evo_ik` (gradient descent) to iteratively solve for joint angles that minimize the error between the end-effector and the target.
    3.  Supports GPU acceleration via CUDA when available.
*   **Configuration:**
    *   `max_steps=100`: Maximum iterations for IK solver
    *   Left arm uses reduced joint set due to non-functional wrist motors
*   **Dependencies:** `evo_ik`, `torch`, `numpy`.
*   **Integration Points:** Service: `inverse_kinematics`.

#### `scripts/v2/llm_api_v2.py`
*   **Primary Responsibility:** Acts as the central gateway for all MLLM interactions, abstracting specific provider implementations (OpenAI, Google).
*   **Key Components:**
    *   `MLLMGateway`: Main ROS node class.
    *   `handle_chat`, `handle_vision`, `handle_detect`: Service callbacks.
*   **Internal Logic:**
    1.  **Initialization:** Loads configuration and initializes the specific provider.
    2.  **Routing:** Routes ROS service requests to the appropriate provider method.
    3.  **Standardization:** Converts provider-specific responses into standard ROS messages/JSON formats.
*   **Dependencies:** `providers` package, `utils` package, `rospy`.
*   **Integration Points:** Services: `mllm_chat`, `mllm_vision`, `mllm_detect`.

### 3.2 nicomotion Module (`api/src/nicomotion`)

#### `scripts/nicomotion/Mover.py`
*   **Primary Responsibility:** High-level recording and playback of joint movements and positions.
*   **Key Components:**
    *   `class Mover`: Main controller.
    *   `play_movement(fname)`: Replays a recorded trajectory.
    *   `move_position(target_positions)`: Moves joints to a specific target configuration.
*   **Internal Logic:**
    *   **Playback Synchronization:** Calculates the time required for the slowest joint and scales others to match.
    *   **Data Storage:** Uses CSV files to store joint names and angle sequences.
*   **Dependencies:** `nicomotion.Motion`, `csv`, `time`.

#### `scripts/nicomotion/Motion.py`
*   **Primary Responsibility:** The core hardware abstraction layer (HAL). Unifies control for physical robot and simulation.
*   **Key Components:**
    *   `class Motion`: Main interface.
    *   `setAngle`, `getAngle`: Joint control methods.
    *   `startSimulation`: Connects to V-REP/PyRep if configured.
*   **Internal Logic:**
    *   **Initialization:** Reads `motorConfig` JSON. Connects to `pypot` (hardware) or `pyrep` (sim).
    *   **Hand Abstraction:** Detects attached hand types (RH4D, RH5D, RH7D) and initializes drivers.
*   **Dependencies:** `pypot`, `pypot.vrep`.

### 3.3 nicoface Module (`api/src/nicoface`)

#### `scripts/nicoface/FaceExpression.py`
*   **Primary Responsibility:** Generates and sends facial expressions to the robot's face displays.
*   **Key Components:**
    *   `sendFaceExpression(expression)`: Sends a predefined preset.
    *   `morph_face_expression`: Smoothly transitions between expressions.
*   **Internal Logic:**
    *   **Procedural Generation:** Uses Polynomials or Ricker Wavelets to generate face curves.
    *   **Rendering:** Converts curves to bitmaps and serializes to byte strings for Arduino.
*   **Dependencies:** `SerialConnectionManager`, `PIL`, `numpy`.

### 3.4 nicoaudio Module (`api/src/nicoaudio`)

#### `scripts/nicoaudio/AudioPlayer.py`
*   **Primary Responsibility:** Handles asynchronous audio playback with pitch/speed manipulation.
*   **Key Components:**
    *   `play(volume)`: Starts playback.
    *   `pitch(octaves)`, `speed(speed)`: Modifies audio properties.
*   **Internal Logic:**
    *   Uses `audiotsm` (phase vocoder) for time-scale modification.
    *   Playback handled via `pyaudio` streams in a daemon thread.
*   **Dependencies:** `pyaudio`, `pydub`, `audiotsm`.

#### `scripts/nicoaudio/TextToSpeech.py`
*   **Primary Responsibility:** Converts text to speech using deep learning models.
*   **Key Components:**
    *   `say(text)`: Generates and plays audio.
*   **Internal Logic:**
    *   Uses `TTS` (Coqui TTS) library.
    *   Implements caching to store generated audio files.
*   **Dependencies:** `TTS`, `nicoaudio.AudioPlayer`.

### 3.5 nicoemotionrecognition Module (`api/src/nicoemotionrecognition`)

#### `scripts/nicoemotionrecognition/EmotionRecognition.py`
*   **Primary Responsibility:** Client-side interface for emotion recognition.
*   **Key Components:**
    *   `get_categorical_data()`: Retrieves emotion probabilities.
*   **Internal Logic:**
    *   Uses `flaskcom.remote_object` to communicate with the backend Docker container.
*   **Dependencies:** `flaskcom`.

#### `_nicoemotionrecognition_internal/EmotionRecognitionBackend.py`
*   **Primary Responsibility:** Core processing logic for face detection and emotion classification.
*   **Key Components:**
    *   `detectFace(image)`: Locates faces.
    *   `classify(face)`: Infers emotions.
*   **Internal Logic:**
    *   **Face Detection:** Uses `dlib`.
    *   **Inference:** Uses a Keras/TensorFlow model to classify emotions.
*   **Dependencies:** `tensorflow`, `keras`, `cv2`, `dlib`.

### 3.6 nicomoveit & nicovision Modules

#### `nicomoveit/kinematics/src/kinematics_server.cpp`
*   **Primary Responsibility:** C++ ROS node providing IK/FK and collision checking via MoveIt!.
*   **Key Components:**
    *   `compute_ik`, `compute_fk`: Service callbacks.
*   **Internal Logic:**
    *   Uses `moveit_core` to solve kinematics based on the loaded `robot_description`.
*   **Integration Points:** Services: `moveit/compute_ik`, `moveit/compute_fk`.

#### `nicovision/scripts/nicovision/MultiCamRecorder.py`
*   **Primary Responsibility:** Manages synchronized image capture from multiple cameras.
*   **Key Components:**
    *   `class MultiCamRecorder`: Main controller.
    *   `_eventloop`: Threaded capture loop.
*   **Internal Logic:**
    *   Initializes multiple `VideoDevice` instances.
    *   Uses a `Barrier` to synchronize frame capture across threads.
*   **Dependencies:** `cv2`, `threading`, `VideoDevice`.

---

## 4. Current Development State

### 4.1 Hardware Limitations

| Component | Status | Notes |
|-----------|--------|-------|
| Right Arm | ✅ Functional | Full arm and hand working |
| Left Arm | ⚠️ Partial | Shoulder/elbow functional; wrist/fingers non-functional |
| Head | ✅ Functional | Pan/tilt working |
| Right Eye Camera | ✅ Functional | See3CAM_CU135 on `/dev/video4` → `/nico/vision/right` |
| Left Eye Camera | ✅ Functional | See3CAM_CU135 on `/dev/video2` → `/nico/vision/left` |
| TTS | ✅ Functional | Coqui TTS with VCTK model |
| ASR | ✅ Functional | OpenAI Whisper (small.en) |

> **Note:** Left hand (wrist/fingers) motors have physical issues but the left arm (shoulder/elbow) is functional and can be used for pointing/pushing actions.

### 4.2 Recent Fixes (December 2024 - January 2026)

#### SMACH Userdata Fix
*   **File:** `action_planner.py`
*   **Issue:** `InvalidUserCodeError` when reading `hand_action` without declaring as input key
*   **Fix:** Removed redundant check that attempted to read `hand_action` from userdata

#### Gemini 3 Flash Token Limit
*   **Files:** `llm_api_v2.py`, `google_provider.py`
*   **Issue:** Reasoning model tokens causing truncated JSON responses
*   **Fix:** Increased `max_tokens` from 1024 → 4096

#### Movement Timeout
*   **File:** `move_robot.py`
*   **Issue:** Robot movements timing out before reaching target
*   **Fix:** Increased timeout from 6s → 30s (`max_checks`: 300 → 1500)

#### Stereo Camera Configuration
*   **File:** `camera.launch`
*   **Issue:** Only right eye camera was publishing
*   **Fix:** Changed mode from `"right"` to `"stereo"` to enable both cameras

#### Left Arm IK Configuration (January 2026)
*   **File:** `ik_solver.py`
*   **Issue:** Left arm IK failing due to non-functional wrist motors
*   **Fix:** Created `nico_left_arm_no_wrist.urdf` with 4 joints (shoulder/elbow only), IK solver now uses appropriate URDF per arm

### 4.3 Coordinate System & Mapping Pipeline

The robot uses a **learned implicit coordinate transfer** to map 2D image coordinates to 3D table coordinates:

#### Coordinate Transfer Pipeline
```
Bounding Box (MLLM) → Center Point (0-1) → MLP Network → Real-World (X, Y meters)
```

1. **Input:** Normalized image coordinates (0-1 range) from bounding box center
2. **Network:** `ImplicitCoordinateTransfer` MLP (4→1024→1024→1) with derivative-free optimization
3. **Output:** Real-world X, Y coordinates in meters relative to robot base

#### Fixed Z-Height Assumption
```python
# In state_machine.py
sm.userdata.table_z = 0.68  # Fixed table height in meters
```

*   **X, Y coordinates:** Provided by MLLM detection → Coordinate Transfer MLP
*   **Z coordinate:** Hardcoded as `table_z` (robot cannot detect object height)

#### Gemini Bounding Box Format
Gemini returns `box_2d` in `[y_min, x_min, y_max, x_max]` format with 0-1000 scale:
```python
# In google_provider.py
y_min, x_min, y_max, x_max = [v / 1000.0 for v in box[:4]]
center_x = (x_min + x_max) / 2  # Normalized 0-1
center_y = (y_min + y_max) / 2  # Normalized 0-1
```

#### Workspace Polygon
Objects are validated against a 9-vertex polygon defining reachable table area:
```python
workspace = np.array([
    [0.0396, 0.7160], [0.2021, 0.3444], [0.7646, 0.3278],
    [0.9448, 0.7313], [0.8162, 0.8069], [0.6391, 0.8632],
    [0.4380, 0.8757], [0.2599, 0.8375], [0.1328, 0.7771],
])
```

### 4.4 Arm Selection Logic

Arm selection in `action_planner.py` is based on **target Y coordinate**:

```python
is_right = userdata.target_y < 0  # Negative Y = right side of table
userdata.planning_group = "r_arm" if is_right else "l_arm"
```

### 4.5 Action Offsets

#### Push Action
```python
offsets = [
    (-0.04, 0.0, 0.0),  # Start 4cm behind object
    (0.03, 0.0, 0.0),   # Move 3cm forward
    (0.06, 0.0, 0.0),   # Move 6cm forward
    (0.06, 0.0, 0.10),  # Lift up 10cm
]
```

#### Show Action
```python
offset = (-0.04, 0.0, 0.03)  # 4cm behind, 3cm above object
```

#### Touch Action
```python
offset = (0.0, 0.0, 0.0)  # Directly at object position
```

### 4.6 Running the System

```bash
# Terminal 1: ROS Core
roscore

# Terminal 2: Launch nodes
roslaunch elmira init_nodes_v2.launch mllm_provider:=google

# Terminal 3: State machine
rosrun elmira state_machine.py

# Optional: View camera feed
rqt_image_view
```

### 4.7 Streamlit Dashboard (Recommended)

A developer-focused Streamlit UI is available for launching and monitoring ELMiRA v2 with a graphical interface.

**Features:**
- Configure all launch parameters via sidebar controls (provider, temperature, grounding options, ASR thresholds)
- One-click launch of the full ELMiRA v2 stack
- Separate button to start/stop the state machine
- Live camera feed from `/elmira/debug/detections` showing workspace and bounding boxes
- Dual terminal tabs for roslaunch and state_machine logs
- Real-time latency and accuracy metrics display (when tracking enabled)
- Emergency stop button to terminate all processes

**Quick Start:**
```bash
cd api/src/ELMiRA/scripts/ui
./run_elmira_v2_dashboard.sh
```

Then open `http://localhost:8501` in your browser.

**Usage Workflow:**
1. Configure settings in the sidebar (provider, model, temperature, etc.)
2. Click "🚀 Launch ELMiRA v2" to start the ROS stack
3. Wait for nodes to initialize (monitor in roslaunch tab)
4. Click "🧠 Start State Machine" to begin the interaction loop
5. Use "⏹️ Stop SM" to stop only the state machine
6. Use "🛑 Emergency Stop" to terminate everything

**Dependencies:**
```bash
pip install streamlit pandas
```

### 4.8 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes (for Google provider) | Gemini API key |
| `OPENAI_API_KEY` | Yes (for OpenAI provider) | OpenAI API key |

---

## 5. Recent Enhancements (December 2024 - January 2026)

### 5.1 Conversation Memory

The MLLM providers now maintain conversation history for multi-turn interactions.

**Features:**
- Up to 10 turns of conversation history retained
- Enables pronoun resolution ("touch the red ball" → "push *it*")
- Text-only history storage (images not retained to save memory)
- Reset via `/mllm_reset_conversation` service

**Implementation:**
```python
# OpenAI/Google providers maintain conversation_history list
conversation_history: List[Dict] = []

# Reset service
rosservice call /mllm_reset_conversation "{}"
```

### 5.2 Grounded Action Planning

Single MLLM call for action interpretation AND object localization, eliminating two-stage disconnect.

**Features:**
- Fresh frame capture for accurate grounding
- Combines command parsing with object detection
- Toggle via ROS parameter: `/use_grounded_action_planning`
- Fallback to separate detection path available

**Flow (when enabled):**
```
LOOK_DOWN_ACT → DECIDE_GROUNDED_PATH → GROUNDED_ACTION_CHAT → GROUNDED_PLAN_ACTION
```

**Flow (when disabled - fallback):**
```
LOOK_DOWN_ACT → DECIDE_GROUNDED_PATH → PLAN_ACTION_TRAJECTORY (separate detection)
```

**Launch options:**
```bash
# Enable grounded action planning (default)
roslaunch elmira init_nodes_v2.launch mllm_provider:=google

# Disable grounded action planning
roslaunch elmira init_nodes_v2.launch use_grounded_action_planning:=false
```

**New states added:**
- `DECIDE_GROUNDED_PATH`: Routes between grounded and separate detection paths
- `GROUNDED_ACTION_CHAT`: Calls `/mllm_grounded_chat` service
- `GROUNDED_PLAN_ACTION`: Uses `GroundedActionPlannerDirect` with pre-computed detections
- `GroundedObjectSelector`: Selects objects from grounded detections

### 5.3 Gemini 3 Flash Integration (January 2026)

Updated Google provider to use Gemini 3 Flash preview model.

**Changes:**
- Model: `gemini-3-flash-preview` (previously `gemini-2.5-flash`)
- Native bounding box grounding support (0-1000 coordinate scale)
- Increased max_tokens to 4096 for complex responses

### 5.4 Detection Visualization

Real-time visualization of MLLM detections with bounding boxes.

**Features:**
- Publishes to `/elmira/debug/detections` topic
- Draws bounding boxes with labels and coordinates on camera feed
- Workspace polygon overlay showing reachable area

**Usage:**
```bash
# View detections in rqt
rqt_image_view /elmira/debug/detections
```

### 5.5 New ROS Services

| Service | Type | Description |
|---------|------|-------------|
| `/mllm_grounded_chat` | `PromptMLLMWithGrounding` | Combined action + detection in one call |
| `/mllm_reset_conversation` | `std_srvs/Trigger` | Clear conversation history |
| `/mllm_chat` | `PromptTextLLM` | Text-only chat (v2 gateway) |
| `/mllm_vision` | `PromptVisionLLM` | Vision + text chat (v2 gateway) |
| `/mllm_visibility` | `CheckLLMObjectVisibility` | Check if object is visible |
| `/mllm_detect` | `DetectWithMLLM` | Detect objects with bounding boxes |

### 5.6 Latency Benchmarking (January 2026)

Performance benchmarking system to measure the unified MLLM cognitive core latency.

**Research Context:**
- **Baseline (ELMiRA v1):** GPT-4 + GPT-4V averaged 8.98 seconds
- **Target (ELMiRA v2):** <8.08 seconds (10% reduction)

**Measurement Window:**
- **Start Timer:** Immediately after ASR completes (transcript available)
- **Stop Timer:** When MLLM returns JSON/structured output (Mode/Action/Target)
- **Excludes:** Robot physical movement (IK/Motion), TTS generation, ASR transcription

**Usage:**
```bash
# Enable latency tracking
roslaunch elmira init_nodes_v2.launch track_latency:=true

# Custom log directory (optional)
roslaunch elmira init_nodes_v2.launch track_latency:=true latency_log_dir:=/path/to/logs
```

**Log Output:**
- CSV files stored in `~/.elmira/latency_logs/latency_YYYYMMDD_HHMMSS.csv`
- Real-time console output with benchmark comparison
- Summary statistics printed on node shutdown

**Log Format (CSV):**
```csv
timestamp,operation_type,latency_ms,provider,model,success,input_length,output_length,detections_count,notes
```

**Operation Types Tracked:**
| Type | Description |
|------|-------------|
| `chat` | Text-only LLM processing |
| `vision` | Vision + text (scene description) |
| `grounded_chat` | Combined action + detection (primary metric) |
| `detect` | Object detection only |
| `visibility` | Object visibility check |

**Implementation:** [latency_tracker.py](../src/ELMiRA/scripts/v2/utils/latency_tracker.py)

### 5.7 Accuracy Benchmarking (January 2026)

Accuracy benchmarking system to validate the unified MLLM architecture against the baseline ELMiRA v1 system.

**Research Context:**
- **Baseline (ELMiRA v1):** 46.67% accuracy
- **Target (ELMiRA v2):** >67% accuracy (20% improvement)

**Measurement Modes:**
| Mode | What's Measured | Image Saved |
|------|-----------------|-------------|
| `describe` | Scene description accuracy | Raw image (no bboxes) |
| `act` | Action + localization accuracy | Image WITH bounding boxes |
| `speak` | Knowledge/conversation accuracy | No image |

**Usage:**
```bash
# Enable accuracy tracking
roslaunch elmira init_nodes_v2.launch track_accuracy:=true

# Enable both latency and accuracy tracking
roslaunch elmira init_nodes_v2.launch track_latency:=true track_accuracy:=true

# Custom log directory (optional)
roslaunch elmira init_nodes_v2.launch track_accuracy:=true accuracy_log_dir:=/path/to/logs
```

**Log Output:**
- Session directory: `~/.elmira/accuracy_logs/session_YYYYMMDD_HHMMSS/`
- CSV file: `accuracy_YYYYMMDD_HHMMSS.csv`
- Images directory: `images/` (annotated with bounding boxes for act mode)
- Summary statistics printed on node shutdown

**Log Format (CSV):**
```csv
timestamp,session_id,interaction_id,asr_transcript,mode_selected,action_type,target_object,image_path,has_bounding_boxes,detections_json,detection_count,selected_bbox_x,selected_bbox_y,selected_bbox_w,selected_bbox_h,robot_output,response_json,success,failure_reason,manual_verdict,notes
```

**Key Columns:**
| Column | Description |
|--------|-------------|
| `asr_transcript` | User's spoken input |
| `mode_selected` | speak, describe, or act |
| `image_path` | Absolute path to saved image |
| `has_bounding_boxes` | True if image has bbox overlay (act mode) |
| `detections_json` | JSON array of all detected objects with bbox coords |
| `selected_bbox_*` | Normalized (0-1) coords of selected target object |
| `robot_output` | Robot's TTS response or description |
| `manual_verdict` | **Empty column for human annotation:** correct/incorrect/partial |
| `notes` | **Empty column for human notes** |

**Manual Review Process:**
1. Run robot interaction session with `track_accuracy:=true`
2. Open generated CSV file in spreadsheet application
3. For each row, open the `image_path` to review the scene/bounding boxes
4. Fill in `manual_verdict` column: `correct`, `incorrect`, or `partial`
5. Add any notes in `notes` column
6. Calculate accuracy: `correct_count / total_count * 100`

**Success Criteria:**
- **Describe Mode:** MLLM generates text description relevant to visible objects
- **Act Mode:** MLLM correctly identifies target object AND bounding box encompasses the correct object

**Implementation:** [accuracy_tracker.py](../src/ELMiRA/scripts/v2/utils/accuracy_tracker.py)

---

## 6. Development Branches

| Branch | Description |
|--------|-------------|
| `master` | Original NICO software |
| `NICO-Amro` | Main development branch |
| `NICO-Amro-backup-*` | Backup branches with dates |
| `feat/handshake` | Feature branch for handshake development |
| `feat/visual-grounding-action-planning` | Grounded action planning feature (merged) |
| `feat/mllm-conversation-memory` | Conversation memory implementation (merged) |
| `feat/view_detected_objects` | **Current** - Detection visualization feature |

---

## 7. Known Issues & Debugging

### 7.1 Trajectory Execution Issues

**Symptom:** Robot arm moves partially toward target, then returns to init position without completing the action.

**Potential Causes:**
1. **IK solution quality** — EvoIK may return partial solutions for edge-of-workspace targets
2. **Coordinate transfer accuracy** — MLP may output positions beyond robot's physical reach
3. **Hardware serial timeout** — pypot motor communication can drop after extended operations

**Debugging Steps:**
```bash
# Check IK target positions in logs
# Look for: "Real coordinates: x=..., y=..."
# Verify target is within workspace polygon

# Monitor for serial errors
# Look for: "device reports readiness to read but returned no data"
```

### 7.2 MLLM Detection Accuracy

**Symptom:** Bounding boxes appear correct in visualization but robot targets wrong position.

**Debugging:**
1. Verify bounding box format (Gemini: `[y_min, x_min, y_max, x_max]` in 0-1000 scale)
2. Check normalization: values should be 0-1 after division by 1000
3. Confirm object is within workspace polygon before coordinate transfer

### 7.3 Userdata Key Errors

**Symptom:** `Userdata key 'X' not available` warning in logs

**Cause:** SMACH state declares output_keys but doesn't write to them on all code paths.

**Impact:** Non-fatal warning; execution continues. Fix by ensuring all declared output_keys are written.

---

## 8. Architecture Diagrams

### 8.1 ELMiRA v2 Service Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                      State Machine (SMACH)                      │
├─────────────────────────────────────────────────────────────────┤
│  SPEECH_ASR → LLM_SPEECH_PROCESSOR → EXECUTE_ACTIONS → ...      │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
      ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
      │  MLLM Gateway │ │ IK Solver    │ │ Coord Xfer   │
      │  (llm_api_v2) │ │ (EvoIK)      │ │ (MLP)        │
      └──────────────┘ └──────────────┘ └──────────────┘
              │
      ┌───────┴───────┐
      ▼               ▼
┌──────────────┐ ┌──────────────┐
│ Google       │ │ OpenAI       │
│ Provider     │ │ Provider     │
│ (Gemini 3)   │ │ (GPT-4o)     │
└──────────────┘ └──────────────┘
```

### 8.2 Grounded Action Planning Flow
```
User Speech → ASR → LLM Scene Description
                          │
                          ▼
              ┌───────────────────────┐
              │ DECIDE_GROUNDED_PATH  │
              └───────────────────────┘
                    │           │
        (grounded)  │           │  (separate)
                    ▼           ▼
        ┌─────────────────┐ ┌─────────────────┐
        │ GROUNDED_ACTION │ │ PLAN_ACTION_    │
        │ _CHAT           │ │ TRAJECTORY      │
        │ (single MLLM)   │ │ (detect + plan) │
        └─────────────────┘ └─────────────────┘
                    │           │
                    └─────┬─────┘
                          ▼
              ┌───────────────────────┐
              │ COORDINATE_TRANSFER   │
              │ → PLAN_ACTION_TARGETS │
              │ → SOLVE_IK            │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ JOINT_TRAJECTORY_     │
              │ ITERATOR              │
              │ (execute + init pose) │
              └───────────────────────┘
```