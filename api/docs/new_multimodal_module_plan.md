# Multimodal Control Module – ROS Noetic Architecture Plan

## 1. Goals & Scope
- Deploy a next-generation multimodal LLM controller (GPT‑5 or Gemini 2.5 Flash) that supersedes the legacy ELMiRA stack.
- **Preserve the existing ROS Noetic environment and hardware interfaces** (motion, vision, tactile, audio drivers). No changes to low-level packages (`nicomotion`, `nicovision`, `nicotouch`, `nicoface`, etc.).
- Introduce modern perception, speech, and planning components while interacting with the robot exclusively through the current ROS topics/services.
- Provide a clear migration path that allows operators to switch between the old and new stacks without touching hardware configuration.

## 2. Architectural Principles
1. **Drop-in replacement**: New nodes coexist within the ROS Noetic graph, reusing existing topic names where practical (or remapped via launch files).
2. **Multimodal context manager**: All sensor streams, dialogue, and past actions are aggregated into a single session memory passed to the LLM.
3. **Guarded execution**: LLM outputs must be validated by deterministic planners before commanding hardware.
4. **Composable upgrades**: Perception (vision, ASR, TTS) upgrades are modular and can be toggled on/off via launch arguments.
5. **Observability**: Maintain ROS-native logging/diagnostics (rosconsole, `/diagnostics`) without introducing non-ROS tooling.

## 3. Proposed Package Layout

```
src/
  multimodal_core/
    launch/
      multimodal_controller.launch        # wires sensors → core → execution guards
    scripts/
      multimodal_hub.py                   # main orchestrator node
      llm_gateway.py                      # wraps GPT‑5 / Gemini APIs
      context_builder.py                  # aggregates sensor summaries
      intent_parser.py                    # normalises LLM outputs
      execution_supervisor.py             # safety checks, action gating
  perception_modern/
    scripts/
      grounding_dino_node.py              # replaces OWLv2
      sam2_mask_node.py                   # optional segmentation refinement
      depth_estimator_node.py             # for table height / grasp planning
  speech_modern/
    scripts/
      streaming_asr_node.py               # Whisper large-v3 turbo + Silero VAD
      neural_tts_node.py                  # ElevenLabs / Coqui XTTS interface
  planning_toolbox/
    scripts/
      task_guard_node.py                  # reachability & collision validation via MoveIt
      trajectory_builder.py               # reuses nicomotion services
```

Each package is a pure ROS Noetic catkin package; dependencies remain Python 3.8 compatible.

## 4. Key Nodes & Responsibilities

| Node | Namespace | Replaces / Extends | Responsibilities | ROS I/O (reuse existing topics/services) |
| --- | --- | --- | --- | --- |
| `multimodal_hub` | `/multimodal_core` | Replaces `elmira/state_machine.py` | Coordinates dialogue loop, builds prompts, dispatches intents | Subscribes `/multimodal/asr_text`, `/multimodal/vision/objects`, `/nico/vision/right`; Publishes `/multimodal/intent`, `/multimodal/system_feedback` |
| `llm_gateway` | `/multimodal_core` | New | Handles GPT‑5 / Gemini REST streaming, enforces JSON schema | Service `llm_multimodal_query` |
| `context_builder` | `/multimodal_core` | New | Summarises world state (object list, joint status, touch events) | Subscribes `/nico/motion/state`, `/multimodal/perception_state`, `/nicotouch/*` |
| `execution_supervisor` | `/multimodal_core` | Replaces `ConcurrentPlanAndVerify` | Validates intents (allowed verbs, resource conflicts) before forwarding to planner | Service `validate_intent`, publishes `/multimodal/validated_intent` |
| `grounding_dino_node` | `/multimodal/perception` | Replaces `owlv2_server` | Vision-language detection, outputs instance IDs and confidences | Subscribes `/nico/vision/right`; service `detect_objects` (same signature as legacy) |
| `depth_estimator_node` | `/multimodal/perception` | Replaces `coordinate_transfer` | Uses Depth Anything v2 / stereo to produce metric coordinates | Service `image_to_table` (same structure as old `CoordinateTransfer`) |
| `task_guard_node` | `/multimodal/planning` | Supersedes EvoIK-based planner | Calls MoveIt (existing ROS Noetic installation) to generate `FollowJointTrajectory` goals; falls back to existing `nicomotion` services | Subscribes `/multimodal/validated_intent`; publishes `/nicomotion/commands` |
| `streaming_asr_node` | `/multimodal/audio` | Supersedes `speech_asr` | Low-latency ASR with diarisation; outputs plain text and partials | Publishes `/multimodal/asr_text`, `/multimodal/asr_partial`; action interface optional |
| `neural_tts_node` | `/multimodal/audio` | Supersedes `nico/text_to_speech/say` | Accesses modern neural TTS, still exposes the same ROS service signature for compatibility | Provides service `nico/text_to_speech/say` (same request/response) |

## 5. Data & Control Flow
1. **Audio capture** → `streaming_asr_node` provides live transcripts under the existing `PerformASRAction` action server name to keep compatibility. Result published to `/multimodal/asr_text`.
2. **Vision capture** remains via `/nico/vision/right`. `grounding_dino_node` replaces OWLv2 but advertises the same `DetectObjects` service (topic names unchanged) and adds richer metadata (object embeddings, segmentation masks) through a new topic `/multimodal/perception_state`.
3. **World state aggregation**: `context_builder` fuses ASR transcripts, detected objects, tactile events, and joint states into a concise JSON summary kept in memory and provided to `multimodal_hub`.
4. **LLM reasoning**: `multimodal_hub` constructs prompts: textual user input, world snapshot, last system status. It invokes `llm_gateway` with the selected provider (GPT‑5 or Gemini). The response adheres to a strict schema, e.g.:
   ```json
   {
     "actions": [
       {"verb": "speak", "payload": {"text": "..."}},
       {"verb": "manipulate", "payload": {"hand": "right", "target": "cup", "policy": "push_forward"}},
       {"verb": "observe", "payload": {"focus": "table"}}
     ]
   }
   ```
5. **Validation & planning**: `execution_supervisor` screens verbs against white-listed capabilities, checks resource locks, and forwards allowed commands to `task_guard_node`.
6. **Motion execution**: `task_guard_node` uses MoveIt (Noetic) with existing robot descriptions to plan trajectories, then dispatches them via existing services (`/left/open_manipulator_p/goal_joint_space_path`, etc.). If MoveIt fails, it falls back to simpler scripted motions, ensuring the hardware interface remains unchanged.
7. **Speech output**: `neural_tts_node` handles `speak` commands, continuing to service `nico/text_to_speech/say` so downstream tools remain compatible.
8. **Feedback loop**: Execution status, planner results, and error messages are published to `/multimodal/system_feedback` and fed back into the next LLM prompt.

## 6. Component Replacement Matrix

| Legacy Component | New Component | Interface Strategy |
| --- | --- | --- |
| `elmira/state_machine.py` | `multimodal_hub` + helpers | Topics/services identical where feasible; wrap legacy action servers for gradual switchover |
| `speech_asr.py` | `streaming_asr_node` | Provide same `PerformASRAction`; add topic for streaming partial transcripts |
| `llm_api.py` | `llm_gateway` | Extended to support GPT‑5/Gemini; new schema; maintain ROS service call semantics |
| `object_localiser.py` | `grounding_dino_node` | Same `DetectObjects` service signature; extra topic for masks |
| `coordinate_transfer.py` | `depth_estimator_node` | Same service name `image_to_real`; now uses depth estimation |
| `ik_solver.py` + `states/move_robot.py` | `task_guard_node` + `trajectory_builder` | Shift planning to MoveIt while still executing through existing open manipulator services |
| `nicoros/TextToSpeech.py` | `neural_tts_node` | Expose same service; optional pitch/speed extensions |

## 7. Implementation Roadmap (Noetic-Compliant)

### Phase 1 – Baseline Harness
- Mirror existing launch files to spin up hardware drivers unchanged.
- Create `multimodal_core` package with minimal `multimodal_hub` that simply relays ASR text to LLM and logs responses (no actuation yet).
- Verify GPT‑5 and Gemini integration (API keys via env vars). Ensure context summarisation fits provider limits.

### Phase 2 – Perception Upgrades
- Replace OWLv2 server by deploying `grounding_dino_node` with the same ROS service definition; keep fallback launch option to revert.
- Add optional SAM2 segmentation node for object masks; produce new topic `/multimodal/perception_state`.
- Implement `depth_estimator_node` using Depth Anything v2 (or stereo disparity). Maintain compatibility with `CoordinateTransfer` service name.

### Phase 3 – Speech Pipeline
- Implement `streaming_asr_node` (Whisper large-v3 turbo via CTranslate2) exposing identical action API plus new partial transcript topic.
- Implement `neural_tts_node` bridging to ElevenLabs (or Coqui XTTS). Wrap it inside ROS service with same request fields so existing nodes remain compatible.

### Phase 4 – Execution Guard & Planning
- Develop `execution_supervisor` and `task_guard_node` using MoveIt for path planning; integrate with existing `/left/right/open_manipulator_p/goal_joint_space_path` services for execution.
- Add safety constraints (workspace polygons, velocity and acceleration limits, collision checks) before sending commands.
- Provide clear fallback behaviour (LLM notified via `SYSTEM:` message) if planning fails.

### Phase 5 – Rollout & Toggle
- Offer launch arguments to switch between legacy ELMiRA stack and new multimodal stack without stopping core hardware nodes.
- Create ROS bag-based regression tests comparing performance across typical tasks (touch, push, show).
- Document operator procedures, environment variables (API keys), and resource requirements (GPU for perception/ASR).

## 8. Risk Management
- **Cloud LLM Reliability**: Provide local fallback (e.g., LLaVA-Next) and allow offline mode where the hub reverts to scripted behaviours.
- **Latency**: Use streaming APIs (server-sent events) to start planning while LLM continues generating; keep context summarisation compact.
- **Compatibility**: Maintain existing service names and message types. Any additions must be optional and off by default.
- **Resource Usage**: Grounding DINO & Whisper large require GPU memory. Include configuration for model quantisation or CPU fallbacks with reduced performance.

## 9. Deliverables
- New catkin packages (`multimodal_core`, `perception_modern`, `speech_modern`, `planning_toolbox`) with launch files and configuration.
- Updated documentation describing architecture, environment variables, safety policies, and migration steps.
- Test suites (rostest / pytest) verifying intent parsing, perception accuracy, motion plan validation, and end-to-end conversational tasks.
- Scripts for easy rollback to ELMiRA if needed.

This plan modernises the NICO interaction stack while respecting the ROS Noetic ecosystem and existing hardware interfaces, enabling a high-confidence transition to multimodal LLM-driven control without touching low-level robot components.
