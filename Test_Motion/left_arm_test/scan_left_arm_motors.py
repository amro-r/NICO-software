#!/usr/bin/env python3
"""
Robust Motor Scanner with Protocol Detection

The new left arm may use Dynamixel Protocol 2.0 while the old arm used Protocol 1.0.
This scanner tries both and scans motors one at a time to avoid cascading failures.
"""

import sys
import time
import serial

sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')

# Try to import both protocol handlers
try:
    from pypot.dynamixel.io import DxlIO
    print("✓ DxlIO (Protocol 1.0) imported")
    HAS_DXL1 = True
except ImportError as e:
    print(f"⚠️ DxlIO import failed: {e}")
    HAS_DXL1 = False

try:
    from pypot.dynamixel.io.io_320 import Dxl320IO
    print("✓ Dxl320IO (Protocol 2.0 / XL-320) imported")
    HAS_DXL320 = True
except ImportError:
    HAS_DXL320 = False

# Try the newer protocol 2.0 handler
try:
    from pypot.dynamixel.io.io_2 import Dxl2IO  
    print("✓ Dxl2IO (Protocol 2.0) imported")
    HAS_DXL2 = True
except ImportError:
    HAS_DXL2 = False


def scan_with_protocol_1(port, baud, ids_to_scan):
    """Scan using Dynamixel Protocol 1.0"""
    if not HAS_DXL1:
        return []
    
    found = []
    try:
        dxl_io = DxlIO(port, baudrate=baud, timeout=0.05)
        for motor_id in ids_to_scan:
            try:
                result = dxl_io.ping(motor_id)
                if result:
                    found.append(motor_id)
                    print(f"  ✓ ID {motor_id} responds (Protocol 1.0)")
            except Exception:
                pass  # Motor not responding on this protocol
        dxl_io.close()
    except Exception as e:
        print(f"  Protocol 1.0 connection error: {e}")
    return found


def scan_with_protocol_2(port, baud, ids_to_scan):
    """Scan using Dynamixel Protocol 2.0"""
    if not HAS_DXL2:
        return []
    
    found = []
    try:
        dxl_io = Dxl2IO(port, baudrate=baud, timeout=0.05)
        for motor_id in ids_to_scan:
            try:
                result = dxl_io.ping(motor_id)
                if result:
                    found.append(motor_id)
                    print(f"  ✓ ID {motor_id} responds (Protocol 2.0)")
            except Exception:
                pass
        dxl_io.close()
    except Exception as e:
        print(f"  Protocol 2.0 connection error: {e}")
    return found


def scan_with_xl320(port, baud, ids_to_scan):
    """Scan using XL-320 / Protocol 2.0"""
    if not HAS_DXL320:
        return []
    
    found = []
    try:
        dxl_io = Dxl320IO(port, baudrate=baud, timeout=0.05)
        for motor_id in ids_to_scan:
            try:
                result = dxl_io.ping(motor_id)
                if result:
                    found.append(motor_id)
                    print(f"  ✓ ID {motor_id} responds (XL-320/Protocol 2.0)")
            except Exception:
                pass
        dxl_io.close()
    except Exception as e:
        print(f"  XL-320 connection error: {e}")
    return found


def raw_serial_scan(port, baud):
    """
    Low-level serial scan - just check what bytes come back from pings.
    This helps identify if motors are responding at all.
    """
    print("\n" + "-" * 60)
    print("RAW SERIAL SCAN (checking for any responses)")
    print("-" * 60)
    
    try:
        ser = serial.Serial(port, baudrate=baud, timeout=0.1)
        print(f"✓ Serial port opened: {port} @ {baud}")
        
        responding_ids = []
        
        # Protocol 1.0 ping packet format: [0xFF, 0xFF, ID, 0x02, 0x01, CHECKSUM]
        for motor_id in range(1, 50):  # Scan likely IDs
            # Create Protocol 1.0 ping packet
            checksum = (~(motor_id + 0x02 + 0x01)) & 0xFF
            ping_packet = bytes([0xFF, 0xFF, motor_id, 0x02, 0x01, checksum])
            
            ser.reset_input_buffer()
            ser.write(ping_packet)
            time.sleep(0.01)
            
            response = ser.read(100)  # Read any response
            if response and len(response) > 0:
                # Filter out echo of our own packet
                if response != ping_packet:
                    responding_ids.append((motor_id, response))
                    print(f"  ID {motor_id}: Got response {response.hex()}")
        
        ser.close()
        
        if responding_ids:
            print(f"\n✅ Motors responding: {[x[0] for x in responding_ids]}")
        else:
            print("\n⚠️ No responses detected")
            
        return responding_ids
        
    except Exception as e:
        print(f"✗ Serial error: {e}")
        return []


def main():
    print("=" * 60)
    print("ROBUST MOTOR SCANNER - MULTI-PROTOCOL")
    print("=" * 60)
    
    port = "/dev/ttyUSB0"
    baud = 1000000
    
    # IDs likely to be left arm/hand motors
    left_arm_ids = [2, 4, 6, 22, 24, 26, 28, 30, 31]
    # All possible NICO IDs
    all_ids = list(range(1, 50))
    
    print(f"\nPort: {port}")
    print(f"Baudrate: {baud}")
    print(f"Scanning IDs: {all_ids}")
    
    all_found = {}
    
    # Try Protocol 1.0
    print("\n" + "-" * 60)
    print("SCANNING WITH PROTOCOL 1.0 (standard MX/AX servos)")
    print("-" * 60)
    p1_found = scan_with_protocol_1(port, baud, all_ids)
    if p1_found:
        all_found['Protocol 1.0'] = p1_found
    
    # Try Protocol 2.0
    print("\n" + "-" * 60)
    print("SCANNING WITH PROTOCOL 2.0 (XM/XH/XC servos)")
    print("-" * 60)
    p2_found = scan_with_protocol_2(port, baud, all_ids)
    if p2_found:
        all_found['Protocol 2.0'] = p2_found
    
    # Try XL-320
    print("\n" + "-" * 60)
    print("SCANNING WITH XL-320 PROTOCOL")
    print("-" * 60)
    xl_found = scan_with_xl320(port, baud, all_ids)
    if xl_found:
        all_found['XL-320'] = xl_found
    
    # Raw serial scan
    raw_results = raw_serial_scan(port, baud)
    
    # Summary
    print("\n" + "=" * 60)
    print("SCAN RESULTS SUMMARY")
    print("=" * 60)
    
    if all_found:
        for protocol, ids in all_found.items():
            print(f"\n{protocol}: {ids}")
    else:
        print("\n⚠️ No motors found with standard protocols")
    
    if raw_results:
        print(f"\n📡 Raw responses detected from IDs: {[x[0] for x in raw_results]}")
        print("   These motors ARE responding but may need protocol adjustments")
    
    # Recommendations
    print("\n" + "-" * 60)
    print("RECOMMENDATIONS")
    print("-" * 60)
    
    if not all_found and not raw_results:
        print("• No responses at all - check physical connections and power")
    elif raw_results and not all_found:
        print("• Motors ARE physically responding but protocol mismatch detected")
        print("• The new arm likely uses different servo models")
        print("• Options:")
        print("  1. Use Dynamixel Wizard 2.0 to identify the servo models")
        print("  2. Check the servo labels for model numbers (XM, XH, XL, etc.)")
        print("  3. The servos may need firmware/protocol configuration")


if __name__ == "__main__":
    main()
