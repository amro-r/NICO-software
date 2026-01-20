#!/usr/bin/env python3
"""
ELMiRA v2 Streamlit Dashboard

A developer-focused UI for launching and monitoring the ELMiRA v2 robot stack.
Provides:
- Launch configuration for all init_nodes_v2.launch parameters
- Live camera feed from /elmira/debug/detections
- Dual terminal log panels for roslaunch and state_machine
- Real-time latency and accuracy metrics display

Usage:
    ./run_dashboard.sh
    # or
    source /path/to/activate.bash && streamlit run elmira_dashboard.py
"""

import os
import sys
import time
import signal
import atexit
import subprocess
import threading
import csv
from pathlib import Path
from datetime import datetime
from collections import deque
from typing import Optional, Dict, List, Any, Deque

import streamlit as st
import numpy as np

# Constants
ACTIVATE_BASH = Path(__file__).parent.parent.parent.parent.parent / "activate.bash"
LAUNCH_FILE = "init_nodes_v2.launch"
PACKAGE_NAME = "elmira"
LOG_BUFFER_SIZE = 500
CAMERA_TOPIC = "/elmira/debug/detections"
LATENCY_LOG_DIR = Path.home() / ".elmira" / "latency_logs"
ACCURACY_LOG_DIR = Path.home() / ".elmira" / "accuracy_logs"

# Baseline metrics for comparison
BASELINE_LATENCY_MS = 8980.0  # ELMiRA v1 average
BASELINE_ACCURACY = 46.67    # ELMiRA v1 percentage


# =============================================================================
# Process Management
# =============================================================================

class ProcessManager:
    """Manages ROS processes with thread-safe log collection."""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.log_buffers: Dict[str, Deque[str]] = {}
        self.log_threads: Dict[str, threading.Thread] = {}
        self.running = threading.Event()
        self.running.set()
        
        # Register cleanup on exit (atexit works from any thread)
        atexit.register(self.cleanup_all)
    
    def _log_reader_thread(self, name: str, pipe, buffer: Deque[str]):
        """Background thread to read subprocess output."""
        try:
            for line in iter(pipe.readline, ''):
                if not self.running.is_set():
                    break
                if line:
                    # Strip ANSI codes for cleaner display
                    clean_line = self._strip_ansi(line.rstrip())
                    buffer.append(f"[{datetime.now().strftime('%H:%M:%S')}] {clean_line}")
            pipe.close()
        except Exception as e:
            buffer.append(f"[ERROR] Log reader error: {e}")
    
    @staticmethod
    def _strip_ansi(text: str) -> str:
        """Remove ANSI escape codes from text."""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def start_process(self, name: str, command: str, env: Optional[Dict] = None) -> bool:
        """Start a process with log collection."""
        if name in self.processes and self.processes[name].poll() is None:
            return True  # Already running
        
        # Create log buffer
        self.log_buffers[name] = deque(maxlen=LOG_BUFFER_SIZE)
        self.log_buffers[name].append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting: {command}")
        
        try:
            # Build environment with ROS sourced
            proc_env = os.environ.copy()
            if env:
                proc_env.update(env)
            
            # Wrap command to source activate.bash first
            full_command = f"source {ACTIVATE_BASH} && {command}"
            
            process = subprocess.Popen(
                full_command,
                shell=True,
                executable="/bin/bash",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=proc_env,
                text=True,
                bufsize=1,  # Line buffered
                start_new_session=True,  # Create new process group for clean killing
            )
            
            self.processes[name] = process
            
            # Start log reader thread
            thread = threading.Thread(
                target=self._log_reader_thread,
                args=(name, process.stdout, self.log_buffers[name]),
                daemon=True,
            )
            thread.start()
            self.log_threads[name] = thread
            
            return True
            
        except Exception as e:
            self.log_buffers[name].append(f"[ERROR] Failed to start: {e}")
            return False
    
    def stop_process(self, name: str) -> bool:
        """Stop a specific process."""
        if name not in self.processes:
            return True
        
        process = self.processes[name]
        if process.poll() is not None:
            return True  # Already stopped
        
        try:
            self.log_buffers[name].append(f"[{datetime.now().strftime('%H:%M:%S')}] Stopping process...")
            
            # Send SIGINT first for graceful shutdown
            process.send_signal(signal.SIGINT)
            
            # Wait up to 5 seconds
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill
                process.kill()
                process.wait(timeout=2)
            
            self.log_buffers[name].append(f"[{datetime.now().strftime('%H:%M:%S')}] Process stopped")
            return True
            
        except Exception as e:
            self.log_buffers[name].append(f"[ERROR] Failed to stop: {e}")
            return False
    
    def force_kill_process(self, name: str) -> bool:
        """Force kill a process and all its children."""
        if name not in self.processes:
            return True
        
        process = self.processes[name]
        if process.poll() is not None:
            return True  # Already stopped
        
        try:
            import os
            self.log_buffers[name].append(f"[{datetime.now().strftime('%H:%M:%S')}] Force killing process...")
            
            # Kill the entire process group
            pid = process.pid
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError:
                # Fallback to just killing the process
                process.kill()
            
            process.wait(timeout=2)
            self.log_buffers[name].append(f"[{datetime.now().strftime('%H:%M:%S')}] Process killed")
            return True
            
        except Exception as e:
            self.log_buffers[name].append(f"[ERROR] Failed to kill: {e}")
            return False
    
    def is_running(self, name: str) -> bool:
        """Check if a process is running."""
        if name not in self.processes:
            return False
        return self.processes[name].poll() is None
    
    def get_logs(self, name: str) -> List[str]:
        """Get current logs for a process."""
        if name not in self.log_buffers:
            return []
        return list(self.log_buffers[name])
    
    def cleanup_all(self):
        """Stop all processes."""
        self.running.clear()
        for name in list(self.processes.keys()):
            self.stop_process(name)


# =============================================================================
# Camera Feed Manager
# =============================================================================

class CameraManager:
    """Manages ROS camera subscription in background thread."""
    
    def __init__(self):
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_lock = threading.Lock()
        self.running = threading.Event()
        self.subscriber = None
        self.ros_initialized = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start camera subscription in background."""
        if self._thread is not None and self._thread.is_alive():
            return
        
        self.running.set()
        self._thread = threading.Thread(target=self._ros_spin_thread, daemon=True)
        self._thread.start()
    
    def _ros_spin_thread(self):
        """Background thread for ROS camera subscription."""
        try:
            import rospy
            from sensor_msgs.msg import Image
            from cv_bridge import CvBridge
            
            # Initialize ROS node if not already done
            if not self.ros_initialized:
                try:
                    rospy.init_node("elmira_dashboard_camera", anonymous=True, disable_signals=True)
                    self.ros_initialized = True
                except rospy.exceptions.ROSException:
                    # Node already initialized
                    self.ros_initialized = True
            
            self.bridge = CvBridge()
            
            def image_callback(msg):
                try:
                    cv_image = self.bridge.imgmsg_to_cv2(msg, "rgb8")
                    with self.frame_lock:
                        self.latest_frame = cv_image
                except Exception as e:
                    pass  # Silently ignore conversion errors
            
            self.subscriber = rospy.Subscriber(
                CAMERA_TOPIC, Image, image_callback, queue_size=1
            )
            
            # Spin at 10Hz
            rate = rospy.Rate(10)
            while self.running.is_set() and not rospy.is_shutdown():
                rate.sleep()
                
        except ImportError:
            pass  # ROS not available
        except Exception as e:
            pass  # Ignore errors
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get the latest camera frame."""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def stop(self):
        """Stop camera subscription."""
        self.running.clear()
        if self.subscriber is not None:
            try:
                self.subscriber.unregister()
            except:
                pass


# =============================================================================
# Metrics Reader
# =============================================================================

class MetricsReader:
    """Reads latency and accuracy CSV logs."""
    
    @staticmethod
    def find_latest_log(log_dir: Path, prefix: str = "") -> Optional[Path]:
        """Find the most recent log file."""
        if not log_dir.exists():
            return None
        
        files = list(log_dir.glob(f"{prefix}*.csv"))
        if not files:
            return None
        
        return max(files, key=lambda f: f.stat().st_mtime)
    
    @staticmethod
    def read_latency_log(log_file: Path) -> List[Dict[str, Any]]:
        """Read latency log CSV."""
        records = []
        try:
            with open(log_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append({
                        'timestamp': row.get('timestamp', ''),
                        'operation': row.get('operation_type', ''),
                        'latency_ms': float(row.get('latency_ms', 0)),
                        'provider': row.get('provider', ''),
                        'model': row.get('model', ''),
                        'success': row.get('success', 'true').lower() == 'true',
                    })
        except Exception:
            pass
        return records
    
    @staticmethod
    def read_accuracy_log(log_file: Path) -> List[Dict[str, Any]]:
        """Read accuracy log CSV."""
        records = []
        try:
            with open(log_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append({
                        'timestamp': row.get('timestamp', ''),
                        'interaction_id': row.get('interaction_id', ''),
                        'mode': row.get('mode_selected', ''),
                        'action': row.get('action_type', ''),
                        'target': row.get('target_object', ''),
                        'manual_verdict': row.get('manual_verdict', ''),
                    })
        except Exception:
            pass
        return records


# =============================================================================
# Streamlit App
# =============================================================================

def init_session_state():
    """Initialize Streamlit session state."""
    if 'process_manager' not in st.session_state:
        st.session_state.process_manager = ProcessManager()
    
    if 'camera_manager' not in st.session_state:
        st.session_state.camera_manager = CameraManager()
    
    if 'launched' not in st.session_state:
        st.session_state.launched = False
    
    if 'launch_config' not in st.session_state:
        st.session_state.launch_config = {}
    
    if 'metrics_reader' not in st.session_state:
        st.session_state.metrics_reader = MetricsReader()
    
    if 'last_latency_count' not in st.session_state:
        st.session_state.last_latency_count = 0
    
    if 'last_accuracy_count' not in st.session_state:
        st.session_state.last_accuracy_count = 0
    
    if 'state_machine_started' not in st.session_state:
        st.session_state.state_machine_started = False


def render_sidebar() -> Dict[str, Any]:
    """Render configuration sidebar and return config dict."""
    st.sidebar.title("🤖 ELMiRA v2")
    st.sidebar.markdown("---")
    
    # Disable inputs after launch
    disabled = st.session_state.launched
    
    st.sidebar.header("🧠 MLLM Configuration")
    
    mllm_provider = st.sidebar.selectbox(
        "Provider",
        options=["openai", "google"],
        index=0,
        disabled=disabled,
        help="MLLM provider: OpenAI GPT-5.2 or Google Gemini 3 Flash"
    )
    
    mllm_model = st.sidebar.text_input(
        "Model (optional)",
        value="",
        disabled=disabled,
        help="Leave empty for provider default"
    )
    
    temperature = st.sidebar.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        disabled=disabled,
    )
    
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Detection Settings")
    
    use_mllm_grounding = st.sidebar.checkbox(
        "Use MLLM for detection",
        value=True,
        disabled=disabled,
        help="Use MLLM's native object detection"
    )
    
    use_grounded_action_planning = st.sidebar.checkbox(
        "Grounded action planning",
        value=True,
        disabled=disabled,
        help="Single MLLM call for action + detection"
    )
    
    use_owlv2_fallback = st.sidebar.checkbox(
        "OWLv2 fallback",
        value=False,
        disabled=disabled,
        help="Launch OWLv2 as fallback detector"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.header("🎤 ASR Settings")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        energy_silence = st.number_input(
            "Energy silence",
            value=2000,
            min_value=500,
            max_value=10000,
            step=100,
            disabled=disabled,
        )
    with col2:
        energy_start = st.number_input(
            "Energy start",
            value=4000,
            min_value=1000,
            max_value=15000,
            step=100,
            disabled=disabled,
        )
    
    energy_stop = st.sidebar.number_input(
        "Energy stop",
        value=3000,
        min_value=1000,
        max_value=10000,
        step=100,
        disabled=disabled,
    )
    
    energy_dynamic = st.sidebar.checkbox(
        "Dynamic energy adjustment",
        value=True,
        disabled=disabled,
    )
    
    st.sidebar.markdown("---")
    st.sidebar.header("📊 Benchmarking")
    
    track_latency = st.sidebar.checkbox(
        "Track latency",
        value=False,
        disabled=disabled,
        help="Log MLLM latency to ~/.elmira/latency_logs/"
    )
    
    track_accuracy = st.sidebar.checkbox(
        "Track accuracy",
        value=False,
        disabled=disabled,
        help="Log accuracy data to ~/.elmira/accuracy_logs/"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.header("📷 Camera")
    
    image_topic = st.sidebar.selectbox(
        "Image topic",
        options=["/nico/vision/right", "/nico/vision/left"],
        index=0,
        disabled=disabled,
    )
    
    return {
        'mllm_provider': mllm_provider,
        'mllm_model': mllm_model,
        'temperature': temperature,
        'use_mllm_grounding': use_mllm_grounding,
        'use_grounded_action_planning': use_grounded_action_planning,
        'use_owlv2_fallback': use_owlv2_fallback,
        'energy_silence': energy_silence,
        'energy_start': energy_start,
        'energy_stop': energy_stop,
        'energy_dynamic': energy_dynamic,
        'track_latency': track_latency,
        'track_accuracy': track_accuracy,
        'image_topic': image_topic,
    }


def build_launch_command(config: Dict[str, Any]) -> str:
    """Build roslaunch command from config."""
    args = [
        f"mllm_provider:={config['mllm_provider']}",
        f"temperature:={config['temperature']}",
        f"use_mllm_grounding:={str(config['use_mllm_grounding']).lower()}",
        f"use_grounded_action_planning:={str(config['use_grounded_action_planning']).lower()}",
        f"use_owlv2_fallback:={str(config['use_owlv2_fallback']).lower()}",
        f"energy_silence:={config['energy_silence']}",
        f"energy_start:={config['energy_start']}",
        f"energy_stop:={config['energy_stop']}",
        f"energy_dynamic:={str(config['energy_dynamic']).lower()}",
        f"track_latency:={str(config['track_latency']).lower()}",
        f"track_accuracy:={str(config['track_accuracy']).lower()}",
        f"image_topic:={config['image_topic']}",
    ]
    
    if config['mllm_model']:
        args.append(f"mllm_model:={config['mllm_model']}")
    
    return f"roslaunch {PACKAGE_NAME} {LAUNCH_FILE} " + " ".join(args)


def render_launch_controls(config: Dict[str, Any]):
    """Render launch control buttons."""
    pm = st.session_state.process_manager
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if not st.session_state.launched:
            if st.button("🚀 Launch ELMiRA v2", type="primary", use_container_width=True):
                st.session_state.launch_config = config.copy()
                
                # Check if roscore is running
                roscore_check = subprocess.run(
                    ["bash", "-c", f"source {ACTIVATE_BASH} && rostopic list"],
                    capture_output=True,
                    text=True,
                )
                
                if roscore_check.returncode != 0:
                    # Start roscore
                    pm.start_process("roscore", "roscore")
                    time.sleep(2)  # Give roscore time to start
                
                # Start roslaunch
                launch_cmd = build_launch_command(config)
                if pm.start_process("roslaunch", launch_cmd):
                    st.session_state.launched = True
                    # Start camera manager
                    st.session_state.camera_manager.start()
                    st.rerun()
        else:
            st.success("✅ ELMiRA v2 Running")
    
    with col2:
        if st.session_state.launched:
            roslaunch_status = "🟢 Running" if pm.is_running("roslaunch") else "🔴 Stopped"
            st.markdown(f"**roslaunch:** {roslaunch_status}")
    
    with col3:
        if st.session_state.launched:
            roscore_status = "🟢 Running" if pm.is_running("roscore") else "🟡 External"
            st.markdown(f"**roscore:** {roscore_status}")
    
    # State machine controls - separate row
    if st.session_state.launched:
        st.markdown("")
        col_sm1, col_sm2, col_sm3 = st.columns([2, 1, 1])
        
        with col_sm1:
            if not st.session_state.state_machine_started:
                if st.button("🧠 Start State Machine", type="primary", use_container_width=True):
                    if pm.start_process("state_machine", "rosrun elmira state_machine.py"):
                        st.session_state.state_machine_started = True
                        st.rerun()
            else:
                st.success("🧠 State Machine Running")
        
        with col_sm2:
            if st.session_state.state_machine_started:
                sm_status = "🟢 Running" if pm.is_running("state_machine") else "🔴 Stopped"
                st.markdown(f"**state_machine:** {sm_status}")
        
        with col_sm3:
            if st.session_state.state_machine_started and pm.is_running("state_machine"):
                if st.button("⏹️ Stop SM", use_container_width=True):
                    pm.force_kill_process("state_machine")
                    st.session_state.state_machine_started = False
                    st.rerun()


def render_camera_feed():
    """Render the camera feed panel."""
    st.subheader("📷 Detection Visualizer")
    
    if not st.session_state.launched:
        st.info("Launch ELMiRA to see the detection feed from `/elmira/debug/detections`")
        return
    
    camera_placeholder = st.empty()
    
    frame = st.session_state.camera_manager.get_frame()
    if frame is not None:
        camera_placeholder.image(frame, channels="RGB", use_container_width=True)
    else:
        camera_placeholder.warning("Waiting for detection images... (images appear when object detection is triggered)")


def render_terminal_logs():
    """Render terminal log panels."""
    st.subheader("📟 Terminal Output")
    
    pm = st.session_state.process_manager
    
    # Two tabs for roslaunch and state_machine logs
    tab_launch, tab_sm = st.tabs(["🖥️ roslaunch", "🧠 state_machine"])
    
    with tab_launch:
        logs = pm.get_logs("roslaunch")
        if logs:
            log_text = "\n".join(logs[-100:])  # Show last 100 lines
            st.code(log_text, language="bash")
        else:
            st.info("No logs yet. Launch ELMiRA to see output.")
    
    with tab_sm:
        if st.session_state.state_machine_started:
            logs = pm.get_logs("state_machine")
            if logs:
                log_text = "\n".join(logs[-100:])  # Show last 100 lines
                st.code(log_text, language="bash")
            else:
                st.info("State machine started. Waiting for output...")
        else:
            st.info("State machine not started. Click '🧠 Start State Machine' after launching ELMiRA.")


def render_metrics_panel(config: Dict[str, Any]):
    """Render latency and accuracy metrics."""
    if not config.get('track_latency') and not config.get('track_accuracy'):
        return
    
    st.subheader("📊 Benchmarking Metrics")
    
    reader = st.session_state.metrics_reader
    
    col1, col2 = st.columns(2)
    
    # Latency metrics
    if config.get('track_latency'):
        with col1:
            st.markdown("### ⏱️ Latency")
            
            log_file = reader.find_latest_log(LATENCY_LOG_DIR, "latency_")
            if log_file:
                records = reader.read_latency_log(log_file)
                
                if records:
                    # Calculate stats
                    latencies = [r['latency_ms'] for r in records if r['success']]
                    avg_latency = np.mean(latencies) if latencies else 0
                    delta = avg_latency - BASELINE_LATENCY_MS
                    
                    st.metric(
                        "Average Latency",
                        f"{avg_latency:.0f} ms",
                        delta=f"{delta:.0f} ms vs baseline",
                        delta_color="inverse",  # Green if negative (faster)
                    )
                    
                    st.metric(
                        "Interactions",
                        len(records),
                    )
                    
                    # Show recent records
                    st.markdown("**Recent:**")
                    import pandas as pd
                    df = pd.DataFrame(records[-10:])
                    if not df.empty:
                        st.dataframe(
                            df[['timestamp', 'operation', 'latency_ms', 'success']],
                            hide_index=True,
                            use_container_width=True,
                        )
                else:
                    st.info("No latency data yet")
            else:
                st.info("No latency log found")
    
    # Accuracy metrics
    if config.get('track_accuracy'):
        with col2:
            st.markdown("### 🎯 Accuracy")
            
            log_file = reader.find_latest_log(ACCURACY_LOG_DIR, "accuracy_")
            if log_file:
                records = reader.read_accuracy_log(log_file)
                
                if records:
                    # Calculate stats (only for manually reviewed)
                    reviewed = [r for r in records if r['manual_verdict']]
                    correct = len([r for r in reviewed if r['manual_verdict'] == 'correct'])
                    accuracy = (correct / len(reviewed) * 100) if reviewed else 0
                    delta = accuracy - BASELINE_ACCURACY
                    
                    st.metric(
                        "Accuracy",
                        f"{accuracy:.1f}%",
                        delta=f"{delta:.1f}% vs baseline",
                        delta_color="normal",  # Green if positive (better)
                    )
                    
                    st.metric(
                        "Reviewed / Total",
                        f"{len(reviewed)} / {len(records)}",
                    )
                    
                    # Show recent records
                    st.markdown("**Recent:**")
                    import pandas as pd
                    df = pd.DataFrame(records[-10:])
                    if not df.empty:
                        st.dataframe(
                            df[['timestamp', 'mode', 'action', 'target', 'manual_verdict']],
                            hide_index=True,
                            use_container_width=True,
                        )
                else:
                    st.info("No accuracy data yet")
            else:
                st.info("No accuracy log found")


def render_emergency_stop():
    """Render emergency stop button."""
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.session_state.launched:
            if st.button("🛑 Emergency Stop", type="secondary", use_container_width=True):
                pm = st.session_state.process_manager
                pm.cleanup_all()
                st.session_state.camera_manager.stop()
                st.session_state.launched = False
                st.rerun()


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="ELMiRA v2 Dashboard",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # Initialize session state
    init_session_state()
    
    # Render sidebar and get config
    config = render_sidebar()
    
    # Use launch config if already launched
    if st.session_state.launched:
        config = st.session_state.launch_config
    
    # Main content
    st.title("🤖 ELMiRA v2 Dashboard")
    st.markdown("Developer UI for the Enhanced Language-Mediated Interactive Robot Architecture")
    
    # Launch controls
    render_launch_controls(config)
    
    st.markdown("---")
    
    # Two-column layout: camera left, logs right
    col_camera, col_logs = st.columns([1, 1])
    
    with col_camera:
        render_camera_feed()
    
    with col_logs:
        render_terminal_logs()
    
    # Metrics panel
    render_metrics_panel(config)
    
    # Emergency stop
    render_emergency_stop()
    
    # Auto-refresh when running
    if st.session_state.launched:
        time.sleep(1)
        st.rerun()


if __name__ == "__main__":
    main()
