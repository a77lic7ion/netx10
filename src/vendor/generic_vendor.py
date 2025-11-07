"""
Generic vendor implementation used as a lightweight handler for H3C, Juniper and Huawei
Provides minimal mocked behaviour suitable for UI wiring and cross-vendor translation tests.
"""
from typing import Dict, List, Any
from datetime import datetime

from core.constants import VendorType, CROSS_VENDOR_MAPPINGS
from vendor.base_vendor import BaseVendor
from models.device_models import DeviceInfo, CommandResult, ConnectionConfig, DeviceCapabilities
from utils.logging import get_logger


class GenericVendor(BaseVendor):
    """A small generic vendor implementation that mimics basic device behavior.
    It uses cross-vendor mappings for known operations and returns mock outputs.
    """

    def __init__(self, vendor_type: VendorType):
        super().__init__(vendor_type)
        self.config_mode = False

    async def connect(self, config: ConnectionConfig) -> bool:
        self.logger.info(f"(mock) Connecting to {self.vendor_type.value} on {config.com_port}")
        # Simulate quick connect
        await __import__('asyncio').sleep(0.2)
        self.connection = config
        self._connected = True
        self.device_info = await self.get_device_info()
        self.capabilities = await self.get_capabilities()
        return True

    async def disconnect(self) -> bool:
        self.logger.info(f"(mock) Disconnecting from {self.vendor_type.value}")
        self._connected = False
        self.connection = None
        return True

    async def execute_command(self, command: str, command_type=None) -> CommandResult:
        from datetime import datetime
        start = datetime.utcnow()
        if not self._connected:
            return CommandResult(command=command, output="", success=False, error="Not connected", timestamp=start)

        # Try to translate common operation
        op = None
        try:
            # Find operation by matching to CROSS_VENDOR_MAPPINGS
            for k, v in CROSS_VENDOR_MAPPINGS.items():
                for vendor, cmd in v.items():
                    if isinstance(cmd, str) and cmd in command.lower():
                        op = k
                        break
                if op:
                    break
        except Exception:
            op = None

        # Create mock output
        if op:
            output = f"{self.vendor_type.value.upper()} mock output for operation: {op}\nCommand: {command}"
        else:
            output = f"{self.vendor_type.value.upper()} mock response for: {command}"

        return CommandResult(command=command, output=output, success=True, timestamp=start)

    async def get_device_info(self) -> DeviceInfo:
        # Return a small mock device info
        return DeviceInfo(
            device_model=f"{self.vendor_type.value.upper()}-MOCK-1",
            os_version="mock-1.0",
            serial_number="MOCK123456",
            hostname=f"{self.vendor_type.value}-device",
            uptime="0 days"
        )

    async def get_capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            supports_config_mode=True,
            supports_commit_rollback=(self.vendor_type == VendorType.JUNIPER),
            supports_hierarchical_config=(self.vendor_type == VendorType.JUNIPER),
            supports_multiple_contexts=False,
            supports_stacking=False,
            supports_virtualization=False,
            supported_protocols=["STP", "LLDP"]
        )

    def get_prompt_patterns(self) -> Dict[str, str]:
        return {
            "default": r"[>#]$"
        }

    def get_command_templates(self) -> Dict[str, List[str]]:
        # Basic templates based on CROSS_VENDOR_MAPPINGS for vendor
        commands = {}
        for op, mapping in CROSS_VENDOR_MAPPINGS.items():
            cmd = mapping.get(self.vendor_type)
            if cmd:
                commands[op] = [cmd]
        return commands

    def parse_show_output(self, command: str, output: str) -> Dict[str, Any]:
        # Minimal parser: return raw_output
        return {"raw_output": output}

    def parse_config_output(self, output: str) -> Dict[str, Any]:
        return {"raw_config": output}

    def normalize_command(self, command: str) -> str:
        return command.strip()
