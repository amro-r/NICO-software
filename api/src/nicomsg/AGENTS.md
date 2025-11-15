# Interfaces Catalogue

`nicomsg` does not ship executable agents; it defines the ROS message and service contracts that bind the NICO software stack together.

## Message Families (`msg/`)
- **Motion Control**: `sff`, `sfff`, `sf`, `sffff`, etc. carry joint names with position/velocity targets used by `nicoros/Motion.py` and MoveIt wrappers.
- **Facial Expressions**: `polynomial_face`, `polynomial_mouth`, `wavelet_face`, `bitmap_face` encapsulate parameters for head display control.
- **Generic Data**: `empty`, `f`, `fff`, `affffa`, `iii`, `hs`, etc. provide typed payloads for recurrent patterns (floats, ints, string+float combos).

## Services (`srv/`)
- **Motion Services**: `GetAngle`, `GetValues`, `GetNames`, `SetIntValue`, `GetPID`, etc. allow clients to query and command actuators.
- **Audio Services**: `SayText`, `LoadAudio`, `StartAudioStream`, `StopAudioStream`, `GetAudioIDs` underpin the speech subsystem.
- **Utility Services**: `GetString`, `GetFilename`, `GetChannelStates` supply configuration and diagnostics.

These interfaces act as the common vocabulary for agents in `nicoros`, `ELMiRA`, and supporting packages.
