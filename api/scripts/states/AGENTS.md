# Agents Overview – `scripts/states/`
- SMACH state definitions used by the main state machine.
- `action_parser.py` decodes LLM action lists, `action_planner.py` handles perception-to-motion planning, `move_robot.py` provides motion execution helpers.
- Enables modular orchestration of speech, perception, planning, and motion within `state_machine.py`.

