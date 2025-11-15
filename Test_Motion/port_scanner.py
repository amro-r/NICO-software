#!/usr/bin/env python3
"""
NICO Robot Port Scanner and Motor Discovery
Scans all available serial ports to discover connected Dynamixel motors
"""

import sys
import time
import traceback
import serial
from serial.tools import list_ports

# Add the nicomotion library path
sys.path.insert(0, '/home/amr/catkin_ws/src/NICO-software/api/src/nicomotion/scripts')

try:
    import pypot.dynamixel
    from pypot.dynamixel.io import DxlIO
    print("✓ Successfully imported pypot.dynamixel")
except ImportError as e:
    print(f"✗ Failed to import pypot.dynamixel: {e}")
    sys.exit(1)

class PortScanner:
    def __init__(self):
        self.scan_results = {}
        
    def discover_serial_ports(self):
        """Discover all available serial ports"""
        print("=" * 60)
        print("SERIAL PORT DISCOVERY")
        print("=" * 60)
        
        # Get all available ports
        ports = list_ports.comports()
        available_ports = []
        
        print(f"Found {len(ports)} serial ports:")
        for port in ports:
            port_info = {
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid,
                'vid': port.vid,
                'pid': port.pid,
                'manufacturer': port.manufacturer
            }
            available_ports.append(port_info)
            print(f"  {port.device}: {port.description}")
            print(f"    Hardware ID: {port.hwid}")
            if port.manufacturer:
                print(f"    Manufacturer: {port.manufacturer}")
        
        # Also check for standard robot ports
        robot_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']
        print(f"\nChecking standard robot ports:")
        for port in robot_ports:
            try:
                # Try to open the port briefly to check if it exists
                with serial.Serial(port, 1000000, timeout=0.1):
                    print(f"  ✓ {port} - Available")
                    if port not in [p['device'] for p in available_ports]:
                        available_ports.append({'device': port, 'description': 'Robot port'})
            except (serial.SerialException, FileNotFoundError):
                print(f"  ✗ {port} - Not available")
        
        return available_ports
    
    def scan_port_for_motors(self, port_path, baudrates=[1000000, 57600, 115200]):
        """Scan a specific port for Dynamixel motors"""
        print(f"\n--- Scanning {port_path} ---")
        
        port_results = {
            'port': port_path,
            'motors': [],
            'errors': [],
            'working_baudrate': None
        }
        
        for baudrate in baudrates:
            print(f"  Trying baudrate {baudrate}...")
            
            try:
                # Try to create DxlIO connection
                dxl_io = DxlIO(port_path, baudrate=baudrate, timeout=0.1)
                
                # Scan for motors (common ID range 1-32)
                print(f"    Scanning for motors...")
                found_motors = dxl_io.scan(range(1, 33))
                
                if found_motors:
                    print(f"    ✓ Found {len(found_motors)} motors: {found_motors}")
                    port_results['motors'] = found_motors
                    port_results['working_baudrate'] = baudrate
                    
                    # Get detailed motor info
                    for motor_id in found_motors:
                        try:
                            model = dxl_io.get_model([motor_id])[0]
                            voltage = dxl_io.get_present_voltage([motor_id])[0]
                            temp = dxl_io.get_present_temperature([motor_id])[0]
                            
                            motor_info = {
                                'id': motor_id,
                                'model': model,
                                'voltage': voltage,
                                'temperature': temp
                            }
                            
                            print(f"      Motor {motor_id}: {model} (V:{voltage:.1f}V, T:{temp}°C)")
                            
                        except Exception as e:
                            print(f"      Motor {motor_id}: Details unavailable ({e})")
                
                else:
                    print(f"    No motors found")
                
                dxl_io.close()
                
                # If we found motors, use this baudrate
                if found_motors:
                    break
                    
            except Exception as e:
                error_msg = f"Baudrate {baudrate}: {str(e)}"
                port_results['errors'].append(error_msg)
                print(f"    ✗ {error_msg}")
                continue
        
        return port_results
    
    def comprehensive_scan(self):
        """Perform comprehensive scan of all ports"""
        print("\n" + "=" * 60)
        print("COMPREHENSIVE MOTOR DISCOVERY SCAN")
        print("=" * 60)
        
        # Discover ports
        available_ports = self.discover_serial_ports()
        
        # Scan each port
        all_results = []
        total_motors = 0
        
        for port_info in available_ports:
            port_path = port_info['device']
            
            # Skip camera devices
            if 'camera' in port_info.get('description', '').lower():
                print(f"\nSkipping camera device: {port_path}")
                continue
            
            result = self.scan_port_for_motors(port_path)
            all_results.append(result)
            total_motors += len(result['motors'])
            self.scan_results[port_path] = result
        
        # Summary report
        print("\n" + "=" * 60)
        print("MOTOR DISCOVERY SUMMARY")
        print("=" * 60)
        
        print(f"\nTotal motors found: {total_motors}")
        
        for result in all_results:
            port = result['port']
            motors = result['motors']
            baudrate = result['working_baudrate']
            
            if motors:
                print(f"\n✓ {port} (baudrate: {baudrate})")
                print(f"  Motors: {motors}")
            else:
                print(f"\n✗ {port}")
                print(f"  No motors found")
                if result['errors']:
                    print(f"  Errors: {result['errors'][:2]}...")  # Show first 2 errors
        
        return all_results
    
    def create_motor_map(self):
        """Create a mapping of found motors to expected robot joints"""
        print("\n" + "=" * 60)
        print("MOTOR TO JOINT MAPPING")
        print("=" * 60)
        
        # Expected motor mapping based on config
        expected_motors = {
            1: "r_shoulder_y",
            2: "l_shoulder_y", 
            3: "r_arm_x",
            4: "l_arm_x",
            5: "r_elbow_y",
            6: "l_elbow_y",
            19: "head_z",
            20: "head_y",
            21: "l_shoulder_z",
            22: "r_shoulder_z",
            23: "r_wrist_z",
            24: "l_wrist_z",  # Missing
            25: "l_wrist_x",
            26: "r_wrist_x",  # Missing
            27: "l_indexfingers_x",
            28: "r_indexfingers_x",  # Missing
            29: "l_thumb_x",
            30: "r_thumb_x",  # Missing
            31: "l_virtualhand_x",
            32: "r_virtualhand_x"  # Missing
        }
        
        # Collect all found motors
        all_found_motors = []
        for port, result in self.scan_results.items():
            for motor_id in result['motors']:
                all_found_motors.append((motor_id, port))
        
        # Sort by motor ID
        all_found_motors.sort(key=lambda x: x[0])
        
        print(f"\nFound {len(all_found_motors)} motors:")
        for motor_id, port in all_found_motors:
            joint_name = expected_motors.get(motor_id, f"Unknown motor {motor_id}")
            print(f"  ID {motor_id:2d}: {joint_name:20s} on {port}")
        
        print(f"\nMissing motors:")
        found_ids = [motor_id for motor_id, _ in all_found_motors]
        for motor_id, joint_name in expected_motors.items():
            if motor_id not in found_ids:
                print(f"  ID {motor_id:2d}: {joint_name:20s} ❌")
        
        return all_found_motors
    
    def check_specific_port(self, port_path):
        """Check a specific port in detail"""
        print(f"\n" + "=" * 60)
        print(f"DETAILED CHECK: {port_path}")
        print("=" * 60)
        
        # Check if port exists
        try:
            with serial.Serial(port_path, 1000000, timeout=0.1):
                print(f"✓ Port {port_path} is accessible")
        except Exception as e:
            print(f"✗ Cannot access {port_path}: {e}")
            return None
        
        # Scan for motors
        result = self.scan_port_for_motors(port_path)
        
        if result['motors']:
            print(f"\n✓ Found {len(result['motors'])} motors on {port_path}")
            
            # Test basic communication with each motor
            try:
                dxl_io = DxlIO(port_path, baudrate=result['working_baudrate'], timeout=0.1)
                
                for motor_id in result['motors']:
                    try:
                        # Try to read position
                        position = dxl_io.get_present_position([motor_id])[0]
                        print(f"  Motor {motor_id}: Position = {position:.1f}°")
                    except Exception as e:
                        print(f"  Motor {motor_id}: Communication error - {e}")
                
                dxl_io.close()
                
            except Exception as e:
                print(f"✗ Communication test failed: {e}")
        
        else:
            print(f"✗ No motors found on {port_path}")
        
        return result

def main():
    scanner = PortScanner()
    
    try:
        # Comprehensive scan
        results = scanner.comprehensive_scan()
        
        # Create motor mapping
        motor_map = scanner.create_motor_map()
        
        # Detailed check of /dev/ttyUSB0 (requested)
        print("\n" + "=" * 80)
        print("DETAILED /dev/ttyUSB0 ANALYSIS")
        print("=" * 80)
        ttyUSB0_result = scanner.check_specific_port('/dev/ttyUSB0')
        
        if ttyUSB0_result and ttyUSB0_result['motors']:
            print(f"\n/dev/ttyUSB0 contains the expected hand motors:")
            expected_hand_motors = [23, 25, 27, 29, 31]
            found_hand_motors = [m for m in ttyUSB0_result['motors'] if m in expected_hand_motors]
            missing_hand_motors = [m for m in expected_hand_motors if m not in ttyUSB0_result['motors']]
            
            print(f"  Found: {found_hand_motors}")
            print(f"  Missing: {missing_hand_motors}")
        
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()