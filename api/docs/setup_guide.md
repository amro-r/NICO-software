# 🤖 ELMiRA v2 Robot Operation Guide - OpenAI GPT-4o

## Pre-Flight Checklist

### 1. USB Connections Verified
```
✅ /dev/ttyUSB0 - FTDI Dynamixel Motor Controller
✅ /dev/ttyACM0 - Teensyduino (face expressions)
✅ /dev/ttyACM1 - OptoForce DAQ (force sensor)
✅ /dev/video* - Cameras
```

### 2. Working Motors (13 total)
| Part | Motors |
|------|--------|
| Head | `head_z`, `head_y` |
| Left Arm | `l_shoulder_y`, `l_shoulder_z`, `l_arm_x`, `l_elbow_y` |
| Right Arm | `r_shoulder_y`, `r_shoulder_z`, `r_arm_x`, `r_elbow_y` |
| Right Hand | `r_wrist_z`, `r_wrist_x`, `r_indexfingers_x` |

---

## Step 1: Set Up Environment

### Terminal 1: Start ROS Core
```bash
roscore
```

### Terminal 2: Set API Key & Source Workspace
```bash
cd ~/catkin_ws/src/NICO-software/api
source activate.bash
source devel/setup.bash

# Set OpenAI API key
export OPENAI_API_KEY="your-openai-api-key-here"

# Verify it's set
echo $OPENAI_API_KEY
```

---

## Step 2: Launch the Robot

### Terminal 2 (same terminal): Launch ELMiRA v2
```bash
roslaunch elmira init_nodes_v2.launch mllm_provider:=openai
```

**Expected output:**
```
... loading Motion.py
... Connecting to /dev/ttyUSB0
✅ Robot initialized with 13 motors
... Camera node started
... MLLM Gateway started (provider: openai)
... Speech ASR started
```

---

## Step 3: Verify Nodes Are Running

### Terminal 3: Check ROS Status
```bash
cd ~/catkin_ws/src/NICO-software/api
source activate.bash
source devel/setup.bash

# Check all nodes
rosnode list
```

**Expected nodes:**
```
/rosout
/motion
/joint_controller_left
/joint_controller_right
/joint_controller_head
/camera_node (or similar)
/speech_asr
/mllm_gateway
/coordinate_transfer
/ik_solver
/text_to_speech
```

### Check Services
```bash
rosservice list | grep -E "mllm|llm|motion"
```

**Expected services:**
```
/mllm_chat
/mllm_vision
/nico/motion/getAngle
/nico/motion/setAngle
```

---

## Step 4: Test Components Individually

### Test 1: Motor Control
```bash
# Read a motor position
rosservice call /nico/motion/getAngle "joint: 'head_z'"

# Move head slightly (be careful!)
rosservice call /nico/motion/setAngle "joint: 'head_z'
angle: 10.0
speed: 0.3"
```

### Test 2: Camera
```bash
# Check camera topic
rostopic hz /nico/vision/right

# View camera (if you have display)
rosrun image_view image_view image:=/nico/vision/right
```

### Test 3: MLLM Gateway (GPT-4o)
```bash
# Simple text chat
rosservice call /mllm_chat "prompt: 'Hello, what can you do?'"
```

---

## Step 5: Run the State Machine

### Terminal 4: Start Interactive Session
```bash
cd ~/catkin_ws/src/NICO-software/api
source activate.bash
source devel/setup.bash

# Run the state machine
rosrun elmira state_machine.py
```

**The robot will now:**
1. 🎤 Listen for your voice commands
2. 🧠 Process with GPT-4o
3. 🤖 Execute actions (speak, move, detect objects)
4. 🔁 Loop back to listening

---

## Step 6: Interact with the Robot

### Voice Commands to Try:
- "Hello NICO, how are you?"
- "What objects can you see on the table?"
- "Can you touch the red ball?"
- "Push the cup to the left"
- "Wave your right arm"
- "Look down at the table"
- "Goodbye" (to quit)

---

## Troubleshooting

### Motor Connection Failed
```bash
# Check USB permissions
sudo chmod 666 /dev/ttyUSB0

# Verify config
cat ~/catkin_ws/src/NICO-software/json/nico_humanoid_upper_fixed.json | grep port
# Should show: "port": "/dev/ttyUSB0"
```

### MLLM Gateway Not Responding
```bash
# Check API key
echo $OPENAI_API_KEY

# Check node logs
rosnode info /mllm_gateway

# Test directly
python3 -c "
import openai
client = openai.OpenAI()
r = client.chat.completions.create(model='gpt-4o', messages=[{'role':'user','content':'Hi'}])
print(r.choices[0].message.content)
"
```

### Camera Not Publishing
```bash
# List video devices
ls -la /dev/video*

# Check camera node
rosnode info /camera_node
rostopic echo /nico/vision/right --noarr -n1
```

### Speech ASR Not Hearing
```bash
# Check microphone
arecord -l

# Test ASR node
rostopic echo /speech_text
```

---

## Quick Command Reference

| Action | Command |
|--------|---------|
| Start ROS | `roscore` |
| Launch robot | `roslaunch elmira init_nodes_v2.launch mllm_provider:=openai` |
| Run state machine | `rosrun elmira state_machine.py` |
| Check nodes | `rosnode list` |
| Check topics | `rostopic list` |
| View camera | `rosrun image_view image_view image:=/nico/vision/right` |
| Stop all | `Ctrl+C` in each terminal |

---

## Ready to Test?

Open **4 terminals** and run:

```bash
# Terminal 1
roscore

# Terminal 2
cd ~/catkin_ws/src/NICO-software/api && source activate.bash && source devel/setup.bash
export OPENAI_API_KEY="sk-your-key-here"
roslaunch elmira init_nodes_v2.launch mllm_provider:=openai

# Terminal 3 (after Terminal 2 is fully loaded)
cd ~/catkin_ws/src/NICO-software/api && source activate.bash && source devel/setup.bash
rosrun elmira state_machine.py

# Terminal 4 (for monitoring/debugging)
cd ~/catkin_ws/src/NICO-software/api && source activate.bash && source devel/setup.bash
rostopic echo /speech_text


```
## Peview OWLv2 Object detector

```bash
rostopic list | grep -E "result|debug|owlv2|detect"
```
You can view the OWLv2 bounding box visualization using `image_view`:

```bash
rosrun image_view image_view image:=/owlv2_server/result_image
```

This will open a window showing the camera image with bounding boxes drawn around detected objects.

**Note:** The debug image is only published when a detection request is made (when you ask the robot to interact with an object). So:

1. First run the image viewer:
   ```bash
   rosrun image_view image_view image:=/owlv2_server/result_image
   ```

2. Then ask the robot to do something like "push the orange ball" - the detection will run and you'll see the bounding boxes appear in the viewer.

Alternatively, you can also use `rqt_image_view` which has a dropdown to select topics:
```bash
rqt_image_view
```

Then select `/owlv2_server/result_image` from the dropdown menu.