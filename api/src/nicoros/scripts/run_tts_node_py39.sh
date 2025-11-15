#!/bin/bash
# Wrapper script to run TextToSpeech.py with Python 3.9

# Activate the Python 3.9 virtual environment
# Adjust this path if your venv is located elsewhere
source ~/nico_tts_py39_env/bin/activate

# Add Catkin workspace's Python message/service modules to PYTHONPATH
# This ensures that 'import nicomsg' or other custom msgs work.
# Adjust this path to your catkin workspace's devel space.
export PYTHONPATH=~/catkin_ws/src/NICO-software/api/devel/lib/python3/dist-packages:$PYTHONPATH 

# Directly execute the specific script with the Python 3.9 from the venv
# The "$@" correctly passes all arguments from roslaunch (e.g., __name:=..., __log:=...)
exec ~/nico_tts_py39_env/bin/python $(rospack find nicoros)/scripts/TextToSpeech.py "$@"
