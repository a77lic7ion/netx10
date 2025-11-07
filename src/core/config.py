"""
Application Configuration Management
"""

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any


class DatabaseConfig(BaseSettings):
    """Database configuration"""
    url: str = Field(default="sqlite:///network_switch_ai.db", env="DB_URL")
    echo: bool = Field(default=False, env="DB_ECHO")


class AIConfig(BaseSettings):
    """AI/ML configuration"""
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    model_name: str = Field(default="gpt-3.5-turbo", env="AI_MODEL_NAME")
    max_tokens: int = Field(default=1000, env="AI_MAX_TOKENS")
    temperature: float = Field(default=0.1, env="AI_TEMPERATURE")
    # Optional Ollama / LLM settings (used by ai_service)
    ollama_url: Optional[str] = Field(default=None, env="OLLAMA_URL")
    top_p: float = Field(default=1.0, env="AI_TOP_P")
    timeout: int = Field(default=30, env="AI_TIMEOUT")


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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
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
            "resources/vendors/huawei"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_vendor_config_path(self, vendor: str) -> Path:
        """Get vendor configuration file path"""
        return Path(self.vendor.config_dir) / f"{vendor.lower()}.yaml"
    
    def get_vendor_template_path(self, vendor: str) -> Path:
        """Get vendor template directory path"""
        return Path(self.vendor.template_dir) / vendor.lower()


# Global configuration instance
config = AppConfig()