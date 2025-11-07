"""
Session Manager Widget for NetworkSwitch AI Assistant
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QSplitter, QTextEdit,
    QHeaderView, QMessageBox, QInputDialog, QFileDialog,
    QMenu, QTabWidget, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QDateTime
from PySide6.QtGui import QFont, QIcon, QAction

from core.config import AppConfig
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.application import NetworkSwitchAIApp
from core.constants import SessionStatus, VendorType
from utils.logging import get_logger
from models.device_models import Session


class SessionManagerWidget(QWidget):
    """Session manager widget"""
    
    session_selected = Signal(str)
    session_created = Signal(str)
    session_ended = Signal(str)
    
    def __init__(self, app: 'NetworkSwitchAIApp'):
        super().__init__()
        self.app = app
        self.config = app.config
        self.logger = get_logger("session_manager")
        
        # Session state
        self.current_session_id: Optional[str] = None
        self.sessions: Dict[str, Session] = {}
        
        # Setup UI
        self.setup_ui()
        
        # Connect signals
        self.connect_signals()
        
        # Load existing sessions
        self.load_sessions()
        
        self.logger.info("Session manager initialized")
    
    def setup_ui(self):
        """Setup session manager UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create main splitter
        main_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(main_splitter)
        
        # Top panel - Session list
        top_panel = self.create_session_list_panel()
        main_splitter.addWidget(top_panel)
        
        # Bottom panel - Session details
        bottom_panel = self.create_session_details_panel()
        main_splitter.addWidget(bottom_panel)
        
        # Set splitter proportions
        main_splitter.setSizes([300, 200])
    
    def create_session_list_panel(self) -> QWidget:
        """Create session list panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Active Sessions")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Control buttons
        self.new_session_btn = QPushButton("New Session")
        self.new_session_btn.clicked.connect(self.create_new_session)
        header_layout.addWidget(self.new_session_btn)
        
        self.end_session_btn = QPushButton("End Session")
        self.end_session_btn.clicked.connect(self.end_selected_session)
        self.end_session_btn.setEnabled(False)
        header_layout.addWidget(self.end_session_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_sessions)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Session table
        self.session_table = QTableWidget()
        self.session_table.setColumnCount(6)
        self.session_table.setHorizontalHeaderLabels([
            "Session ID", "Device", "Vendor", "Status", "Start Time", "Commands"
        ])
        
        # Configure table
        self.session_table.horizontalHeader().setStretchLastSection(True)
        self.session_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.session_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.session_table.setSelectionMode(QTableWidget.SingleSelection)
        self.session_table.itemSelectionChanged.connect(self.on_session_selection_changed)
        self.session_table.itemDoubleClicked.connect(self.on_session_double_clicked)
        
        layout.addWidget(self.session_table)
        
        return panel
    
    def create_session_details_panel(self) -> QWidget:
        """Create session details panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # Session Info Tab
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # Session details
        details_group = QGroupBox("Session Details")
        details_layout = QVBoxLayout()
        details_group.setLayout(details_layout)
        
        self.session_id_label = QLabel("Session ID: -")
        self.device_label = QLabel("Device: -")
        self.vendor_label = QLabel("Vendor: -")
        self.status_label = QLabel("Status: -")
        self.start_time_label = QLabel("Start Time: -")
        self.duration_label = QLabel("Duration: -")
        self.commands_count_label = QLabel("Commands: 0")
        
        for label in [
            self.session_id_label, self.device_label, self.vendor_label,
            self.status_label, self.start_time_label, self.duration_label,
            self.commands_count_label
        ]:
            details_layout.addWidget(label)
        
        info_layout.addWidget(details_group)
        
        # Connection details
        connection_group = QGroupBox("Connection Details")
        connection_layout = QVBoxLayout()
        connection_group.setLayout(connection_layout)
        
        self.port_label = QLabel("Port: -")
        self.baud_rate_label = QLabel("Baud Rate: -")
        self.data_bits_label = QLabel("Data Bits: -")
        self.parity_label = QLabel("Parity: -")
        self.stop_bits_label = QLabel("Stop Bits: -")
        
        for label in [
            self.port_label, self.baud_rate_label, self.data_bits_label,
            self.parity_label, self.stop_bits_label
        ]:
            connection_layout.addWidget(label)
        
        info_layout.addWidget(connection_group)
        info_layout.addStretch()
        
        tab_widget.addTab(info_widget, "Session Info")
        
        # Command History Tab
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        
        # Command history controls
        history_controls_layout = QHBoxLayout()
        
        self.export_commands_btn = QPushButton("Export Commands")
        self.export_commands_btn.clicked.connect(self.export_commands)
        history_controls_layout.addWidget(self.export_commands_btn)
        
        self.clear_commands_btn = QPushButton("Clear History")
        self.clear_commands_btn.clicked.connect(self.clear_command_history)
        history_controls_layout.addWidget(self.clear_commands_btn)
        
        history_controls_layout.addStretch()
        
        history_layout.addLayout(history_controls_layout)
        
        # Command history text
        self.command_history_text = QTextEdit()
        self.command_history_text.setReadOnly(True)
        self.command_history_text.setFont(QFont("Consolas", 9))
        history_layout.addWidget(self.command_history_text)
        
        tab_widget.addTab(history_widget, "Command History")
        
        # AI Interactions Tab
        ai_widget = QWidget()
        ai_layout = QVBoxLayout(ai_widget)
        
        # AI interactions controls
        ai_controls_layout = QHBoxLayout()
        
        self.export_ai_btn = QPushButton("Export AI Log")
        self.export_ai_btn.clicked.connect(self.export_ai_log)
        ai_controls_layout.addWidget(self.export_ai_btn)
        
        self.clear_ai_btn = QPushButton("Clear AI Log")
        self.clear_ai_btn.clicked.connect(self.clear_ai_log)
        ai_controls_layout.addWidget(self.clear_ai_btn)
        
        ai_controls_layout.addStretch()
        
        ai_layout.addLayout(ai_controls_layout)
        
        # AI interactions text
        self.ai_interactions_text = QTextEdit()
        self.ai_interactions_text.setReadOnly(True)
        self.ai_interactions_text.setFont(QFont("Arial", 9))
        ai_layout.addWidget(self.ai_interactions_text)
        
        tab_widget.addTab(ai_widget, "AI Interactions")
        
        return panel
    
    def connect_signals(self):
        """Connect application signals"""
        # Connect to application signals
        self.app.session_created.connect(self.on_session_created)
        self.app.session_ended.connect(self.on_session_ended)
        self.app.command_executed.connect(self.on_command_executed)
        self.app.ai_interaction_logged.connect(self.on_ai_interaction_logged)
    
    @Slot(str)
    def on_session_created(self, session_id: str):
        """Handle session created"""
        self.current_session_id = session_id
        self.refresh_sessions()
        self.session_created.emit(session_id)
        self.logger.info(f"Session created: {session_id}")
    
    @Slot(str)
    def on_session_ended(self, session_id: str):
        """Handle session ended"""
        if self.current_session_id == session_id:
            self.current_session_id = None
        self.refresh_sessions()
        self.session_ended.emit(session_id)
        self.logger.info(f"Session ended: {session_id}")
    
    @Slot(str, str, str, str)
    def on_command_executed(self, session_id: str, command: str, output: str, timestamp: str):
        """Handle command executed"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.command_count += 1
            session.last_activity = datetime.fromisoformat(timestamp)
            self.update_session_details()
            self.update_command_history()
    
    @Slot(str, str, str, str, str)
    def on_ai_interaction_logged(self, session_id: str, query: str, response: str, query_type: str, timestamp: str):
        """Handle AI interaction logged"""
        if session_id == self.current_session_id:
            self.update_ai_interactions()
    
    @Slot()
    def on_session_selection_changed(self):
        """Handle session selection changed"""
        selected_items = self.session_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            session_id = self.session_table.item(row, 0).text()
            self.select_session(session_id)
            self.end_session_btn.setEnabled(True)
        else:
            self.end_session_btn.setEnabled(False)
    
    @Slot()
    def on_session_double_clicked(self):
        """Handle session double clicked"""
        selected_items = self.session_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            session_id = self.session_table.item(row, 0).text()
            self.session_selected.emit(session_id)
    
    def create_new_session(self):
        """Create new session"""
        # Get session details from user
        dialog = QInputDialog(self)
        dialog.setWindowTitle("New Session")
        dialog.setLabelText("Session Name:")
        dialog.setTextValue(f"Session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        if dialog.exec():
            session_name = dialog.textValue().strip()
            if session_name:
                # Create session through application
                asyncio.create_task(self.app.create_session(session_name))
    
    def end_selected_session(self):
        """End selected session"""
        selected_items = self.session_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            session_id = self.session_table.item(row, 0).text()
            
            reply = QMessageBox.question(
                self,
                "End Session",
                f"Are you sure you want to end session {session_id}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                asyncio.create_task(self.app.end_session(session_id))
    
    def refresh_sessions(self):
        """Refresh sessions"""
        # Get sessions from application
        # Since get_all_sessions is async, we need to handle it differently
        # For now, get sessions from the active sessions dict
        sessions = list(self.app.session_service.active_sessions.values())
        
        # Clear table
        self.session_table.setRowCount(0)
        
        # Add sessions to table
        for session in sessions:
            self.sessions[session.session_id] = session
            
            row = self.session_table.rowCount()
            self.session_table.insertRow(row)
            
            # Session ID
            self.session_table.setItem(row, 0, QTableWidgetItem(session.session_id))
            
            # Device
            device_text = f"{session.device_info.hostname}" if session.device_info else "Unknown"
            self.session_table.setItem(row, 1, QTableWidgetItem(device_text))
            
            # Vendor
            vendor_text = session.device_info.vendor if session.device_info else "Unknown"
            self.session_table.setItem(row, 2, QTableWidgetItem(vendor_text))
            
            # Status
            status_item = QTableWidgetItem(session.status.value)
            if session.status == SessionStatus.ACTIVE:
                status_item.setBackground(Qt.green)
            elif session.status == SessionStatus.DISCONNECTED:
                status_item.setBackground(Qt.red)
            else:
                status_item.setBackground(Qt.yellow)
            self.session_table.setItem(row, 3, status_item)
            
            # Start Time
            start_time_text = session.start_time.strftime("%Y-%m-%d %H:%M:%S")
            self.session_table.setItem(row, 4, QTableWidgetItem(start_time_text))
            
            # Commands
            commands_text = str(session.command_count)
            self.session_table.setItem(row, 5, QTableWidgetItem(commands_text))
        
        # Update details
        self.update_session_details()
    
    def select_session(self, session_id: str):
        """Select session"""
        self.current_session_id = session_id
        self.update_session_details()
        self.update_command_history()
        self.update_ai_interactions()
    
    def update_session_details(self):
        """Update session details"""
        if self.current_session_id and self.current_session_id in self.sessions:
            session = self.sessions[self.current_session_id]
            
            # Update labels
            self.session_id_label.setText(f"Session ID: {session.session_id}")
            
            device_text = f"{session.device_info.hostname}" if session.device_info else "Unknown"
            self.device_label.setText(f"Device: {device_text}")
            
            vendor_text = session.device_info.vendor if session.device_info else "Unknown"
            self.vendor_label.setText(f"Vendor: {vendor_text}")
            
            self.status_label.setText(f"Status: {session.status.value}")
            self.start_time_label.setText(f"Start Time: {session.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            duration = datetime.utcnow() - session.start_time
            duration_text = str(duration).split('.')[0]
            self.duration_label.setText(f"Duration: {duration_text}")
            
            self.commands_count_label.setText(f"Commands: {session.command_count}")
            
            # Update connection details
            if session.connection_config:
                self.port_label.setText(f"Port: {session.connection_config.port}")
                self.baud_rate_label.setText(f"Baud Rate: {session.connection_config.baud_rate}")
                self.data_bits_label.setText(f"Data Bits: {session.connection_config.data_bits}")
                self.parity_label.setText(f"Parity: {session.connection_config.parity}")
                self.stop_bits_label.setText(f"Stop Bits: {session.connection_config.stop_bits}")
            else:
                self.port_label.setText("Port: -")
                self.baud_rate_label.setText("Baud Rate: -")
                self.data_bits_label.setText("Data Bits: -")
                self.parity_label.setText("Parity: -")
                self.stop_bits_label.setText("Stop Bits: -")
        else:
            # Clear labels
            self.session_id_label.setText("Session ID: -")
            self.device_label.setText("Device: -")
            self.vendor_label.setText("Vendor: -")
            self.status_label.setText("Status: -")
            self.start_time_label.setText("Start Time: -")
            self.duration_label.setText("Duration: -")
            self.commands_count_label.setText("Commands: 0")
            
            self.port_label.setText("Port: -")
            self.baud_rate_label.setText("Baud Rate: -")
            self.data_bits_label.setText("Data Bits: -")
            self.parity_label.setText("Parity: -")
            self.stop_bits_label.setText("Stop Bits: -")
    
    def update_command_history(self):
        """Update command history"""
        if self.current_session_id:
            commands = self.app.get_session_commands(self.current_session_id)
            
            history_text = ""
            for cmd in commands:
                timestamp = datetime.fromisoformat(cmd["timestamp"]).strftime("%H:%M:%S")
                command = cmd["command"]
                output = cmd["output"]
                
                history_text += f"[{timestamp}] {command}\n"
                history_text += f"{output}\n"
                history_text += "-" * 50 + "\n\n"
            
            self.command_history_text.setPlainText(history_text)
        else:
            self.command_history_text.clear()
    
    def update_ai_interactions(self):
        """Update AI interactions"""
        if self.current_session_id:
            interactions = self.app.get_session_ai_interactions(self.current_session_id)
            
            ai_text = ""
            for interaction in interactions:
                timestamp = datetime.fromisoformat(interaction["timestamp"]).strftime("%H:%M:%S")
                query = interaction["query"]
                response = interaction["response"]
                query_type = interaction["query_type"]
                confidence = interaction.get("confidence", 0.0)
                
                ai_text += f"[{timestamp}] {query_type} (Confidence: {confidence:.1f}%)\n"
                ai_text += f"Query: {query}\n"
                ai_text += f"Response: {response}\n"
                ai_text += "-" * 50 + "\n\n"
            
            self.ai_interactions_text.setPlainText(ai_text)
        else:
            self.ai_interactions_text.clear()
    
    def export_current_session(self):
        """Export current session"""
        if not self.current_session_id:
            QMessageBox.warning(self, "Export Session", "No session selected.")
            return
        
        # Get save file name
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Export Session",
            f"session_{self.current_session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        
        if file_name:
            session_data = self.app.export_session(self.current_session_id)
            
            try:
                with open(file_name, 'w') as f:
                    json.dump(session_data, f, indent=2, default=str)
                
                QMessageBox.information(self, "Export Session", f"Session exported to {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export session: {str(e)}")
    
    def export_commands(self):
        """Export commands"""
        if not self.current_session_id:
            QMessageBox.warning(self, "Export Commands", "No session selected.")
            return
        
        # Get save file name
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Export Commands",
            f"commands_{self.current_session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )
        
        if file_name:
            commands = self.app.get_session_commands(self.current_session_id)
            
            try:
                with open(file_name, 'w') as f:
                    for cmd in commands:
                        timestamp = datetime.fromisoformat(cmd["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                        command = cmd["command"]
                        output = cmd["output"]
                        
                        f.write(f"[{timestamp}] {command}\n")
                        f.write(f"{output}\n")
                        f.write("-" * 50 + "\n\n")
                
                QMessageBox.information(self, "Export Commands", f"Commands exported to {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export commands: {str(e)}")
    
    def export_ai_log(self):
        """Export AI log"""
        if not self.current_session_id:
            QMessageBox.warning(self, "Export AI Log", "No session selected.")
            return
        
        # Get save file name
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Export AI Log",
            f"ai_log_{self.current_session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        
        if file_name:
            interactions = self.app.get_session_ai_interactions(self.current_session_id)
            
            try:
                with open(file_name, 'w') as f:
                    json.dump(interactions, f, indent=2, default=str)
                
                QMessageBox.information(self, "Export AI Log", f"AI log exported to {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export AI log: {str(e)}")
    
    def clear_command_history(self):
        """Clear command history"""
        if not self.current_session_id:
            return
        
        reply = QMessageBox.question(
            self,
            "Clear Command History",
            "Are you sure you want to clear the command history for this session?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.app.clear_session_commands(self.current_session_id)
            self.update_command_history()
    
    def clear_ai_log(self):
        """Clear AI log"""
        if not self.current_session_id:
            return
        
        reply = QMessageBox.question(
            self,
            "Clear AI Log",
            "Are you sure you want to clear the AI interaction log for this session?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.app.clear_session_ai_interactions(self.current_session_id)
            self.update_ai_interactions()
    
    def load_sessions(self):
        """Load existing sessions"""
        # This would typically load from a database or file
        # For now, we'll just refresh from the application
        self.refresh_sessions()
    
    def open_session(self):
        """Open session from file"""
        # Get file name
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Session",
            "",
            "JSON Files (*.json)"
        )
        
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    session_data = json.load(f)
                
                # Import session through application
                asyncio.create_task(self.app.import_session(session_data))
                
                QMessageBox.information(self, "Open Session", f"Session loaded from {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Open Error", f"Failed to open session: {str(e)}")