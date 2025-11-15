# Motor ID Map

This document captures the verified motor ID assignments on the NICO humanoid upper-body robot. Each entry lists the logical joint name, the intended axis of rotation, and any hardware or software mismatches uncovered while running the dedicated motion tests. The mapping is built while executing the `Test_Motion` diagnostics so that any misconfiguration can be corrected immediately.

## Left Arm Motors

| Joint Name | Intended Axis | Verified Motor ID | Config Reference | Test Result | Notes |
|------------|---------------|-------------------|------------------|-------------|-------|
| `l_shoulder_y` | Shoulder pitch (forward/back) | 2 | `Test_Motion/test_config.json` &rarr; `motors.l_shoulder_y.id` | ✅ Pass (pitch test) | Motion matches the left shoulder pitch joint exactly.
| `l_shoulder_z` | Shoulder roll (lift/drop arm sideways) | **22** | `json/nico_humanoid_upper.json` & `json/nico_humanoid_upper_rh7d.json` &rarr; `motors.l_shoulder_z.id` | ⚠️ Roll command moved the **right** shoulder | Hardware wiring follows the canonical configs (ID 22); the old `Test_Motion/test_config.json` used ID 21, which triggered the right shoulder until we swapped the IDs back.
| `l_arm_x` | Arm twist/yaw (rotates upper arm) | 4 | `Test_Motion/test_config.json` &rarr; `motors.l_arm_x.id` | ✅ Pass (twist test) | Angle offsets already include the +32° compensation used in tests.
| `l_elbow_y` | Elbow flexion | 6 | `Test_Motion/test_config.json` &rarr; `motors.l_elbow_y.id` | ⏳ Pending | Not part of the initial left-shoulder test run but included here for completeness before elbow tests.

### Findings for the Left Shoulder Roll
- The dedicated `l_shoulder_z` test invoked motor ID 21 because the test harness reads IDs from `Test_Motion/test_config.json`.
- Motor ID 21 is actually wired to the **right** shoulder roll (`r_shoulder_z`), as confirmed by the reaction observed during the test and by the canonical robot configs under the `json/` directory.
- Therefore the left and right shoulder roll IDs are swapped in `Test_Motion/test_config.json` (and in helper utilities such as `Test_Motion/port_scanner.py`).

### Resolution
- `Test_Motion/test_config.json` (and helper utilities) now map:
  - `l_shoulder_z` &rarr; motor ID **22**
  - `r_shoulder_z` &rarr; motor ID **21**
- Re-run `Test_Motion/left_arm_test/l_shoulder_test.py` to verify the roll motion now stays on the left shoulder.

Future sections of this document will be expanded with the remaining motors as their diagnostic tests are executed.
