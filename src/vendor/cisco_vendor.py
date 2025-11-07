"""
Cisco Vendor Implementation
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from core.constants import VendorType, CommandType, CISCO_COMMAND_TEMPLATES
from models.device_models import DeviceInfo, CommandResult, ConnectionConfig, DeviceCapabilities
from vendor.base_vendor import BaseVendor
from utils.logging import get_logger


class CiscoVendor(BaseVendor):
    """Cisco vendor implementation"""
    
    def __init__(self):
        super().__init__(VendorType.CISCO)
        self.config_mode = False
        self.privileged_mode = False
        self.current_context = ""
        
    async def connect(self, config: ConnectionConfig) -> bool:
        """Connect to Cisco device via serial"""
        try:
            # Simulate serial connection (in real implementation, use pyserial)
            self.logger.info(f"Connecting to Cisco device on {config.com_port}")
            
            # Simulate connection delay
            await asyncio.sleep(1)
            
            # Set connection properties
            self.connection = config
            self._connected = True
            
            # Get device info
            self.device_info = await self.get_device_info()
            self.capabilities = await self.get_capabilities()
            
            self.logger.info(f"Connected to Cisco device: {self.device_info.device_model}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Cisco device: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Cisco device"""
        try:
            self.logger.info("Disconnecting from Cisco device")
            self._connected = False
            self.connection = None
            self.device_info = None
            self.capabilities = None
            return True
        except Exception as e:
            self.logger.error(f"Error disconnecting from Cisco device: {e}")
            return False
    
    async def execute_command(self, command: str, command_type: CommandType = CommandType.MANUAL) -> CommandResult:
        """Execute command on Cisco device"""
        start_time = datetime.utcnow()
        
        try:
            if not self._connected:
                return CommandResult(
                    command=command,
                    output="",
                    success=False,
                    error="Not connected to device",
                    execution_time=(datetime.utcnow() - start_time).total_seconds()
                )
            
            # Validate command
            if not self.validate_command(command, command_type):
                return CommandResult(
                    command=command,
                    output="",
                    success=False,
                    error="Invalid command",
                    execution_time=(datetime.utcnow() - start_time).total_seconds()
                )
            
            # Normalize command
            normalized_command = self.normalize_command(command)
            
            # Simulate command execution (in real implementation, use netmiko)
            self.logger.debug(f"Executing command: {normalized_command}")
            
            # Simulate execution delay
            await asyncio.sleep(0.5)
            
            # Generate mock output based on command
            output = self._generate_mock_output(normalized_command, command_type)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return CommandResult(
                command=command,
                output=output,
                success=True,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.logger.error(f"Error executing command '{command}': {e}")
            return CommandResult(
                command=command,
                output="",
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def _generate_mock_output(self, command: str, command_type: CommandType) -> str:
        """Generate mock output for testing"""
        command_lower = command.lower()
        
        if "show version" in command_lower:
            return """Cisco IOS Software, C2960 Software (C2960-LANBASEK9-M), Version 15.0(2)SE11, RELEASE SOFTWARE (fc3)
Technical Support: http://www.cisco.com/techsupport
Copyright (c) 1986-2017 by Cisco Systems, Inc.
Compiled Mon 18-Dec-17 05:03 by prod_rel_team

ROM: Bootstrap program is C2960 boot loader
BOOTLDR: C2960 Boot Loader (C2960-HBOOT-M) Version 12.2(58r)SE1, RELEASE SOFTWARE (fc1)

Switch uptime is 1 week, 3 days, 15 hours, 22 minutes
System returned to ROM by power-on
System image file is "flash:c2960-lanbasek9-mz.150-2.SE11.bin"

This product contains cryptographic features and is subject to United
States and local country laws governing import, export, transfer and
use. Delivery of Cisco cryptographic products does not imply
third-party authority to import, export, distribute or use encryption.
Importers, exporters, distributors and users are responsible for
compliance with U.S. and local country laws. By using this product you
agree to comply with applicable laws and regulations. If you are unable
to comply with U.S. and local laws, return this product immediately.

cisco WS-C2960-24TT-L (PowerPC405) processor (revision H0) with 65536K bytes of memory.
Processor board ID FOC12345678
Last reset from power-on
1 Virtual Ethernet interface
24 FastEthernet interfaces
2 Gigabit Ethernet interfaces
The password-recovery mechanism is enabled.

64K bytes of flash-simulated non-volatile configuration memory.
Base ethernet MAC Address       : 00:1A:2B:3C:4D:5E
Motherboard assembly number     : 73-12345-67
Power supply part number        : 341-0097-02
Motherboard serial number       : FOC12345678
Power supply serial number      : DCA12345678
Model revision number           : H0
Motherboard revision number     : A0
Model number                    : WS-C2960-24TT-L
System serial number            : FOC12345678
Top Assembly Part Number        : 800-12345-67
Top Assembly Revision Number    : A0
Version ID                      : V02
CLEI Code Number                : COUIAB8BAA
Hardware Board Revision Number  : 0x01


Switch Ports Model              SW Version            SW Image                 
------ ----- -----             ----------            ----------               
*    1 26    WS-C2960-24TT-L   15.0(2)SE11         C2960-LANBASEK9-M      


Configuration register is 0xF"""
        
        elif "show interfaces" in command_lower:
            return """FastEthernet0/1 is up, line protocol is up (connected) 
  Hardware is Fast Ethernet, address is 001a.2b3c.4d5e (bia 001a.2b3c.4d5e)
  MTU 1500 bytes, BW 100000 Kbit/sec, DLY 100 usec, 
     reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA, loopback not set
  Keepalive set (10 sec)
  Full-duplex, 100Mb/s, media type is 10/100BaseTX
  input flow-control is off, output flow-control is unsupported 
  ARP type: ARPA, ARP Timeout 04:00:00
  Last input 00:00:05, output 00:00:01, output hang never
  Last clearing of "show interface" counters never
  Input queue: 0/75/0/0 (size/max/drops/flushes); Total output drops: 0
  Queueing strategy: fifo
  Output queue: 0/40 (size/max)
  5 minute input rate 0 bits/sec, 0 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     1234567 packets input, 123456789 bytes, 0 no buffer
     Received 1234567 broadcasts (1234567 multicasts)
     0 runts, 0 giants, 0 throttles
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored
     0 watchdog, 1234567 multicast, 0 pause input
     0 input packets with dribble condition detected
     2345678 packets output, 234567890 bytes, 0 underruns
     0 output errors, 0 collisions, 1 interface resets
     0 unknown protocol drops
     0 babbles, 0 late collision, 0 deferred
     0 lost carrier, 0 no carrier, 0 pause output
     0 output buffer failures, 0 output buffers swapped out

FastEthernet0/2 is down, line protocol is down (notconnect)
  Hardware is Fast Ethernet, address is 001a.2b3c.4d5f (bia 001a.2b3c.4d5f)
  MTU 1500 bytes, BW 100000 Kbit/sec, DLY 100 usec, 
     reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA, loopback not set
  Keepalive set (10 sec)
  Auto-duplex, Auto-speed, media type is 10/100BaseTX
  input flow-control is off, output flow-control is unsupported 
  ARP type: ARPA, ARP Timeout 04:00:00
  Last input never, output never, output hang never
  Last clearing of "show interface" counters never
  Input queue: 0/75/0/0 (size/max/drops/flushes); Total output drops: 0
  Queueing strategy: fifo
  Output queue: 0/40 (size/max)"""
        
        elif "show vlan" in command_lower:
            return """VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Fa0/3, Fa0/4, Fa0/5, Fa0/6, Fa0/7, Fa0/8, Fa0/9
                                                Fa0/10, Fa0/11, Fa0/12, Fa0/13, Fa0/14, Fa0/15
                                                Fa0/16, Fa0/17, Fa0/18, Fa0/19, Fa0/20, Fa0/21
                                                Fa0/22, Fa0/23, Fa0/24, Gi0/1, Gi0/2
10   SALES                            active    Fa0/1, Fa0/2
20   MARKETING                        active    
30   ENGINEERING                      active    
100  MANAGEMENT                       active    
1002 fddi-default                     act/unsup 
1003 token-ring-default               act/unsup 
1004 fddinet-default                  act/unsup 
1005 trnet-default                     act/unsup 

VLAN Type  SAID       MTU   Parent RingNo BridgeNo Stp  BrdgMode Trans1 Trans2
---- ----- ---------- ----- ------ ------ -------- ---- -------- ------ ------
1    enet  100001     1500  -      -      -        -    -        0      0   
10   enet  100010     1500  -      -      -        -    -        0      0   
20   enet  100020     1500  -      -      -        -    -        0      0   
30   enet  100030     1500  -      -      -        -    -        0      0   
100  enet  100100     1500  -      -      -        -    -        0      0   
1002 fddi  101002     1500  -      -      -        -    -        0      0   
1003 tr    101003     1500  -      -      -        -    -        0      0   
1004 fdnet 101004     1500  -      -      -        ieee -        0      0   
1005 trnet 101005     1500  -      -      -        ibm  -        0      0   

Remote SPAN VLANs
------------------------------------------------------------------------------
Primary Secondary Type              Ports
------- --------- ----------------- ------------------------------------------"""
        
        elif "show ip route" in command_lower:
            return """Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area 
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, E - EGP
       i - IS-IS, L1 - IS-IS level-1, L2 - IS-IS level-2, ia - IS-IS inter area
       * - candidate default, U - per-user static route, o - ODR
       P - periodic downloaded static route

Gateway of last resort is 192.168.1.1 to network 0.0.0.0

     10.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
C       10.1.1.0/24 is directly connected, Vlan10
L       10.1.1.254/32 is directly connected, Vlan10
     192.168.1.0/24 is variably subnetted, 2 subnets, 2 masks
C       192.168.1.0/24 is directly connected, Vlan1
L       192.168.1.254/32 is directly connected, Vlan1
S*   0.0.0.0/0 [1/0] via 192.168.1.1"""
        
        else:
            return f"Command '{command}' executed successfully.\nOutput: [Command output would appear here]"
    
    async def get_device_info(self) -> DeviceInfo:
        """Get Cisco device information"""
        try:
            result = await self.execute_command("show version")
            if result.success:
                # Parse device info from show version output
                device_info = self.parse_show_output("show version", result.output)
                return DeviceInfo(**device_info)
            
            # Return default device info
            return DeviceInfo(
                device_model="WS-C2960-24TT-L",
                os_version="15.0(2)SE11",
                serial_number="FOC12345678",
                hostname="Switch",
                uptime="1 week, 3 days, 15 hours, 22 minutes"
            )
        except Exception as e:
            self.logger.error(f"Failed to get device info: {e}")
            return DeviceInfo()
    
    async def get_capabilities(self) -> DeviceCapabilities:
        """Get Cisco device capabilities"""
        return DeviceCapabilities(
            supports_config_mode=True,
            supports_commit_rollback=False,
            supports_hierarchical_config=False,
            supports_multiple_contexts=False,
            supports_stacking=True,
            supports_virtualization=False,
            max_interfaces=26,
            max_vlans=1005,
            supported_protocols=["STP", "RSTP", "PVST+", "VTP", "CDP", "LLDP", "SNMP", "RIP", "OSPF", "EIGRP", "BGP"]
        )
    
    def get_prompt_patterns(self) -> Dict[str, str]:
        """Get Cisco prompt patterns"""
        return {
            "user_mode": r"^[^#>]+>",
            "privileged_mode": r"^[^#>]+#",
            "config_mode": r"^[^#>]+\(config\)#",
            "interface_config": r"^[^#>]+\(config-if\)#",
            "line_config": r"^[^#>]+\(config-line\)#",
            "vlan_config": r"^[^#>]+\(config-vlan\)#"
        }
    
    def get_command_templates(self) -> Dict[str, List[str]]:
        """Get Cisco command templates"""
        return CISCO_COMMAND_TEMPLATES
    
    def parse_show_output(self, command: str, output: str) -> Dict[str, Any]:
        """Parse Cisco show command output"""
        command_lower = command.lower()
        
        if "show version" in command_lower:
            return self._parse_show_version(output)
        elif "show interfaces" in command_lower:
            return self._parse_show_interfaces(output)
        elif "show vlan" in command_lower:
            return self._parse_show_vlan(output)
        elif "show ip route" in command_lower:
            return self._parse_show_ip_route(output)
        
        return {"raw_output": output}
    
    def _parse_show_version(self, output: str) -> Dict[str, Any]:
        """Parse show version output"""
        device_info = {}
        
        # Extract software version
        version_match = re.search(r"Version\s+(\S+)", output)
        if version_match:
            device_info["os_version"] = version_match.group(1)
        
        # Extract device model
        model_match = re.search(r"Model number\s*:\s*(\S+)", output, re.IGNORECASE)
        if model_match:
            device_info["device_model"] = model_match.group(1)
        
        # Extract serial number
        serial_match = re.search(r"System serial number\s*:\s*(\S+)", output, re.IGNORECASE)
        if serial_match:
            device_info["serial_number"] = serial_match.group(1)
        
        # Extract hostname
        hostname_match = re.search(r"^([^#>\s]+)", output)
        if hostname_match:
            device_info["hostname"] = hostname_match.group(1)
        
        # Extract uptime
        uptime_match = re.search(r"uptime is\s+(.+?)(?:\n|$)", output, re.IGNORECASE)
        if uptime_match:
            device_info["uptime"] = uptime_match.group(1).strip()
        
        return device_info
    
    def _parse_show_interfaces(self, output: str) -> List[Dict[str, Any]]:
        """Parse show interfaces output"""
        interfaces = []
        interface_blocks = re.split(r'\n(?=\w+\d+/\d+\s+is)', output)
        
        for block in interface_blocks:
            if not block.strip():
                continue
                
            interface = {}
            
            # Extract interface name and status
            name_status_match = re.match(r'(\S+)\s+is\s+(\w+),\s+line protocol is\s+(\w+)', block)
            if name_status_match:
                interface["name"] = name_status_match.group(1)
                interface["status"] = name_status_match.group(2)
                interface["protocol_status"] = name_status_match.group(3)
            
            # Extract MAC address
            mac_match = re.search(r'address is\s+([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})', block)
            if mac_match:
                interface["mac_address"] = mac_match.group(1)
            
            # Extract MTU and bandwidth
            mtu_match = re.search(r'MTU\s+(\d+)\s+bytes.*BW\s+(\d+)\s+Kbit', block)
            if mtu_match:
                interface["mtu"] = int(mtu_match.group(1))
                interface["bandwidth"] = int(mtu_match.group(2))
            
            # Extract duplex and speed
            duplex_speed_match = re.search(r'(\w+)-duplex.*?(\d+\w+/s)', block)
            if duplex_speed_match:
                interface["duplex"] = duplex_speed_match.group(1)
                interface["speed"] = duplex_speed_match.group(2)
            
            # Extract input/output rates
            rate_match = re.search(r'5 minute input rate\s+(\d+)\s+bits/sec.*?(\d+)\s+packets/sec', block)
            if rate_match:
                interface["input_rate_bps"] = int(rate_match.group(1))
                interface["input_rate_pps"] = int(rate_match.group(2))
            
            rate_match = re.search(r'5 minute output rate\s+(\d+)\s+bits/sec.*?(\d+)\s+packets/sec', block)
            if rate_match:
                interface["output_rate_bps"] = int(rate_match.group(1))
                interface["output_rate_pps"] = int(rate_match.group(2))
            
            # Extract error counters
            error_match = re.search(r'(\d+)\s+input errors.*?(\d+)\s+CRC', block)
            if error_match:
                interface["input_errors"] = int(error_match.group(1))
                interface["crc_errors"] = int(error_match.group(2))
            
            error_match = re.search(r'(\d+)\s+output errors.*?(\d+)\s+collisions', block)
            if error_match:
                interface["output_errors"] = int(error_match.group(1))
                interface["collisions"] = int(error_match.group(2))
            
            if interface:
                interfaces.append(interface)
        
        return interfaces
    
    def _parse_show_vlan(self, output: str) -> List[Dict[str, Any]]:
        """Parse show vlan output"""
        vlans = []
        lines = output.split('\n')
        
        for line in lines:
            if re.match(r'^\d+\s+', line):
                parts = line.split()
                if len(parts) >= 3:
                    vlan = {
                        "vlan_id": int(parts[0]),
                        "name": parts[1],
                        "status": parts[2],
                        "ports": []
                    }
                    
                    # Extract ports if present
                    if len(parts) > 3:
                        vlan["ports"] = parts[3:]
                    
                    vlans.append(vlan)
        
        return vlans
    
    def _parse_show_ip_route(self, output: str) -> List[Dict[str, Any]]:
        """Parse show ip route output"""
        routes = []
        lines = output.split('\n')
        
        for line in lines:
            # Look for route entries
            route_match = re.match(r'^([A-Z*]+)\s+([0-9.]+/[0-9]+)\s+\[([0-9]+)/([0-9]+)\]\s+via\s+([0-9.]+)', line)
            if route_match:
                route = {
                    "protocol": route_match.group(1),
                    "network": route_match.group(2),
                    "admin_distance": int(route_match.group(3)),
                    "metric": int(route_match.group(4)),
                    "next_hop": route_match.group(5)
                }
                routes.append(route)
        
        return routes
    
    def parse_config_output(self, output: str) -> Dict[str, Any]:
        """Parse Cisco configuration output"""
        # Basic config parsing
        config_lines = output.split('\n')
        config_dict = {
            "hostname": None,
            "interfaces": [],
            "vlans": [],
            "routing": {}
        }
        
        current_interface = None
        
        for line in config_lines:
            line = line.strip()
            
            # Hostname
            if line.startswith("hostname "):
                config_dict["hostname"] = line.split()[1]
            
            # Interface configuration
            elif line.startswith("interface "):
                current_interface = line.split()[1]
                config_dict["interfaces"].append({
                    "name": current_interface,
                    "config": []
                })
            
            elif current_interface and line.startswith(" "):
                if config_dict["interfaces"]:
                    config_dict["interfaces"][-1]["config"].append(line.strip())
            
            elif line and not line.startswith("!"):
                current_interface = None
        
        return config_dict
    
    def normalize_command(self, command: str) -> str:
        """Normalize Cisco command"""
        command = command.strip()
        
        # Handle common abbreviations
        abbreviations = {
            "sh": "show",
            "shw": "show",
            "int": "interface",
            "intface": "interface",
            "conf": "configure",
            "config": "configure",
            "ter": "terminal",
            "ver": "version",
            "vlan": "vlan",
            "ip": "ip",
            "route": "route",
            "rt": "route"
        }
        
        parts = command.split()
        normalized_parts = []
        
        for part in parts:
            lower_part = part.lower()
            if lower_part in abbreviations:
                normalized_parts.append(abbreviations[lower_part])
            else:
                normalized_parts.append(part)
        
        return " ".join(normalized_parts)
    
    def _validate_config_command(self, command: str) -> bool:
        """Validate Cisco configuration commands"""
        # Basic validation for Cisco config commands
        valid_config_commands = [
            "configure", "interface", "vlan", "hostname", "ip",
            "router", "line", "enable", "username", "password",
            "spanning-tree", "switchport", "no"
        ]
        
        command_lower = command.lower().strip()
        
        # Check if command starts with valid config command
        for valid_cmd in valid_config_commands:
            if command_lower.startswith(valid_cmd):
                return True
        
        return False
    
    def _validate_show_command(self, command: str) -> bool:
        """Validate Cisco show commands"""
        # Basic validation for Cisco show commands
        valid_show_commands = [
            "show version", "show interfaces", "show vlan", "show ip",
            "show running-config", "show startup-config", "show mac",
            "show arp", "show cdp", "show lldp", "show spanning-tree",
            "show port", "show users", "show sessions", "show history"
        ]
        
        command_lower = command.lower().strip()
        
        # Check if command matches valid show command patterns
        for valid_cmd in valid_show_commands:
            if command_lower.startswith(valid_cmd.split()[0]) and command_lower.split()[1] in valid_cmd:
                return True
        
        return command_lower.startswith("show")
    
    def _validate_debug_command(self, command: str) -> bool:
        """Validate Cisco debug commands"""
        # Basic validation for Cisco debug commands
        return command.lower().strip().startswith("debug")
    
    def is_config_mode_prompt(self, prompt: str) -> bool:
        """Check if prompt indicates configuration mode"""
        return "(config)" in prompt or "(config-" in prompt
    
    def is_privileged_mode_prompt(self, prompt: str) -> bool:
        """Check if prompt indicates privileged mode"""
        return prompt.endswith("#") and not self.is_config_mode_prompt(prompt)
    
    async def enter_config_mode(self) -> bool:
        """Enter configuration mode"""
        try:
            result = await self.execute_command("configure terminal", CommandType.CONFIG)
            if result.success:
                self.config_mode = True
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to enter config mode: {e}")
            return False
    
    async def exit_config_mode(self) -> bool:
        """Exit configuration mode"""
        try:
            result = await self.execute_command("exit", CommandType.CONFIG)
            if result.success:
                self.config_mode = False
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to exit config mode: {e}")
            return False
    
    async def save_config(self) -> CommandResult:
        """Save configuration"""
        try:
            result = await self.execute_command("write memory", CommandType.CONFIG)
            if result.success:
                return CommandResult(
                    command="write memory",
                    output="Configuration saved successfully",
                    success=True
                )
            return result
        except Exception as e:
            return CommandResult(
                command="write memory",
                output="",
                success=False,
                error=str(e)
            )
    
    def get_error_recovery_suggestions(self, error: str) -> List[str]:
        """Get Cisco-specific error recovery suggestions"""
        suggestions = [
            "Check command syntax with 'show ?' or 'command ?'",
            "Verify device is in correct mode (user/exec/config)",
            "Use 'show running-config' to verify current configuration",
            "Check privilege level with 'show privilege'"
        ]
        
        error_lower = error.lower()
        
        if "invalid" in error_lower:
            suggestions.append("Use '?' to see available command options")
        elif "incomplete" in error_lower:
            suggestions.append("Use '?' to see required parameters")
        elif "unrecognized" in error_lower:
            suggestions.append("Check for typos in command")
        
        return suggestions


# Import asyncio for the mock implementation
import asyncio