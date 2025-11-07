from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QMessageBox
from PySide6.QtCore import Signal, Slot

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.application import NetworkSwitchAIApp


class SessionManagerWidget(QWidget):
    """Minimal session manager to list and manage sessions."""

    # Signals expected by MainWindow
    session_selected = Signal(str)
    session_created = Signal(str)
    session_ended = Signal(str)

    def __init__(self, app: 'NetworkSwitchAIApp'):
        super().__init__()
        self.app = app
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.session_list = QListWidget()
        layout.addWidget(self.session_list)

        # Populate existing active sessions
        self.refresh_sessions()
        self.session_list.currentItemChanged.connect(self._on_selection_changed)

    def refresh_sessions(self):
        self.session_list.clear()
        try:
            sessions = self.app.session_service.active_sessions.values() if self.app and self.app.session_service else []
            for s in sessions:
                item = QListWidgetItem(f"{s.session_id} | {s.com_port} | {s.status.value}")
                item.setData(0x0100, s.session_id)  # Qt.UserRole
                self.session_list.addItem(item)
        except Exception:
            pass

    @Slot()
    def create_new_session(self):
        """Emit session_created when a new session is initiated via UI."""
        # This widget does not create sessions directly; delegate to MainWindow/app.
        # Emit a placeholder event to update UI.
        if self.app and self.app.current_session_id:
            self.session_created.emit(self.app.current_session_id)

    @Slot()
    def open_session(self):
        """Placeholder: would load a saved session."""
        QMessageBox.information(self, "Open Session", "Session loading is not implemented yet.")

    @Slot()
    def export_current_session(self):
        """Export current session via app helper if available."""
        if not self.app or not self.app.current_session_id:
            QMessageBox.information(self, "Export Session", "No active session to export.")
            return
        data = self.app.export_session(self.app.current_session_id)
        if data is None:
            QMessageBox.warning(self, "Export Session", "Failed to export session.")
        else:
            QMessageBox.information(self, "Export Session", "Session exported (in-memory). File export coming soon.")

    @Slot('QListWidgetItem', 'QListWidgetItem')
    def _on_selection_changed(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]):
        if current:
            session_id = current.data(0x0100)  # Qt.UserRole
            if session_id:
                self.session_selected.emit(session_id)

