"""
Logging configuration for NetworkSwitch AI Assistant
"""

import logging
import logging.handlers
import structlog
from pathlib import Path
from typing import Optional

from core.config import AppConfig


def setup_logging(config: Optional[AppConfig] = None):
    """Setup application logging"""
    if config is None:
        config = AppConfig()
    
    # Create logs directory
    log_dir = Path(config.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure standard logging
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        config.log_file,
        maxBytes=config.log_max_size,
        backupCount=config.log_backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, config.log_level.upper()))
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Log startup
    logger = structlog.get_logger(__name__)
    logger.info("Logging system initialized", 
                log_file=config.log_file,
                log_level=config.log_level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


class SessionLogger:
    """Logger for session-specific logging"""
    
    def __init__(self, session_id: str, vendor_type: str):
        self.session_id = session_id
        self.vendor_type = vendor_type
        self.logger = get_logger(f"session.{session_id}")
    
    def log_command(self, command: str, output: str, success: bool = True):
        """Log command execution"""
        self.logger.info("Command executed",
                        command=command,
                        output_length=len(output),
                        success=success,
                        vendor=self.vendor_type)
    
    def log_connection(self, action: str, details: Optional[dict] = None):
        """Log connection events"""
        self.logger.info(f"Connection {action}",
                        action=action,
                        vendor=self.vendor_type,
                        details=details)
    
    def log_error(self, error_type: str, error_message: str, context: Optional[dict] = None):
        """Log errors"""
        self.logger.error(f"Error occurred: {error_type}",
                         error_type=error_type,
                         error_message=error_message,
                         vendor=self.vendor_type,
                         context=context)
    
    def log_ai_interaction(self, query: str, response: str, prompt_type: str):
        """Log AI interactions"""
        self.logger.info("AI interaction",
                        query_length=len(query),
                        response_length=len(response),
                        prompt_type=prompt_type,
                        vendor=self.vendor_type)


class VendorLogger:
    """Logger for vendor-specific operations"""
    
    def __init__(self, vendor_type: str):
        self.vendor_type = vendor_type
        self.logger = get_logger(f"vendor.{vendor_type}")
    
    def log_command_translation(self, source_command: str, target_command: str, 
                              source_vendor: str, target_vendor: str):
        """Log command translation"""
        self.logger.info("Command translation",
                        source_command=source_command,
                        target_command=target_command,
                        source_vendor=source_vendor,
                        target_vendor=target_vendor)
    
    def log_vendor_detection(self, method: str, result: str, confidence: float):
        """Log vendor detection attempts"""
        self.logger.info("Vendor detection",
                        method=method,
                        result=result,
                        confidence=confidence)
    
    def log_template_usage(self, template_name: str, parameters: dict):
        """Log template usage"""
        self.logger.info("Template used",
                        template_name=template_name,
                        parameters=parameters,
                        vendor=self.vendor_type)