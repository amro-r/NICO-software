# Individual Arm Test Results

## Test Overview
Systematic testing of left and right arm components to identify malfunctioning motors.

**Test Date:** 2025-07-08  
**Test Purpose:** Identify specific motor failures through isolated component testing  
**Hardware:** NICO Robot - Upper Body with Arms  

---

## Test Structure

### Left Arm Components
- **Shoulder:** 3 motors (pitch, roll, yaw/twist)
- **Elbow:** 1 motor (pitch)
- **Wrist:** 1 motor (roll only)
- **Fingers:** 3 fingers (index, middle, thumb)

### Right Arm Components
- **Shoulder:** 3 motors (pitch, roll, yaw/twist)
- **Elbow:** 1 motor (pitch)
- **Wrist:** 1 motor (roll only)
- **Fingers:** 3 fingers (index, middle, thumb)

---

## Test Results

### LEFT ARM TESTS

#### Test 1: Left Shoulder Test
**Script:** `left_arm_test/l_shoulder_test.py`  
**Status:** ✅ COMPLETED  
**Motors Tested:** l_shoulder_y (ID: 2), l_shoulder_z (ID: 21), l_arm_x (ID: 4)  

**Results:**
2 motors ran successfully yaw (left-right) and pitch (up-down). The roll (twist) motor didn't run
Also, during the test, when the YAW motor was running, the RIGHT shoulder YAW also ran by mistake

---

#### Test 2: Left Elbow Test
**Script:** `left_arm_test/l_elbow_test.py`  
**Motors Tested:** l_elbow_y (ID: 6)  

**Results:**
- left elbow working sucessfully

---

#### Test 3: Left Wrist Test
**Script:** `left_arm_test/l_wrist_test.py`  
**Status:** ✅ COMPLETED 
**Motors Tested:** l_wrist_z (ID: 24), l_wrist_x (ID: 25)  

**Results:**
- Unsucessful. Wrist should be tested for roll, instead the right wrist PITCH ran

---

#### Test 4: Left Fingers Test
**Script:** `left_arm_test/l_fingers_test.py`  
**Status:** ✅ COMPLETED 
**Motors Tested:** l_indexfingers_x (ID: 27), l_thumb_x (ID: 29), Middle finger (ID: TBD)  

**Results:**
- Unsucessful, Right fingers ran instead of left fingers
---

### RIGHT ARM TESTS

#### Test 5: Right Shoulder Test
**Script:** `right_arm_test/r_shoulder_test.py`  
**Status:** ✅ COMPLETED 
**Motors Tested:** r_shoulder_y (ID: 1), r_shoulder_z (ID: 22), r_arm_x (ID: 3)  

**Results:**
- Roll and pitch ran successfully, Yaw didn't run, instead the left yaw motor ran.

---

#### Test 6: Right Elbow Test
**Script:** `right_arm_test/r_elbow_test.py`  
**Status:** ✅ COMPLETED 
**Motors Tested:** r_elbow_y (ID: 5)  

**Results:**
- Sucesful, need to test in a wider range of motion, current test moved into negative angle

---

#### Test 7: Right Wrist Test
**Script:** `right_arm_test/r_wrist_test.py`  
**Status:** ✅ COMPLETED 
**Motors Tested:** r_wrist_z (ID: 23), r_wrist_x (ID: 26)  

**Results:**
Unsuccessful, didn't run
---

#### Test 8: Right Fingers Test
**Script:** `right_arm_test/r_fingers_test.py`  
**Status:** ✅ COMPLETED 
**Motors Tested:** r_indexfingers_x (ID: 28), r_thumb_x (ID: 30), Middle finger (ID: TBD)  

**Results:**
- Error, was not able to initiate motor id's (No motors found)

---

## Summary

**Working Motors:** TBD  
**Faulty Motors:** TBD  
**Overall Arm Status:** TBD  

**Key Issues Identified:**
- TBD

**Recommendations:**
- TBD

---

*Test conducted with isolated motor control to prevent cross-arm interference*