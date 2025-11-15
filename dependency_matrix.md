=== NICO-software Dependency Matrix ===

## Python Packages Setup.py Dependencies

### nicoaudio
```
    install_requires=[
        "audiotsm",
        "numpy==1.21.6",
        "pydub",
        "pyaudio",
        "pyalsaaudio",
        "requests",
        "tts",
    ],

)
```

### nicoemotionrecognition
```
    install_requires=[
        "docker",
        "flaskcom @ git+https://github.com/LemonSpeech/flaskcom.git@44660c8#egg=flaskcom",
    ],

)
```

### nicoface
```
    install_requires=["matplotlib", "numpy==1.21.6", "pillow", "posix_ipc"],

)
```

### nicomotion
```
    install_requires=["math3d", "transforms3d", "numpy==1.21.6", "matplotlib", "gaikpy",],

)
```

### nicotouch
```
```

### nicovision
```
    install_requires=[
        "numpy==1.21.6",
        # FIXME remove version when qt incompatibility fixed
        "opencv-python==4.3.0.36",
    ],

)
```


## Additional Requirements.txt Dependencies

### nicoemotionrecognition (internal requirements.txt)
```
keras==2.1.6
dlib
opencv-python==4.3.0.36
opencv-contrib-python==4.3.0.36
git+https://github.com/LemonSpeech/flaskcom.git@44660c8#egg=flaskcom
```

### ELMiRA requirements.txt
```
sounddevice
openai-whisper
openai
scipy>=1.6
evo_ik @ git+https://github.com/knowledgetechnologyuhh/evo_ik.git@v0.1.0```


## Compatibility Analysis

