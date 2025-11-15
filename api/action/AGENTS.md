# Agents Overview – `action/`
- **PerformASR.action** defines the ROS action contract used by the speech recognition server.
- Captures goal parameters (start/stop detection flags, timing thresholds, live feedback toggle) consumed by `speech_asr.py`.
- Exposes result/feedback channels with stop reasons, transcript text, and timing metadata so the SMACH state machine can react to audio capture progress.

