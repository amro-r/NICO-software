# Agents Catalogue

## Audio Playback — `scripts/nicoaudio/AudioPlayer.py`
- **Role**: Loads audio files (or in-memory streams) and plays them asynchronously using PyAudio.
- **Key Behaviours**: Detects PulseAudio output, supports pitch shifting and time-stretching (phase vocoder), tracks playback progress, exposes volume control.
- **Used By**: `nicoaudio.TextToSpeech`, ROS TTS node in `nicoros`.

## Text-To-Speech — `scripts/nicoaudio/TextToSpeech.py`
- **Role**: High-level speech synthesis wrapper with caching and multi-backend fallbacks.
- **Backends**:
  - Mozilla TTS REST endpoint (preferred for English voices).
  - Google gTTS cloud service (when network is available).
  - `pico2wave` local CLI fallback.
- **Key Behaviours**: Caches generated clips in JSON index, exposes `say()` with language, pitch, speed, and blocking controls, streams audio through `AudioPlayer`.

## Audio Capture — `scripts/nicoaudio/AudioRecorder.py`
- **Role**: Simplified microphone recorder that writes WAV files.
- **Key Behaviours**: Wraps `_nicoaudio_internal.record_sound.RecordSound`, supports configurable samplerate and channel selection, persists recordings once stopped.

## Low-Level Utilities
- `_nicoaudio_internal/record_sound.py`: Threaded ALSA/PyAudio recorder yielding raw frames.
- `pulse_audio_recorder.py`: PulseAudio-specific stream capture helper.
- `scripts/nicoaudio/__init__.py`: Convenience imports for package consumers.

Together these agents deliver playback, synthesis, and capture capabilities that higher ROS layers (e.g., `nicoros/TextToSpeech.py`, ELMiRA's ASR beeps) depend on.
