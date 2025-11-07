import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Slot


from services.database_service import DatabaseService
from services.serial_service import SerialService
from vendor.vendor_factory import VendorFactory
from core.config import AppConfig
from core.constants import SessionStatus, VendorType
from utils.logging import get_logger
from models.device_models import Session as DBSession

class Session:
    def __init__(self, session_id: str, com_port: str, baud_rate: int, vendor_type: str, start_time: datetime, status: SessionStatus):
        self.session_id = session_id
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.vendor_type = vendor_type
        self.start_time = start_time
        self.status = status
        self.connected_at: Optional[datetime] = None
        self.disconnected_at: Optional[datetime] = None
        # Command tracking
        self.commands: List[str] = []  # Placeholder
        self.command_history: List[str] = []
        # Device/session metadata compatible with DatabaseService expectations
        self.device_name: Optional[str] = None
        self.device_model: Optional[str] = None
        self.os_version: Optional[str] = None
        self.vendor_specific_data: Optional[Dict[str, Any]] = None
        # Error tracking
        self.error_message: str = ""  # Placeholder

    def add_command(self, command: str, output: str, success: bool):
        """Add command to session history."""
        self.commands.append(command)  # Simplified for now
        self.command_history.append(command)

class CommandResult:
    def __init__(self, success: bool, output: str, error: str, execution_time: float):
        self.success = success
        self.output = output
        self.error = error
        self.execution_time = execution_time

class DeviceInfo:
    def __init__(self, vendor_type: str, model: str, firmware_version: str, serial_number: str):
        self.vendor_type = vendor_type
        self.model = model
        self.firmware_version = firmware_version
        self.serial_number = serial_number


class SessionService(QObject):
    """Service for managing device sessions"""
    
    # Signals
    session_created = Signal(str)  # session_id
    session_connected = Signal(str)  # session_id
    session_disconnected = Signal(str)  # session_id
    command_executed = Signal(str, str, str, str)  # session_id, command, output, timestamp
    session_error = Signal(str, str, str)  # session_id, error_type, error_message
    
    def __init__(self, db: DatabaseService, serial_service: SerialService, config: AppConfig):
        super().__init__()
        self.db = db
        self.serial_service = serial_service
        self.config = config
        self.logger = get_logger("session_service")
        
        # Active sessions
        self.active_sessions: Dict[str, Session] = {}
        self.vendor_factory = VendorFactory()

        self.logger.info("Session service initialized")

    def _to_db_session(self, session: "Session") -> DBSession:
        """Convert internal Session to Pydantic DB Session model."""
        status_str = session.status.value if hasattr(session.status, "value") else str(session.status)
        return DBSession(
            session_id=session.session_id,
            device_name=session.device_name,
            com_port=session.com_port,
            baud_rate=session.baud_rate,
            vendor_type=session.vendor_type,
            device_model=session.device_model,
            os_version=session.os_version,
            start_time=session.start_time,
            end_time=session.disconnected_at,
            status=status_str,
            error_message=getattr(session, "error_message", None),
            vendor_specific_data=session.vendor_specific_data,
        )
    
    async def create_session(self, com_port: str, vendor_type: str, baud_rate: int = 9600) -> Session:
        """Create a new device session"""
        try:
            session_id = str(uuid.uuid4())
            
            # Create session
            session = Session(
                session_id=session_id,
                com_port=com_port,
                baud_rate=baud_rate,
                vendor_type=vendor_type,
                start_time=datetime.utcnow(),
                status=SessionStatus.CREATED,
            )
            
            # Store session
            self.active_sessions[session_id] = session
            
            # Save to database with proper model mapping
            await self.db.save_session(self._to_db_session(session))
            
            self.logger.info(f"Session created: {session_id}")
            self.session_created.emit(session_id)
            
            return session
            
        except Exception as e:
            self.logger.error(f"Failed to create session: {e}")
            raise
    
    async def connect_session(self, session_id: str) -> bool:
        """Connect to a device session"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")
            

            
            # Connect to device
            success = await self.serial_service.connect_port(port=session.com_port, vendor_type=session.vendor_type)
            
            if success:
                session.status = SessionStatus.CONNECTED
                session.connected_at = datetime.now()
                
                # Update database
                await self.db.update_session(self._to_db_session(session))
                
                self.logger.info(f"Session connected: {session_id}")
                self.session_connected.emit(session_id)
                return True
            else:
                session.status = SessionStatus.ERROR
                session.error_message = "Failed to establish connection"
                
                # Update database
                await self.db.update_session(self._to_db_session(session))
                
                self.logger.error(f"Failed to connect session: {session_id}")
                self.session_error.emit(session_id, "Connection Error", "Failed to establish connection")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection error for session {session_id}: {e}")
            
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session.status = SessionStatus.ERROR
                session.error_message = str(e)
                await self.db.update_session(session)
            
            self.session_error.emit(session_id, "Connection Error", str(e))
            return False
    
    async def disconnect_session(self, session_id: str) -> bool:
        """Disconnect from a device session"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")
            
            # Disconnect from device
            if self.serial_service:
                await self.serial_service.disconnect_port(session.com_port)
            
            # Update session status
            session.status = SessionStatus.DISCONNECTED
            session.disconnected_at = datetime.now()
            
            # Update database
            await self.db.update_session(self._to_db_session(session))
            
            self.logger.info(f"Session disconnected: {session_id}")
            self.session_disconnected.emit(session_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Disconnection error for session {session_id}: {e}")
            self.session_error.emit(session_id, "Disconnection Error", str(e))
            return False
    
    async def execute_command(self, session_id: str, command: str) -> CommandResult:
        """Execute a command on the device"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")
            
            if session.status != SessionStatus.CONNECTED:
                raise ValueError(f"Session not connected: {session_id}")
            
            # Execute command
            if not self.serial_service:
                raise ValueError("Serial service not initialized")
            
            response = await self.serial_service.send_command(session.com_port, command)
            
            # Build result object based on response
            success = response is not None
            output = response or ""
            error = "" if success else "No response or port not connected"
            result = CommandResult(success=success, output=output, error=error, execution_time=0.0)
            
            # Add command to session history (simplified placeholder)
            session.add_command(command, result.output, result.success)
            
            # Update database
            await self.db.update_session(self._to_db_session(session))
            
            # Emit signal
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.command_executed.emit(session_id, command, result.output, timestamp)
            
            self.logger.info(f"Command executed in session {session_id}: {command}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Command execution error for session {session_id}: {e}")
            
            error_result = CommandResult(
                success=False,
                output="",
                error=str(e),
                execution_time=0.0
            )
            
            self.session_error.emit(session_id, "Command Error", str(e))
            return error_result

    async def send_enter(self, session_id: str) -> CommandResult:
        """Send a raw newline to the device (simulate pressing Enter)."""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            if session.status != SessionStatus.CONNECTED:
                raise ValueError(f"Session not connected: {session_id}")

            # Send an empty command; SerialService will append newline
            response = await self.serial_service.send_command(session.com_port, "")

            success = response is not None
            output = response or ""
            error = "" if success else "No response or port not connected"
            result = CommandResult(success=success, output=output, error=error, execution_time=0.0)

            # Emit signal to reflect interaction (using a placeholder command label)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.command_executed.emit(session_id, "<ENTER>", result.output, timestamp)

            self.logger.info(f"Sent ENTER in session {session_id}")
            return result
        except Exception as e:
            self.logger.error(f"Send ENTER error for session {session_id}: {e}")
            error_result = CommandResult(success=False, output="", error=str(e), execution_time=0.0)
            self.session_error.emit(session_id, "Command Error", str(e))
            return error_result

    async def fetch_device_info(self, session_id: str) -> Dict[str, Any]:
        """Fetch and parse device information via vendor implementation.

        Returns a dict with keys like device_model, os_version, serial_number, hostname, uptime.
        """
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            # Create vendor instance
            try:
                vendor_enum = VendorType(session.vendor_type)
            except Exception:
                # Accept raw strings already matching enum values
                vendor_enum = VendorType[session.vendor_type.upper()] if isinstance(session.vendor_type, str) else session.vendor_type

            vendor = self.vendor_factory.create_vendor(vendor_enum)
            if not vendor:
                raise ValueError(f"Unsupported vendor type: {session.vendor_type}")

            # Delegate to vendor-specific implementation
            device_info_obj = await vendor.get_device_info()
            # Convert to dict
            info_dict: Dict[str, Any] = {
                "device_model": getattr(device_info_obj, "device_model", None),
                "os_version": getattr(device_info_obj, "os_version", None),
                "serial_number": getattr(device_info_obj, "serial_number", None),
                "hostname": getattr(device_info_obj, "hostname", None),
                "uptime": getattr(device_info_obj, "uptime", None),
            }

            # Update session fields for persistence
            session.device_model = info_dict.get("device_model")
            session.os_version = info_dict.get("os_version")
            # Store remaining details in vendor_specific_data
            session.vendor_specific_data = {
                k: v for k, v in info_dict.items() if k not in ("device_model", "os_version")
            }

            # Persist using Pydantic DB model mapping
            await self.db.update_session(self._to_db_session(session))

            # Emit a synthetic event indicating info retrieval
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pretty_output = (
                f"Model: {info_dict.get('device_model') or 'N/A'}\n"
                f"OS: {info_dict.get('os_version') or 'N/A'}\n"
                f"Serial: {info_dict.get('serial_number') or 'N/A'}\n"
                f"Hostname: {info_dict.get('hostname') or 'N/A'}\n"
                f"Uptime: {info_dict.get('uptime') or 'N/A'}"
            )
            self.command_executed.emit(session_id, "fetch_device_info", pretty_output, timestamp)

            self.logger.info(f"Fetched device info for session {session_id}: {info_dict}")
            return info_dict
        except Exception as e:
            self.logger.error(f"Fetch device info error for session {session_id}: {e}")
            self.session_error.emit(session_id, "Device Info Error", str(e))
            return {}
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self.active_sessions.get(session_id)
    
    async def get_all_sessions(self) -> List[Session]:
        """Get all active sessions"""
        return list(self.active_sessions.values())
    
    async def save_all_sessions(self):
        """Save all sessions to database"""
        try:
            for session in self.active_sessions.values():
                await self.db.update_session(self._to_db_session(session))
            
            self.logger.info("All sessions saved to database")
            
        except Exception as e:
            self.logger.error(f"Failed to save sessions: {e}")
    
    def get_active_session_count(self) -> int:
        """Get count of active sessions"""
        return len([
            session for session in self.active_sessions.values()
            if session.status == SessionStatus.CONNECTED
        ])
    
    def get_total_command_count(self) -> int:
        """Get total command count across all sessions"""
        return sum(len(session.commands) for session in self.active_sessions.values())
    
    async def cleanup(self):
        """Cleanup all sessions"""
        try:
            self.logger.info("Cleaning up session service")
            
            # Disconnect all sessions
            for session_id in list(self.active_sessions.keys()):
                await self.disconnect_session(session_id)
            
            # Close serial service
            if self.serial_service:
                await self.serial_service.cleanup()
            
            # Save all sessions
            await self.save_all_sessions()
            
            self.logger.info("Session service cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Session service cleanup error: {e}")
