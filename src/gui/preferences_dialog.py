"""
Preferences Dialog for NetworkSwitch AI Assistant
"""

import json
import requests
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTextEdit, QGroupBox, QTabWidget,
    QMessageBox, QWidget
)
from PySide6.QtCore import Qt, Signal
from core.config import AppConfig
from utils.logging_utils import get_logger


class PreferencesDialog(QDialog):
    """Preferences dialog for configuring application settings"""
    
    settings_changed = Signal()
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.logger = get_logger("preferences_dialog")
        self.setWindowTitle("Preferences")
        self.setModal(False)
        self.resize(600, 400)
        
        # Initialize UI
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # AI Provider tab
        ai_tab = self.create_ai_tab()
        tab_widget.addTab(ai_tab, "AI Providers")
        
        # General tab (placeholder)
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.addWidget(QLabel("General settings coming soon..."))
        tab_widget.addTab(general_tab, "General")
        
        # Button layout
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)
        
        # Test connection button
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_btn)
        
        button_layout.addStretch()
        
        # Save and Cancel buttons
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
    
    def create_ai_tab(self):
        """Create AI provider configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Provider selection
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("Default Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["ollama", "openai", "anthropic", "xai", "mistral", "gemini"])
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        provider_layout.addStretch()
        layout.addLayout(provider_layout)
        
        # Provider configuration group
        self.provider_group = QGroupBox("Provider Configuration")
        group_layout = QVBoxLayout(self.provider_group)
        
        # API Key
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(QLabel("API Key:"))
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        api_key_layout.addWidget(self.api_key_edit)
        group_layout.addLayout(api_key_layout)
        
        # Base URL
        base_url_layout = QHBoxLayout()
        base_url_layout.addWidget(QLabel("Base URL:"))
        self.base_url_edit = QLineEdit()
        base_url_layout.addWidget(self.base_url_edit)
        group_layout.addLayout(base_url_layout)
        
        # Model name
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_edit = QLineEdit()
        model_layout.addWidget(self.model_edit)
        group_layout.addLayout(model_layout)
        
        layout.addWidget(self.provider_group)
        layout.addStretch()
        
        return tab
    
    def on_provider_changed(self, provider):
        """Handle provider selection change"""
        # Update UI based on provider
        if provider == "ollama":
            self.base_url_edit.setText("http://localhost:11434")
            self.model_edit.setText("llama2")
            self.api_key_edit.setEnabled(False)
        elif provider == "openai":
            self.base_url_edit.setText("https://api.openai.com/v1")
            self.model_edit.setText("gpt-3.5-turbo")
            self.api_key_edit.setEnabled(True)
        elif provider == "anthropic":
            self.base_url_edit.setText("https://api.anthropic.com")
            self.model_edit.setText("claude-3-sonnet-20240229")
            self.api_key_edit.setEnabled(True)
        elif provider == "xai":
            self.base_url_edit.setText("https://api.x.ai/v1")
            self.model_edit.setText("grok-2-mini")
            self.api_key_edit.setEnabled(True)
        elif provider == "mistral":
            self.base_url_edit.setText("https://api.mistral.ai/v1")
            self.model_edit.setText("mistral-small-latest")
            self.api_key_edit.setEnabled(True)
        elif provider == "gemini":
            # Gemini REST base URL
            self.base_url_edit.setText("https://generativelanguage.googleapis.com")
            self.model_edit.setText("gemini-1.5-flash")
            self.api_key_edit.setEnabled(True)
    
    def load_settings(self):
        """Load current settings"""
        # Load AI provider settings
        ai_config = self.config.ai
        if ai_config.default_provider in ["ollama", "openai", "anthropic", "xai", "mistral", "gemini"]:
            self.provider_combo.setCurrentText(ai_config.default_provider)
        
        # Load provider-specific settings
        provider_name = self.provider_combo.currentText()
        if provider_name in ai_config.providers:
            provider_config = ai_config.providers[provider_name]
            self.api_key_edit.setText(provider_config.api_key or "")
            # Ensure non-str values like HttpUrl are converted to string
            self.base_url_edit.setText(str(provider_config.base_url) if provider_config.base_url else "")
            self.model_edit.setText(provider_config.model or "")
    
    def save_settings(self):
        """Save settings"""
        try:
            # Update AI provider settings
            provider_name = self.provider_combo.currentText()
            self.config.ai.default_provider = provider_name
            
            # Update provider configuration
            if provider_name not in self.config.ai.providers:
                from core.config import ProviderConfig
                self.config.ai.providers[provider_name] = ProviderConfig()
            
            provider_config = self.config.ai.providers[provider_name]
            provider_config.api_key = self.api_key_edit.text().strip() or None
            provider_config.base_url = self.base_url_edit.text().strip() or None
            provider_config.model = self.model_edit.text().strip() or None
            
            # Save configuration
            self.config.save()
            
            # Emit settings changed signal
            self.settings_changed.emit()
            
            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
            self.accept()
            
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
    
    def test_connection(self):
        """Test connection to AI provider"""
        try:
            provider_name = self.provider_combo.currentText()
            api_key = (self.api_key_edit.text().strip() or None) or ""
            base_url = (self.base_url_edit.text().strip() or None) or ""

            if not base_url:
                QMessageBox.warning(self, "Missing Base URL", "Please set a base URL for the selected provider.")
                return

            # Compose endpoint and headers for model listing
            endpoint = None
            headers = {}
            params = {}

            if provider_name in ("openai", "xai", "mistral"):
                endpoint = base_url.rstrip('/') + "/models"
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            elif provider_name == "anthropic":
                endpoint = base_url.rstrip('/') + "/v1/models"
                headers = {"x-api-key": api_key} if api_key else {}
            elif provider_name == "gemini":
                endpoint = base_url.rstrip('/') + "/v1/models"
                params = {"key": api_key} if api_key else {}
            elif provider_name == "ollama":
                endpoint = base_url.rstrip('/') + "/api/tags"
                headers = {}
            else:
                QMessageBox.critical(self, "Unsupported Provider", f"Provider '{provider_name}' is not supported.")
                return

            # Perform request
            resp = requests.get(endpoint, headers=headers, params=params, timeout=10)
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")

            data = resp.json()

            # Extract model names across providers
            models = []
            if provider_name == "ollama":
                # Ollama returns tags: [{"name": "model"}, ...]
                tags = data if isinstance(data, list) else data.get("models") or data.get("tags") or []
                for t in tags:
                    name = t.get("name") or t.get("model") or t.get("id")
                    if name:
                        models.append(name)
            else:
                # Common shapes: {data: [{id: ...}]}, {models: [...]}
                items = data.get("data") or data.get("models") or []
                for item in items:
                    name = item.get("id") or item.get("name")
                    if name:
                        models.append(name)

            if not models:
                QMessageBox.information(self, "Connection Test", f"Connected to {provider_name} at {endpoint}\nNo models returned.")
                return

            preview = "\n".join(models[:20])
            QMessageBox.information(
                self,
                "Connection Test",
                f"Connected to {provider_name}.\nEndpoint: {endpoint}\n\nAvailable models (first {min(20, len(models))}):\n{preview}"
            )
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            QMessageBox.critical(self, "Connection Test Failed", str(e))
