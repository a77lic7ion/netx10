"""
Session Service for managing device connections and command execution
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from PySide6.QtCore import QObject, Signal, Slot

from services.database_service import DatabaseService
from services.serial_service import SerialService
from vendor.vendor_factory import VendorFactory
from core.config import AppConfig
from core.constants import SessionStatus, VendorType
from utils.logging import get_logger
from models.device_models import Session, CommandResult, DeviceInfo


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
            
            # Save to database
            await self.db.save_session(session)
            
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
                await self.db.update_session(session)
                
                self.logger.info(f"Session connected: {session_id}")
                self.session_connected.emit(session_id)
                return True
            else:
                session.status = SessionStatus.ERROR
                session.error_message = "Failed to establish connection"
                
                # Update database
                await self.db.update_session(session)
                
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
            await self.db.update_session(session)
            
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
            
            result = await self.serial_service.send_command(command)
            
            # Add command to session history
            session.add_command(command, result.output, result.success)
            
            # Update database
            await self.db.update_session(session)
            
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
                await self.db.update_session(session)
            
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