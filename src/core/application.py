"""
Main Application Controller
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from PySide6.QtWidgets import QMainWindow, QMessageBox
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QIcon, QFont

from gui.main_window import MainWindow
from services.session_service import SessionService
from services.ai_service import AIService
from services.serial_service import SerialService
from services.database_service import DatabaseService
from core.config import AppConfig
from core.constants import VendorType
from utils.logging import get_logger

logger = get_logger(__name__)


class NetworkSwitchAIApp(QMainWindow):
    """Main application controller"""
    
    # Signals
    session_created = Signal(str, str)  # session_id, vendor_type
    session_ended = Signal(str)
    command_executed = Signal(str, str, str, str)  # session_id, command, output, timestamp
    ai_interaction_logged = Signal(str, str, str, str, str)  # session_id, query, response, query_type, timestamp
    ai_response_received = Signal(str, str)  # session_id, response
    error_occurred = Signal(str, str)  # error_type, error_message
    terminal_data_received = Signal(str)  # data received from terminal
    connection_status_changed = Signal(str, bool)  # status, connected
    ai_response_started = Signal(str)  # query
    ai_response_ended = Signal()  # no parameters
    ai_suggestion_received = Signal(list)  # suggestions list
    ai_status_changed = Signal(str, str)  # status, details
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._services_initialized = False
        self._current_session_id: Optional[str] = None
        self.start_time = datetime.utcnow()
        self.current_device = None
        
        # Initialize services
        self._initialize_services()
        
        # Setup UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Setup auto-save timer
        self._setup_auto_save()
        
        logger.info("NetworkSwitch AI Assistant initialized successfully")
    
    def _initialize_services(self):
        """Initialize application services"""
        try:
            # Database service
            self.db = DatabaseService(self.config)
            # Run async initialization
            loop = asyncio.get_event_loop()
            if not loop.run_until_complete(self.db.initialize()):
                logger.error("Failed to initialize the database. Exiting.")
                sys.exit(1)
            
            self.serial_service = SerialService(self.config.serial)
            self.session_service = SessionService(self.db, self.serial_service, self.config)
            self.ai_service = AIService(self.config.ai)

            # Forward serial data to terminal output
            self.serial_service.data_listener = lambda data: self.terminal_data_received.emit(data)
            
            self._services_initialized = True
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            self._show_error("Initialization Error", f"Failed to initialize services: {e}")
            sys.exit(1)
    
    def _setup_ui(self):
        """Setup user interface"""
        self.main_window = MainWindow(self)
        self.setCentralWidget(self.main_window)
        
        # Window properties
        self.setWindowTitle(self.config.window_title)
        self.setMinimumSize(1200, 800)
        self.resize(self.config.window_width, self.config.window_height)
        
        # Set window icon if available
        icon_path = Path("resources/icons/app.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Set application font
        font = QFont(self.config.font_family, self.config.font_size)
        self.setFont(font)
        
        # Center window on screen
        self._center_window()
    
    def _connect_signals(self):
        """Connect UI signals to service slots"""
        # Main window signals
        self.main_window.connect_requested.connect(self._handle_connect_request)
        self.main_window.disconnect_requested.connect(self._handle_disconnect_request)
        self.main_window.command_sent.connect(self._handle_command_sent)
        self.main_window.ai_query_sent.connect(self._handle_ai_query)
        
        # Service signals
        self.session_created.connect(self.main_window.on_session_created)
        self.session_ended.connect(self.main_window.on_session_ended)
        self.ai_response_received.connect(self.main_window.on_ai_response_received)
        self.error_occurred.connect(self.main_window.on_error_occurred)

        # Wire session service events to app-level status updates
        self.session_service.session_connected.connect(self._on_session_connected)
        self.session_service.session_disconnected.connect(self._on_session_disconnected)
        self.session_service.session_error.connect(self._on_session_error)

        # Also reflect low-level serial connection changes directly
        self.serial_service.add_connection_listener(lambda port, connected: self.connection_status_changed.emit("Connected" if connected else "Disconnected", connected))
    
    def _setup_auto_save(self):
        """Setup auto-save functionality"""
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_timer.start(300000)  # 5 minutes
    
    def _center_window(self):
        """Center window on screen"""
        screen = self.screen()
        screen_geometry = screen.geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
    
    @Slot(str, str, int)
    def _handle_connect_request(self, com_port: str, vendor_type: str, baud_rate: int):
        """Handle connection request from UI"""
        asyncio.create_task(self._connect_device(com_port, vendor_type, baud_rate))
    
    @Slot()
    def _handle_disconnect_request(self):
        """Handle disconnection request from UI"""
        asyncio.create_task(self._disconnect_device())
    
    @Slot(str, str)
    def _handle_command_sent(self, session_id: str, command: str):
        """Handle command sent from UI"""
        asyncio.create_task(self._execute_command(session_id, command))
    
    @Slot(str, str, str)
    def _handle_ai_query(self, session_id: str, query: str, context: str):
        """Handle AI query from UI"""
        asyncio.create_task(self._process_ai_query(session_id, query, context))
    
    async def _connect_device(self, com_port: str, vendor_type: str, baud_rate: int):
        """Connect to network device"""
        try:
            logger.info(f"Connecting to {com_port} ({vendor_type}) at {baud_rate} baud")
            
            # Create new session
            session = await self.session_service.create_session(
                com_port=com_port,
                vendor_type=vendor_type,
                baud_rate=baud_rate
            )
            
            self._current_session_id = session.session_id
            
            # Connect to device
            success = await self.session_service.connect_session(session.session_id)
            
            if success:
                logger.info(f"Successfully connected to {com_port}")
                self.session_created.emit(session.session_id, session.vendor_type)
            else:
                logger.error(f"Failed to connect to {com_port}")
                error_msg = session.error_message if session and session.error_message else f"Failed to connect to {com_port}"
                self.error_occurred.emit("Connection Error", error_msg)
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.error_occurred.emit("Connection Error", str(e))

    async def _disconnect_device(self):
        """Disconnect from current device"""
        if not self._current_session_id:
            return
        
        try:
            logger.info(f"Disconnecting from session {self._current_session_id}")
            
            await self.session_service.disconnect_session(self._current_session_id)
            
            session_id = self._current_session_id
            self._current_session_id = None
            
            logger.info("Successfully disconnected")
            self.session_ended.emit(session_id)
            
        except Exception as e:
            logger.error(f"Disconnection error: {e}")
            self.error_occurred.emit("Disconnection Error", str(e))

    @Slot(str)
    def _on_session_connected(self, session_id: str):
        """Handle session connected event from SessionService"""
        self.connection_status_changed.emit("Connected", True)

    @Slot(str)
    def _on_session_disconnected(self, session_id: str):
        """Handle session disconnected event from SessionService"""
        self.connection_status_changed.emit("Disconnected", False)

    @Slot(str, str, str)
    def _on_session_error(self, session_id: str, error_type: str, error_message: str):
        """Forward session errors to UI"""
        self.error_occurred.emit(error_type, error_message)

    async def _execute_command(self, session_id: str, command: str):
        """Execute command on device"""
        try:
            logger.info(f"Executing command: {command}")
            
            result = await self.session_service.execute_command(session_id, command)
            
            if result.success:
                logger.info("Command executed successfully")
                # Emit signal for session manager
                from datetime import datetime
                timestamp = datetime.utcnow().isoformat()
                self.command_executed.emit(session_id, command, result.output or "", timestamp)
            else:
                logger.error(f"Command failed: {result.error}")
                self.error_occurred.emit("Command Error", result.error or "Unknown error")
                
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            self.error_occurred.emit("Command Error", str(e))

    async def _process_ai_query(self, session_id: str, query: str, context: str):
        """Process AI query"""
        try:
            logger.info(f"Processing AI query: {query}")
            
            # Get session context
            session = await self.session_service.get_session(session_id)
            if not session:
                self.error_occurred.emit("AI Error", "Session not found")
                return
            
            # Process with AI service
            response = await self.ai_service.process_query(
                query=query,
                vendor_type=session.vendor_type,
                device_context=context,
                command_history=session.command_history
            )
            
            logger.info("AI query processed successfully")
            self.ai_response_received.emit(session_id, response)
            
        except Exception as e:
            logger.error(f"AI processing error: {e}")
            self.error_occurred.emit("AI Error", str(e))

    def _auto_save(self):
        """Auto-save application state"""
        try:
            # Save current sessions and settings
            if self._services_initialized:
                asyncio.create_task(self.session_service.save_all_sessions())
                logger.debug("Auto-save completed")
        except Exception as e:
            logger.error(f"Auto-save error: {e}")

    def _show_error(self, title: str, message: str):
        """Show error dialog"""
        QMessageBox.critical(self, title, message)

    def closeEvent(self, event):
        """Handle application close event"""
        try:
            logger.info("Application closing...")
            
            # Disconnect any active sessions
            if self._current_session_id:
                asyncio.create_task(self._disconnect_device())
            
            # Save application state
            if self._services_initialized:
                self.db.close()
            
            logger.info("Application closed successfully")
            event.accept()
            
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")
            event.accept()

    @property
    def current_session_id(self) -> Optional[str]:
        """Get current session ID"""
        return self._current_session_id

    @property
    def is_connected(self) -> bool:
        """Check if connected to a device"""
        return self._current_session_id is not None

    def get_all_sessions(self):
        """Get all sessions from session service"""
        return self.session_service.get_all_sessions()

    def get_session(self, session_id: str):
        """Get specific session by ID"""
        return self.session_service.get_session(session_id)

    def get_session_commands(self, session_id: str):
        """Get command history for a session"""
        session = self.session_service.active_sessions.get(session_id)
        if session:
            return [
                {
                    "command": cmd.command,
                    "output": cmd.output,
                    "timestamp": cmd.timestamp.isoformat(),
                    "success": cmd.success
                }
                for cmd in session.commands
            ]
        return []

    def get_session_ai_interactions(self, session_id: str):
        """Get AI interactions for a session"""
        # This would come from AI service in a real implementation
        # For now, return empty list
        return []

    def export_session(self, session_id: str):
        """Export session data"""
        session = self.session_service.active_sessions.get(session_id)
        if session:
            return {
                "session_id": session.session_id,
                "device_info": {
                    "vendor": session.device_info.vendor_type.value,
                    "model": session.device_info.model,
                    "firmware": session.device_info.firmware_version,
                    "serial": session.device_info.serial_number
                },
                "connection": {
                    "com_port": session.com_port,
                    "baud_rate": session.baud_rate
                },
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "connected_at": session.connected_at.isoformat() if session.connected_at else None,
                "disconnected_at": session.disconnected_at.isoformat() if session.disconnected_at else None,
                "commands": self.get_session_commands(session_id),
                "command_count": len(session.commands)
            }
        return None

    async def create_session(self, session_name: str):
        """Create a new session"""
        # This would be implemented based on your session service
        pass

    async def end_session(self, session_id: str):
        """End a specific session"""
        # This would be implemented based on your session service
        pass

    @property
    def active_sessions(self) -> Dict[str, Any]:
        """Get active sessions from session service"""
        if self._services_initialized:
            return self.session_service.active_sessions
        return {}

    def get_application_state(self):
        """Get current application state"""
        return {
            "is_connected": self.is_connected,
            "current_session_id": self.current_session_id,
            "start_time": self.start_time.isoformat(),
            "uptime": (datetime.utcnow() - self.start_time).total_seconds(),
            "services_initialized": self._services_initialized,
            "active_sessions": len(self.session_service.active_sessions) if self._services_initialized else 0
        }

    async def send_command(self, command: str):
        """Execute a command against the current session."""
        if not self._current_session_id:
            self.error_occurred.emit("Command Error", "No active session")
            return
        await self._execute_command(self._current_session_id, command)

    async def send_enter(self):
        """Send raw newline to the device (simulate Enter)."""
        if not self._current_session_id:
            self.error_occurred.emit("Command Error", "No active session")
            return
        result = await self.session_service.send_enter(self._current_session_id)
        if not result.success:
            self.error_occurred.emit("Command Error", result.error or "Unknown error")

    async def fetch_device_info(self) -> Dict[str, Any]:
        """Fetch device info for the current session and allow naming."""
        if not self._current_session_id:
            self.error_occurred.emit("Device Info Error", "No active session")
            return {}

        info = await self.session_service.fetch_device_info(self._current_session_id)
        if not info:
            self.error_occurred.emit("Device Info Error", "Failed to retrieve device information")
            return {}

        summary = (
            f"Device Model: {info.get('device_model') or 'N/A'}\n"
            f"OS Version: {info.get('os_version') or 'N/A'}\n"
            f"Serial Number: {info.get('serial_number') or 'N/A'}\n"
            f"Hostname: {info.get('hostname') or 'N/A'}\n"
            f"Uptime: {info.get('uptime') or 'N/A'}\n"
        )
        self.terminal_data_received.emit(summary)

        # Optional: auto-apply hostname as device name if empty (no UI prompt here)
        try:
            session = self.session_service.active_sessions.get(self._current_session_id)
            if session and not getattr(session, "device_name", None) and info.get("hostname"):
                session.device_name = info.get("hostname")
                # Persist using DB mapping to avoid runtime model mismatches
                await self.db.update_session(self.session_service._to_db_session(session))
                self.terminal_data_received.emit(f"Saved device name: {session.device_name}\n")
        except Exception as e:
            logger.error(f"Device name persistence error: {e}")

        return info
