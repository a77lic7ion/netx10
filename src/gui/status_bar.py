"""
Status Bar Widget for NetworkSwitch AI Assistant
"""

from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QFrame, QMenu, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QDateTime
from PySide6.QtGui import QFont, QIcon, QAction

from core.config import AppConfig
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.application import NetworkSwitchAIApp
from core.constants import SessionStatus, VendorType
from utils.logging_utils import get_logger


class StatusBarWidget(QWidget):
    """Status bar widget"""
    
    def __init__(self, app: 'NetworkSwitchAIApp'):
        super().__init__()
        self.app = app
        self.config = app.config
        self.logger = get_logger("status_bar")
        
        # Status tracking
        self.current_status: str = "Ready"
        self.connection_status: str = "Disconnected"
        self.ai_status: str = "Idle"
        self.active_sessions: int = 0
        self.total_commands: int = 0
        self.last_error: Optional[str] = None
        
        # Setup UI
        self.setup_ui()
        
        # Connect signals
        self.connect_signals()
        
        # Start update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(1000)  # Update every second
        
        self.logger.info("Status bar initialized")
    
    def setup_ui(self):
        """Setup status bar UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)
        
        # Application status
        self.app_status_label = QLabel("Ready")
        self.app_status_label.setFont(QFont("Arial", 9))
        self.app_status_label.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(self.app_status_label)
        
        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.VLine)
        separator1.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator1)
        
        # Connection status
        self.connection_status_label = QLabel("Disconnected")
        self.connection_status_label.setFont(QFont("Arial", 9))
        self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.connection_status_label)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        separator2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator2)
        
        # AI status
        self.ai_status_label = QLabel("Idle")
        self.ai_status_label.setFont(QFont("Arial", 9))
        self.ai_status_label.setStyleSheet("color: blue; font-weight: bold;")
        layout.addWidget(self.ai_status_label)
        
        # Separator
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.VLine)
        separator3.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator3)
        
        # Session count
        self.session_count_label = QLabel("Sessions: 0")
        self.session_count_label.setFont(QFont("Arial", 9))
        self.session_count_label.setStyleSheet("color: #d4d4d4;")
        layout.addWidget(self.session_count_label)
        
        # Command count
        self.command_count_label = QLabel("Commands: 0")
        self.command_count_label.setFont(QFont("Arial", 9))
        self.command_count_label.setStyleSheet("color: #d4d4d4;")
        layout.addWidget(self.command_count_label)
        
        # Progress indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Add stretch
        layout.addStretch()
        
        # Current time
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Arial", 9))
        self.time_label.setAlignment(Qt.AlignRight)
        self.time_label.setStyleSheet("color: #d4d4d4;")
        layout.addWidget(self.time_label)
        
        # Error indicator
        self.error_button = QPushButton("⚠️")
        self.error_button.setFixedSize(20, 20)
        self.error_button.setVisible(False)
        self.error_button.clicked.connect(self.show_last_error)
        layout.addWidget(self.error_button)
    
    def connect_signals(self):
        """Connect application signals"""
        # Connect to application signals
        self.app.connection_status_changed.connect(self.on_connection_status_changed)
        self.app.ai_status_changed.connect(self.on_ai_status_changed)
        self.app.session_created.connect(self.on_session_created)
        self.app.session_ended.connect(self.on_session_ended)
        self.app.command_executed.connect(self.on_command_executed)
        self.app.error_occurred.connect(self.on_error_occurred)
    
    @Slot(str, bool)
    def on_connection_status_changed(self, status: str, connected: bool):
        """Handle connection status changed"""
        self.connection_status = status
        self.update_connection_status_display()
        
        if connected:
            self.logger.info(f"Connection established: {status}")
        else:
            self.logger.info(f"Connection status: {status}")
    
    @Slot(str, str)
    def on_ai_status_changed(self, status: str, details: str):
        """Handle AI status changed"""
        self.ai_status = status
        self.update_ai_status_display()
        
        if status == "Processing":
            self.logger.info(f"AI processing: {details}")
        elif status == "Error":
            self.logger.error(f"AI error: {details}")
        elif status == "Idle":
            self.logger.info(f"AI idle: {details}")
    
    @Slot(str)
    def on_session_created(self, session_id: str):
        """Handle session created"""
        self.active_sessions += 1
        self.update_session_count_display()
        self.logger.info(f"Session created: {session_id}")
    
    @Slot(str)
    def on_session_ended(self, session_id: str):
        """Handle session ended"""
        if self.active_sessions > 0:
            self.active_sessions -= 1
        self.update_session_count_display()
        self.logger.info(f"Session ended: {session_id}")
    
    @Slot(str, str, str, str)
    def on_command_executed(self, session_id: str, command: str, output: str, timestamp: str):
        """Handle command executed"""
        self.total_commands += 1
        self.update_command_count_display()
        self.logger.debug(f"Command executed in {session_id}: {command}")
    
    @Slot(str, str)
    def on_error_occurred(self, error_type: str, error_message: str):
        """Handle error occurred"""
        self.last_error = f"{error_type}: {error_message}"
        self.current_status = "Error"
        self.update_app_status_display()
        self.error_button.setVisible(True)
        self.logger.error(f"Error occurred: {error_type} - {error_message}")
    
    @Slot()
    def update_status(self):
        """Update status display"""
        # Update time
        current_time = QDateTime.currentDateTime().toString("HH:mm:ss")
        self.time_label.setText(current_time)
        
        # Update from application state
        self.update_from_application()
        
        # Update displays
        self.update_app_status_display()
        self.update_connection_status_display()
        self.update_ai_status_display()
        self.update_session_count_display()
        self.update_command_count_display()
    
    def update_from_application(self):
        """Update status from application state"""
        # Get current application state
        app_state = self.app.get_application_state()
        
        # Update local status variables
        self.current_status = app_state.get("status", "Ready")
        self.active_sessions = app_state.get("active_sessions", 0)
        self.total_commands = app_state.get("total_commands", 0)
        
        # Update connection status from serial service
        if hasattr(self.app, 'serial_service') and self.app.serial_service:
            if self.app.serial_service.is_any_connection_active():
                self.connection_status = "Connected"
            else:
                self.connection_status = "Disconnected"
        
        # Update AI status from AI service
        if hasattr(self.app, 'ai_service') and self.app.ai_service:
            if self.app.ai_service.is_processing():
                self.ai_status = "Processing"
            else:
                self.ai_status = "Idle"
    
    def update_app_status_display(self):
        """Update application status display"""
        self.app_status_label.setText(self.current_status)
        
        if self.current_status == "Ready":
            self.app_status_label.setStyleSheet("color: green; font-weight: bold;")
        elif self.current_status == "Processing":
            self.app_status_label.setStyleSheet("color: orange; font-weight: bold;")
        elif self.current_status == "Error":
            self.app_status_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.app_status_label.setStyleSheet("color: #d4d4d4; font-weight: bold;")
    
    def update_connection_status_display(self):
        """Update connection status display"""
        self.connection_status_label.setText(self.connection_status)
        
        if self.connection_status == "Connected":
            self.connection_status_label.setStyleSheet("color: green; font-weight: bold;")
        elif self.connection_status == "Connecting":
            self.connection_status_label.setStyleSheet("color: orange; font-weight: bold;")
        elif self.connection_status == "Disconnected":
            self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.connection_status_label.setStyleSheet("color: #d4d4d4; font-weight: bold;")
    
    def update_ai_status_display(self):
        """Update AI status display"""
        self.ai_status_label.setText(self.ai_status)
        
        if self.ai_status == "Idle":
            self.ai_status_label.setStyleSheet("color: blue; font-weight: bold;")
        elif self.ai_status == "Processing":
            self.ai_status_label.setStyleSheet("color: orange; font-weight: bold;")
        elif self.ai_status == "Error":
            self.ai_status_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.ai_status_label.setStyleSheet("color: #d4d4d4; font-weight: bold;")
    
    def update_session_count_display(self):
        """Update session count display"""
        self.session_count_label.setText(f"Sessions: {self.active_sessions}")
    
    def update_command_count_display(self):
        """Update command count display"""
        self.command_count_label.setText(f"Commands: {self.total_commands}")

    def set_connection_status(self, status: str):
        """Set connection status and update display."""
        self.connection_status = status
        self.update_connection_status_display()
    
    @Slot()
    def show_last_error(self):
        """Show last error"""
        if self.last_error:
            QMessageBox.critical(
                self,
                "Last Error",
                f"Last error occurred:\n\n{self.last_error}",
                QMessageBox.Ok
            )
    
    def show_progress(self, visible: bool = True, maximum: int = 0, value: int = 0):
        """Show/hide progress bar"""
        self.progress_bar.setVisible(visible)
        if visible:
            self.progress_bar.setMaximum(maximum)
            self.progress_bar.setValue(value)
    
    def update_progress(self, value: int):
        """Update progress bar value"""
        self.progress_bar.setValue(value)
    
    def show_status_message(self, message: str, timeout: int = 3000):
        """Show status message"""
        # This could be extended to show temporary status messages
        self.logger.info(f"Status message: {message}")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get current status summary"""
        return {
            "application_status": self.current_status,
            "connection_status": self.connection_status,
            "ai_status": self.ai_status,
            "active_sessions": self.active_sessions,
            "total_commands": self.total_commands,
            "last_error": self.last_error,
            "timestamp": datetime.now().isoformat()
        }
