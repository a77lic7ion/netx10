"""
Serial Communication Service for NetworkSwitch AI Assistant
"""

import asyncio
import serial
import serial.tools.list_ports
import serial_asyncio
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
import re
import time

from core.config import AppConfig
from core.constants import VENDOR_CONFIGS
from utils.logging import get_logger


class SerialConnection:
    """Serial connection wrapper with enhanced features"""

    def __init__(self, port: str, serial_config):
        self.port = port
        # serial_config is expected to be SerialConfig (from core.config)
        self.config = serial_config
        self.logger = get_logger(f"serial_connection_{port}")
        
        self.serial: Optional[serial_asyncio.SerialTransport] = None
        self.reader: Optional[serial_asyncio.SerialReader] = None
        self.writer: Optional[serial_asyncio.SerialWriter] = None
        
        self.is_connected = False
        self.is_connecting = False
        self.connection_start_time: Optional[datetime] = None
        
        # Connection settings (read directly from SerialConfig passed in)
        self.baud_rate = getattr(self.config, "baud_rate", 9600)
        self.data_bits = getattr(self.config, "data_bits", 8)
        self.parity = getattr(self.config, "parity", "N")
        self.stop_bits = getattr(self.config, "stop_bits", 1)
        self.timeout = getattr(self.config, "timeout", 10.0)
        self.write_timeout = getattr(self.config, "write_timeout", 2.0)

        # Vendor-specific settings
        self.vendor_type: Optional[str] = None
        # Support multiple vendor prompt patterns
        self.prompt_patterns: Optional[List[str]] = None
        self.login_sequence: Optional[List[str]] = None
        
        # Data handling
        self.receive_buffer = ""
        self.response_callback: Optional[Callable[[str], None]] = None
        self.data_callback: Optional[Callable[[bytes], None]] = None
        # Per-command completion signaling (used by send_command)
        self._command_event: Optional[asyncio.Event] = None
        
        # Statistics
        self.bytes_sent = 0
        self.bytes_received = 0
        self.commands_sent = 0
        self.responses_received = 0
        self.errors_count = 0
        
    async def connect(self, vendor_type: Optional[str] = None) -> bool:
        """Establish serial connection"""
        if self.is_connected or self.is_connecting:
            return self.is_connected
        
        self.is_connecting = True
        self.logger.info(f"Connecting to {self.port} at {self.baud_rate} baud")
        
        try:
            # Apply vendor-specific settings if provided
            if vendor_type:
                await self._apply_vendor_settings(vendor_type)
            
            # Create serial connection
            self.reader, self.writer = await serial_asyncio.open_serial_connection(
                url=self.port,
                baudrate=self.baud_rate,
                bytesize=self.data_bits,
                parity=self.parity,
                stopbits=self.stop_bits,
                timeout=self.timeout,
                write_timeout=self.write_timeout
            )
            
            # Get the transport for advanced features
            self.serial = self.writer.transport
            
            self.is_connected = True
            self.is_connecting = False
            self.connection_start_time = datetime.utcnow()
            
            self.logger.info(f"Successfully connected to {self.port}")
            
            # Start reading task
            asyncio.create_task(self._read_loop())
            
            # Perform vendor-specific login sequence if needed
            if self.login_sequence:
                await self._perform_login_sequence()
            
            return True
            
        except Exception as e:
            self.is_connecting = False
            self.logger.error(f"Failed to connect to {self.port}: {e}")
            self.errors_count += 1
            return False
    
    async def _apply_vendor_settings(self, vendor_type: str):
        """Apply vendor-specific serial settings"""
        self.vendor_type = vendor_type.lower()
        
        if self.vendor_type in VENDOR_CONFIGS:
            vendor_config = VENDOR_CONFIGS[self.vendor_type].get('serial_settings', {})
            
            # Apply settings
            if "baud_rate" in vendor_config:
                self.baud_rate = vendor_config["baud_rate"]
            if "data_bits" in vendor_config:
                self.data_bits = vendor_config["data_bits"]
            if "parity" in vendor_config:
                self.parity = vendor_config["parity"]
            if "stop_bits" in vendor_config:
                self.stop_bits = vendor_config["stop_bits"]
            if "timeout" in vendor_config:
                self.timeout = vendor_config["timeout"]
            
            # Set prompt pattern for command completion detection
            # Accept multiple prompt patterns from vendor config
            if "prompt_patterns" in vendor_config:
                self.prompt_patterns = vendor_config["prompt_patterns"]
            
            # Set login sequence if needed
            if "login_sequence" in vendor_config:
                self.login_sequence = vendor_config["login_sequence"]
            
            self.logger.info(f"Applied vendor settings for {vendor_type}")
    
    async def _perform_login_sequence(self):
        """Perform vendor-specific login sequence"""
        if not self.login_sequence:
            return
        
        self.logger.info(f"Performing login sequence for {self.vendor_type}")
        
        try:
            for step in self.login_sequence:
                if isinstance(step, dict):
                    command = step.get("command", "")
                    expect = step.get("expect", "")
                    wait_time = step.get("wait", 1)
                    
                    if command:
                        await self.write(command + "\n")
                    
                    if expect:
                        # Wait for expected response
                        await asyncio.sleep(wait_time)
                else:
                    # Simple string command
                    await self.write(step + "\n")
                    await asyncio.sleep(1)
            
            self.logger.info("Login sequence completed")
            
        except Exception as e:
            self.logger.error(f"Login sequence failed: {e}")
            self.errors_count += 1
    
    async def _read_loop(self):
        """Main read loop for incoming data"""
        try:
            while self.is_connected and self.reader:
                try:
                    # Read available data
                    data = await self.reader.read(1024)
                    
                    if not data:
                        continue

                    self.bytes_received += len(data)
                    
                    # Handle raw data callback
                    if self.data_callback:
                        try:
                            self.data_callback(data)
                        except Exception as cb_err:
                            self.logger.error(f"Data callback error: {cb_err!r}")
                            self.errors_count += 1
                    
                    # Process text data
                    try:
                        text_data = data.decode('utf-8', errors='ignore')
                    except Exception as dec_err:
                        self.logger.error(f"Decode error: {dec_err!r}")
                        text_data = ""
                    self.receive_buffer += text_data
                    
                    # Check for complete responses
                    try:
                        await self._process_receive_buffer()
                    except Exception as proc_err:
                        # Never let buffer processing kill the read loop
                        self.logger.error(f"Buffer processing error: {proc_err!r}")
                        self.errors_count += 1
                        await asyncio.sleep(0.05)
                        continue
                
                except asyncio.TimeoutError:
                    continue
                except AssertionError as e:
                    # Some serial backends may raise AssertionError on edge cases; don't drop connection
                    self.logger.error(f"Serial read assertion: {e!r}")
                    self.errors_count += 1
                    self.receive_buffer = ""  # Clear buffer to prevent getting stuck
                    await asyncio.sleep(0.05)
                    continue
                except serial.SerialException as e:
                    self.logger.error(f"Serial read error: {e}")
                    self.errors_count += 1
                    break
                except Exception as e:
                    # Keep the loop alive on unexpected errors to avoid immediate disconnects
                    self.logger.error(f"Unexpected read error: {e!r}")
                    self.errors_count += 1
                    await asyncio.sleep(0.05)
                    continue
                    
        except Exception as e:
            # Include exception type for better diagnostics
            self.logger.error(f"Read loop error: {e!r}")
            self.errors_count += 1
        finally:
            await self.disconnect()
    
    async def _process_receive_buffer(self):
        """Process received data buffer"""
        # Look for prompt patterns indicating command completion
        if self.prompt_patterns:
            earliest_match = None
            for pat in self.prompt_patterns:
                try:
                    m = re.search(pat, self.receive_buffer)
                except re.error:
                    continue
                if m and (earliest_match is None or m.start() < earliest_match.start()):
                    earliest_match = m
            if earliest_match:
                # Extract response (everything before the prompt)
                response_text = self.receive_buffer[:earliest_match.start()].strip()

                if response_text and self.response_callback:
                    try:
                        # Run callback in a thread to avoid blocking the read loop
                        await asyncio.to_thread(self.response_callback, response_text)
                    except Exception as e:
                        self.logger.error(f"Response callback failed: {e!r}")
                    finally:
                        self.responses_received += 1

                # Keep the prompt for next command
                self.receive_buffer = self.receive_buffer[earliest_match.end():]
                # Signal command completion for send_command waiters
                if self._command_event and not self._command_event.is_set():
                    self._command_event.set()
        
        # Handle line-by-line processing for real-time output
        lines = self.receive_buffer.split('\n')
        if len(lines) > 1:
            # Process complete lines
            for line in lines[:-1]:
                line = line.strip()
                if line and self.response_callback:
                    await asyncio.to_thread(self.response_callback, line)
            
            # Keep incomplete line in buffer
            self.receive_buffer = lines[-1]
    
    async def write(self, data: str) -> bool:
        """Write data to serial port"""
        if not self.is_connected or not self.writer:
            return False
        
        try:
            # Convert to bytes and add line ending if needed
            if isinstance(data, str):
                # Prefer CRLF for common network vendors that expect it
                vendor_crlf = False
                if self.vendor_type:
                    if self.vendor_type in {"cisco", "h3c", "juniper", "huawei"}:
                        vendor_crlf = True
                if vendor_crlf:
                    if not data.endswith('\r\n'):
                        data = data.rstrip('\r\n') + '\r\n'
                else:
                    if not data.endswith('\n') and not data.endswith('\r'):
                        data += '\n'
                data_bytes = data.encode('utf-8')
            else:
                data_bytes = data
            
            self.writer.write(data_bytes)
            await self.writer.drain()
            
            self.bytes_sent += len(data_bytes)
            self.commands_sent += 1
            
            self.logger.debug(f"Sent: {data.strip()}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write data: {e}")
            self.errors_count += 1
            return False
    
    async def send_command(self, command: str, timeout: Optional[float] = None) -> Optional[str]:
        """Send command and wait for response"""
        if not self.is_connected:
            return None
        
        timeout = timeout or self.timeout
        response_event = asyncio.Event()
        response_data = []
        
        # Set up temporary response handler
        original_callback = self.response_callback
        # Also allow read loop to signal completion via _command_event
        self._command_event = response_event
        
        # Callback must be synchronous because it is invoked via to_thread
        def command_response_handler(data: str):
            response_data.append(data)
            # If no vendor prompt patterns configured, consider first chunk as completion
            if not self.prompt_patterns:
                response_event.set()
                return
            # Check if response is complete (contains any configured prompt)
            try:
                for pat in self.prompt_patterns:
                    if re.search(pat, data):
                        response_event.set()
                        return
            except re.error:
                # Fallback: set event to avoid hanging
                response_event.set()
        
        self.response_callback = command_response_handler
        
        try:
            # Clear buffer
            self.receive_buffer = ""
            
            # Send command
            success = await self.write(command)
            if not success:
                return None
            
            # Wait for response with timeout
            try:
                await asyncio.wait_for(response_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                self.logger.warning(f"Command timeout after {timeout}s")
            
            # Return collected response
            return '\n'.join(response_data)
            
        finally:
            # Restore original callback
            self.response_callback = original_callback
            # Clear command event
            self._command_event = None
    
    async def disconnect(self):
        """Disconnect from serial port"""
        if not self.is_connected:
            return
        
        self.logger.info(f"Disconnecting from {self.port}")
        
        try:
            self.is_connected = False
            
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()
            
            self.serial = None
            self.reader = None
            self.writer = None
            
            self.logger.info(f"Disconnected from {self.port}")
            
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get connection statistics"""
        uptime = None
        if self.connection_start_time and self.is_connected:
            uptime = (datetime.utcnow() - self.connection_start_time).total_seconds()
        
        return {
            "port": self.port,
            "is_connected": self.is_connected,
            "vendor_type": self.vendor_type,
            "connection_time": self.connection_start_time.isoformat() if self.connection_start_time else None,
            "uptime_seconds": uptime,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "commands_sent": self.commands_sent,
            "responses_received": self.responses_received,
            "errors_count": self.errors_count,
            "success_rate": (self.responses_received / max(self.commands_sent, 1)) * 100
        }


class SerialService:
    """Serial communication service for managing multiple connections"""

    def __init__(self, serial_config):
        # serial_config is expected to be core.config.SerialConfig
        self.config = serial_config
        self.logger = get_logger("serial_service")
        
        self.connections: Dict[str, SerialConnection] = {}
        self.connection_listeners: List[Callable[[str, bool], None]] = []
        # Optional listener to forward incoming serial data upstream
        self.data_listener: Optional[Callable[[str], None]] = None
        
        self.is_running = False
        self.monitor_task: Optional[asyncio.Task] = None
    
    async def start(self) -> bool:
        """Start the serial service"""
        try:
            self.is_running = True
            
            # Start connection monitor
            self.monitor_task = asyncio.create_task(self._connection_monitor())
            
            self.logger.info("Serial service started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start serial service: {e}")
            return False
    
    async def stop(self):
        """Stop the serial service"""
        self.is_running = False
        
        # Disconnect all connections
        for port in list(self.connections.keys()):
            await self.disconnect_port(port)
        
        # Stop monitor task
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Serial service stopped")
    
    def get_available_ports(self) -> List[Dict[str, str]]:
        """Get list of available serial ports"""
        try:
            ports = serial.tools.list_ports.comports()
            return [
                {
                    "device": port.device,
                    "description": port.description,
                    "hwid": port.hwid,
                    "vid": str(port.vid) if port.vid else "",
                    "pid": str(port.pid) if port.pid else ""
                }
                for port in ports
            ]
        except Exception as e:
            self.logger.error(f"Failed to list serial ports: {e}")
            return []

    async def connect(self, port: str, vendor_type: Optional[str] = None, baud_rate: Optional[int] = None) -> bool:
        """Alias for connect_port for backward compatibility."""
        return await self.connect_port(port, vendor_type)

    async def disconnect(self, port: str) -> bool:
        """Alias for disconnect_port for backward compatibility."""
        return await self.disconnect_port(port)
    
    async def connect_port(self, port: str, vendor_type: Optional[str] = None) -> bool:
        """Connect to a serial port"""
        if port in self.connections:
            self.logger.warning(f"Port {port} is already connected")
            return self.connections[port].is_connected
        
        try:
            # Create connection
            connection = SerialConnection(port, self.config)
            
            # Set up connection event handlers
            # Forward raw bytes immediately to UI to ensure terminal displays streaming output
            connection.data_callback = self._on_connection_bytes
            # Do NOT set a default response_callback here; send_command will manage it temporarily
            
            # Attempt connection
            success = await connection.connect(vendor_type)
            
            if success:
                self.connections[port] = connection
                self._notify_connection_listeners(port, True)
                self.logger.info(f"Connected to port {port}")
            else:
                self.logger.error(f"Failed to connect to port {port}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error connecting to port {port}: {e}")
            return False
    
    async def disconnect_port(self, port: str) -> bool:
        """Disconnect from a serial port"""
        if port not in self.connections:
            return False
        
        try:
            connection = self.connections[port]
            await connection.disconnect()
            
            del self.connections[port]
            self._notify_connection_listeners(port, False)
            
            self.logger.info(f"Disconnected from port {port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from port {port}: {e}")
            return False
    
    async def send_command(self, port: str, command: str, timeout: Optional[float] = None) -> Optional[str]:
        """Send command to a specific port"""
        if port not in self.connections:
            self.logger.error(f"Port {port} is not connected")
            return None
        
        connection = self.connections[port]
        return await connection.send_command(command, timeout)
    
    def get_connection_status(self, port: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific connection"""
        if port not in self.connections:
            return None
        
        connection = self.connections[port]
        return connection.get_statistics()
    
    def get_all_connections(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all connections"""
        return {
            port: connection.get_statistics()
            for port, connection in self.connections.items()
        }
    
    def is_any_connection_active(self) -> bool:
        """Check if any serial connection is active."""
        return any(conn.is_connected for conn in self.connections.values())
    
    def add_connection_listener(self, callback: Callable[[str, bool], None]):
        """Add connection status change listener"""
        self.connection_listeners.append(callback)
    
    def remove_connection_listener(self, callback: Callable[[str, bool], None]):
        """Remove connection status change listener"""
        if callback in self.connection_listeners:
            self.connection_listeners.remove(callback)
    
    def _notify_connection_listeners(self, port: str, connected: bool):
        """Notify all connection listeners"""
        for callback in self.connection_listeners:
            try:
                callback(port, connected)
            except Exception as e:
                self.logger.error(f"Error in connection listener: {e}")
    
    def _on_connection_data(self, data: str):
        """Handle data from connection"""
        # This can be overridden or extended to handle incoming data
        self.logger.debug(f"Received data: {data[:100]}...")
        # Forward data to external listener if provided
        if self.data_listener:
            try:
                self.data_listener(data)
            except Exception as e:
                self.logger.error(f"Error in data listener: {e}")

    def _on_connection_bytes(self, data: bytes):
        """Handle raw bytes from connection and forward as text."""
        try:
            text = data.decode('utf-8', errors='ignore')
        except Exception:
            text = str(data)
        # Reuse the string handler to keep logging and forwarding consistent
        self._on_connection_data(text)
    
    async def _connection_monitor(self):
        """Monitor connections and handle reconnections"""
        while self.is_running:
            try:
                # Check all connections
                for port, connection in list(self.connections.items()):
                    if not connection.is_connected and not connection.is_connecting:
                        self.logger.warning(f"Connection to {port} lost, attempting reconnection")
                        
                        # Attempt reconnection
                        success = await connection.connect(connection.vendor_type)
                        if success:
                            self.logger.info(f"Successfully reconnected to {port}")
                        else:
                            self.logger.error(f"Failed to reconnect to {port}")
                
                # Monitor interval
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Connection monitor error: {e}")
                await asyncio.sleep(5)
