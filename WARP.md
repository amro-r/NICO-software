# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project overview
- This repo provides software for the NICO humanoid robot. The ROS catkin workspace lives in api; it aggregates low‑level Python device libraries, ROS wrappers, MoveIt! integration, and the ELMiRA cognitive layer.
- Key packages and roles:
  - nicomotion, nicovision, nicoaudio, nicoface, nicotouch: low‑level Python libraries (installed via setup.py) for motors, cameras, audio/TTS, face, and touch.
  - nicomsg: custom ROS messages/services used across the stack.
  - nicoros: ROS nodes wrapping the low‑level libs (e.g., Motion, Vision, TextToSpeech) plus launch files for typical runtime configurations (real robot and simulated).
  - nicomoveit: MoveIt! configuration, meshes/URDFs, and a small wrapper; includes a kinematics package with C++ nodes and launch files.
  - ELMiRA: cognitive layer with launch/init, SMACH-like state machine, object localization, ASR, LLM prompts, IK clients, and custom msgs/srvs/actions.
  - Test_Motion: standalone hardware diagnostics that use nicomotion directly without ROS.

Quick start and environment
- First‑time setup (creates Python 3 venv at ~/.NICO-python3, installs deps, builds catkin, and generates api/activate.bash):
  ```bash
  source api/NICO-python3.bash
  ```
- Day‑to‑day activation (sources ROS + this workspace and activates the venv):
  ```bash
  source api/activate.bash
  ```
- PyRep/CoppeliaSim support when required by examples:
  ```bash
  export COPPELIASIM_ROOT=/path/to/CoppeliaSim
  source api/pyrep_env.bash
  ```
- Serial device permissions (motors/touch) per api/readme.md:
  ```bash
  sudo adduser $USER dialout
  # or set permissions per session (less preferred)
  sudo chmod 777 /dev/ttyACM*
  ```

Build (catkin)
- Toplevel catkin lives in api (see api/src/CMakeLists.txt). Rebuild with the workspace’s Python:
  ```bash
  catkin_make -C api -DPYTHON_EXECUTABLE=$HOME/.NICO-python3/bin/python
  source api/activate.bash
  ```
- MoveIt! handling during setup: api/NICO-setup.bash auto‑enables nicomoveit/kinematics by copying nicomoveit/kinematics/package_.xml to package.xml when a system MoveIt! is detected.
- For ROS distros before Noetic, api/NICO-python3.bash can build cv_bridge in api/../cv_bridge_build_ws using catkin tools and will source it automatically if present.

ELMiRA (high‑level system)
- Install ELMiRA Python deps:
  ```bash
  source api/activate.bash
  pip install -r api/src/ELMiRA/requirements.txt
  ```
- Launch all required nodes and run the state machine:
  ```bash
  source api/activate.bash
  export OPENAI_API_KEY={{OPENAI_API_KEY}}
  roslaunch elmira init_nodes.launch
  # In a separate terminal:
  source api/activate.bash
  rosrun elmira state_machine.py
  ```
- Useful visualization (from ELMiRA/README):
  ```bash
  source api/activate.bash
  rqt_image_view
  # optional (if smach_viewer works in your distro)
  rosrun smach_viewer smach_image_publisher.py
  ```

Running nicoros and MoveIt!
- Core wrappers and demos:
  ```bash
  source api/activate.bash
  roslaunch nicoros nicoros.launch
  ```
- Real robot stacks and MoveIt! (see nicoros/launch/ for variants):
  ```bash
  source api/activate.bash
  roslaunch nicoros nicoros_real.launch
  roslaunch nicoros nicoros_moveit.launch
  roslaunch nicoros nicoros_moveit_visual.launch
  ```
- Kinematics utilities (after MoveIt! is installed/enabled):
  ```bash
  source api/activate.bash
  roslaunch kinematics ikTest.launch
  roslaunch kinematics kinematics_server.launch
  ```

Audio/TTS isolation (Python 3.9)
- If TTS requires Python 3.9, use the provided wrapper for nicoros’s TextToSpeech node:
  ```bash
  bash api/src/nicoros/scripts/run_tts_node_py39.sh
  ```
  Ensure the wrapper’s venv path (~/nico_tts_py39_env) exists and that PYTHONPATH includes api/devel/lib/python3/dist-packages so custom messages import correctly.

Diagnostics and “single test” runs
- Standalone hardware diagnostics without ROS (useful for isolating hardware vs. ROS issues):
  ```bash
  source $HOME/.NICO-python3/bin/activate
  python3 Test_Motion/hardware_test.py
  # Focused joint test example:
  python3 Test_Motion/left_arm_test/l_elbow_test.py
  ```
  Note: These scripts import nicomotion directly and typically reference a motor config JSON under json/. Ensure the referenced config file path in the script exists locally.
- ROS examples for nicoros (ensure the corresponding node is also running):
  ```bash
  source api/activate.bash
  rosrun nicoros OptoforceExample.py
  ```

Documentation
- Build Sphinx docs:
  ```bash
  make -C api-doc html
  # output in api-doc/_build/html
  ```

Linting and tests
- No repo‑wide Python linter or automated unit test suite is configured. Validation is primarily via ROS nodes/launches, ELMiRA workflows, MoveIt! demos, and Test_Motion scripts.

Architecture overview (big picture)
- Low‑level device libraries (Python):
  - Each library is packaged under scripts/ with setup.py (e.g., api/src/nicomotion/setup.py). api/NICO-setup.bash installs these into the venv. nicomotion provides Motion/Mover/Kinematics; nicovision wraps video devices and image capture; nicoaudio offers playback/recording/TTS; nicoface renders and controls expressive face; nicotouch handles OptoForce and related sensors.
- ROS messaging and wrappers:
  - nicomsg defines shared msgs/srvs (e.g., bitmap_face, polynomial_face msgs; GetValue/GetValues/GetNames, audio streaming services, etc.).
  - nicoros exposes device capabilities as ROS nodes with launch files for common configurations (vision, audio, motion, touch). Scripts like Motion.py, Vision.py, TextToSpeech.py bridge to the low‑level libs.
- Motion planning and kinematics:
  - nicomoveit houses MoveIt! config (moveitgenerated), meshes/URDFs (moveitmeshes, moveiturdf), and a thin Python wrapper (moveitwrapper). The kinematics package provides C++ nodes (ikTest, kinematics_server) and simple launch files; it also defines small helper messages/services (FloatList, IK_request, FK_request, collision_check).
- Cognitive layer (ELMiRA):
  - Provides end‑to‑end demos integrating vision (object_localiser), ASR (speech_asr), LLM prompting (llm_api), coordinate transforms (coordinate_transfer), and motion execution; orchestrated by scripts/state_machine.py and scripts/states/*. Custom msgs/srvs/actions live under msg/, srv/, action/ (e.g., DetectedObject, JointPosition, PromptTextLLM, PerformASR.action). Launch/init_nodes.launch brings up the stack.
- Tooling and docs:
  - api-doc is a Sphinx project with module documentation and ROS usage pages. Test_Motion provides direct hardware tests to validate motors/hands independent of ROS.

Operational notes from repo docs
- Use api/activate.bash for consistent environment setup (ROS + venv + optional cv_bridge build overlay).
- If you depend on CoppeliaSim/PyRep features, set COPPELIASIM_ROOT and source api/pyrep_env.bash on-demand to avoid global library conflicts.
- Some systems require additional apt packages (from api/readme.md): portaudio19-dev, ffmpeg, pico2wave, setserial, v4l-utils; for building cv-bridge on older ROS: python-catkin-tools.
- TTS vs. IK dependencies can conflict across PyTorch versions; the provided run_tts_node_py39.sh demonstrates running TTS in a separate Python 3.9 venv while keeping ROS message imports working.
