"""
Base Vendor Interface
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import asyncio
import logging

from core.constants import VendorType, CommandType
from models.device_models import DeviceInfo, CommandResult, ConnectionConfig, DeviceCapabilities
from utils.logging_utils import get_logger


class BaseVendor(ABC):
    """Base class for all vendor implementations"""
    
    def __init__(self, vendor_type: VendorType):
        self.vendor_type = vendor_type
        self.logger = get_logger(f"vendor.{vendor_type.value}")
        self.connection = None
        self.device_info = None
        self.capabilities = None
        self._connected = False
        
    @property
    def is_connected(self) -> bool:
        """Check if vendor is connected"""
        return self._connected
    
    @abstractmethod
    async def connect(self, config: ConnectionConfig) -> bool:
        """Establish connection to device"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from device"""
        pass
    
    @abstractmethod
    async def execute_command(self, command: str, command_type: CommandType = CommandType.MANUAL) -> CommandResult:
        """Execute a command and return result"""
        pass
    
    @abstractmethod
    async def get_device_info(self) -> DeviceInfo:
        """Get device information"""
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> DeviceCapabilities:
        """Get device capabilities"""
        pass
    
    @abstractmethod
    def get_prompt_patterns(self) -> Dict[str, str]:
        """Get vendor-specific prompt patterns"""
        pass
    
    @abstractmethod
    def get_command_templates(self) -> Dict[str, List[str]]:
        """Get vendor-specific command templates"""
        pass
    
    @abstractmethod
    def parse_show_output(self, command: str, output: str) -> Dict[str, Any]:
        """Parse show command output"""
        pass
    
    @abstractmethod
    def parse_config_output(self, output: str) -> Dict[str, Any]:
        """Parse configuration output"""
        pass
    
    @abstractmethod
    def normalize_command(self, command: str) -> str:
        """Normalize command for this vendor"""
        pass
    
    def validate_command(self, command: str, command_type: CommandType) -> bool:
        """Validate command for this vendor"""
        # Basic validation - override in subclasses for vendor-specific validation
        if not command or not command.strip():
            return False
        
        command = command.strip()
        
        # Vendor-specific validation rules
        if command_type == CommandType.MANUAL:
            return self._validate_manual_command(command)
        elif command_type == CommandType.AI_GENERATED:
            return self._validate_ai_generated_command(command)
        elif command_type == CommandType.TEMPLATE:
            return self._validate_template_command(command)
        elif command_type == CommandType.TRANSLATED:
            return self._validate_translated_command(command)
        
        return True
    
    def _validate_manual_command(self, command: str) -> bool:
        """Validate manual commands"""
        # Override in subclasses
        return True
    
    def _validate_ai_generated_command(self, command: str) -> bool:
        """Validate AI generated commands"""
        # Override in subclasses
        return True
    
    def _validate_template_command(self, command: str) -> bool:
        """Validate template commands"""
        # Override in subclasses
        return True
    
    def _validate_translated_command(self, command: str) -> bool:
        """Validate translated commands"""
        # Override in subclasses
        return True
    
    async def get_interface_info(self) -> List[Dict[str, Any]]:
        """Get interface information"""
        try:
            result = await self.execute_command(
                self.get_command_templates().get("interface_info", ["show interfaces"])[0]
            )
            if result.success:
                return self.parse_show_output("interface_info", result.output)
            return []
        except Exception as e:
            self.logger.error(f"Failed to get interface info: {e}")
            return []
    
    async def get_vlan_info(self) -> List[Dict[str, Any]]:
        """Get VLAN information"""
        try:
            result = await self.execute_command(
                self.get_command_templates().get("vlan_info", ["show vlan"])[0]
            )
            if result.success:
                return self.parse_show_output("vlan_info", result.output)
            return []
        except Exception as e:
            self.logger.error(f"Failed to get VLAN info: {e}")
            return []
    
    async def get_routing_info(self) -> List[Dict[str, Any]]:
        """Get routing information"""
        try:
            result = await self.execute_command(
                self.get_command_templates().get("routing_info", ["show ip route"])[0]
            )
            if result.success:
                return self.parse_show_output("routing_info", result.output)
            return []
        except Exception as e:
            self.logger.error(f"Failed to get routing info: {e}")
            return []
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status information"""
        try:
            result = await self.execute_command(
                self.get_command_templates().get("system_status", ["show version"])[0]
            )
            if result.success:
                return self.parse_show_output("system_status", result.output)
            return {}
        except Exception as e:
            self.logger.error(f"Failed to get system status: {e}")
            return {}
    
    def format_output(self, output: str) -> str:
        """Format command output"""
        # Remove common artifacts
        lines = output.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.rstrip()
            # Remove empty lines at the beginning and end
            if line or formatted_lines:
                formatted_lines.append(line)
        
        # Remove trailing empty lines
        while formatted_lines and not formatted_lines[-1]:
            formatted_lines.pop()
        
        return '\n'.join(formatted_lines)
    
    def extract_error_message(self, output: str) -> str:
        """Extract error message from output"""
        error_patterns = [
            r"%\s*(.*)",
            r"Error:\s*(.*)",
            r"ERROR:\s*(.*)",
            r"Invalid\s+(.*)",
            r"Unknown\s+(.*)",
            r"Cannot\s+(.*)",
            r"Failed\s+(.*)"
        ]
        
        import re
        for pattern in error_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Unknown error occurred"
    
    def is_config_mode_prompt(self, prompt: str) -> bool:
        """Check if prompt indicates configuration mode"""
        # Override in subclasses
        return False
    
    def is_privileged_mode_prompt(self, prompt: str) -> bool:
        """Check if prompt indicates privileged mode"""
        # Override in subclasses
        return False
    
    async def save_config(self) -> CommandResult:
        """Save configuration"""
        # Override in subclasses if vendor supports config saving
        return CommandResult(
            command="save_config",
            output="Configuration save not supported for this vendor",
            success=False,
            error="Save config not implemented"
        )
    
    async def enter_config_mode(self) -> bool:
        """Enter configuration mode"""
        # Override in subclasses
        return False
    
    async def exit_config_mode(self) -> bool:
        """Exit configuration mode"""
        # Override in subclasses
        return False
    
    def get_error_recovery_suggestions(self, error: str) -> List[str]:
        """Get error recovery suggestions"""
        # Override in subclasses for vendor-specific suggestions
        return [
            "Check command syntax",
            "Verify device is in correct mode",
            "Check device documentation"
        ]
    
    def __str__(self) -> str:
        return f"{self.vendor_type.value} Vendor"
    
    def __repr__(self) -> str:
        return f"BaseVendor(vendor_type={self.vendor_type.value}, connected={self._connected})"
