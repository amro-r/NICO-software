# Agents Overview – `scripts/`
- Runtime ROS nodes and helpers powering ELMiRA.
- Key executables: `state_machine.py`, `speech_asr.py`, `object_localiser.py`, `coordinate_transfer.py`, `ik_solver.py`, `llm_api.py`.
- Support modules: `coordinate_transfer_net.py`, `multi_action_server.py`, `states/` SMACH definitions.
- All scripts are installed as ROS nodes via `rosrun elmira <script>.py`.

