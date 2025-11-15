# Agents Catalogue

## Emotion Recognition Runtime — `scripts/nicoemotionrecognition/EmotionRecognition.py`
- **Role**: Real-time facial affect analysis using TensorFlow models and NICO-specific peripherals.
- **Capabilities**:
  - Captures frames via `nicovision.VideoDevice`.
  - Runs categorical CNN (`modelDictionary.CategoricaModel`) for discrete emotion labels; optional dimensional model hooks.
  - Drives GUI overlays (`GUIController`) and optional face mirroring via `nicoface.FaceExpression`.
  - Triggers spoken reactions with `nicoaudio.TextToSpeech` when voice feedback is enabled.
- **Key Behaviours**: Manages capture callbacks, throttles detection, keeps history counters to avoid jitter, and optionally steers robot head for face tracking.

## Internal Modules (`_nicoemotionrecognition_internal`)
- `GUIController`: Tkinter/Qt-based interface for live visuals and charts.
- `imageProcessingUtil`: Face detection, alignment, and preprocessing pipeline.
- `modelLoader`: Convenience loader for TensorFlow models defined in `modelDictionary`.

These agents combine to provide an affective perception channel that can be integrated into broader interaction workflows.
