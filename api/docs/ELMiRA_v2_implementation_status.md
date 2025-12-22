# ELMiRA v2 Implementation Status

**Date:** December 4, 2025  
**Project:** NICO Humanoid Robot - Multimodal LLM Upgrade  
**Objective:** Upgrade from separate VLM/LLM setup to unified multimodal LLMs (GPT-4o/Gemini 2.5 Flash)  
**Environment:** Ubuntu 20.04, ROS Noetic, Python 3.8

---

## Executive Summary

The ELMiRA v2 upgrade replaces the existing multi-step LLM pipeline with a unified Multimodal LLM (MLLM) gateway. This eliminates redundant API calls and leverages native visual grounding capabilities of modern models like GPT-4o and Gemini 2.5 Flash.

**Expected Improvements:**
- **Response Time:** 5-12s → 1.5-3s (3-5x faster)
- **Object Localization:** Improved accuracy with native visual grounding
- **Maintainability:** Single provider abstraction, easier to add new models

---

## ✅ COMPLETED TASKS (ALL IMPLEMENTATION DONE)

### 1. Codebase Analysis

Analyzed the complete ELMiRA v1 pipeline to understand the LLM-to-motor communication:

| Component | File | Purpose |
|-----------|------|---------|
| Speech Recognition | `speech_asr.py` | Whisper ASR for voice input |
| LLM Chat | `llm_api.py` | GPT-4o Assistant API (1Hz polling - **slow**) |
| Object Detection | `object_localiser.py` | OWLv2 for object detection |
| Coordinate Mapping | `coordinate_transfer.py` | MLP for image→real coordinates |
| Inverse Kinematics | `ik_solver.py` | EvoIK for joint angle computation |
| Action Planning | `states/action_planner.py` | Trajectory generation |
| Motor Control | `states/move_robot.py` | ROS SetJointPosition services |

**Key Finding:** The v1 system makes 3 separate API calls (chat, vision, object visibility) sequentially, causing significant latency.

### 2. Architecture Design Document

Created comprehensive upgrade plan at:
```
api/docs/ELMiRA_v2_upgrade_plan.md
```

Contains:
- Section 1: Analysis, Tech Stack, Architecture diagrams
- Section 2: File structure, Service contracts
- Section 3: Gateway specs, State machine updates, Testing, Timeline, Risks

### 3. Directory Structure Created

```
scripts/v2/
├── __init__.py           ✅ Created
├── llm_api_v2.py         ✅ Created (Main MLLM Gateway node)
├── providers/
│   ├── __init__.py       ✅ Created (Provider factory)
│   ├── base.py           ✅ Created (Abstract base class)
│   ├── openai_provider.py ✅ Created (GPT-4o implementation)
│   └── google_provider.py ✅ Created (Gemini 2.5 Flash implementation)
├── utils/
│   ├── __init__.py       ✅ Created
│   └── image_cache.py    ✅ Created (Efficient frame sharing)
├── schemas/
│   ├── __init__.py       ✅ Created
│   ├── actions.py        ✅ Created (Action dataclasses)
│   └── detections.py     ✅ Created (Detection dataclasses)
└── config/
    └── mllm_config.yaml  ✅ Created
```

### 4. Core Provider Implementation

#### `providers/base.py`
- `MLLMResponse` dataclass - Standard response format
- `DetectionResult` dataclass - Bounding box + label
- `GroundedResponse` dataclass - Response with detections
- `BaseMLLMProvider` abstract class with methods:
  - `generate()` - Text + image → response
  - `generate_with_grounding()` - With object detection
  - `detect_objects()` - Object detection only

#### `providers/openai_provider.py`
- Full GPT-4o implementation using OpenAI SDK v1.40+
- Supports structured outputs with JSON mode
- Automatic retry with exponential backoff (tenacity)
- Bounding box extraction from responses

#### `providers/google_provider.py`
- Full Gemini 2.5 Flash implementation using google-genai SDK
- Native bounding box support
- Automatic retry logic
- Temperature/max_tokens configuration

#### `providers/__init__.py`
- `get_provider(name)` factory function
- Supports: "openai", "gpt4o", "google", "gemini"

### 5. MLLM Gateway ROS Node

**File:** `scripts/v2/llm_api_v2.py`

Features:
- ROS node `mllm_gateway` with three services:
  - `/mllm/prompt` - Basic MLLM query
  - `/mllm/prompt_grounded` - MLLM with object grounding
  - `/mllm/detect` - Object detection only
- Configurable provider via ROS param `~mllm_provider`
- Uses `CachedImageGrabber` for efficient frame sharing
- Publishes debug images to `/mllm/debug_image`
- JSON-based structured response format

### 6. Image Caching Utility

**File:** `scripts/v2/utils/image_cache.py`

`CachedImageGrabber` class:
- Subscribes to camera topic once
- Caches latest frame with timestamp
- Thread-safe access
- Staleness detection (default 5s timeout)
- Base64 encoding for API calls

### 7. New ROS Service Definitions

Created in `srv/`:

| Service | Purpose |
|---------|---------|
| `PromptMLLM.srv` | Text prompt + optional image → response |
| `PromptMLLMWithGrounding.srv` | Prompt with object detection results |
| `DetectWithMLLM.srv` | Object detection with target labels |

### 8. Launch File

**File:** `launch/init_nodes_v2.launch`

- Launches MLLM gateway node
- Configurable provider via arg (default: openai)
- Can be extended for full v2 system

### 9. Requirements File

**File:** `requirements_v2.txt`

New dependencies:
- `openai>=1.40.0` - Modern OpenAI SDK with structured outputs
- `google-genai>=1.0.0` - Google Generative AI SDK
- `pydantic>=2.0.0` - Schema validation
- `tenacity>=8.0.0` - Retry logic

### 10. MLLMDetection Message (NEW)

**File:** `msg/MLLMDetection.msg`

Extended detection message with MLLM-specific fields:
- Standard detection fields (label, score, center_x, center_y, width, height)
- Grounding text description
- Raw bounding box
- Provider identification

### 11. State Machine v1/v2 Switching (NEW)

**File:** `scripts/state_machine.py`

Added dynamic service routing based on ROS params:
- `/use_mllm` - Enable MLLM v2 gateway
- `/use_mllm_grounding` - Use MLLM for object detection
- `/mllm_provider` - Provider selection (openai/google)

Services automatically switch between:
- v1: `llm_chat`, `llm_vision`, `llm_object_visibility`
- v2: `mllm_chat`, `mllm_vision`, `mllm_visibility`

### 12. Action Planner MLLM Detection Path (NEW)

**File:** `scripts/states/action_planner.py`

Updated `ActionPlanner` and `ConcurrentPlanAndVerify` classes:
- Dynamic detection service selection (OWLv2 vs MLLM)
- Dynamic visibility service selection
- Full backward compatibility with v1

---

## 🔧 REMAINING STEPS (Build & Test Only)

### Step 1: Install Python Dependencies
```bash
cd ~/catkin_ws/src/NICO-software/api/src/ELMiRA
pip install -r requirements_v2.txt
```

### Step 2: Build Catkin Workspace
```bash
cd ~/catkin_ws/src/NICO-software/api
source activate.bash
catkin_make
```

### Step 3: Test Services
```bash
# Terminal 1: Start ROS core
roscore

# Terminal 2: Start MLLM Gateway (standalone test)
export OPENAI_API_KEY="your-api-key"
roslaunch elmira mllm_only.launch mllm_provider:=openai

# Terminal 3: Test services
rosservice call /mllm_chat "prompt: 'Hello, describe what you see'"
rosservice call /mllm_vision "{}"
```

### Step 4: Full System Test (with v2)
```bash
# Launch full v2 system
roslaunch elmira init_nodes_v2.launch mllm_provider:=openai

# Or use v1 fallback
roslaunch elmira init_nodes.launch
```

---

## FILE INVENTORY (COMPLETE)

### All Files Created/Updated

| File | Status | Purpose |
|------|--------|---------|
| `docs/ELMiRA_v2_upgrade_plan.md` | ✅ | Architecture documentation |
| `src/ELMiRA/requirements_v2.txt` | ✅ | Python dependencies |
| `scripts/v2/__init__.py` | ✅ | Package init |
| `scripts/v2/llm_api_v2.py` | ✅ | Main MLLM Gateway node (executable) |
| `scripts/v2/providers/__init__.py` | ✅ | Provider factory |
| `scripts/v2/providers/base.py` | ✅ | Abstract base class |
| `scripts/v2/providers/openai_provider.py` | ✅ | GPT-4o provider |
| `scripts/v2/providers/google_provider.py` | ✅ | Gemini provider |
| `scripts/v2/utils/__init__.py` | ✅ | Utils package init |
| `scripts/v2/utils/image_cache.py` | ✅ | Frame caching |
| `scripts/v2/schemas/__init__.py` | ✅ | Schema exports |
| `scripts/v2/schemas/actions.py` | ✅ | Action dataclasses |
| `scripts/v2/schemas/detections.py` | ✅ | Detection dataclasses |
| `srv/PromptMLLM.srv` | ✅ | Service definition |
| `srv/PromptMLLMWithGrounding.srv` | ✅ | Service definition |
| `srv/DetectWithMLLM.srv` | ✅ | Service definition |
| `msg/MLLMDetection.msg` | ✅ | Extended detection message |
| `launch/init_nodes_v2.launch` | ✅ | Full v2 launch file |
| `launch/mllm_only.launch` | ✅ | Standalone test launch |
| `config/mllm_config.yaml` | ✅ | MLLM configuration |
| `CMakeLists.txt` | ✅ | Updated with v2 srv/msg |
| `scripts/state_machine.py` | ✅ | v1/v2 service switching |
| `scripts/states/action_planner.py` | ✅ | MLLM detection path |

---

## QUICK START COMMANDS

```bash
# Terminal 1: Start ROS core
roscore

# Terminal 2: Start camera (if not running)
roslaunch elmira camera.launch

# Terminal 3: Start MLLM Gateway (v2)
cd ~/catkin_ws/src/NICO-software/api
source activate.bash
source devel/setup.bash
export OPENAI_API_KEY="your-api-key"
roslaunch elmira init_nodes_v2.launch mllm_provider:=openai

# Terminal 4: Test
rosservice call /mllm_chat "{prompt: 'Hello, what can you see?'}"
```

---

## ENVIRONMENT VARIABLES REQUIRED

```bash
# For OpenAI provider
export OPENAI_API_KEY="your-api-key"

# For Google/Gemini provider  
export GOOGLE_API_KEY="your-api-key"
```

---

## v1/v2 SWITCHING

The system supports runtime switching between v1 and v2:

```bash
# Use v2 (default in init_nodes_v2.launch)
rosparam set /use_mllm true
rosparam set /use_mllm_grounding true

# Use v1 (fallback)
rosparam set /use_mllm false

# Or use v1 launch file directly
roslaunch elmira init_nodes.launch
```

---

## CONTACT

For questions about this implementation, refer to:
- `api/docs/ELMiRA_v2_upgrade_plan.md` - Full architecture details
- `api/CLAUDE.md` - Project context for AI assistants
