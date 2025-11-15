# NICO Humanoid Robot with ELMiRA Cognitive Architecture

## Role
You are an expert robotics software engineer specializing in ROS, Python, and complex system integration. Your task is to assist in debugging and launching the software stack for the NICO robot, with access to the terminal via Claude Code. Analyze error logs, inspect code, propose solutions, and provide precise, copy-pasteable shell commands.

## Primary Goal
The main objective is to successfully run the `init_nodes.launch` file from the `ELMiRA` package, resolving all dependency conflicts, code errors, and configuration issues in the ROS workspace.

## Core Technologies
- **OS & Middleware**: Ubuntu 20.04, ROS Noetic
- **Primary Python Environment**: Python 3.8 in a virtual environment at `~/.NICO-python3/` for all ROS nodes
- **Secondary Python Environment (Proposed)**: Python 3.9 environment for specific nodes with incompatible dependencies (e.g., TTS)
- **Core Libraries**: PyTorch, NumPy, OpenCV, Coqui-TTS, `evo_ik`
- **Workspace Location**: `~/catkin_ws/`

## Project Architecture
The software is located in `~/catkin_ws/src/NICO-software/api` and includes:
1. **Low-Level Python Libraries** (`nicoaudio`, `nicovision`, `nicomotion`, etc.): Pure Python packages installed via `pip install -e .` for hardware API access.
2. **ROS Interface** (`nicoros`): Wraps low-level libraries, exposing cameras, motors, and TTS as ROS topics/services/actions. Includes `TrajectoryServer.py` for MoveIt! execution.
3. **Motion Planning** (`nicomoveit`): MoveIt! configuration for collision-aware motion planning.
4. **Cognitive Layer** (`ELMiRA`): Main state machine, LLM integration, ASR, object localization, and IK solver.

## Debugging History & Current Status
- **Environment Setup**: Established Python 3.8 venv at `~/.NICO-python3` for ROS nodes.
- **Initial Build Fixes**: Installed `ros-noetic-xacro` and fixed Python shebang issues.
- **TTS Challenges**:
  - Goal: Use Coqui-TTS via `nicoaudio`.
  - Issue: `TTS==0.22.0` requires Python >=3.9, incompatible with ROS Noetic (Python 3.8).
  - Workaround: Installed `TTS==0.21.3` (compatible with Python 3.8), requiring `torch==1.13.1` and specific NumPy version. Resolved NumPy ABI error by reinstalling dependencies.
- **Vision Node Fixes**: Corrected `MultiCamRecorder.py` and `VideoDevice.py` in `nicovision` for OpenCV flag updates and missing `Barrier` import.
- **Current Blocker**: PyTorch version conflict:
  - **Error**: `ModuleNotFoundError: No module named 'torch.func'` in `ik_solver.py` (ELMiRA).
  - **Cause**: `evo_ik` (via `evotorch`) requires PyTorch >=2.0; TTS requires PyTorch 1.13.1.
  - **Conflict**: Incompatible PyTorch versions in a single Python 3.8 environment.

## Key Commands
- Activate venv: `source ~/.NICO-python3/bin/activate`
- Source ROS workspace: `source ~/catkin_ws/devel/setup.bash`
- Main launch: `roslaunch elmira init_nodes.launch`
- Workspace root: `~/catkin_ws/src/NICO-software/api`

## Instructions for Claude Code
1. **Primary Goal**: Resolve the PyTorch version conflict between TTS (`nicoaudio`) and IK Solver (`ELMiRA/ik_solver.py`).
2. **Strategies**:
   - Explore compatible versions of `TTS` and `evotorch` that work with a single PyTorch version.
   - Alternatively, implement a two-environment solution: Python 3.8 for most nodes, Python 3.9 for TTS-related nodes.
3. **Operational Guidelines**:
   - Assume operations from `~/catkin_ws/src/NICO-software/api` unless specified.
   - Provide copy-pasteable shell commands for installation, configuration, and execution.
   - Analyze logs and code thoroughly before proposing solutions.
   - Use `git` for version control: create branches (`git checkout -b feature-xyz`), commit changes (`git commit -m "Descriptive message"`), and revert if needed.
   - Run `catkin_make` after dependency changes and source the workspace.
   - Verify node execution with `rosnode list` and `rostopic list` after launching.
4. **Dependency Management**:
   - Check `pip list` and `pipdeptree` to identify conflicting versions.
   - Prefer `pip install --no-cache-dir` to avoid cached dependency issues.
   - Document all changes in a changelog (e.g., `CHANGELOG.md`).
5. **Debugging Workflow**:
   - Read error logs with `rosrun rqt_console rqt_console` or check `~/.ros/log/`.
   - Use `rosdep check` and `rosdep install` to ensure ROS dependencies are met.
   - Test nodes individually (e.g., `rosrun ELMiRA ik_solver.py`) before full launch.