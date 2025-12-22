# ELMiRA v2 Upgrade Plan: Modern Multimodal LLM Integration

**Document Version:** 2.1  
**Date:** December 16, 2025  
**Status:** Bimanual Support Implemented

---

## Table of Contents
1. [Executive Summary & Goals](#section-1-executive-summary--goals)
2. [Current System Analysis](#section-1-current-system-analysis)
3. [Tech Stack & Dependencies](#section-1-tech-stack--dependencies)
4. [File Structure](#section-2-file-structure)
5. [Implementation Details](#section-2-implementation-details)
6. [Service Contracts](#section-2-service-contracts)
7. [State Machine Updates](#section-3-state-machine-updates)
8. [Testing & Validation](#section-3-testing--validation)
9. [Rollout & Rollback](#section-3-rollout--rollback)
10. [Timeline & Risks](#section-3-timeline--risks)
11. [Bimanual Support](#section-4-bimanual-support) ← **NEW**

---

# SECTION 1: Analysis, Tech Stack & Architecture

## 1.1 Executive Summary

**Goal:** Replace the current `llm_api.py` + OWLv2 vision pipeline with a unified multimodal LLM (GPT-4o/Gemini 2.5 Flash) to achieve:
- **3-5x faster response time** (from 5-12s to 1.5-3s)
- **Single API call** instead of 2-3 separate calls
- **Built-in visual grounding** eliminating OWLv2 dependency for most cases
- **Streaming responses** for immediate TTS feedback
- **Bimanual manipulation** with both left and right hands (NEW)

**Constraints:**
- Retain all hardware-facing ROS interfaces (IK, motion, coordinate transfer)
- Keep SMACH state machine topology intact
- Maintain backward compatibility with v1 via ROS params

---

## 1.2 Current System Analysis

### 1.2.1 Data Flow: Speech → LLM → Motor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CURRENT ARCHITECTURE (v1)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐    ┌───────────┐    ┌────────────┐    ┌──────────────────┐   │
│  │Microphone│───▶│speech_asr │───▶│ llm_chat   │───▶│  ActionParser    │   │
│  │(PyAudio) │    │ (Whisper) │    │ (GPT-4o)   │    │                  │   │
│  └──────────┘    └───────────┘    └────────────┘    └────────┬─────────┘   │
│                                                               │             │
│                         ┌─────────────────────────────────────┘             │
│                         ▼                                                   │
│              ┌─────────────────────┐                                        │
│              │ConcurrentPlanVerify │                                        │
│              └──────────┬──────────┘                                        │
│                         │                                                   │
│         ┌───────────────┼───────────────┐                                   │
│         ▼               ▼               ▼                                   │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐                          │
│  │llm_object_ │  │  OWLv2     │  │ coordinate   │                          │
│  │visibility  │  │ Detection  │  │ transfer     │                          │
│  │ (GPT-4o)   │  │            │  │ (MLP)        │                          │
│  └────────────┘  └─────┬──────┘  └──────┬───────┘                          │
│                        │                │                                   │
│                        └────────┬───────┘                                   │
│                                 ▼                                           │
│                    ┌─────────────────────┐                                  │
│                    │  ActionTrajectory   │                                  │
│                    │  (Pose Generation)  │                                  │
│                    └──────────┬──────────┘                                  │
│                               ▼                                             │
│                    ┌─────────────────────┐                                  │
│                    │    EvoIK Solver     │                                  │
│                    │    (GPU-based)      │                                  │
│                    └──────────┬──────────┘                                  │
│                               ▼                                             │
│                    ┌─────────────────────┐                                  │
│                    │   MoveRobot         │                                  │
│                    │ (SetJointPosition)  │                                  │
│                    └─────────────────────┘                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2.2 Current Bottlenecks

| Component | Current Latency | Issue |
|-----------|-----------------|-------|
| `llm_chat` (GPT-4o Assistant API) | 2-5s | Thread-based polling at 1Hz, no streaming |
| `llm_object_visibility` | 1-3s | Separate API call with image upload |
| `OWLv2 Detection` | 0.5-1s | Separate model, redundant vision processing |
| `coordinate_transfer` | <50ms | ✅ Fast (local MLP) |
| `ik_solver` (EvoIK) | 100-500ms | ✅ GPU-accelerated |
| `move_robot` | Variable | ✅ Hardware-dependent |

**Total time before motion starts: 5-12 seconds**

### 1.2.3 Current LLM Action Schema

The LLM returns JSON with this structure:
```json
{
  "actions": [
    {"action": "speak", "text": "I'll move the orange now."},
    {"action": "act", "object": "orange", "type": "push_right"},
    {"action": "describe"},
    {"action": "quit"}
  ]
}
```

**Valid action types for `act`:**
- `touch` - Touch object with hand
- `push` - Push object forward
- `push_left` - Push object to the left
- `push_right` - Push object to the right
- `show` - Point at object

---

## 1.3 Tech Stack & Dependencies

### 1.3.1 Existing Stack (Unchanged)

| Component | Version | Purpose |
|-----------|---------|---------|
| **ROS** | Noetic | Middleware |
| **Ubuntu** | 20.04 LTS | OS |
| **Python** | 3.8 | Runtime |
| **PyTorch** | 1.x/2.x | ML Backend |
| **Whisper** | openai-whisper | ASR |
| **EvoIK** | evo_ik | Inverse Kinematics |
| **OpenManipulator** | open_manipulator_msgs | Motor control |
| **SMACH** | smach_ros | State machine |

### 1.3.2 New Dependencies for v2

| Package | Version | Purpose | Installation |
|---------|---------|---------|--------------|
| **openai** | >=1.40.0 | GPT-4o/GPT-4.5 API | `pip install openai>=1.40.0` |
| **google-genai** | >=1.0.0 | Gemini 2.5 Flash API | `pip install google-genai` |
| **httpx** | >=0.25.0 | Async HTTP (streaming) | `pip install httpx` |
| **pydantic** | >=2.0.0 | Schema validation | `pip install pydantic>=2.0` |
| **tenacity** | >=8.0.0 | Retry logic | `pip install tenacity` |

### 1.3.3 Requirements File (New)

```
# api/src/ELMiRA/requirements_v2.txt

# MLLM Providers
openai>=1.40.0
google-genai>=1.0.0

# Async & HTTP
httpx>=0.25.0
aiohttp>=3.9.0

# Validation & Schema
pydantic>=2.0.0
jsonschema>=4.0.0

# Utilities
tenacity>=8.0.0
python-dotenv>=1.0.0

# Existing (for reference)
# torch, whisper, cv_bridge, etc. already in requirements.txt
```

---

## 1.4 Proposed Architecture (v2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NEW ARCHITECTURE (v2)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐    ┌───────────┐    ┌────────────────────────────────────┐   │
│  │Microphone│───▶│speech_asr │───▶│        UNIFIED MLLM GATEWAY        │   │
│  │(PyAudio) │    │ (Whisper) │    │         (llm_api_v2.py)            │   │
│  └──────────┘    └───────────┘    │                                    │   │
│                                   │  • Single API call with image      │   │
│                                   │  • Streaming JSON responses        │   │
│                                   │  • Built-in object grounding       │   │
│                                   │  • Tool/Function calling           │   │
│                                   │  • Provider abstraction            │   │
│                                   │    (OpenAI / Google)               │   │
│                                   └─────────────────┬──────────────────┘   │
│                                                     │                       │
│                          ┌──────────────────────────┴─────┐                │
│                          ▼                                ▼                │
│               ┌──────────────────┐            ┌──────────────────┐        │
│               │  ActionParser    │            │  Detected Objects │        │
│               │  (Extended)      │            │  (from MLLM)      │        │
│               └────────┬─────────┘            └────────┬─────────┘        │
│                        │                               │                   │
│                        └───────────────┬───────────────┘                   │
│                                        ▼                                   │
│                    ┌─────────────────────────────────┐                     │
│                    │     ActionPlanner (Simplified)   │                     │
│                    │  • Skip OWLv2 when MLLM grounds │                     │
│                    │  • Direct to coordinate_transfer │                     │
│                    └─────────────────┬───────────────┘                     │
│                                      ▼                                     │
│                    ┌─────────────────────────────────┐                     │
│                    │        UNCHANGED PIPELINE        │                     │
│                    │  coordinate_transfer → EvoIK →  │                     │
│                    │  ActionTrajectory → MoveRobot   │                     │
│                    └─────────────────────────────────┘                     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  FALLBACK PATH (when use_mllm_grounding=false or offline)          │    │
│  │  OWLv2 Detection → ObjectSelector → coordinate_transfer → ...     │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.4.1 Key Architecture Changes

1. **Unified MLLM Gateway** (`llm_api_v2.py`)
   - Single entry point for all LLM operations
   - Combines: chat, vision, visibility check, object detection
   - Supports streaming for faster TTS trigger

2. **Provider Abstraction**
   - Swap between OpenAI (GPT-4o) and Google (Gemini 2.5 Flash)
   - Environment variable: `MLLM_PROVIDER=openai|google`

3. **Built-in Visual Grounding**
   - MLLM returns object bounding boxes directly
   - Eliminates separate OWLv2 call in most cases
   - OWLv2 kept as fallback for offline/precision mode

4. **Cached Image Grabber**
   - Single frame capture shared across services
   - Reduces ROS topic wait overhead

---

## 1.5 Design Principles

1. **Backward Compatibility**
   - All v1 services remain functional
   - ROS params control v1/v2 switching
   - No changes to hardware interfaces

2. **Minimal SMACH Changes**
   - Same state topology
   - Only service targets change
   - New action types are additive

3. **Graceful Degradation**
   - Cloud failure → OWLv2 fallback
   - Timeout handling with cached detections
   - Local-only mode available

4. **Observability**
   - Latency metrics per component
   - Debug image publishing
   - Structured logging

---

**END OF SECTION 1**

---

# SECTION 2: File Structure, Implementation & Service Contracts

## 2.1 Complete File Structure

```
api/src/ELMiRA/
├── scripts/                          # Existing scripts directory
│   ├── coordinate_transfer.py        # ✅ UNCHANGED
│   ├── coordinate_transfer_net.py    # ✅ UNCHANGED
│   ├── ik_solver.py                  # ✅ UNCHANGED
│   ├── llm_api.py                    # ✅ UNCHANGED (v1, kept for fallback)
│   ├── multi_action_server.py        # ✅ UNCHANGED
│   ├── object_localiser.py           # ✅ UNCHANGED (OWLv2, kept for fallback)
│   ├── speech_asr.py                 # ✅ UNCHANGED
│   ├── state_machine.py              # ⚠️  MINOR UPDATES (param-based branching)
│   │
│   ├── states/                       # Existing states directory
│   │   ├── action_parser.py          # ⚠️  MINOR UPDATES (new action types)
│   │   ├── action_planner.py         # ⚠️  MINOR UPDATES (MLLM detection path)
│   │   └── move_robot.py             # ✅ UNCHANGED
│   │
│   └── v2/                           # 🆕 NEW v2 implementation directory
│       ├── __init__.py               # Package init
│       ├── llm_api_v2.py             # 🆕 Unified MLLM gateway node
│       ├── providers/                # 🆕 Provider adapters
│       │   ├── __init__.py
│       │   ├── base.py               # 🆕 Abstract provider interface
│       │   ├── openai_provider.py    # 🆕 OpenAI/GPT-4o adapter
│       │   └── google_provider.py    # 🆕 Gemini 2.5 Flash adapter
│       ├── schemas/                  # 🆕 Pydantic schemas
│       │   ├── __init__.py
│       │   ├── actions.py            # 🆕 Action schema definitions
│       │   └── detections.py         # 🆕 Detection schema definitions
│       ├── utils/                    # 🆕 Utility modules
│       │   ├── __init__.py
│       │   ├── image_cache.py        # 🆕 Cached image grabber
│       │   ├── rate_limiter.py       # 🆕 API rate limiting
│       │   └── metrics.py            # 🆕 Latency tracking
│       └── config/                   # 🆕 Configuration
│           ├── __init__.py
│           ├── prompts.py            # 🆕 System prompts
│           └── tool_schemas.py       # 🆕 Function calling schemas
│
├── srv/                              # Service definitions
│   ├── PromptTextLLM.srv             # ✅ UNCHANGED (v1)
│   ├── PromptVisionLLM.srv           # ✅ UNCHANGED (v1)
│   ├── CheckLLMObjectVisibility.srv  # ✅ UNCHANGED (v1)
│   ├── DetectObjects.srv             # ✅ UNCHANGED (v1)
│   ├── CoordinateTransfer.srv        # ✅ UNCHANGED
│   ├── InverseKinematics.srv         # ✅ UNCHANGED
│   │
│   ├── PromptMLLM.srv                # 🆕 Unified MLLM service
│   ├── PromptMLLMWithGrounding.srv   # 🆕 MLLM + object detection
│   └── DetectWithMLLM.srv            # 🆕 MLLM-based detection
│
├── msg/                              # Message definitions
│   ├── DetectedObject.msg            # ✅ UNCHANGED
│   ├── JointPosition.msg             # ✅ UNCHANGED
│   ├── PerformASRAction.msg          # ✅ UNCHANGED
│   │
│   └── MLLMDetection.msg             # 🆕 Extended detection with confidence
│
├── launch/
│   ├── init_nodes.launch             # ✅ UNCHANGED (v1 launch)
│   ├── camera.launch                 # ✅ UNCHANGED
│   │
│   ├── init_nodes_v2.launch          # 🆕 v2 launch file
│   └── mllm_only.launch              # 🆕 MLLM gateway standalone
│
├── config/                           # 🆕 Configuration directory
│   ├── mllm_config.yaml              # 🆕 MLLM parameters
│   └── providers.yaml                # 🆕 Provider settings
│
├── requirements.txt                  # ✅ UNCHANGED (v1 deps)
├── requirements_v2.txt               # 🆕 v2 additional deps
│
└── CMakeLists.txt                    # ⚠️  UPDATE (add new srv/msg)
    package.xml                       # ⚠️  UPDATE (add new deps)
```

---

## 2.2 New Service Definitions

### 2.2.1 `srv/PromptMLLM.srv` - Unified MLLM Service

```
# PromptMLLM.srv
# Unified multimodal LLM service for ELMiRA v2
# Handles text prompts with optional image input

string prompt                    # User/system text input
bool include_image               # If true, capture and send current camera frame
string image_topic               # Camera topic (default: /nico/vision/right)
float32 temperature              # LLM temperature (0.0-2.0, default: 0.7)
int32 max_tokens                 # Max response tokens (default: 1024)
---
string response_json             # JSON string with actions array
bool success                     # True if request completed successfully
string error_message             # Error details if success=false
float32 latency_ms               # Request latency in milliseconds
```

### 2.2.2 `srv/PromptMLLMWithGrounding.srv` - MLLM with Object Detection

```
# PromptMLLMWithGrounding.srv
# MLLM service with built-in object grounding/detection
# Returns both action plan and detected object locations

string prompt                    # User/system text input
string[] detect_objects          # List of objects to detect and ground
bool include_image               # If true, capture current camera frame
float32 temperature              # LLM temperature
---
string response_json             # JSON string with actions array
DetectedObject[] detections      # Grounded object locations
bool success
string error_message
float32 latency_ms
```

### 2.2.3 `srv/DetectWithMLLM.srv` - MLLM-based Detection Only

```
# DetectWithMLLM.srv
# Use MLLM for object detection (alternative to OWLv2)
# Compatible with existing DetectedObject message

string[] texts                   # Object labels to detect
float32 confidence_threshold     # Minimum confidence (default: 0.5)
---
DetectedObject[] objects         # Detected objects with bounding boxes
bool success
string error_message
float32 latency_ms
```

### 2.2.4 `msg/MLLMDetection.msg` - Extended Detection Message

```
# MLLMDetection.msg
# Extended detection message with MLLM-specific fields

string label                     # Object label
float64 score                    # Confidence score (0-1)
float64 center_x                 # Normalized center x (0-1)
float64 center_y                 # Normalized center y (0-1)
float64 width                    # Normalized width
float64 height                   # Normalized height

# Extended fields for MLLM
string grounding_text            # Natural language grounding description
float64[] bbox_raw               # Raw bounding box [x_min, y_min, x_max, y_max]
string provider                  # Which provider detected this (openai/google)
```

---

## 2.3 Implementation Details

### 2.3.1 `scripts/v2/__init__.py`

```python
#!/usr/bin/env python3
"""
ELMiRA v2 - Modern Multimodal LLM Integration
"""

__version__ = "2.0.0"
__author__ = "ELMiRA Team"

from .llm_api_v2 import MLLMGateway
```

---

**END OF SECTION 2**

---

*Please approve Section 2 before I continue with Section 3 (Main Gateway Node, State Machine Updates, Launch Files, Testing & Rollout)*

---

# SECTION 3: Gateway Node, State Machine, Launch, Testing & Rollout

## 3.1 Main Gateway Node (`llm_api_v2.py`)

### 3.1.1 Node Specifications

| Attribute | Value |
|-----------|-------|
| **Node Name** | `mllm_gateway` |
| **Package** | `elmira` |
| **Script Path** | `scripts/v2/llm_api_v2.py` |
| **Dependencies** | providers, utils, schemas modules |

### 3.1.2 ROS Services Provided

| Service Name | Type | Description |
|--------------|------|-------------|
| `mllm_chat` | `PromptMLLM` | Unified chat with optional image |
| `mllm_chat_with_grounding` | `PromptMLLMWithGrounding` | Chat + object detection |
| `mllm_detect` | `DetectWithMLLM` | Object detection only |
| `mllm_visibility` | `CheckLLMObjectVisibility` | Object visibility check |

### 3.1.3 ROS Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `~provider` | string | `"openai"` | MLLM provider (`openai` or `google`) |
| `~model` | string | `"gpt-4o"` | Model name |
| `~temperature` | float | `0.7` | Default temperature |
| `~max_tokens` | int | `1024` | Default max tokens |
| `~timeout` | float | `30.0` | Request timeout (seconds) |
| `~image_topic` | string | `"/nico/vision/right"` | Camera topic |
| `~enable_streaming` | bool | `true` | Enable streaming responses |
| `~cache_duration` | float | `0.5` | Image cache duration (seconds) |

### 3.1.4 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes (if openai) | OpenAI API key |
| `GOOGLE_API_KEY` | Yes (if google) | Google AI API key |
| `MLLM_PROVIDER` | No | Override provider selection |

### 3.1.5 Gateway Features

1. **Provider Factory Pattern**
   - Dynamically instantiate provider based on config
   - Hot-swappable at runtime via ROS param

2. **Backward Compatibility Layer**
   - Also advertise legacy service names (`llm_chat`, `llm_vision`, etc.)
   - Route to v2 implementation when `use_mllm=true`

3. **Error Handling**
   - Retry with exponential backoff (3 attempts)
   - Timeout handling with graceful degradation
   - Structured error messages in response

4. **Metrics & Logging**
   - Latency tracking per request
   - Provider/model usage logging
   - Debug image publishing to `/mllm_gateway/debug_image`

---

## 3.2 State Machine Updates

### 3.2.1 Changes to `state_machine.py`

**New ROS Parameters:**
```yaml
~use_mllm: true              # Use v2 MLLM gateway
~use_mllm_grounding: true    # Use MLLM for object detection
~mllm_provider: "openai"     # Provider selection
```

**Service Routing Logic:**
- If `use_mllm=true`: Route to `mllm_chat` instead of `llm_chat`
- If `use_mllm=false`: Use existing `llm_chat` (v1 behavior)

**Affected States:**
1. `LLM_SPEECH_PROCESSOR` - Swap service target
2. `LLM_SCENE_DESCRIPTION` - Swap service target
3. Add new userdata key: `mllm_detections` for grounded objects

### 3.2.2 Changes to `action_parser.py`

**New Action Types (Optional):**
- `grasp` - Pick up object
- `place` - Put down object at location

**New Output Keys:**
- `mllm_detections` - Pass through MLLM detections
- `gripper_action` - For grasp/place actions

### 3.2.3 Changes to `action_planner.py`

**New Perception Path:**

```
If use_mllm_grounding AND mllm_detections available:
    → Skip OBJECT_DETECTION state
    → Use mllm_detections directly
    → Continue to COORDINATE_TRANSFER
Else:
    → Use existing OWLv2 path (fallback)
```

**New State: `USE_MLLM_DETECTION`**
- Converts MLLM detection format to existing `DetectedObject` format
- Passes to `ObjectSelector` unchanged

### 3.2.4 No Changes Required

- `move_robot.py` - ✅ No changes
- `ik_solver.py` - ✅ No changes
- `coordinate_transfer.py` - ✅ No changes
- `speech_asr.py` - ✅ No changes

---

## 3.3 Launch Files

### 3.3.1 `init_nodes_v2.launch`

**Purpose:** Full ELMiRA v2 stack with MLLM gateway

**Nodes Launched:**
1. Camera (from `camera.launch`)
2. Joint controller (from `joint_controller.launch`)
3. `speech_asr` - ASR node
4. `mllm_gateway` - v2 LLM gateway (NEW)
5. `coordinate_transfer` - Coordinate mapper
6. `ik_solver` - IK solver
7. `text_to_speech` - TTS node

**Optional Nodes (via args):**
- `object_localiser` - OWLv2 fallback (if `use_owlv2_fallback:=true`)

**Arguments:**
```xml
<arg name="mllm_provider" default="openai"/>
<arg name="use_mllm_grounding" default="true"/>
<arg name="use_owlv2_fallback" default="false"/>
```

### 3.3.2 `mllm_only.launch`

**Purpose:** Standalone MLLM gateway for testing

**Nodes Launched:**
1. Camera (from `camera.launch`)
2. `mllm_gateway` - v2 LLM gateway only

**Use Case:** Testing MLLM responses without full robot stack

---

## 3.4 Configuration Files

### 3.4.1 `config/mllm_config.yaml`

```yaml
# MLLM Gateway Configuration

provider: "openai"  # or "google"

openai:
  model: "gpt-4o"
  temperature: 0.7
  max_tokens: 1024

google:
  model: "gemini-2.5-flash"
  temperature: 0.7
  max_tokens: 1024

common:
  timeout: 30.0
  retry_attempts: 3
  image_quality: 85
  cache_duration: 0.5

grounding:
  enabled: true
  confidence_threshold: 0.5
  fallback_to_owlv2: true
```

---

## 3.5 Testing & Validation

### 3.5.1 Unit Tests

| Test | Description | Location |
|------|-------------|----------|
| Provider Tests | Mock API responses, validate parsing | `tests/test_providers.py` |
| Schema Tests | Validate action/detection schemas | `tests/test_schemas.py` |
| Image Cache Tests | Test caching behavior | `tests/test_image_cache.py` |

### 3.5.2 Integration Tests

| Test | Description | Method |
|------|-------------|--------|
| Service Connectivity | All services respond | `rosservice call` |
| End-to-End Chat | Full conversation flow | Scripted scenario |
| Grounding Accuracy | Compare MLLM vs OWLv2 | A/B test with metrics |
| Latency Benchmark | Measure response times | Automated timing |

### 3.5.3 Hardware Validation Scenarios

1. **"Describe the scene"**
   - Expected: TTS describes visible objects
   - Measure: Response latency, accuracy

2. **"Touch the apple"**
   - Expected: Robot touches correct object
   - Measure: Grounding accuracy, motion success

3. **"Push the orange to the right"**
   - Expected: Robot performs push_right action
   - Measure: Object displacement, arm trajectory

4. **"Move the banana from left to right"**
   - Expected: Multi-step action execution
   - Measure: Full pipeline latency

### 3.5.4 Metrics to Collect

| Metric | Target | Current (v1) |
|--------|--------|--------------|
| First response (speak) | < 1.5s | 3-5s |
| Full planning latency | < 3s | 5-12s |
| Grounding accuracy | > 90% | ~85% (OWLv2) |
| API calls per action | 1 | 2-3 |

---

## 3.6 Rollout & Rollback Strategy

### 3.6.1 Rollout Phases

**Phase 1: Shadow Mode (1 week)**
- Run v2 alongside v1
- Log v2 responses without executing
- Compare outputs

**Phase 2: Opt-In Testing (1 week)**
- Enable v2 via launch arg
- Test with controlled scenarios
- Collect metrics

**Phase 3: Default Switch**
- Make v2 the default
- Keep v1 as fallback
- Monitor for issues

### 3.6.2 Rollback Instructions

**Immediate Rollback (runtime):**
```bash
rosparam set /use_mllm false
```

**Launch Rollback:**
```bash
# Use v1 launch file
roslaunch elmira init_nodes.launch
```

**Full Rollback:**
- v1 code remains untouched
- Simply don't use v2 launch files

### 3.6.3 Feature Flags

| Flag | Default | Effect |
|------|---------|--------|
| `use_mllm` | `true` | Use v2 gateway |
| `use_mllm_grounding` | `true` | Use MLLM for detection |
| `enable_streaming` | `true` | Stream responses |
| `fallback_to_owlv2` | `true` | OWLv2 on MLLM failure |

---

## 3.7 Timeline & Effort Estimate

### 3.7.1 Implementation Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Phase 1** | 2-3 days | Gateway node + providers + services |
| **Phase 2** | 1-2 days | State machine updates + launch files |
| **Phase 3** | 2-3 days | Grounding integration + testing harness |
| **Phase 4** | 1-2 days | Documentation + metrics |
| **Phase 5** | 3-5 sessions | Hardware validation + tuning |

**Total: ~10-15 days**

### 3.7.2 Task Breakdown

1. **Gateway Implementation (2-3 days)**
   - [ ] Create `scripts/v2/` directory structure
   - [ ] Implement base provider interface
   - [ ] Implement OpenAI provider
   - [ ] Implement Google provider
   - [ ] Create main gateway node
   - [ ] Add new service definitions

2. **State Machine Updates (1-2 days)**
   - [ ] Add ROS params for v2 switching
   - [ ] Update service routing
   - [ ] Add MLLM detection path
   - [ ] Test backward compatibility

3. **Launch & Config (1 day)**
   - [ ] Create `init_nodes_v2.launch`
   - [ ] Create `mllm_only.launch`
   - [ ] Create config YAML files
   - [ ] Update CMakeLists.txt and package.xml

4. **Testing (2-3 days)**
   - [ ] Unit tests for providers
   - [ ] Integration tests
   - [ ] Latency benchmarks
   - [ ] A/B grounding comparison

5. **Hardware Validation (3-5 sessions)**
   - [ ] Basic interaction tests
   - [ ] Object manipulation tests
   - [ ] Full scenario tests
   - [ ] Edge case handling

---

## 3.8 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cloud API latency | Medium | High | OWLv2 fallback, caching |
| API rate limits | Low | Medium | Rate limiter, backoff |
| Grounding inaccuracy | Medium | High | A/B testing, hybrid mode |
| Schema changes | Low | Medium | Validation, versioning |
| Network outage | Low | High | Offline mode (OWLv2 only) |

---

## 3.9 Success Criteria

### 3.9.1 Must Have
- [ ] Response latency < 3 seconds for full pipeline
- [ ] 100% backward compatibility with v1
- [ ] Graceful fallback on API failure
- [ ] All existing scenarios work unchanged

### 3.9.2 Should Have
- [ ] Streaming for faster TTS
- [ ] MLLM grounding accuracy ≥ OWLv2
- [ ] Support for both OpenAI and Google

### 3.9.3 Nice to Have
- [ ] New grasp/place actions
- [ ] Metrics dashboard
- [ ] Hot-swappable providers

---

**END OF SECTION 3**

---

# Summary: Files to Create

| File | Type | Priority | Status |
|------|------|----------|--------|
| `scripts/v2/__init__.py` | Python | P0 | ✅ Done |
| `scripts/v2/llm_api_v2.py` | Python | P0 | ✅ Done |
| `scripts/v2/providers/__init__.py` | Python | P0 | ✅ Done |
| `scripts/v2/providers/base.py` | Python | P0 | ✅ Done |
| `scripts/v2/providers/openai_provider.py` | Python | P0 | ✅ Done |
| `scripts/v2/providers/google_provider.py` | Python | P1 | ✅ Done |
| `scripts/v2/utils/__init__.py` | Python | P0 | ✅ Done |
| `scripts/v2/utils/image_cache.py` | Python | P0 | ✅ Done |
| `scripts/v2/schemas/__init__.py` | Python | P1 | ✅ Done |
| `scripts/v2/schemas/actions.py` | Python | P1 | ✅ Done |
| `srv/PromptMLLM.srv` | ROS Srv | P0 | ✅ Done |
| `srv/PromptMLLMWithGrounding.srv` | ROS Srv | P1 | ✅ Done |
| `srv/DetectWithMLLM.srv` | ROS Srv | P1 | ✅ Done |
| `msg/MLLMDetection.msg` | ROS Msg | P2 | Pending |
| `launch/init_nodes_v2.launch` | Launch | P0 | Pending |
| `launch/mllm_only.launch` | Launch | P2 | Pending |
| `config/mllm_config.yaml` | YAML | P1 | Pending |
| `requirements_v2.txt` | Text | P0 | Pending |
| `scripts/states/hand_control.py` | Python | P0 | ✅ Done (NEW) |

**Priority Legend:** P0 = Critical, P1 = Important, P2 = Nice to have

---

# SECTION 4: Bimanual Support

## 4.1 Overview

As of December 16, 2025, ELMiRA v2 now supports **bimanual manipulation** using both the left and right hands. This enables grasp and place actions with automatic arm selection based on object position.

## 4.2 Hardware Configuration

### Left Hand (New SEED Robotics - XL-320 Protocol)

| Motor ID | Joint Name | Description |
|----------|------------|-------------|
| 31 | `l_wrist_z` | Wrist Roll |
| 33 | `l_wrist_x` | Wrist Pitch |
| 34 | `l_thumb_z` | Thumb Roll (2-DOF) |
| 35 | `l_thumb_x` | Thumb Pitch |
| 36 | `l_indexfingers_x` | Index Finger |
| 37 | `l_middlefingers_x` | Middle Finger |

### Right Hand (Protocol 1.0)

| Motor ID | Joint Name | Description |
|----------|------------|-------------|
| 23 | `r_wrist_z` | Wrist Roll |
| 25 | `r_wrist_x` | Wrist Pitch |
| 29 | `r_indexfingers_x` | Index Finger |
| 32 | `r_virtualhand_x` | Virtual Hand (coupled) |

## 4.3 New Action Types

The following action types were added to `ActionTrajectory`:

| Action Type | Description | Hand Action |
|-------------|-------------|-------------|
| `grasp` | Pick up object | Close after approach |
| `place` | Put down object | Open before retreat |
| `open_hand` | Open gripper only | Open |
| `close_hand` | Close gripper only | Close |

## 4.4 State Machine Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ACT ACTION FLOW (v2 with hand control)           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  LOOK_DOWN_ACT ──▶ PLAN_ACTION_TRAJECTORY                           │
│                            │                                         │
│                            ▼                                         │
│                    CHECK_PREGRASP ─────────────────┐                │
│                      │        │                    │                │
│                      │ grasp  │ other              │                │
│                      ▼        ▼                    │                │
│              PREGRASP_OPEN_HAND                    │                │
│                      │                             │                │
│                      └─────────────┬───────────────┘                │
│                                    ▼                                 │
│                        JOINT_TRAJECTORY_ITERATOR                     │
│                                    │                                 │
│                                    ▼                                 │
│                         EXECUTE_HAND_ACTION                          │
│                           (open/close/none)                          │
│                                    │                                 │
│                                    ▼                                 │
│                              next_action                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 4.5 Files Modified/Created

| File | Change |
|------|--------|
| `states/action_planner.py` | Added grasp/place trajectories, hand_action output |
| `states/hand_control.py` | **NEW** - HandControl, OpenHand, CloseHand states |
| `state_machine.py` | Integrated hand control states |
| `v2/schemas/actions.py` | Added VALID_INTERACTION_TYPES |

## 4.6 Protocol Handling

The `HandControl` state automatically handles protocol differences:

```python
# Left hand (XL-320 protocol)
from pypot.dynamixel.io.io_320 import Dxl320IO

# Right hand (Protocol 1.0)
from pypot.dynamixel.io import DxlIO
```

**Important**: SEED servo position feedback is unreliable. Hand control uses timeout-based completion (1.5s) instead of position verification.

## 4.7 Testing Commands

```bash
# Test grasp action
rostopic pub /test_action std_msgs/String "data: 'grasp red ball'"

# Test place action  
rostopic pub /test_action std_msgs/String "data: 'place it on the left'"

# Test arm selection (should use left arm for Y > 0)
# Place object on left side of table and request grasp
```

---

**PLAN COMPLETE - Ready for Implementation**
