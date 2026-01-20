# ELMiRA v2 Dashboard UI

This package provides a Streamlit-based developer dashboard for launching and monitoring the ELMiRA v2 robot stack.

## Features

- **Launch Configuration**: Configure all `init_nodes_v2.launch` parameters via sidebar controls
- **Live Camera Feed**: Display `/elmira/debug/detections` with workspace polygon and bounding boxes
- **Terminal Logs**: Live scrolling output from roslaunch
- **Benchmarking Metrics**: Real-time latency and accuracy tracking with per-interaction updates

## Quick Start

```bash
# Navigate to UI directory
cd /home/amr/catkin_ws/src/NICO-software/api/src/ELMiRA/scripts/ui

# Make the launcher executable
chmod +x run_elmira_v2_dashboard.sh

# Launch the dashboard
./run_elmira_v2_dashboard.sh
```

The dashboard will be available at `http://localhost:8501`

## Usage

1. **Configure Settings** in the sidebar:
   - Select MLLM provider (OpenAI or Google)
   - Adjust temperature, ASR thresholds
   - Enable/disable grounding options
   - Toggle latency/accuracy tracking

2. **Click "🚀 Launch ELMiRA v2"** to start the robot stack

3. **Monitor**:
   - Detection visualizer shows camera feed with bounding boxes
   - Terminal logs show real-time output
   - Metrics panel updates after each interaction (when tracking enabled)

4. **Click "🛑 Emergency Stop"** to terminate all processes

## Requirements

Install UI dependencies:
```bash
pip install -r requirements_ui.txt
```

## Architecture

```
run_elmira_v2_dashboard.sh
    └── sources activate.bash (NICO environment)
        └── streamlit run elmira_v2_dashboard.py
            ├── ProcessManager: Spawns roscore + roslaunch
            ├── CameraManager: Subscribes to /elmira/debug/detections
            └── MetricsReader: Polls CSV logs for latency/accuracy
```
