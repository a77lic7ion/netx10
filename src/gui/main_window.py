"""
Main Window for NetworkSwitch AI Assistant
"""

import sys
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QMenuBar, QStatusBar, QMessageBox, QProgressBar,
    QLabel, QPushButton, QComboBox, QTextEdit, QGroupBox,
    QFrame, QToolBar, QDockWidget, QListWidget, QListWidgetItem,
    QFileDialog, QInputDialog, QLineEdit, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QThread, QObject
from PySide6.QtGui import QAction, QIcon, QFont, QTextCharFormat, QColor

from core.config import AppConfig
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.application import NetworkSwitchAIApp
from utils.logging_utils import get_logger
from .terminal_widget import TerminalWidget
from .chat_widget import ChatWidget
from .session_manager import SessionManagerWidget
from .status_bar import StatusBarWidget
from .preferences_dialog import PreferencesDialog

class MainWindow(QMainWindow):
    """Main application window"""
    
    # Signals
    connect_requested = Signal(str, str, int, str, str)  # com_port, vendor_type, baud_rate, username, password
    disconnect_requested = Signal()
    command_sent = Signal(str, str)  # session_id, command
    ai_query_sent = Signal(str, str, str)  # session_id, query, context
    save_session_requested = Signal()
    load_session_requested = Signal()

    def __init__(self, app: 'NetworkSwitchAIApp'):
        super().__init__()
        self.app = app
        self.config = app.config
        self.logger = get_logger("main_window")
        self.preferences_dialog = None  # Initialize preferences dialog

        # Initialize UI
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_tool_bar()
        self.setup_status_bar()

        # Connect signals
        self.connect_signals()

        # Initialize widgets
        self.init_widgets()

        # Start update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(1000)  # Update every second

        self.logger.info("Main window initialized")
    
    def setup_ui(self):
        """Setup the main UI"""
        self.setWindowTitle("NetworkSwitch AI Assistant")
        self.setGeometry(100, 100, 1200, 800)

        # Set application dark theme style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            QWidget {
                color: #d4d4d4;
            }
            QTabWidget::pane {
                border: 1px solid #3e3e3e;
                background-color: #252526;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #d4d4d4;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                border-bottom: 2px solid #0078d4;
            }
            QGroupBox {
                color: #d4d4d4;
                font-weight: bold;
                border: 2px solid #3e3e3e;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #252526;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel {
                color: #d4d4d4;
            }
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
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            QComboBox {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 120px;
            }
            QStatusBar {
                background-color: #2c2c2c;
                color: #d4d4d4;
                border-top: 1px solid #3e3e3e;
            }
        """)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create main splitter
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)

        # Left panel - Session and Device Management
        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)

        # Center panel - Terminal and Chat
        center_panel = self.create_center_panel()
        main_splitter.addWidget(center_panel)

        # Right panel - Status and Info
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)

        # Set splitter proportions
        main_splitter.setSizes([300, 600, 300])
        main_splitter.setStretchFactor(0, 0)  # Left panel - no stretch
        main_splitter.setStretchFactor(1, 1)  # Center panel - stretch
        main_splitter.setStretchFactor(2, 0)  # Right panel - no stretch
    
    def create_left_panel(self) -> QWidget:
        """Create left panel with session and device management"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # Session Manager Tab
        self.session_manager = SessionManagerWidget(self.app)
        tab_widget.addTab(self.session_manager, "Sessions")
        
        # Device Manager Tab (placeholder for now)
        device_placeholder = QWidget()
        device_placeholder.setLayout(QVBoxLayout())
        device_placeholder.layout().addWidget(QLabel("Device Manager - Coming Soon"))
        tab_widget.addTab(device_placeholder, "Devices")
        
        # Connection Controls
        connection_group = QGroupBox("Connection Controls")
        connection_layout = QVBoxLayout()
        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)
        
        # Port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        port_layout.addWidget(self.port_combo)
        connection_layout.addLayout(port_layout)
        
        # Vendor selection
        vendor_layout = QHBoxLayout()
        vendor_layout.addWidget(QLabel("Vendor:"))
        self.vendor_combo = QComboBox()
        self.vendor_combo.addItems(["Cisco", "H3C", "Juniper", "Huawei"])
        vendor_layout.addWidget(self.vendor_combo)
        connection_layout.addLayout(vendor_layout)

        # Credentials
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("Username:"))
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Optional username")
        user_layout.addWidget(self.username_edit)
        connection_layout.addLayout(user_layout)

        pass_layout = QHBoxLayout()
        pass_layout.addWidget(QLabel("Password:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Optional password")
        pass_layout.addWidget(self.password_edit)
        connection_layout.addLayout(pass_layout)

        # Option: Send credentials to CLI for login
        cli_login_layout = QHBoxLayout()
        self.cli_login_checkbox = QCheckBox("Send credentials to CLI for login")
        self.cli_login_checkbox.setToolTip("If enabled, after connecting the app will send the username and password directly to the device CLI.")
        cli_login_layout.addWidget(self.cli_login_checkbox)
        connection_layout.addLayout(cli_login_layout)
        
        # Connection buttons
        button_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.on_connect_clicked)
        button_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.on_disconnect_clicked)
        self.disconnect_btn.setEnabled(False)
        button_layout.addWidget(self.disconnect_btn)
        
        connection_layout.addLayout(button_layout)
        
        # Refresh ports button
        self.refresh_ports_btn = QPushButton("Refresh Ports")
        self.refresh_ports_btn.clicked.connect(self.refresh_serial_ports)
        connection_layout.addWidget(self.refresh_ports_btn)
        
        layout.addStretch()
        
        # Connect session manager signals
        self.session_manager.session_selected.connect(self.on_session_selected)
        self.session_manager.session_created.connect(self.on_session_created)
        self.session_manager.session_ended.connect(self.on_session_ended)
        
        return panel
    
    def create_center_panel(self) -> QWidget:
        """Create center panel with terminal and chat"""
        # Create terminal widget
        self.terminal_widget = TerminalWidget(self.app)
        
        return self.terminal_widget
    
    def create_right_panel(self) -> QWidget:
        """Create right panel with status and information"""
        # Create chat widget
        self.chat_widget = ChatWidget(self.app)
        
        return self.chat_widget
    
    def setup_menu_bar(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("File")
        
        new_session_action = QAction("New Session", self)
        new_session_action.setShortcut("Ctrl+N")
        new_session_action.triggered.connect(self.on_new_session)
        file_menu.addAction(new_session_action)
        
        open_session_action = QAction("Open Session", self)
        open_session_action.setShortcut("Ctrl+O")
        open_session_action.triggered.connect(self.on_open_session)
        file_menu.addAction(open_session_action)

        save_session_action = QAction("Save Session", self)
        save_session_action.triggered.connect(self.on_save_session)
        file_menu.addAction(save_session_action)

        load_session_action = QAction("Load Session", self)
        load_session_action.triggered.connect(self.on_load_session)
        file_menu.addAction(load_session_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit Menu
        edit_menu = menubar.addMenu("Edit")
        
        preferences_action = QAction("Preferences", self)
        preferences_action.setShortcut("Ctrl+,")
        preferences_action.triggered.connect(self.on_preferences)
        edit_menu.addAction(preferences_action)
        
        # View Menu
        view_menu = menubar.addMenu("View")
        
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.on_refresh)
        view_menu.addAction(refresh_action)
        
        # Tools Menu
        tools_menu = menubar.addMenu("Tools")

        discover_devices_action = QAction("Discover Devices", self)
        discover_devices_action.triggered.connect(self.on_discover_devices)
        tools_menu.addAction(discover_devices_action)

        import_configs_action = QAction("Import Configs", self)
        import_configs_action.triggered.connect(self.on_import_configs)
        tools_menu.addAction(import_configs_action)

        # Fetch Device Info action
        fetch_device_info_action = QAction("Fetch Device Info", self)
        fetch_device_info_action.triggered.connect(self.on_fetch_device_info)
        tools_menu.addAction(fetch_device_info_action)
        
        # Help Menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.on_about)
        help_menu.addAction(about_action)
        
        help_action = QAction("Help", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.on_help)
        help_menu.addAction(help_action)
    
    def setup_tool_bar(self):
        """Setup tool bar"""
        toolbar = self.addToolBar("Main")
        
        # Connect/Disconnect actions
        self.connect_action = QAction("Connect", self)
        self.connect_action.triggered.connect(self.on_connect_clicked)
        toolbar.addAction(self.connect_action)
        
        self.disconnect_action = QAction("Disconnect", self)
        self.disconnect_action.triggered.connect(self.on_disconnect_clicked)
        self.disconnect_action.setEnabled(False)
        toolbar.addAction(self.disconnect_action)
        
        toolbar.addSeparator()
        
        # Clear terminal
        clear_action = QAction("Clear Terminal", self)
        clear_action.triggered.connect(self.terminal_widget.clear_terminal)
        toolbar.addAction(clear_action)
        
        # Export session
        export_action = QAction("Export Session", self)
        export_action.triggered.connect(self.on_export_session)
        toolbar.addAction(export_action)
    
    def setup_status_bar(self):
        """Setup status bar"""
        # Create status bar
        status_bar = QStatusBar()
        
        # Create custom status bar widget
        self.status_bar_widget = StatusBarWidget(self.app)
        
        # Add the widget to the status bar
        status_bar.addWidget(self.status_bar_widget, 1)
        
        # Set the status bar
        self.setStatusBar(status_bar)
    
    def connect_signals(self):
        """Connect application signals"""
        # Connect to application signals
        self.app.connection_status_changed.connect(self.on_connection_status_changed)
        self.app.session_created.connect(self.on_session_created)
        self.app.session_ended.connect(self.on_session_ended)
        self.app.ai_response_received.connect(self.on_ai_response_received)
        self.app.error_occurred.connect(self.on_error_occurred)
        
        # Connect terminal signals
        if hasattr(self, 'terminal_widget'):
            self.terminal_widget.command_sent.connect(self.on_command_sent)
        
        # Connect chat signals
        if hasattr(self, 'chat_widget'):
            self.chat_widget.query_sent.connect(self.on_ai_query_sent)
    
    def refresh_serial_ports(self):
        """Refresh available serial ports"""
        self.port_combo.clear()
        
        # Get available ports from serial service
        if self.app.serial_service:
            ports = self.app.serial_service.get_available_ports()
            for port in ports:
                self.port_combo.addItem(port["device"], port)
        
        if self.port_combo.count() == 0:
            self.port_combo.addItem("No ports available")
    
    @Slot()
    def on_connect_clicked(self):
        """Handle connect button click"""
        port = self.port_combo.currentText()
        vendor = self.vendor_combo.currentText().lower()
        baud_rate = 9600  # Default baud rate
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if port and port != "No ports available":
            self.set_connection_status("Connecting...")
            
            # Emit connect requested signal
            self.connect_requested.emit(port, vendor, baud_rate, username, password)
    
    @Slot()
    def on_disconnect_clicked(self):
        """Handle disconnect button click"""
        self.set_connection_status("Disconnecting...")
        
        # Emit disconnect requested signal
        self.disconnect_requested.emit()
    
    @Slot()
    def on_new_session(self):
        """Handle new session"""
        self.session_manager.create_new_session()
    
    @Slot()
    def on_open_session(self):
        """Handle open session"""
        self.session_manager.open_session()
    
    @Slot()
    def on_save_session(self):
        self.save_session_requested.emit()

    @Slot()
    def on_load_session(self):
        self.load_session_requested.emit()

    @Slot()
    def on_preferences(self):
        """Handle preferences dialog"""
        try:
            if not self.preferences_dialog:
                self.preferences_dialog = PreferencesDialog(self.config, self)
                self.preferences_dialog.settings_changed.connect(self.on_settings_changed)
            self.preferences_dialog.show()
        except Exception as e:
            self.logger.error(f"Failed to open Preferences dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open Preferences dialog: {str(e)}")

    @Slot()
    def on_settings_changed(self):
        """Handle settings changed from preferences dialog"""
        self.logger.info("Settings changed via preferences dialog")
        # Notify the application to reload config or reinitialize services if needed
        # This is a placeholder for any reactive logic you might need
        QMessageBox.information(self, "Settings Updated", "Application settings have been updated. Some changes may require a restart to take full effect.")
    
    @Slot()
    def on_refresh(self):
        """Handle refresh"""
        self.refresh_serial_ports()
    
    @Slot()
    def on_discover_devices(self):
        """Handle discover devices"""
        # TODO: Implement device discovery
        QMessageBox.information(self, "Discover Devices", "Device discovery not implemented yet.")
    
    @Slot()
    def on_import_configs(self):
        """Handle import configs"""
        # TODO: Implement config import
        QMessageBox.information(self, "Import Configs", "Config import not implemented yet.")

    @Slot()
    def on_fetch_device_info(self):
        """Fetch device information via Application"""
        if not self.app.is_connected:
            QMessageBox.warning(self, "Not Connected", "Connect to a device first.")
            return
        asyncio.create_task(self.app.fetch_device_info())
    
    @Slot()
    def on_export_session(self):
        """Handle export session"""
        self.session_manager.export_current_session()
    
    @Slot()
    def on_about(self):
        """Handle about"""
        QMessageBox.about(
            self,
            "About NetworkSwitch AI Assistant",
            "NetworkSwitch AI Assistant v1.0\n\n"
            "An intelligent network device management tool with AI assistance.\n\n"
            "Features:\n"
            "• Multi-vendor device support (Cisco, H3C, Juniper, Huawei)\n"
            "• AI-powered troubleshooting and configuration assistance\n"
            "• Real-time terminal access\n"
            "• Session management and logging\n"
            "• Cross-vendor command mapping"
        )
    
    @Slot()
    def on_help(self):
        """Handle help"""
        # TODO: Implement help system
        QMessageBox.information(self, "Help", "Help system not implemented yet.")
    
    @Slot(str, str)
    def on_error_occurred(self, error_type: str, error_message: str):
        """Handle error occurrence"""
        self.logger.error(f"Error occurred: {error_type} - {error_message}")
        QMessageBox.critical(self, f"Error: {error_type}", error_message)
    
    def send_quick_command(self, command: str):
        """Send quick command to terminal"""
        # Map friendly names to actual commands
        command_map = {
            "Show Version": "show version",
            "Show Interfaces": "show interfaces",
            "Show VLAN": "show vlan",
            "Show IP Route": "show ip route",
            "Show Running Config": "show running-config"
        }
        
        actual_command = command_map.get(command, command)
        self.terminal_widget.send_command(actual_command)
    
    @Slot(str, bool)
    def on_connection_status_changed(self, status: str, connected: bool):
        """Handle connection status change"""
        self.set_connection_status(status)
        
        # Update button states
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        self.connect_action.setEnabled(not connected)
        self.disconnect_action.setEnabled(connected)
        
        # Update vendor combo based on connection
        self.vendor_combo.setEnabled(not connected)
    
    @Slot(str)
    def on_session_created(self, session_id: str):
        """Handle session created"""
        if hasattr(self, 'status_message_label'):
            self.status_message_label.setText(f"Session created: {session_id}")
    
    @Slot(str)
    def on_session_ended(self, session_id: str):
        """Handle session ended"""
        if hasattr(self, 'status_message_label'):
            self.status_message_label.setText(f"Session ended: {session_id}")
    
    @Slot(str)
    def on_session_selected(self, session_id: str):
        """Handle session selected"""
        if hasattr(self, 'status_message_label'):
            self.status_message_label.setText(f"Session selected: {session_id}")
        # TODO: Update terminal and chat widgets with selected session data
        # This will be implemented when session switching functionality is added
    
    @Slot(str, str)
    def on_command_sent(self, command: str):
        """Handle command sent"""
        if hasattr(self, 'status_message_label'):
            self.status_message_label.setText(f"Command sent: {command}")
    
    @Slot(str, str)
    def on_ai_query_sent(self, query: str):
        """Handle AI query sent"""
        if hasattr(self, 'status_message_label'):
            self.status_message_label.setText("AI query sent...")
    
    @Slot(str, str)
    def on_ai_response_received(self, query: str, response: str):
        """Handle AI response received"""
        if hasattr(self, 'status_message_label'):
            self.status_message_label.setText("AI response received")
    
    def set_connection_status(self, status: str):
        """Set connection status"""
        # Update status bar widget if available
        if hasattr(self, 'status_bar_widget'):
            self.status_bar_widget.set_connection_status(status)
    
    def create_center_panel(self) -> QWidget:
        """Create center panel with terminal"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # Terminal Tab
        self.terminal_widget = TerminalWidget(self.app)
        tab_widget.addTab(self.terminal_widget, "Terminal")
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """Create right panel with AI chat"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # AI Chat Tab
        self.chat_widget = ChatWidget(self.app)
        tab_widget.addTab(self.chat_widget, "AI Assistant")
        
        return panel
    
    def update_connection_form(self, session_data: dict):
        """Update connection form with data from a loaded session JSON."""
        # Connection: port and vendor
        connection_info = session_data.get('connection', {})
        device_info = session_data.get('device_info', {})

        com_port = connection_info.get('com_port', '')
        if com_port:
            self.port_combo.setCurrentText(com_port)

        vendor = device_info.get('vendor', '')
        if vendor:
            # Vendor combo contains capitalized names; normalize
            self.vendor_combo.setCurrentText(str(vendor).capitalize())

        # Credentials
        credentials = session_data.get('credentials', {})
        if isinstance(credentials, dict):
            self.username_edit.setText(credentials.get('username', '') or '')
            self.password_edit.setText(credentials.get('password', '') or '')

    def init_widgets(self):
        """Initialize widgets"""
        # Initialize widgets with application
        if hasattr(self, 'session_manager'):
            self.session_manager.app = self.app
        if hasattr(self, 'terminal_widget'):
            self.terminal_widget.app = self.app
        if hasattr(self, 'chat_widget'):
            self.chat_widget.app = self.app
        if hasattr(self, 'status_bar_widget'):
            self.status_bar_widget.app = self.app
    
    def update_time(self):
        """Update time display"""
        if hasattr(self, 'status_bar_widget'):
            self.status_bar_widget.update_time()

    def update_status(self):
        """Update status information"""
        # Update system info
        uptime = datetime.utcnow() - self.app.start_time
        system_info = f"""
Uptime: {str(uptime).split('.')[0]}
Sessions: {len(self.app.session_service.active_sessions)}
        """.strip()
        
        if hasattr(self, 'system_info_text'):
            self.system_info_text.setPlainText(system_info)
    
    def closeEvent(self, event):
        """Handle window close event"""
        reply = QMessageBox.question(
            self,
            "Exit Confirmation",
            "Are you sure you want to exit NetworkSwitch AI Assistant?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Stop application
            asyncio.create_task(self.app.stop())
            event.accept()
        else:
            event.ignore()

