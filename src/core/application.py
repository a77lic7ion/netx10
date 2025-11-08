"""
Main Application Controller
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from PySide6.QtWidgets import QMainWindow, QMessageBox, QFileDialog
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QIcon, QFont

from gui.main_window import MainWindow
from services.session_service import SessionService
from services.ai_service import AIService
from services.serial_service import SerialService
from services.database_service import DatabaseService
from core.config import AppConfig
from core.constants import VendorType
from utils.logging_utils import get_logger

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
        # Fallback file tracing during app initialization
        try:
            trace_path = Path(__file__).resolve().parent.parent / "logs" / "startup_trace.txt"
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write("[application] __init__ start\n")
        except Exception:
            trace_path = None
        self.config = config
        self._services_initialized = False
        self._current_session_id: Optional[str] = None
        self.start_time = datetime.utcnow()
        self.current_device = None
        # Track all asyncio tasks to allow graceful shutdown
        self._pending_tasks: set[asyncio.Task] = set()
        # Serialize Enter key dispatches to avoid concurrent coroutine reentry
        self._send_enter_lock = asyncio.Lock()
        
        # Initialize services
        try:
            if trace_path:
                with open(trace_path, "a", encoding="utf-8") as f:
                    f.write("[application] Initializing services...\n")
        except Exception:
            pass
        self._initialize_services()
        try:
            if trace_path:
                with open(trace_path, "a", encoding="utf-8") as f:
                    f.write("[application] Services initialized. Setting up UI...\n")
        except Exception:
            pass
        
        # Setup UI
        self._setup_ui()
        try:
            if trace_path:
                with open(trace_path, "a", encoding="utf-8") as f:
                    f.write("[application] UI setup complete. Connecting signals...\n")
        except Exception:
            pass
        
        # Connect signals
        self._connect_signals()
        try:
            if trace_path:
                with open(trace_path, "a", encoding="utf-8") as f:
                    f.write("[application] Signals connected. Setting up auto-save...\n")
        except Exception:
            pass
        
        # Setup auto-save timer
        self._setup_auto_save()
        try:
            if trace_path:
                with open(trace_path, "a", encoding="utf-8") as f:
                    f.write("[application] Auto-save setup complete. Initialization done.\n")
        except Exception:
            pass
        
        logger.info("NetworkSwitch AI Assistant initialized successfully")
    
    def _initialize_services(self):
        """Initialize application services (construct synchronously, init asynchronously)"""
        try:
            # Construct services synchronously
            self.db = DatabaseService(self.config)
            self.serial_service = SerialService(self.config.serial)
            self.session_service = SessionService(self.db, self.serial_service, self.config)
            self.ai_service = AIService(self.config.ai)

            # Forward serial data to terminal output
            self.serial_service.data_listener = lambda data: self.terminal_data_received.emit(data)

            # Schedule async initialization after event loop starts
            try:
                QTimer.singleShot(0, lambda: self._create_tracked_task(self._initialize_services_async()))
            except Exception:
                # Fallback: create task directly; may fail if no running loop
                self._create_tracked_task(self._initialize_services_async())

            self._services_initialized = True
            logger.info("Services constructed; async initialization scheduled")

        except Exception as e:
            logger.error(f"Failed to construct services: {e}")
            self._show_error("Initialization Error", f"Failed to construct services: {e}")
    
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

    async def _initialize_services_async(self):
        """Perform asynchronous service initialization once the event loop is running"""
        try:
            self.ai_status_changed.emit("Initializing", "AI service is starting...")

            # Initialize database
            ok = await self.db.initialize()
            if not ok:
                logger.error("Failed to initialize the database.")
                self._show_error("Initialization Error", "Failed to initialize the database.")
                return

            # Initialize AI service
            await self._initialize_ai_service()

            logger.info("All services initialized successfully")
        except Exception as e:
            logger.error(f"Async service initialization failed: {e}")
            self._show_error("Initialization Error", f"Async service initialization failed: {e}")
    
    def _connect_signals(self):
        """Connect UI signals to service slots"""
        # Main window signals
        self.main_window.connect_requested.connect(self._handle_connect_request)
        self.main_window.disconnect_requested.connect(self._handle_disconnect_request)
        self.main_window.command_sent.connect(self._handle_command_sent)
        self.main_window.ai_query_sent.connect(self._handle_ai_query)
        self.main_window.save_session_requested.connect(self.save_session)
        self.main_window.load_session_requested.connect(self.load_session)
        
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
    
    async def _initialize_ai_service(self):
        """Asynchronously initialize the AI service and update status."""
        try:
            initialized = await self.ai_service.initialize()
            if initialized:
                self.ai_status_changed.emit("Idle", "AI service is ready.")
            else:
                self.ai_status_changed.emit("Error", "AI service failed to initialize.")
        except Exception as e:
            logger.error(f"Unhandled error during AI service initialization: {e}")
            self.ai_status_changed.emit("Error", "An unexpected error occurred during AI initialization.")
    
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
    
    @Slot(str, str, int, str, str)
    def _handle_connect_request(self, com_port: str, vendor_type: str, baud_rate: int, username: str, password: str):
        """Handle connection request from UI, including optional credentials"""
        self._create_tracked_task(self._connect_device(com_port, vendor_type, baud_rate, username, password))
    
    @Slot()
    def _handle_disconnect_request(self):
        """Handle disconnection request from UI"""
        self._create_tracked_task(self._disconnect_device())
    
    @Slot(str, str)
    def _handle_command_sent(self, session_id: str, command: str):
        """Handle command sent from UI"""
        self._create_tracked_task(self._execute_command(session_id, command))
    
    @Slot(str, str, str)
    def _handle_ai_query(self, session_id: str, query: str, context: str):
        """Handle AI query from UI"""
        self._create_tracked_task(self._process_ai_query(session_id, query, context))
    
    async def _connect_device(self, com_port: str, vendor_type: str, baud_rate: int, username: str = "", password: str = ""):
        """Connect to network device"""
        self.connection_status_changed.emit("Connecting", f"Connecting to {com_port}...")
        logger.info(f"Attempting to connect to {com_port} at {baud_rate} baud.")

        try:
            logger.info(f"Connecting to {com_port} ({vendor_type}) at {baud_rate} baud")
            
            # Create new session
            session = await self.session_service.create_session(
                com_port=com_port,
                vendor_type=vendor_type,
                baud_rate=baud_rate,
                username=username or None,
                password=password or None
            )
            
            self._current_session_id = session.session_id
            
            # Connect to device
            success = await self.session_service.connect_session(session.session_id)

            if success:
                logger.info(f"Successfully connected to {com_port}")
                self.connection_status_changed.emit("Connected", f"Connected to {com_port}")
                self.session_created.emit(session.session_id, session.vendor_type)

                # If enabled in UI, perform prompt-based credential sending
                try:
                    cli_login_enabled = hasattr(self.main_window, 'cli_login_checkbox') and self.main_window.cli_login_checkbox.isChecked()
                    if cli_login_enabled:
                        await self._perform_prompt_login(session.session_id, session.username or "", session.password or "")
                except Exception as cli_err:
                    logger.warning(f"Prompt-based CLI login failed: {cli_err}")
                    self.error_occurred.emit("Login Error", f"Automated login failed: {cli_err}")
            else:
                logger.error(f"Failed to connect to {com_port}")
                error_msg = session.error_message if session and session.error_message else f"Failed to connect to {com_port}"
                self.error_occurred.emit("Connection Error", error_msg)
                self.connection_status_changed.emit("Disconnected", f"Failed to connect to {com_port}")

        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.error_occurred.emit("Connection Error", str(e))
            self.connection_status_changed.emit("Disconnected", "Connection failed")
        finally:
            # In case of failure, ensure status is reset
            # This is a fallback, success/fail cases should set it explicitly
            pass

    async def _disconnect_device(self):
        """Disconnect from current device"""
        if not self._current_session_id:
            return

        session_id_to_disconnect = self._current_session_id
        self.connection_status_changed.emit("Disconnecting", f"Disconnecting from session {session_id_to_disconnect}...")
        logger.info(f"Disconnecting from session {session_id_to_disconnect}")

        try:
            await self.session_service.disconnect_session(session_id_to_disconnect)
            
            self._current_session_id = None
            
            logger.info("Successfully disconnected")
            self.session_ended.emit(session_id_to_disconnect)
            self.connection_status_changed.emit("Disconnected", "Disconnected")
            
        except Exception as e:
            logger.error(f"Disconnection error: {e}")
            self.error_occurred.emit("Disconnection Error", str(e))
            self.connection_status_changed.emit("Disconnected", "Disconnection failed")
        finally:
            # Ensure session ID is cleared even if disconnection fails partway
            self._current_session_id = None

    @Slot()
    def save_session(self):
        """Save the current session to a file."""
        if not self._current_session_id:
            self._show_error("Save Error", "No active session to save.")
            return

        session_data = self.export_session(self._current_session_id)
        if not session_data:
            self._show_error("Save Error", "Failed to export session data.")
            return

        # Add AI history
        session_data['ai_history'] = self.ai_service.get_memory_summary()

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Session",
            self.config.data_dir,
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(session_data, f, indent=4)
                logger.info(f"Session saved to {file_path}")
            except Exception as e:
                logger.error(f"Failed to save session: {e}")
                self._show_error("Save Error", f"Failed to save session: {e}")

    @Slot()
    def load_session(self):
        """Load a session from a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Session",
            self.config.data_dir,
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    session_data = json.load(f)
                
                # This is a simplified load. A real implementation would need to
                # properly restore the session in the services, handle UI updates,
                # and potentially reconnect to the device.
                
                # For now, we'll just log the loaded data.
                logger.info(f"Session loaded from {file_path}")
                
                # Populate connection form from loaded data if method exists
                try:
                    if hasattr(self.main_window, 'update_connection_form') and callable(getattr(self.main_window, 'update_connection_form')):
                        self.main_window.update_connection_form(session_data)
                except Exception as form_err:
                    logger.warning(f"Failed to update connection form from session: {form_err}")
                
                # Example of restoring parts of the session
                if 'session_id' in session_data:
                    self._current_session_id = session_data['session_id']
                    
                if 'ai_history' in session_data:
                    # Restore AI chat memory from saved session
                    try:
                        self.ai_service.clear_conversation_memory()
                        self.ai_service.load_memory_summary(session_data['ai_history'])
                    except Exception as mem_err:
                        logger.warning(f"Failed to load AI memory from session: {mem_err}")
                    
                # Re-create session in session_service (conceptual)
                # await self.session_service.recreate_session(session_data)

                self.main_window.terminal.append(f"Loaded session: {session_data.get('session_id')}")
                if 'commands' in session_data:
                    for cmd in session_data['commands']:
                        self.main_window.terminal.append(f"> {cmd['command']}")
                        self.main_window.terminal.append(cmd['output'])

            except Exception as e:
                logger.error(f"Failed to load session: {e}")
                self._show_error("Load Error", f"Failed to load session: {e}")

    async def _perform_prompt_login(self, session_id: str, username: str, password: str):
        """Send credentials based on detected login prompts from terminal data."""
        self.ai_status_changed.emit("Processing", "Attempting automated login...")
        logger.info(f"Starting automated login for session: {session_id}")

        try:
            # Helper to wait for prompt text on terminal stream
            async def _wait_for_prompt(substrs, timeout: float = 8.0) -> bool:
                evt = asyncio.Event()
                matched = {"hit": False}

                def _on_data(data: str):
                    try:
                        dl = data.lower()
                        for s in substrs:
                            if s in dl:
                                matched["hit"] = True
                                try:
                                    evt.set()
                                except Exception:
                                    pass
                                break
                    except Exception:
                        pass

                try:
                    self.terminal_data_received.connect(_on_data)
                    try:
                        await asyncio.wait_for(evt.wait(), timeout=timeout)
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout waiting for prompts: {substrs}")
                        return False
                    return matched["hit"]
                finally:
                    try:
                        self.terminal_data_received.disconnect(_on_data)
                    except Exception:
                        pass

            # Nudge device to show prompts
            try:
                await self.session_service.write_to_session(session_id, "\r\n")
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.warning(f"Failed to send initial Enter nudge: {e}")

            # Username prompt
            if username:
                username_prompts = ["username", "login:", "user:", "> username", "> login", "] username"]
                logger.info("Waiting for username prompt...")
                if await _wait_for_prompt(username_prompts, timeout=10.0):
                    logger.info("Username prompt detected. Sending username.")
                    await self.session_service.write_to_session(session_id, f"{username}\r\n")
                    await asyncio.sleep(0.3)
                else:
                    logger.warning("Username prompt not detected.")

            # Password prompt
            if password:
                password_prompts = ["password", "passwd:"]
                logger.info("Waiting for password prompt...")
                if await _wait_for_prompt(password_prompts, timeout=10.0):
                    logger.info("Password prompt detected. Sending password.")
                    await self.session_service.write_to_session(session_id, f"{password}\r\n")
                    await asyncio.sleep(0.3)
                else:
                    logger.warning("Password prompt not detected.")

            # Final enter to settle into CLI
            try:
                await self.session_service.send_enter(session_id)
                logger.info("Automated login sequence completed.")
                self.ai_status_changed.emit("Idle", "Login sequence finished.")
            except Exception as e:
                logger.error(f"Failed to send final Enter after login: {e}")
                self.ai_status_changed.emit("Error", "Login failed.")

        except Exception as e:
            logger.error(f"Automated login failed: {e}")
            self.ai_status_changed.emit("Error", "Automated login failed.")
        finally:
            # Ensure status is reset to Idle if it was left in a processing state
            # This is a fallback, individual steps should set status more granularly
            pass

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
        if not self.ai_service.is_initialized():
            self.error_occurred.emit("AI Error", "AI service is not available. Please check configuration.")
            self.ai_status_changed.emit("Error", "AI service is not initialized.")
            return

        self.ai_status_changed.emit("Processing", f"Processing query: {query[:30]}...")
        try:
            logger.info(f"Processing AI query: {query}")
            
            session = await self.session_service.get_session(session_id)
            if not session:
                self.error_occurred.emit("AI Error", "Session not found")
                self.ai_status_changed.emit("Error", "Session not found.")
                return
            
            self.ai_response_started.emit(query)

            # First, try to map simple configuration intents
            cfg_map = self.ai_service.map_config_intent_to_vendor_commands(query, session.vendor_type)
            if cfg_map and isinstance(cfg_map, dict) and cfg_map.get("commands"):
                response_text = cfg_map.get("summary", "Generated configuration sequence.")
                self.ai_response_received.emit(session_id, response_text)
                self.ai_suggestion_received.emit(cfg_map["commands"])
                self.ai_response_ended.emit()
                self.ai_status_changed.emit("Idle", "AI query completed.")
                return

            # Then, try quick vendor-specific commands
            quick_cmd = self.ai_service.map_query_to_vendor_command(query, session.vendor_type)
            if quick_cmd:
                from core.constants import VendorType
                try:
                    display_vendor = VendorType(session.vendor_type).name
                except ValueError:
                    display_vendor = str(session.vendor_type).upper()
                
                response_text = f"For {display_vendor}, use: `{quick_cmd}`"
                self.ai_response_received.emit(session_id, response_text)
                self.ai_suggestion_received.emit([quick_cmd])
                self.ai_response_ended.emit()
                self.ai_status_changed.emit("Idle", "AI query completed.")
                return

            # Fallback to the full AI service for complex queries
            from models.device_models import AIQuery, AIResponse
            ai_query = AIQuery(
                session_id=session_id,
                query=query,
                context=context,
                query_type=self.main_window.get_ai_query_type(),
                vendor=session.vendor_type
            )
            
            response: AIResponse = await self.ai_service.process_query(ai_query)
            
            self.ai_response_received.emit(session_id, response.response_text)
            
            if response.suggestions:
                self.ai_suggestion_received.emit(response.suggestions)
            
            timestamp = datetime.utcnow().isoformat()
            self.ai_interaction_logged.emit(
                session_id, query, response.response_text, ai_query.query_type, timestamp
            )
            
        except Exception as e:
            logger.error(f"AI query processing error: {e}")
            self.error_occurred.emit("AI Error", str(e))
            self.ai_status_changed.emit("Error", "AI query failed.")
        finally:
            self.ai_response_ended.emit()
            self.ai_status_changed.emit("Idle", "AI query finished.")

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
            
            disconnect_task = None
            close_task = None

            # Disconnect any active sessions
            if self._current_session_id:
                disconnect_task = self._create_tracked_task(self._disconnect_device())
            
            # Save application state
            if self._services_initialized:
                # Ensure database close runs in the event loop if it's async
                try:
                    close_task = self._create_tracked_task(self.db.close())
                except TypeError:
                    # Fallback if close is synchronous
                    self.db.close()

                # Cancel any other pending tasks to avoid "Task was destroyed" warnings
                for t in list(self._pending_tasks):
                    if t is not disconnect_task and t is not close_task:
                        try:
                            t.cancel()
                        except Exception as e:
                            logger.warning(f"Failed to cancel task {t}: {e}")
            
            logger.info("Application closed successfully")
            event.accept()
            
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")
            event.accept()

    def _create_tracked_task(self, coro) -> asyncio.Task:
        """Create and track an asyncio task to manage lifecycle and shutdown."""
        task = asyncio.create_task(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(lambda t: self._pending_tasks.discard(t))
        return task

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
        if not session:
            return []
        results = []
        for cmd in session.commands:
            if hasattr(cmd, "command"):
                results.append({
                    "command": cmd.command,
                    "output": getattr(cmd, "output", ""),
                    "timestamp": cmd.timestamp.isoformat() if hasattr(cmd, "timestamp") else datetime.utcnow().isoformat(),
                    "success": getattr(cmd, "success", True)
                })
            elif isinstance(cmd, dict):
                results.append({
                    "command": cmd.get("command", ""),
                    "output": cmd.get("output", ""),
                    "timestamp": cmd.get("timestamp", datetime.utcnow().isoformat()),
                    "success": cmd.get("success", True)
                })
            elif isinstance(cmd, str):
                results.append({
                    "command": cmd,
                    "output": "",
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": True
                })
        return results

    def get_session_ai_interactions(self, session_id: str):
        """Get AI interactions for a session"""
        # This would come from AI service in a real implementation
        # For now, return empty list
        return []

    def export_session(self, session_id: str):
        """Export session data"""
        session = self.session_service.active_sessions.get(session_id)
        if not session:
            return None
        return {
            "session_id": session.session_id,
            "device_info": {
                "vendor": session.vendor_type,
                "model": getattr(session, "device_model", None),
                "firmware": getattr(session, "os_version", None),
                "serial": (session.vendor_specific_data.get("serial_number") if isinstance(getattr(session, "vendor_specific_data", None), dict) else None)
            },
            "connection": {
                "com_port": session.com_port,
                "baud_rate": session.baud_rate
            },
            "credentials": {
                "username": getattr(session, "username", None),
                "password": getattr(session, "password", None)
            },
            "status": session.status.value if hasattr(session.status, "value") else str(session.status),
            "created_at": session.start_time.isoformat() if getattr(session, "start_time", None) else datetime.utcnow().isoformat(),
            "connected_at": session.connected_at.isoformat() if session.connected_at else None,
            "disconnected_at": session.disconnected_at.isoformat() if session.disconnected_at else None,
            "commands": self.get_session_commands(session_id),
            "command_count": len(session.commands)
        }

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

    async def send_enter(self, char: str = '\r'):
        """Send raw newline to the device (simulate Enter)."""
        if not self._current_session_id:
            self.error_occurred.emit("Command Error", "No active session")
            return
        async with self._send_enter_lock:
            result = await self.session_service.send_enter(self._current_session_id, char)
        if not result.success:
            self.error_occurred.emit("Command Error", result.error or "Unknown error")

    def queue_enter(self):
        """Schedule sending Enter using tracked tasks."""
        self._create_tracked_task(self.send_enter())

    async def fetch_device_info(self) -> Dict[str, Any]:
        """Fetch device info for the current session and allow naming."""
        if not self._current_session_id:
            self.error_occurred.emit("Device Info Error", "No active session")
            return {}

        info = await self.session_service.fetch_device_info(self._current_session_id)
        if not info:
            self.error_occurred.emit("Device Info Error", "Failed to retrieve device information")
            return {}
        raw = info.get("raw_output")
        if raw:
            self.terminal_data_received.emit(raw)
        else:
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

    async def send_ai_query(self, query: str, context: str):
        """Public helper to send an AI query for the current session."""
        if not self._current_session_id:
            self.error_occurred.emit("AI Error", "No active session")
            return
        self._create_tracked_task(self._process_ai_query(self._current_session_id, query, context))
