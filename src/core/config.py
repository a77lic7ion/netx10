"""
Application Configuration Management
"""

import os
from pathlib import Path
from datetime import datetime
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Dict, Any


class DatabaseConfig(BaseSettings):
    """Database configuration"""
    url: str = Field(default="sqlite:///network_switch_ai.db", env="DB_URL")
    echo: bool = Field(default=False, env="DB_ECHO")


class ProviderConfig(BaseSettings):
    """Configuration for a single AI provider"""
    api_key: Optional[str] = None
    base_url: Optional[HttpUrl] = None
    model: Optional[str] = None
    timeout: int = 30


class AIConfig(BaseSettings):
    """AI/ML configuration"""
    default_provider: str = Field(default="openai", env="AI_PROVIDER")
    model_name: str = Field(default="gpt-3.5-turbo", env="AI_MODEL_NAME")
    max_tokens: int = Field(default=1000, env="AI_MAX_TOKENS")
    temperature: float = Field(default=0.1, env="AI_TEMPERATURE")
    top_p: float = Field(default=1.0, env="AI_TOP_P")

    # Provider-specific endpoints
    providers: Dict[str, ProviderConfig] = {
        "openai": ProviderConfig(
            base_url="https://api.openai.com/v1",
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        ),
        "ollama": ProviderConfig(
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "llama2")
        ),
        "anthropic": ProviderConfig(
            base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
        ),
        "xai": ProviderConfig(
            base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
            api_key=os.getenv("XAI_API_KEY"),
            model=os.getenv("XAI_MODEL", "grok-2-mini")
        ),
        "mistral": ProviderConfig(
            base_url=os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1"),
            api_key=os.getenv("MISTRAL_API_KEY"),
            model=os.getenv("MISTRAL_MODEL", "mistral-small-latest")
        ),
        "gemini": ProviderConfig(
            base_url=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com"),
            api_key=os.getenv("GEMINI_API_KEY"),
            model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        )
    }


class SerialConfig(BaseSettings):
    """Serial communication configuration"""
    # Common serial parameters used by SerialService/SerialConnection
    baud_rate: int = Field(default=9600, env="DEFAULT_BAUD_RATE")
    data_bits: int = Field(default=8, env="SERIAL_DATA_BITS")
    parity: str = Field(default="N", env="SERIAL_PARITY")
    stop_bits: float = Field(default=1, env="SERIAL_STOP_BITS")
    timeout: float = Field(default=10.0, env="DEFAULT_TIMEOUT")
    write_timeout: float = Field(default=2.0, env="SERIAL_WRITE_TIMEOUT")
    max_retry_attempts: int = Field(default=3, env="MAX_RETRY_ATTEMPTS")


class VendorConfig(BaseSettings):
    """Vendor-specific configuration"""
    config_dir: str = Field(default="config/vendors", env="VENDOR_CONFIG_DIR")
    template_dir: str = Field(default="templates", env="VENDOR_TEMPLATE_DIR")
    auto_detection_timeout: int = Field(default=30, env="VENDOR_DETECTION_TIMEOUT")


class AppConfig(BaseSettings):
    """Main application configuration"""
    
    # Application settings
    app_name: str = "NetworkSwitch AI Assistant"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Window settings
    window_title: str = "NetworkSwitch AI Assistant"
    window_width: int = 1400
    window_height: int = 900
    window_x: Optional[int] = None
    window_y: Optional[int] = None
    
    # UI settings
    theme: str = Field(default="dark", env="UI_THEME")
    font_family: str = Field(default="Consolas", env="UI_FONT_FAMILY")
    font_size: int = Field(default=10, env="UI_FONT_SIZE")
    
    # Sub-configurations
    database: DatabaseConfig = DatabaseConfig()
    ai: AIConfig = AIConfig()
    serial: SerialConfig = SerialConfig()
    vendor: VendorConfig = VendorConfig()
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", env="LOG_FILE")
    log_max_size: int = Field(default=10 * 1024 * 1024, env="LOG_MAX_SIZE")  # 10MB
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")

    # Data directory for session exports and saves
    data_dir: str = Field(default="data", env="DATA_DIR")
    
    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [
            "logs",
            "config/vendors",
            "templates/cisco",
            "templates/h3c", 
            "templates/juniper",
            "templates/huawei",
            "resources/vendors/cisco",
            "resources/vendors/h3c",
            "resources/vendors/juniper",
            "resources/vendors/huawei",
            self.data_dir
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_vendor_config_path(self, vendor: str) -> Path:
        """Get vendor configuration file path"""
        return Path(self.vendor.config_dir) / f"{vendor.lower()}.yaml"
    
    def get_vendor_template_path(self, vendor: str) -> Path:
        """Get vendor template directory path"""
        return Path(self.vendor.template_dir) / vendor.lower()

    def save(self, env_path: Optional[str] = None) -> None:
        """Persist configuration to the .env file, updating AI settings and provider credentials.

        - Merges with existing entries in the env file.
        - Writes keys for general AI settings and each provider: API_KEY, BASE_URL, MODEL.
        """
        # Local import to avoid NameError in environments where module-level imports
        # may be affected by load order or partial imports
        from datetime import datetime as _dt
        # Default to .env; do not rely on deprecated self.Config in pydantic v2
        env_path = env_path or ".env"
        env_file = Path(env_path)

        # Read existing env entries
        existing: Dict[str, str] = {}
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                existing[key.strip()] = value.strip()

        # Update general AI settings
        updates: Dict[str, str] = {
            "AI_PROVIDER": self.ai.default_provider,
            "AI_MODEL_NAME": str(self.ai.model_name),
            "AI_MAX_TOKENS": str(self.ai.max_tokens),
            "AI_TEMPERATURE": str(self.ai.temperature),
            "AI_TOP_P": str(self.ai.top_p),
        }

        # Provider-specific settings
        for name, cfg in self.ai.providers.items():
            prefix = name.upper()
            base_url_val = str(cfg.base_url) if cfg.base_url else ""
            updates[f"{prefix}_API_KEY"] = cfg.api_key or ""
            updates[f"{prefix}_BASE_URL"] = base_url_val
            updates[f"{prefix}_MODEL"] = cfg.model or ""

        # Merge and write
        merged = {**existing, **updates}
        lines = [
            "# Auto-generated by NetworkSwitch AI Assistant",
            f"# Last updated: {_dt.utcnow().isoformat()}Z",
        ]
        for key in sorted(merged.keys()):
            # Quote values containing spaces or special characters
            val = merged[key]
            if any(c in val for c in [' ', '#', '\\', '"']):
                val = '"' + val.replace('"', '\\"') + '"'
            lines.append(f"{key}={val}")

        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


# Global configuration instance
config = AppConfig()
