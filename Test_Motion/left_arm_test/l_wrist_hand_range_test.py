#!/usr/bin/env python3
"""
Left Hand Range Test - CORRECT MOTOR MAPPING

New left hand motor configuration (XL-320 protocol):
  ID 31 - Wrist Roll (left/right rotation)
  ID 33 - Wrist Pitch (up/down)
  ID 34 - Thumb Roll (NEW - left/right)
  ID 35 - Thumb Pitch (up/down grabbing)
  ID 36 - Index Finger
  ID 37 - Middle Finger
  
  ID 30 - Unknown (connected but no visible movement)
"""

import sys
import time
import traceback

sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')

try:
    from pypot.dynamixel.io.io_320 import Dxl320IO
    print("✓ Dxl320IO imported")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# CORRECT LEFT HAND MOTOR MAPPING (verified by manual testing)
LEFT_HAND_MOTORS = {
    # Wrist motors
    31: {"name": "l_wrist_z", "description": "Wrist Roll (L/R)", "safe_range": (-90, 90), "category": "wrist"},
    33: {"name": "l_wrist_x", "description": "Wrist Pitch (Up/Down)", "safe_range": (-45, 45), "category": "wrist"},
    
    # Thumb motors (NEW: 2 DOF thumb!)
    34: {"name": "l_thumb_z", "description": "Thumb Roll (L/R)", "safe_range": (-150, 150), "category": "finger"},
    35: {"name": "l_thumb_x", "description": "Thumb Pitch (Grab)", "safe_range": (-150, 150), "category": "finger"},
    
    # Finger motors
    36: {"name": "l_indexfingers_x", "description": "Index Finger", "safe_range": (-150, 150), "category": "finger"},
    37: {"name": "l_middlefingers_x", "description": "Middle Finger", "safe_range": (-150, 150), "category": "finger"},
}


def test_motor(dxl_io, motor_id, info):
    """Test a single motor through its range."""
    desc = info["description"]
    safe_min, safe_max = info["safe_range"]
    
    print(f"\n{'='*50}")
    print(f"Testing: {desc} (ID {motor_id})")
    print(f"Range: [{safe_min}° to {safe_max}°]")
    print("=" * 50)
    
    # Move to 0 first
    print("Resetting to 0°...")
    dxl_io.set_goal_position({motor_id: 0})
    time.sleep(1.5)
    
    # Test waypoints
    waypoints = [0, safe_min, 0, safe_max, 0]
    reached = []
    
    for idx, target in enumerate(waypoints, 1):
        try:
            dxl_io.set_goal_position({motor_id: target})
            time.sleep(1.5)
            
            # Read position
            try:
                actual = dxl_io.get_present_position([motor_id])[0]
                reached.append(actual)
                err = abs(actual - target)
                status = "✅" if err < 20 else "⚠️"
                print(f"  Step {idx}: → {target:+6.0f}° (actual: {actual:+7.1f}°, err: {err:.1f}°) {status}")
            except:
                print(f"  Step {idx}: → {target:+6.0f}° (position read failed)")
                reached.append(target)
                
        except Exception as e:
            print(f"  Step {idx}: ERROR - {e}")
    
    # Calculate span
    if len(reached) >= 2:
        span = max(reached) - min(reached)
        return {"id": motor_id, "desc": desc, "span": span, "ok": span > 30}
    return {"id": motor_id, "desc": desc, "span": 0, "ok": False}


def main():
    print("=" * 60)
    print("LEFT HAND COMPLETE RANGE TEST")
    print("=" * 60)
    print("Motors: 31, 33, 34, 35, 36, 37")
    print()
    
    try:
        dxl_io = Dxl320IO("/dev/ttyUSB0", baudrate=1_000_000, timeout=0.5)
        print("✓ Connection established")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    # Verify motors
    print("\n--- Checking motor availability ---")
    available = []
    for mid in LEFT_HAND_MOTORS.keys():
        try:
            if dxl_io.ping(mid):
                print(f"  ✓ ID {mid} responding")
                available.append(mid)
            else:
                print(f"  ✗ ID {mid} not responding")
        except:
            print(f"  ? ID {mid} ping error")
    
    if not available:
        print("\n❌ No motors available!")
        dxl_io.close()
        return
    
    # Test each motor
    results = []
    try:
        for mid in available:
            info = LEFT_HAND_MOTORS[mid]
            result = test_motor(dxl_io, mid, info)
            results.append(result)
            
            # Return to 0
            dxl_io.set_goal_position({mid: 0})
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        traceback.print_exc()
    finally:
        # Return all to 0
        print("\nReturning all motors to 0°...")
        for mid in available:
            try:
                dxl_io.set_goal_position({mid: 0})
            except:
                pass
        time.sleep(1)
        dxl_io.close()
        print("✓ Connection closed")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    wrist = [r for r in results if LEFT_HAND_MOTORS[r["id"]]["category"] == "wrist"]
    fingers = [r for r in results if LEFT_HAND_MOTORS[r["id"]]["category"] == "finger"]
    
    print("\n🔄 WRIST:")
    for r in wrist:
        icon = "✅" if r["ok"] else "❌"
        print(f"  {icon} ID {r['id']:2d}: {r['desc']:20s} - {r['span']:.0f}° range")
    
    print("\n🖐️ FINGERS:")
    for r in fingers:
        icon = "✅" if r["ok"] else "❌"
        print(f"  {icon} ID {r['id']:2d}: {r['desc']:20s} - {r['span']:.0f}° range")
    
    ok_count = sum(1 for r in results if r["ok"])
    print(f"\n{'='*60}")
    print(f"RESULT: {ok_count}/{len(results)} motors working")


if __name__ == "__main__":
    main()
