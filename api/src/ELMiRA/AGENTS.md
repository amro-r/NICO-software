# Agents Catalogue

## Dialogue Orchestrator — `scripts/state_machine.py`
- **Role**: Top-level SMACH state machine that loops over ASR → LLM reasoning → action execution and shutdown handling.
- **ROS Interfaces**:
  - Consumes `elmira/PerformASRAction` (`speech_asr` action server).
  - Calls services `llm_chat`, `llm_vision`, `llm_object_visibility`, `object_detector`, `image_to_real`, and `inverse_kinematics`.
  - Publishes `/nico/motion/disableTorqueAll` on shutdown.
- **Key Behaviours**: Maintains userdata (poses, prompts), iterates over LLM-produced action lists, and dispatches to planner/motion sub-state machines.

## Speech Perception — `scripts/speech_asr.py`
- **Role**: Multi-goal Whisper-based ASR action server with adaptive VAD and optional live feedback.
- **ROS Interfaces**:
  - Action server `speech_asr` providing `PerformASRAction`.
  - Optionally publishes live text feedback through action feedback messages.
- **Key Behaviours**: Continuous microphone capture, start/stop beep cues, CUDA-enabled transcription, cancellation handling via `MultiActionServer`.

## Language Model Gateway — `scripts/llm_api.py`
- **Role**: Wraps OpenAI Assistants/GPT-4o for text planning, vision grounding, and object-visibility verification.
- **ROS Interfaces**:
  - Services `llm_chat` (`PromptTextLLM`), `llm_vision` (`PromptVisionLLM`), and `llm_object_visibility` (`CheckLLMObjectVisibility`).
- **Key Behaviours**: Maintains assistant thread state, acquires right-eye camera frames, uploads images to OpenAI, cleans temporary files on shutdown.

## Vision Grounding — `scripts/object_localiser.py`
- **Role**: OWLv2-based zero-shot detector that maps text queries to bounding boxes in the right-eye camera image.
- **ROS Interfaces**:
  - Service `object_detector` (`DetectObjects`) returning `DetectedObject` arrays.
  - Publishes annotated debug images on `owlv2_server/result_image`.
- **Key Behaviours**: Resizes frames, thresholds detections, draws overlays, and forwards scores/boxes to the action planner.

## Coordinate Transfer — `scripts/coordinate_transfer.py`
- **Role**: Neural implicit model that converts image-space detections to table-space coordinates for manipulation.
- **ROS Interfaces**:
  - Service `image_to_real` (`CoordinateTransfer`).
- **Key Behaviours**: Loads MLP weights (`model_checkpoints/implicit_model_weights.pth`), performs derivative-free sampling to infer world coordinates.

## Arm Kinematics — `scripts/ik_solver.py`
- **Role**: EvoIK-backed inverse kinematics solver for left and right manipulators.
- **ROS Interfaces**:
  - Service `inverse_kinematics` (`InverseKinematics`) outputting sequences of `elmira/JointPosition`.
- **Key Behaviours**: Loads per-arm URDFs, orders seed joints to match solver expectations, iteratively seeds solutions to produce smooth trajectories.

## Motion Executors — `scripts/states/move_robot.py`
- **Role**: SMACH helpers for dispatching joint trajectories and monitoring execution.
- **ROS Interfaces**:
  - Calls `open_manipulator_msgs/SetJointPosition` services for head and arm chains.
  - Subscribes to joint state topics for convergence monitoring.
- **Key Behaviours**: Executes synchronized head/arm movements, iterates multi-step trajectories, enforces velocity and angle tolerances before progressing.

## Action Planning States — `scripts/states/action_parser.py` & `scripts/states/action_planner.py`
- **Role**: Parse LLM directives, select target detections, assemble manipulation poses, and manage concurrent planning with LLM-based verification.
- **ROS Interfaces**: Reuse detectors, mapper, IK services; share userdata back to the dialogue state machine as system messages or trajectories.
- **Key Behaviours**: Workspace filtering, action-type-specific pose generation (`touch`, `push`, `show`, etc.), concurrency guard that cancels execution when vision verification fails.

## Shared Utilities
- `scripts/multi_action_server.py`: Generic multi-client action server wrapper used by ASR.
- `scripts/coordinate_transfer_net.py`: Defines the implicit network and workspace polygon utilities reused by planners.
- `json/`, `urdf/`, `model_checkpoints/`: Configuration artefacts supporting the runtime agents above.

These agents cooperate through ROS services/actions to realise the perception-language-action loop that characterises ELMiRA.
