"""
Terminal Widget for NetworkSwitch AI Assistant
"""

import asyncio
from typing import Optional, List
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QComboBox, QLabel, QFrame, QScrollBar,
    QMenu, QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread, QObject
from PySide6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor, QKeySequence, QAction

from core.config import AppConfig
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.application import NetworkSwitchAIApp
from utils.logging import get_logger


class TerminalWidget(QWidget):
    """Terminal widget for device interaction"""
    
    command_sent = Signal(str)
    connection_status_changed = Signal(str, bool)
    
    def __init__(self, app: 'NetworkSwitchAIApp'):
        super().__init__()
        self.app = app
        self.config = app.config
        self.logger = get_logger("terminal_widget")
        
        # Terminal state
        self.current_prompt = ""
        self.command_history: List[str] = []
        self.history_index = -1
        self.is_connected = False
        
        # Setup UI
        self.setup_ui()
        
        # Connect signals
        self.connect_signals()
        
        self.logger.info("Terminal widget initialized")
    
    def setup_ui(self):
        """Setup terminal UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Terminal output area
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setFont(QFont("Consolas", 10))
        self.terminal_output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.terminal_output)
        
        # Command input area
        input_layout = QHBoxLayout()
        
        # Prompt label
        self.prompt_label = QLabel("disconnected>")
        self.prompt_label.setFont(QFont("Consolas", 10))
        self.prompt_label.setStyleSheet("color: #0078d4; font-weight: bold;")
        input_layout.addWidget(self.prompt_label)
        
        # Command input
        self.command_input = QLineEdit()
        self.command_input.setFont(QFont("Consolas", 10))
        self.command_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
        """)
        # Pressing Return submits the typed command; if empty, it sends Enter.
        self.command_input.returnPressed.connect(self.on_command_entered)
        self.command_input.setEnabled(False)
        input_layout.addWidget(self.command_input)
        
        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.on_command_entered)
        self.send_button.setEnabled(False)
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        # Command history
        self.history_combo = QComboBox()
        self.history_combo.setMinimumWidth(200)
        self.history_combo.currentIndexChanged.connect(self.on_history_selected)
        controls_layout.addWidget(QLabel("History:"))
        controls_layout.addWidget(self.history_combo)
        
        controls_layout.addStretch()
        
        # Terminal controls
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_terminal)
        controls_layout.addWidget(self.clear_button)
        
        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self.export_terminal)
        controls_layout.addWidget(self.export_button)

        # Enter button (simulate pressing Enter)
        self.enter_button = QPushButton("Enter")
        self.enter_button.clicked.connect(self.send_enter)
        self.enter_button.setEnabled(False)
        controls_layout.addWidget(self.enter_button)

        # Fetch device info button
        self.fetch_info_button = QPushButton("Fetch Info")
        self.fetch_info_button.clicked.connect(self.fetch_device_info)
        self.fetch_info_button.setEnabled(False)
        controls_layout.addWidget(self.fetch_info_button)
        
        layout.addLayout(controls_layout)
        
        # Setup context menu
        self.setup_context_menu()
    
    def setup_context_menu(self):
        """Setup context menu for terminal"""
        self.terminal_output.setContextMenuPolicy(Qt.CustomContextMenu)
        self.terminal_output.customContextMenuRequested.connect(self.show_context_menu)
        
        self.context_menu = QMenu(self)
        
        # Copy action
        copy_action = QAction("Copy", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy_selected_text)
        self.context_menu.addAction(copy_action)
        
        # Paste action
        paste_action = QAction("Paste", self)
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(self.paste_text)
        self.context_menu.addAction(paste_action)
        
        self.context_menu.addSeparator()
        
        # Clear action
        clear_action = QAction("Clear Terminal", self)
        clear_action.triggered.connect(self.clear_terminal)
        self.context_menu.addAction(clear_action)
        
        # Select all action
        select_all_action = QAction("Select All", self)
        select_all_action.setShortcut(QKeySequence.SelectAll)
        select_all_action.triggered.connect(self.terminal_output.selectAll)
        self.context_menu.addAction(select_all_action)
    
    def connect_signals(self):
        """Connect application signals"""
        # Connect to application signals
        self.app.terminal_data_received.connect(self.on_terminal_data_received)
        self.app.connection_status_changed.connect(self.on_connection_status_changed)
    
    @Slot(str)
    def on_terminal_data_received(self, data: str):
        """Handle terminal data received"""
        self.append_terminal_output(data)
        
        # Extract prompt if available
        lines = data.strip().split('\n')
        if lines:
            last_line = lines[-1]
            if '>' in last_line or '#' in last_line or '$' in last_line:
                self.current_prompt = last_line.strip()
                self.update_prompt_label()
    
    @Slot(str, bool)
    def on_connection_status_changed(self, status: str, connected: bool):
        """Handle connection status change"""
        self.is_connected = connected
        
        # Update UI state
        self.command_input.setEnabled(connected)
        self.send_button.setEnabled(connected)
        if hasattr(self, 'enter_button'):
            self.enter_button.setEnabled(connected)
        if hasattr(self, 'fetch_info_button'):
            self.fetch_info_button.setEnabled(connected)
        
        # Update prompt
        if connected:
            self.current_prompt = ""
            self.update_prompt_label()
        else:
            self.current_prompt = "disconnected"
            self.update_prompt_label()
        
        # Log connection status
        if connected:
            self.append_terminal_output("\n*** Connected to device ***\n", "system")
        else:
            self.append_terminal_output("\n*** Disconnected from device ***\n", "system")
        
        self.connection_status_changed.emit(status, connected)
    
    def update_prompt_label(self):
        """Update prompt label"""
        if self.is_connected and self.current_prompt:
            # Extract just the prompt part
            prompt = self.current_prompt
            if '>' in prompt:
                prompt = prompt[prompt.rfind('\n') + 1:] if '\n' in prompt else prompt
            elif '#' in prompt:
                prompt = prompt[prompt.rfind('\n') + 1:] if '\n' in prompt else prompt
            
            self.prompt_label.setText(prompt)
        else:
            self.prompt_label.setText("disconnected>")
    
    @Slot()
    def on_command_entered(self):
        """Handle command entry"""
        if not self.is_connected:
            return
        
        raw_text = self.command_input.text()
        # If input is empty, send an Enter keystroke to advance CLI
        if not raw_text:
            self.send_enter()
            return
        
        command = raw_text.strip()
        
        # Add to history
        if command not in self.command_history:
            self.command_history.append(command)
            self.history_combo.addItem(command)
        
        # Reset history index
        self.history_index = -1
        
        # Clear input
        self.command_input.clear()
        
        # Send command
        self.send_command(command)
    
    def send_command(self, command: str):
        """Send command to device"""
        if not self.is_connected:
            return
        
        # Add command to terminal with prompt
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.append_terminal_output(f"[{timestamp}] {command}\n", "command")
        
        # Get session ID from main window
        session_id = getattr(self.app, 'current_session_id', 'default_session')
        
        # Emit signal to main window
        if hasattr(self.app, 'main_window'):
            self.app.main_window.command_sent.emit(session_id, command)
        
        # Application handles scheduling via its tracked task mechanism
    
    @Slot(int)
    def on_history_selected(self, index: int):
        """Handle history selection"""
        if index >= 0 and index < len(self.command_history):
            command = self.command_history[index]
            self.command_input.setText(command)
            self.command_input.setFocus()
    
    def append_terminal_output(self, text: str, style: str = "normal"):
        """Append text to terminal output with styling"""
        cursor = self.terminal_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Apply styling
        format = QTextCharFormat()
        
        if style == "command":
            format.setForeground(QColor("#4fc1ff"))  # Light blue
            format.setFontWeight(QFont.Bold)
        elif style == "system":
            format.setForeground(QColor("#ffd700"))  # Gold
            format.setFontWeight(QFont.Bold)
        elif style == "error":
            format.setForeground(QColor("#ff6b6b"))  # Red
            format.setFontWeight(QFont.Bold)
        elif style == "success":
            format.setForeground(QColor("#51cf66"))  # Green
        else:
            format.setForeground(QColor("#d4d4d4"))  # Default light gray
        
        # Insert text with format
        cursor.insertText(text, format)
        
        # Auto-scroll to bottom
        self.terminal_output.setTextCursor(cursor)
        self.terminal_output.ensureCursorVisible()
    
    def clear_terminal(self):
        """Clear terminal output"""
        self.terminal_output.clear()
        self.append_terminal_output("Terminal cleared.\n", "system")
    
    def export_terminal(self):
        """Export terminal output"""
        # TODO: Implement export functionality
        QMessageBox.information(self, "Export", "Export functionality not implemented yet.")

    def send_enter(self):
        """Send raw newline to the device"""
        if not self.is_connected:
            return
        # Use app's tracked scheduling to avoid untracked coroutines
        if hasattr(self.app, 'queue_enter'):
            self.app.queue_enter()
        else:
            asyncio.create_task(self.app.send_enter())

    def fetch_device_info(self):
        """Fetch device information from the device"""
        if not self.is_connected:
            QMessageBox.warning(self, "Not Connected", "Connect to a device first.")
            return
        asyncio.create_task(self.app.fetch_device_info())
    
    def show_context_menu(self, position):
        """Show context menu"""
        self.context_menu.exec_(self.terminal_output.mapToGlobal(position))
    
    def copy_selected_text(self):
        """Copy selected text"""
        cursor = self.terminal_output.textCursor()
        if cursor.hasSelection():
            cursor.copy()
    
    def paste_text(self):
        """Paste text into command input"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.command_input.insert(text)
    
    def get_terminal_content(self) -> str:
        """Get terminal content"""
        return self.terminal_output.toPlainText()
    
    def set_terminal_content(self, content: str):
        """Set terminal content"""
        self.terminal_output.clear()
        self.append_terminal_output(content)
    
    def add_command_to_history(self, command: str):
        """Add command to history"""
        if command not in self.command_history:
            self.command_history.append(command)
            self.history_combo.addItem(command)
    
    def get_command_history(self) -> List[str]:
        """Get command history"""
        return self.command_history.copy()
    
    def set_command_history(self, history: List[str]):
        """Set command history"""
        self.command_history = history.copy()
        self.history_combo.clear()
        for command in history:
            self.history_combo.addItem(command)
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        # Handle up/down arrow for command history
        if event.key() == Qt.Key_Up:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.command_input.setText(self.command_history[-self.history_index - 1])
            event.accept()
            return
        
        elif event.key() == Qt.Key_Down:
            if self.history_index > 0:
                self.history_index -= 1
                self.command_input.setText(self.command_history[-self.history_index - 1])
            elif self.history_index == 0:
                self.history_index = -1
                self.command_input.clear()
            event.accept()
            return
        
        # Handle Ctrl+L to clear
        elif event.key() == Qt.Key_L and event.modifiers() == Qt.ControlModifier:
            self.clear_terminal()
            event.accept()
            return
        
        # Handle Tab for command completion
        elif event.key() == Qt.Key_Tab:
            self.handle_tab_completion()
            event.accept()
            return
        
        super().keyPressEvent(event)
    
    def handle_tab_completion(self):
        """Handle tab completion"""
        # TODO: Implement command completion based on current context
        current_text = self.command_input.text()
        if current_text:
            # Simple completion for common commands
            common_commands = [
                "show", "configure", "interface", "vlan", "ip",
                "router", "ospf", "bgp", "access-list", "username"
            ]
            
            matches = [cmd for cmd in common_commands if cmd.startswith(current_text.lower())]
            if len(matches) == 1:
                self.command_input.setText(matches[0])
            elif len(matches) > 1:
                self.append_terminal_output(f"Possible completions: {', '.join(matches)}\n", "system")
    
    def add_system_message(self, message: str):
        """Add system message to terminal"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.append_terminal_output(f"[{timestamp}] *** {message} ***\n", "system")
    
    def add_error_message(self, message: str):
        """Add error message to terminal"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.append_terminal_output(f"[{timestamp}] ERROR: {message}\n", "error")
    
    def add_success_message(self, message: str):
        """Add success message to terminal"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.append_terminal_output(f"[{timestamp}] SUCCESS: {message}\n", "success")
    
    def focus_command_input(self):
        """Focus command input"""
        self.command_input.setFocus()
    
    def is_command_input_focused(self) -> bool:
        """Check if command input is focused"""
        return self.command_input.hasFocus()
