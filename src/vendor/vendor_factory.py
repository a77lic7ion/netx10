"""
Vendor Factory and Cross-Vendor Mapping
"""

from typing import Dict, Type, Optional
from core.constants import VendorType
from vendor.base_vendor import BaseVendor
from vendor.cisco_vendor import CiscoVendor
from vendor.generic_vendor import GenericVendor


class VendorFactory:
    """Factory for creating vendor instances"""
    
    _vendors: Dict[VendorType, Type[BaseVendor]] = {
        VendorType.CISCO: CiscoVendor,
        VendorType.H3C: lambda: GenericVendor(VendorType.H3C),
        VendorType.JUNIPER: lambda: GenericVendor(VendorType.JUNIPER),
        VendorType.HUAWEI: lambda: GenericVendor(VendorType.HUAWEI),
    }
    
    @classmethod
    def create_vendor(cls, vendor_type: VendorType) -> Optional[BaseVendor]:
        """Create a vendor instance"""
        vendor_class = cls._vendors.get(vendor_type)
        if vendor_class:
            # some registered entries may be classes or callables returning instances
            try:
                return vendor_class()  # if it's a class
            except TypeError:
                # Not a class; assume callable that returns an instance
                return vendor_class()
        return None
    
    @classmethod
    def get_available_vendors(cls) -> list[VendorType]:
        """Get list of available vendor types"""
        return list(cls._vendors.keys())
    
    @classmethod
    def register_vendor(cls, vendor_type: VendorType, vendor_class: Type[BaseVendor]) -> None:
        """Register a new vendor type"""
        cls._vendors[vendor_type] = vendor_class


class CrossVendorMapper:
    """Cross-vendor command mapping utility"""
    
    # Cross-vendor command mappings
    COMMAND_MAPPINGS = {
        "show_version": {
            VendorType.CISCO: ["show version"],
            VendorType.H3C: ["display version"],
            VendorType.JUNIPER: ["show version"],
            VendorType.HUAWEI: ["display version"]
        },
        "show_interfaces": {
            VendorType.CISCO: ["show interfaces"],
            VendorType.H3C: ["display interface"],
            VendorType.JUNIPER: ["show interfaces"],
            VendorType.HUAWEI: ["display interface"]
        },
        "show_vlan": {
            VendorType.CISCO: ["show vlan"],
            VendorType.H3C: ["display vlan"],
            VendorType.JUNIPER: ["show vlans"],
            VendorType.HUAWEI: ["display vlan"]
        },
        "show_ip_route": {
            VendorType.CISCO: ["show ip route"],
            VendorType.H3C: ["display ip routing-table"],
            VendorType.JUNIPER: ["show route"],
            VendorType.HUAWEI: ["display ip routing-table"]
        },
        "show_mac_table": {
            VendorType.CISCO: ["show mac address-table"],
            VendorType.H3C: ["display mac-address"],
            VendorType.JUNIPER: ["show ethernet-switching table"],
            VendorType.HUAWEI: ["display mac-address"]
        },
        "show_arp": {
            VendorType.CISCO: ["show arp"],
            VendorType.H3C: ["display arp"],
            VendorType.JUNIPER: ["show arp"],
            VendorType.HUAWEI: ["display arp"]
        },
        "show_cdp_neighbors": {
            VendorType.CISCO: ["show cdp neighbors"],
            VendorType.H3C: ["display lldp neighbor-information"],
            VendorType.JUNIPER: ["show lldp neighbors"],
            VendorType.HUAWEI: ["display lldp neighbor"]
        },
        "show_running_config": {
            VendorType.CISCO: ["show running-config"],
            VendorType.H3C: ["display current-configuration"],
            VendorType.JUNIPER: ["show configuration"],
            VendorType.HUAWEI: ["display current-configuration"]
        },
        "show_startup_config": {
            VendorType.CISCO: ["show startup-config"],
            VendorType.H3C: ["display saved-configuration"],
            VendorType.JUNIPER: ["show configuration | display set"],
            VendorType.HUAWEI: ["display saved-configuration"]
        },
        "save_config": {
            VendorType.CISCO: ["write memory", "copy running-config startup-config"],
            VendorType.H3C: ["save"],
            VendorType.JUNIPER: ["commit"],
            VendorType.HUAWEI: ["save"]
        },
        "reboot_device": {
            VendorType.CISCO: ["reload"],
            VendorType.H3C: ["reboot"],
            VendorType.JUNIPER: ["request system reboot"],
            VendorType.HUAWEI: ["reboot"]
        },
        "configure_interface": {
            VendorType.CISCO: ["interface {interface}", "switchport mode {mode}", "switchport access vlan {vlan}"],
            VendorType.H3C: ["interface {interface}", "port link-type {mode}", "port default vlan {vlan}"],
            VendorType.JUNIPER: ["set interfaces {interface} unit 0 family ethernet-switching interface-mode {mode}", "set interfaces {interface} unit 0 family ethernet-switching vlan members {vlan}"],
            VendorType.HUAWEI: ["interface {interface}", "port link-type {mode}", "port default vlan {vlan}"]
        },
        "create_vlan": {
            VendorType.CISCO: ["vlan {vlan_id}", "name {vlan_name}"],
            VendorType.H3C: ["vlan {vlan_id}", "name {vlan_name}"],
            VendorType.JUNIPER: ["set vlans {vlan_name} vlan-id {vlan_id}"],
            VendorType.HUAWEI: ["vlan {vlan_id}", "name {vlan_name}"]
        },
        "set_interface_description": {
            VendorType.CISCO: ["interface {interface}", "description {description}"],
            VendorType.H3C: ["interface {interface}", "description {description}"],
            VendorType.JUNIPER: ["set interfaces {interface} description {description}"],
            VendorType.HUAWEI: ["interface {interface}", "description {description}"]
        },
        "enable_interface": {
            VendorType.CISCO: ["interface {interface}", "no shutdown"],
            VendorType.H3C: ["interface {interface}", "undo shutdown"],
            VendorType.JUNIPER: ["delete interfaces {interface} disable"],
            VendorType.HUAWEI: ["interface {interface}", "undo shutdown"]
        },
        "disable_interface": {
            VendorType.CISCO: ["interface {interface}", "shutdown"],
            VendorType.H3C: ["interface {interface}", "shutdown"],
            VendorType.JUNIPER: ["set interfaces {interface} disable"],
            VendorType.HUAWEI: ["interface {interface}", "shutdown"]
        }
    }
    
    @classmethod
    def get_equivalent_commands(cls, operation: str, target_vendor: VendorType) -> list[str]:
        """Get equivalent commands for a specific vendor"""
        if operation in cls.COMMAND_MAPPINGS:
            return cls.COMMAND_MAPPINGS[operation].get(target_vendor, [])
        return []
    
    @classmethod
    def get_operation_for_command(cls, command: str, source_vendor: VendorType) -> Optional[str]:
        """Get the operation type for a given command"""
        command_lower = command.lower().strip()
        
        for operation, vendor_commands in cls.COMMAND_MAPPINGS.items():
            if source_vendor in vendor_commands:
                for vendor_command in vendor_commands[source_vendor]:
                    # Simple matching - in real implementation, use more sophisticated parsing
                    if command_lower in vendor_command.lower():
                        return operation
        
        return None
    
    @classmethod
    def translate_command(cls, command: str, source_vendor: VendorType, target_vendor: VendorType) -> Optional[list[str]]:
        """Translate command from one vendor to another"""
        operation = cls.get_operation_for_command(command, source_vendor)
        if operation:
            return cls.get_equivalent_commands(operation, target_vendor)
        return None
    
    @classmethod
    def get_all_operations(cls) -> list[str]:
        """Get all available operations"""
        return list(cls.COMMAND_MAPPINGS.keys())
    
    @classmethod
    def get_supported_vendors_for_operation(cls, operation: str) -> list[VendorType]:
        """Get vendors that support a specific operation"""
        if operation in cls.COMMAND_MAPPINGS:
            return list(cls.COMMAND_MAPPINGS[operation].keys())
        return []