"""
Chat Widget for NetworkSwitch AI Assistant
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QComboBox, QLabel, QFrame, QListWidget,
    QListWidgetItem, QSplitter, QGroupBox, QScrollArea,
    QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread, QObject
from PySide6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor, QIcon

from core.config import AppConfig
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.application import NetworkSwitchAIApp
from core.constants import AIPromptType, VendorType
from utils.logging import get_logger
from models.device_models import AIQuery, AIResponse


class ChatMessageWidget(QWidget):
    """Widget for individual chat messages"""
    
    def __init__(self, message: str, is_user: bool, timestamp: datetime, confidence: Optional[float] = None):
        super().__init__()
        self.message = message
        self.is_user = is_user
        self.timestamp = timestamp
        self.confidence = confidence
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup message UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Message header
        header_layout = QHBoxLayout()
        
        # Sender label
        sender_label = QLabel("You" if self.is_user else "AI Assistant")
        sender_label.setFont(QFont("Arial", 9, QFont.Bold))
        
        # Timestamp
        timestamp_label = QLabel(self.timestamp.strftime("%H:%M:%S"))
        timestamp_label.setFont(QFont("Arial", 8))
        timestamp_label.setStyleSheet("color: #a6a6a6;")
        
        # Confidence (for AI responses)
        if self.confidence is not None and not self.is_user:
            confidence_label = QLabel(f"Confidence: {self.confidence:.1f}%")
            confidence_label.setFont(QFont("Arial", 8))
            confidence_label.setStyleSheet("color: #a6a6a6;")
        else:
            confidence_label = QLabel()
        
        header_layout.addWidget(sender_label)
        header_layout.addStretch()
        header_layout.addWidget(confidence_label)
        header_layout.addWidget(timestamp_label)
        
        layout.addLayout(header_layout)
        
        # Message content
        message_text = QTextEdit()
        message_text.setReadOnly(True)
        message_text.setPlainText(self.message)
        message_text.setMaximumHeight(200)
        message_text.setMinimumHeight(50)
        
        # Style based on sender
        if self.is_user:
            message_text.setStyleSheet("""
                QTextEdit {
                    background-color: #2d2d2d;
                    border: 1px solid #3e3e3e;
                    border-radius: 8px;
                    padding: 8px;
                    color: #d4d4d4;
                }
            """)
        else:
            message_text.setStyleSheet("""
                QTextEdit {
                    background-color: #233446;
                    border: 1px solid #3b4f63;
                    border-radius: 8px;
                    padding: 8px;
                    color: #d7e8ff;
                }
            """)
        
        layout.addWidget(message_text)
        
        # Add spacing
        layout.addSpacing(10)


class ChatWidget(QWidget):
    """Chat widget for AI assistance"""
    
    query_sent = Signal(str)
    
    def __init__(self, app: 'NetworkSwitchAIApp'):
        super().__init__()
        self.app = app
        self.config = app.config
        self.logger = get_logger("chat_widget")
        
        # Chat state
        self.current_session_id: Optional[str] = None
        self.is_ai_responding = False
        self.message_history: List[Dict[str, Any]] = []
        
        # Setup UI
        self.setup_ui()
        
        # Connect signals
        self.connect_signals()
        
        self.logger.info("Chat widget initialized")
    
    def setup_ui(self):
        """Setup chat UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create main splitter
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # Left panel - Chat messages
        chat_panel = self.create_chat_panel()
        main_splitter.addWidget(chat_panel)
        
        # Right panel - Quick actions and context
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # Set splitter proportions
        main_splitter.setSizes([600, 300])
    
    def create_chat_panel(self) -> QWidget:
        """Create chat panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Chat header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("AI Assistant")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # AI status
        self.ai_status_label = QLabel("Ready")
        self.ai_status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        header_layout.addWidget(self.ai_status_label)
        
        layout.addLayout(header_layout)
        
        # Chat messages area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                background-color: #252526;
            }
        """)
        
        # Chat messages container
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.addStretch()
        
        self.chat_scroll.setWidget(self.chat_container)
        layout.addWidget(self.chat_scroll)
        
        # Input area
        input_group = QGroupBox("Ask AI Assistant")
        input_layout = QVBoxLayout()
        input_group.setLayout(input_layout)
        
        # Query type selection
        query_type_layout = QHBoxLayout()
        query_type_layout.addWidget(QLabel("Query Type:"))
        
        self.query_type_combo = QComboBox()
        self.query_type_combo.addItems([
            "General Question",
            "Network Troubleshooting",
            "Configuration Help",
            "Command Explanation",
            "Best Practices"
        ])
        query_type_layout.addWidget(self.query_type_combo)
        query_type_layout.addStretch()
        
        input_layout.addLayout(query_type_layout)
        
        # Query input
        self.query_input = QTextEdit()
        self.query_input.setMaximumHeight(100)
        self.query_input.setPlaceholderText("Type your question here... Use @device to include device context, @session to include session history, @config to include configuration context.")
        self.query_input.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px;
                font-family: Arial;
            }
            QTextEdit:focus {
                border-color: #0078d4;
            }
        """)
        input_layout.addWidget(self.query_input)
        
        # Input controls
        input_controls_layout = QHBoxLayout()
        
        # Context checkboxes
        self.include_device_context = QComboBox()
        self.include_device_context.addItems(["No Context", "Current Session", "All Sessions"])
        input_controls_layout.addWidget(QLabel("Context:"))
        input_controls_layout.addWidget(self.include_device_context)
        
        input_controls_layout.addStretch()
        
        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.on_send_query)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #3e3e3e;
                color: #888888;
            }
        """)
        input_controls_layout.addWidget(self.send_button)
        
        input_layout.addLayout(input_controls_layout)
        
        layout.addWidget(input_group)
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """Create right panel with quick actions and context"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Quick Actions
        quick_actions_group = QGroupBox("Quick Actions")
        quick_actions_layout = QVBoxLayout()
        quick_actions_group.setLayout(quick_actions_layout)
        
        quick_actions = [
            ("Analyze Network Issue", "Analyze the current network issue and suggest solutions"),
            ("Check Configuration", "Review current device configuration for issues"),
            ("Troubleshoot Connectivity", "Help troubleshoot connectivity problems"),
            ("Optimize Performance", "Suggest performance optimizations"),
            ("Security Check", "Check for security vulnerabilities"),
            ("Best Practices", "Provide best practices for current setup")
        ]
        
        for action_name, action_desc in quick_actions:
            btn = QPushButton(action_name)
            btn.setToolTip(action_desc)
            btn.clicked.connect(lambda checked, a=action_name: self.on_quick_action(a))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    color: #d4d4d4;
                    border: 1px solid #3e3e3e;
                    border-radius: 4px;
                    padding: 6px 12px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #353535;
                }
            """)
            quick_actions_layout.addWidget(btn)
        
        layout.addWidget(quick_actions_group)
        
        # Suggested Commands
        suggested_group = QGroupBox("Suggested Commands")
        suggested_layout = QVBoxLayout()
        suggested_group.setLayout(suggested_layout)
        
        self.suggested_list = QListWidget()
        self.suggested_list.setMaximumHeight(200)
        self.suggested_list.itemDoubleClicked.connect(self.on_suggested_command_selected)
        suggested_layout.addWidget(self.suggested_list)
        
        layout.addWidget(suggested_group)
        
        # AI Response Info
        response_info_group = QGroupBox("Response Info")
        response_info_layout = QVBoxLayout()
        response_info_group.setLayout(response_info_layout)
        
        self.response_info_text = QTextEdit()
        self.response_info_text.setReadOnly(True)
        self.response_info_text.setMaximumHeight(150)
        self.response_info_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                font-size: 12px;
            }
        """)
        response_info_layout.addWidget(self.response_info_text)
        
        layout.addWidget(response_info_group)
        
        layout.addStretch()
        
        return panel
    
    def connect_signals(self):
        """Connect application signals"""
        # Connect to application signals
        self.app.ai_response_received.connect(self.on_ai_response_received)
        self.app.ai_response_started.connect(self.on_ai_response_started)
        self.app.ai_response_ended.connect(self.on_ai_response_ended)
        self.app.ai_suggestion_received.connect(self.on_ai_suggestion_received)
        
        # Connect session signals
        self.app.session_created.connect(self.on_session_created)
        self.app.session_ended.connect(self.on_session_ended)
    
    @Slot(str, str, float)
    def on_ai_response_received(self, query: str, response: str, confidence: float):
        """Handle AI response received"""
        self.add_ai_message(response, confidence)
        
        # Update response info
        response_info = f"""
Query Type: {self.query_type_combo.currentText()}
Confidence: {confidence:.1f}%
Response Time: {datetime.now().strftime('%H:%M:%S')}
Context: {self.include_device_context.currentText()}
        """.strip()
        
        self.response_info_text.setPlainText(response_info)
        
        # Add to message history
        self.message_history.append({
            "timestamp": datetime.now(),
            "type": "ai_response",
            "query": query,
            "response": response,
            "confidence": confidence,
            "query_type": self.query_type_combo.currentText()
        })
    
    @Slot(str)
    def on_ai_response_started(self, query: str):
        """Handle AI response started"""
        self.is_ai_responding = True
        self.ai_status_label.setText("Thinking...")
        self.ai_status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
        self.send_button.setEnabled(False)
        
        # Add user message
        self.add_user_message(query)
        
        # Add to message history
        self.message_history.append({
            "timestamp": datetime.now(),
            "type": "user_query",
            "query": query,
            "query_type": self.query_type_combo.currentText()
        })
    
    @Slot()
    def on_ai_response_ended(self):
        """Handle AI response ended"""
        self.is_ai_responding = False
        self.ai_status_label.setText("Ready")
        self.ai_status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        self.send_button.setEnabled(True)
    
    @Slot(list)
    def on_ai_suggestion_received(self, suggestions: List[str]):
        """Handle AI suggestions received"""
        self.suggested_list.clear()
        for suggestion in suggestions:
            item = QListWidgetItem(suggestion)
            self.suggested_list.addItem(item)
    
    @Slot(str)
    def on_session_created(self, session_id: str):
        """Handle session created"""
        self.current_session_id = session_id
        self.add_system_message(f"Session started: {session_id}")
    
    @Slot(str)
    def on_session_ended(self, session_id: str):
        """Handle session ended"""
        if self.current_session_id == session_id:
            self.current_session_id = None
            self.add_system_message(f"Session ended: {session_id}")
    
    @Slot()
    def on_send_query(self):
        """Handle send query button click"""
        if self.is_ai_responding:
            return
        
        query = self.query_input.toPlainText().strip()
        if not query:
            return
        
        # Clear input
        self.query_input.clear()
        
        # Prepare context
        context = self.prepare_context()
        
        # Send query
        self.query_sent.emit(query)
        asyncio.create_task(self.app.send_ai_query(query, context))
    
    @Slot(str)
    def on_quick_action(self, action: str):
        """Handle quick action"""
        action_queries = {
            "Analyze Network Issue": "Please analyze the current network issue and provide troubleshooting steps. Include potential causes and solutions.",
            "Check Configuration": "Please review the current device configuration and identify any potential issues, inconsistencies, or areas for improvement.",
            "Troubleshoot Connectivity": "Help troubleshoot connectivity problems. What commands should I run and what should I look for?",
            "Optimize Performance": "Suggest performance optimizations for the current network setup. What can be improved?",
            "Security Check": "Check for security vulnerabilities in the current configuration. What security best practices should be implemented?",
            "Best Practices": "Provide best practices for the current network setup and configuration."
        }
        
        query = action_queries.get(action, action)
        self.query_input.setPlainText(query)
        self.on_send_query()
    
    @Slot(QListWidgetItem)
    def on_suggested_command_selected(self, item: QListWidgetItem):
        """Handle suggested command selected"""
        command = item.text()
        self.query_input.setPlainText(f"Execute command: {command}")
        self.on_send_query()
    
    def prepare_context(self) -> Dict[str, Any]:
        """Prepare context for AI query"""
        context = {
            "query_type": self.query_type_combo.currentText(),
            "include_context": self.include_device_context.currentText(),
            "current_session": self.current_session_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add device context if available
        if self.app.current_device:
            context["device"] = {
                "vendor": self.app.current_device.vendor,
                "model": self.app.current_device.model,
                "version": self.app.current_device.version
            }
        
        # Add session context if requested
        if self.include_device_context.currentText() != "No Context":
            if self.include_device_context.currentText() == "Current Session":
                session_commands = self.app.get_session_commands(self.current_session_id)
            else:
                session_commands = self.app.get_all_session_commands()
            
            context["session_commands"] = session_commands
        
        return context
    
    def add_user_message(self, message: str):
        """Add user message to chat"""
        message_widget = ChatMessageWidget(message, True, datetime.now())
        
        # Insert at the end (before the stretch)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, message_widget)
        
        # Scroll to bottom
        self.scroll_to_bottom()
    
    def add_ai_message(self, message: str, confidence: Optional[float] = None):
        """Add AI message to chat"""
        message_widget = ChatMessageWidget(message, False, datetime.now(), confidence)
        
        # Insert at the end (before the stretch)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, message_widget)
        
        # Scroll to bottom
        self.scroll_to_bottom()
    
    def add_system_message(self, message: str):
        """Add system message to chat"""
        message_widget = ChatMessageWidget(f"*** {message} ***", False, datetime.now())
        message_widget.setStyleSheet("color: #a6a6a6; font-style: italic;")
        
        # Insert at the end (before the stretch)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, message_widget)
        
        # Scroll to bottom
        self.scroll_to_bottom()
    
    def scroll_to_bottom(self):
        """Scroll chat to bottom"""
        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_chat(self):
        """Clear chat messages"""
        # Clear all messages except the stretch
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.message_history.clear()
        self.add_system_message("Chat cleared")
    
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Get chat history"""
        return self.message_history.copy()
    
    def export_chat_history(self) -> str:
        """Export chat history as JSON"""
        return json.dumps(self.message_history, default=str, indent=2)
    
    def focus_query_input(self):
        """Focus query input"""
        self.query_input.setFocus()
    
    def set_query_type(self, query_type: str):
        """Set query type"""
        index = self.query_type_combo.findText(query_type)
        if index >= 0:
            self.query_type_combo.setCurrentIndex(index)
    
    def get_current_query_type(self) -> str:
        """Get current query type"""
        return self.query_type_combo.currentText()
