## ELMiRA Language‑to‑Motion Data Flow

This document traces how the current ELMiRA stack (commit state in this workspace) routes information from human speech to NICO’s actuators, with emphasis on the perception–LLM–manipulation loop. Paths, topics, and message types are taken from the live code under `src/ELMiRA/scripts` unless stated otherwise.

---

## 1) Human ➜ LLM side

- **ASR capture** — `scripts/speech_asr.py`
  - Node name: `speech_asr` (action server `elmira/PerformASRAction`).
  - Captures microphone audio (PyAudio/sounddevice), uses energy/VAD gating, plays start/stop beeps, then runs Whisper (CUDA if available).
  - Result: `PerformASRResult.text` (transcript) plus stop metadata.

- **Dialogue orchestrator (SMACH)** — `scripts/state_machine.py`
  - State `SPEECH_ASR` launches the action above; on success sets `userdata.llm_input = "USER: <text>"`.
  - State `LLM_SPEECH_PROCESSOR` calls service `llm_chat` (`elmira/PromptTextLLM`), passing `llm_input`.
  - `llm_chat` response is JSON; `llm_response_callback` parses it to `userdata.llm_actions` (list of action dicts).
  - An iterator (`LLM_RESPONSE_ITERATOR`) walks `llm_actions`, handing each item to `ActionParser`.

- **LLM gateway** — `scripts/llm_api.py`
  - Services:
    - `llm_chat` → textual planning (GPT‑4o assistant thread).
    - `llm_vision` → uploads current `/nico/vision/right` frame, asks the assistant to replan; returns JSON actions.
    - `llm_object_visibility` → single-shot GPT‑4o vision check; replies `bool object_visible` + `system_message`.
  - Assistant instruction enforces a **fixed JSON schema**: actions must be one of `speak`, `describe`, `act`, `initial_pose`, `quit` with extra keys (`text`, `object`, `type`).
  - Context retention: assistant thread and file uploads stay alive for the session; `system_message` strings from failures are fed back into `llm_input` as `SYSTEM: …`.

---

## 2) LLM ➜ Robot side

- **Action parsing** — `scripts/states/action_parser.py`
  - For each action dict:
    - `speak`: stores `tts_text`, returns `speak`.
    - `describe`: returns `describe` (triggers vision-driven replan).
    - `act`: sets `action_type` (`touch|push|push_left|push_right|show`), `target_object` (list with object name), `llm_input` (object name for visibility check), then returns `act`.
    - `initial_pose`: injects `motion_init_pose` as one-step trajectory.
    - `quit`: propagates quit.

- **Describe branch**
  - Head is tilted down (`MoveRobotPart` to `/NICOL/head/goal_joint_space_path`).
  - Service `llm_vision` is called; returned actions overwrite `userdata.llm_actions` and the iterator restarts.

- **Act branch: concurrent planning + verification** — `scripts/states/action_planner.py::ConcurrentPlanAndVerify`
  - Runs two children in parallel; if either fails, both are pre-empted and a `SYSTEM` message is produced.
  - **Visibility check** (`llm_object_visibility` or `mllm_visibility` in v2):
    - Sends the current camera frame + the target object name to GPT‑4o vision.
    - If `object_visible` is false, outcome is `system_out` with the provided message.
  - **Action planner pipeline** (`ActionPlanner`):
    1. **Detect object** — service `object_detector` (OWLv2) or `mllm_detect` (v2) on `/nico/vision/right`; returns `DetectedObject[]` (label, score, center_x/y, width, height).
    2. **Select reachable detection** — `ObjectSelector` picks highest-score detection whose bottom point lies inside a hard-coded table workspace polygon; outputs normalized `image_x/y`. If none, sets `system_message` and aborts.
    3. **Image ➜ table coordinates** — service `image_to_real` (`scripts/coordinate_transfer.py`) runs an implicit MLP (`coordinate_transfer_net.py`) to map `image_x/y` to `(real_x, real_y)` in meters; `table_z` (0.68 m) comes from state machine userdata.
    4. **Pose generation** — `ActionTrajectory` builds one or more `geometry_msgs/Pose` goals with orientation/offset heuristics per action type:
       - `touch`: single contact pose.
       - `show`: offset upward and backward to point.
       - `push`, `push_left`, `push_right`: four-step slide trajectories with lateral/forward offsets and a lift-off.
       - `grasp`: three-step sequence (approach from above, lower to object, lift after close).
       - `place`: three-step sequence (pre-place above, lower to table, retreat after open).
       - `open_hand`, `close_hand`: pure hand actions, no arm movement.
       - Arm choice: right arm if `real_y < 0`, else left arm (bimanual support).
       - Hand action signaling: sets `hand_action` to `"open"` or `"close"` for grasp/place.
    5. **Inverse kinematics** — service `inverse_kinematics` (`scripts/ik_solver.py`):
       - Uses EvoIK with per-arm URDFs (`urdf/nico_left_arm.urdf`, `nico_right_arm.urdf`).
       - Seeds solver with the initial pose joint order; solves each pose in sequence, feeding the previous solution as the next seed.
       - Returns list of `elmira/JointPosition` (joint_name[], position[]).
    6. **Trajectory assembly** — IK results are wrapped into joint dictionaries (`{"l_arm":{names,positions}}` or `{"r_arm":...}`) and appended with the nominal `motion_init_pose` so the arm returns to neutral after acting. `joint_trajectory` is emitted to the executor.

- **Hand control** — `scripts/states/hand_control.py` (NEW)
  - `HandControl` state executes open/close actions on left or right hand.
  - **Pre-grasp**: For grasp actions, `OpenHand` is called before arm approach.
  - **Post-motion**: After trajectory execution, `HandControl` checks `hand_action`:
    - `"close"`: Close fingers for grasping (after arm reaches object).
    - `"open"`: Open fingers for placing (after arm reaches table).
  - **Protocol handling**:
    - Left hand (new SEED Robotics): Uses `Dxl320IO` for XL-320 protocol, motor IDs 34-37.
    - Right hand: Uses `DxlIO` for Protocol 1.0, motor IDs 29, 32.
  - **Timeout-based completion**: Due to unreliable SEED servo position feedback, uses 1.5s timeout.

- **Motion execution** — `scripts/states/move_robot.py`
  - `JointTrajectoryIterator` iterates `joint_trajectory` steps.
  - Each step:
    - Parses head/left/right targets; missing groups are skipped.
    - `MoveRobot` runs three concurrent `MoveRobotPart` sequences (head, left arm, right arm).
    - `MoveRobotPart` calls `open_manipulator_msgs/SetJointPosition` on:
      - Head: `/NICOL/head/goal_joint_space_path`
      - Left arm: `/left/open_manipulator_p/goal_joint_space_path`
      - Right arm: `/right/open_manipulator_p/goal_joint_space_path`
    - Monitors `/NICOL/joint_states` or `/left|right/open_manipulator_p/joint_states` until positions are within ~0.052 rad (≈3°) and velocities are zero.
  - Iterator completes when all poses in the list are reached.
  - **Hand action execution**: After trajectory, `EXECUTE_HAND_ACTION` state runs if `hand_action` is set.

- **Safety / shutdown path**
  - `MOVE_TO_SHUTDOWN_POSITION` drives head to look-down and arms to `motion_safe_pose_*` (predefined joint arrays).
  - Publishes on `/nico/motion/disableTorqueAll` (message type `nicomsg/empty`) to cut torque.

---

## 3) End-to-end scenario trace (“move the orange from the left corner to the right corner”)

1. User speaks the command → `speech_asr` transcribes → `state_machine` sets `llm_input="USER: …"`.
2. `llm_chat` (GPT‑4o) returns actions like: `speak` confirm, `act` with `object:"orange"`, `type:"push_right"`.
3. `ActionParser` selects `act`, stores target, passes control to `ConcurrentPlanAndVerify`.
4. In parallel:
   - GPT‑4o vision (`llm_object_visibility`) checks the orange is visible; if not, returns a `SYSTEM:` message and planning stops.
   - Planner runs: OWLv2 detects the orange; `ObjectSelector` picks a reachable detection; `image_to_real` maps to table coordinates; `ActionTrajectory` builds four push-right poses (approach, push, continue, lift); `inverse_kinematics` produces right-arm joint sets; `motion_init_pose` is appended.
5. `JointTrajectoryIterator` executes the joint sets: head stays in look-down; right arm follows the four poses to slide the orange rightwards, then returns to neutral.
6. Remaining queued actions (e.g., a `speak` acknowledgement) run; the SMACH loop returns to ASR for the next user turn.

---

## 4) Interfaces at a glance

- **Services consumed by SMACH**
  - `llm_chat` (PromptTextLLM) — text ➜ JSON actions.
  - `llm_vision` (PromptVisionLLM) — image + context ➜ JSON actions.
  - `llm_object_visibility` (CheckLLMObjectVisibility) — object presence check.
  - `object_detector` (DetectObjects) — OWLv2 detections.
  - `image_to_real` (CoordinateTransfer) — pixel ➜ table coords.
  - `inverse_kinematics` (InverseKinematics) — poses ➜ joint lists.
  - `nico/text_to_speech/say` (nicomsg/SayText) — TTS playback.

- **Motion command channels**
  - `open_manipulator_msgs/SetJointPosition` services:
    - `/left/open_manipulator_p/goal_joint_space_path`
    - `/right/open_manipulator_p/goal_joint_space_path`
    - `/NICOL/head/goal_joint_space_path`
  - State feedback topics:
    - `/left/open_manipulator_p/joint_states`
    - `/right/open_manipulator_p/joint_states`
    - `/NICOL/joint_states`

- **Camera feed used**
  - `/nico/vision/right` (sensor_msgs/Image) for OWLv2, GPT‑4o vision, and visibility checks.

---

## 5) Upgrade considerations for newer multimodal LLMs

- Swap-in point is `scripts/llm_api.py`; keep the JSON schema stable or extend `ActionParser` plus `ActionTrajectory` for new verbs (e.g., grasp/place with gripper control).
- Motor side stays ROS-native; no changes needed to the IK, coordinate transfer, or OpenManipulator services when changing the LLM, as long as the action schema is honored.
- For faster cycles, ensure the new LLM supports streamed responses and image inputs; the rest of the pipeline (detection → mapping → IK → SetJointPosition) is already asynchronous and GPU-accelerated where available.
