"""
Application Constants and Enumerations
"""

from enum import Enum
from typing import Dict, List, Tuple


class VendorType(str, Enum):
    """Supported network device vendors"""
    CISCO = "cisco"
    H3C = "h3c"
    JUNIPER = "juniper"
    HUAWEI = "huawei"


class SessionStatus(str, Enum):
    """Session connection statuses"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    TIMEOUT = "timeout"


class CommandType(str, Enum):
    """Command execution types"""
    MANUAL = "manual"
    AI_GENERATED = "ai_generated"
    TEMPLATE = "template"
    TRANSLATED = "translated"


class AIPromptType(str, Enum):
    """AI prompt categories"""
    GENERAL = "general"
    COMMAND_GENERATION = "command_generation"
    CONFIG_TRANSLATION = "config_translation"
    TROUBLESHOOTING = "troubleshooting"
    BEST_PRACTICES = "best_practices"
    EXPLANATION = "explanation"


# Vendor-specific constants
VENDOR_CONFIGS = {
    VendorType.CISCO: {
        "display_name": "Cisco IOS",
        "default_baud_rate": 9600,
        "prompt_patterns": [
            r'\w+#',
            r'\w+\(config\)#',
            r'\w+\(config-\w+\)#'
        ],
        "config_mode_command": "configure terminal",
        "exit_config_command": "exit",
        "safe_commands": [
            "show", "display", "ping", "traceroute", "telnet", "ssh"
        ],
        "dangerous_commands": [
            "reload", "erase", "delete", "format", "write erase"
        ],
        "command_aliases": {
            "config": "configure terminal",
            "conf t": "configure terminal",
            "sh": "show",
            "dis": "show"
        }
    },
    VendorType.H3C: {
        "display_name": "H3C Comware",
        "default_baud_rate": 9600,
        "prompt_patterns": [
            r'<\w+>',
            r'\[\w+\]',
            r'\[\w+-\w+\]'
        ],
        "config_mode_command": "system-view",
        "exit_config_command": "quit",
        "safe_commands": [
            "display", "ping", "tracert", "telnet", "ssh"
        ],
        "dangerous_commands": [
            "reboot", "reset saved-configuration", "restore factory-default"
        ],
        "command_aliases": {
            "sys": "system-view",
            "dis": "display",
            "int": "interface"
        }
    },
    VendorType.JUNIPER: {
        "display_name": "Juniper JunOS",
        "default_baud_rate": 9600,
        "prompt_patterns": [
            r'\w+@\w+>',
            r'\w+@\w+#'
        ],
        "config_mode_command": "configure",
        "exit_config_command": "exit",
        "safe_commands": [
            "show", "ping", "traceroute", "telnet", "ssh", "file"
        ],
        "dangerous_commands": [
            "request system reboot", "request system halt"
        ],
        "command_aliases": {
            "config": "configure",
            "sh": "show",
            "set": "set"
        }
    },
    VendorType.HUAWEI: {
        "display_name": "Huawei VRP",
        "default_baud_rate": 9600,
        "prompt_patterns": [
            r'<\w+>',
            r'\[\w+\]',
            r'\[\w+-\w+\]'
        ],
        "config_mode_command": "system-view",
        "exit_config_command": "quit",
        "safe_commands": [
            "display", "ping", "tracert", "telnet", "ssh"
        ],
        "dangerous_commands": [
            "reboot", "reset saved-configuration", "restore factory-default"
        ],
        "command_aliases": {
            "sys": "system-view",
            "dis": "display",
            "int": "interface"
        }
    }
}

# Cross-vendor command mappings for common operations
CROSS_VENDOR_MAPPINGS = {
    "show_interfaces": {
        VendorType.CISCO: "show interfaces",
        VendorType.H3C: "display interface",
        VendorType.JUNIPER: "show interfaces",
        VendorType.HUAWEI: "display interface"
    },
    "show_vlan": {
        VendorType.CISCO: "show vlan",
        VendorType.H3C: "display vlan",
        VendorType.JUNIPER: "show vlans",
        VendorType.HUAWEI: "display vlan"
    },
    "show_routing": {
        VendorType.CISCO: "show ip route",
        VendorType.H3C: "display ip routing-table",
        VendorType.JUNIPER: "show route",
        VendorType.HUAWEI: "display ip routing-table"
    },
    "show_version": {
        VendorType.CISCO: "show version",
        VendorType.H3C: "display version",
        VendorType.JUNIPER: "show version",
        VendorType.HUAWEI: "display version"
    },
    "show_running_config": {
        VendorType.CISCO: "show running-config",
        VendorType.H3C: "display current-configuration",
        VendorType.JUNIPER: "show configuration",
        VendorType.HUAWEI: "display current-configuration"
    }
}

# AI system prompts for different vendors
VENDOR_AI_PROMPTS = {
    VendorType.CISCO: {
        "system_prompt": """You are a Cisco IOS networking expert with deep knowledge of:
- Cisco IOS, IOS-XE, and NX-OS command syntax
- Catalyst and Nexus switch families
- Cisco-specific configuration patterns and best practices
- Common Cisco troubleshooting procedures

When generating commands:
- Use proper Cisco command syntax
- Include appropriate error checking
- Follow Cisco configuration hierarchies
- Consider platform-specific differences""",
        "examples": [
            {"input": "configure vlan 10", "output": "vlan 10\nname VLAN10"},
            {"input": "show interface status", "output": "show interfaces status"},
            {"input": "configure trunk port", "output": "interface gigabitethernet0/1\nswitchport mode trunk\nswitchport trunk allowed vlan all"}
        ]
    },
    VendorType.H3C: {
        "system_prompt": """You are an H3C Comware networking expert with expertise in:
- H3C Comware 5 and Comware 7 operating systems
- IRF (Intelligent Resilient Framework) stacking
- H3C-specific configuration patterns
- H3C switch and router families

When generating commands:
- Use proper H3C Comware syntax
- Account for IRF vs standalone modes
- Include proper system-view navigation
- Follow H3C configuration best practices""",
        "examples": [
            {"input": "configure vlan 10", "output": "system-view\nvlan 10\ndescription VLAN10"},
            {"input": "show interface status", "output": "display interface brief"},
            {"input": "configure trunk port", "output": "system-view\ninterface gigabitethernet1/0/1\nport link-type trunk\nport trunk permit vlan all"}
        ]
    },
    VendorType.JUNIPER: {
        "system_prompt": """You are a Juniper JunOS networking expert with comprehensive knowledge of:
- Juniper JunOS hierarchical configuration model
- Commit and rollback procedures
- Juniper EX, QFX, and MX series devices
- JunOS-specific operational commands

When generating commands:
- Use proper JunOS hierarchical syntax
- Include appropriate commit procedures
- Follow JunOS configuration hierarchy
- Consider the candidate vs active configuration""",
        "examples": [
            {"input": "configure vlan 10", "output": "configure\nset vlans VLAN10 vlan-id 10\ncommit"},
            {"input": "show interface status", "output": "show interfaces terse"},
            {"input": "configure trunk port", "output": "configure\nset interfaces ge-0/0/0 unit 0 family ethernet-switching interface-mode trunk\nset interfaces ge-0/0/0 unit 0 family ethernet-switching vlan members all\ncommit"}
        ]
    },
    VendorType.HUAWEI: {
        "system_prompt": """You are a Huawei VRP networking expert with expertise in:
- Huawei VRP (Versatile Routing Platform) versions 5 and 8
- CSS (Cluster Switch System) stacking
- Huawei S, E, and CE series switches
- VRP-specific configuration patterns

When generating commands:
- Use proper Huawei VRP syntax
- Account for CSS vs standalone modes
- Include proper system-view navigation
- Follow Huawei configuration best practices""",
        "examples": [
            {"input": "configure vlan 10", "output": "system-view\nvlan 10\ndescription VLAN10"},
            {"input": "show interface status", "output": "display interface brief"},
            {"input": "configure trunk port", "output": "system-view\ninterface gigabitethernet0/0/1\nport link-type trunk\nport trunk allow-pass vlan all"}
        ]
    }
}

# Default serial port settings
DEFAULT_SERIAL_SETTINGS = {
    "baudrate": 9600,
    "bytesize": 8,
    "parity": "N",
    "stopbits": 1,
    "timeout": 10,
    "xonxoff": False,
    "rtscts": False,
    "dsrdtr": False
}

# Cisco command templates for different operations
CISCO_COMMAND_TEMPLATES = {
    "interface_info": ["show interfaces", "show ip interface brief", "show interface status"],
    "vlan_info": ["show vlan", "show vlan brief", "show interfaces switchport"],
    "routing_info": ["show ip route", "show ip route summary", "show routing-table"],
    "system_status": ["show version", "show processes", "show memory"],
    "configuration": ["show running-config", "show startup-config", "show configuration"],
    "neighbors": ["show cdp neighbors", "show lldp neighbors", "show ip arp"],
    "port_security": ["show port-security", "show port-security interface", "show mac address-table"],
    "diagnostics": ["show logging", "show tech-support", "show environment"]
}

# AI system prompts for different query types
AI_SYSTEM_PROMPTS = {
    AIPromptType.COMMAND_GENERATION: """You are a network command generation assistant. Generate accurate, vendor-specific network commands based on user requirements.

Guidelines:
- Use proper command syntax for the specified vendor
- Include necessary configuration mode transitions
- Add appropriate error checking where applicable
- Follow vendor-specific best practices
- Consider the device model and software version

Always provide complete, executable commands with proper context.""",

    AIPromptType.CONFIG_TRANSLATION: """You are a network configuration translation expert. Translate configurations between different network vendors while maintaining functionality.

Guidelines:
- Preserve the logical intent of the original configuration
- Use target vendor's native syntax and conventions
- Account for feature differences between vendors
- Include necessary configuration mode commands
- Add comments explaining any significant changes

Provide accurate translations that maintain network functionality.""",

    AIPromptType.TROUBLESHOOTING: """You are a network troubleshooting specialist. Help diagnose and resolve network issues with systematic troubleshooting approaches.

Guidelines:
- Ask clarifying questions when symptoms are unclear
- Provide step-by-step diagnostic procedures
- Include relevant show/debug commands for the vendor
- Suggest common causes based on symptoms described
- Offer multiple troubleshooting paths when appropriate

Focus on practical, actionable troubleshooting steps.""",

    AIPromptType.BEST_PRACTICES: """You are a network design and implementation consultant. Provide industry best practices and recommendations for network configurations.

Guidelines:
- Reference established industry standards (Cisco, Juniper, etc.)
- Consider scalability, security, and maintainability
- Explain the reasoning behind recommendations
- Provide configuration examples following best practices
- Address common pitfalls and how to avoid them

Give comprehensive, well-reasoned best practice advice.""",

    AIPromptType.EXPLANATION: """You are a network technology educator. Explain network concepts, commands, and configurations in clear, understandable terms.

Guidelines:
- Break down complex concepts into digestible explanations
- Provide context for why certain commands/configurations are used
- Include practical examples and use cases
- Use analogies when helpful for understanding
- Address both "what" and "why" aspects

Make technical concepts accessible and educational.""",

    AIPromptType.GENERAL: """You are a knowledgeable network assistant. Answer general networking questions and provide helpful information.

Guidelines:
- Provide accurate, up-to-date networking information
- Be helpful and professional in responses
- Acknowledge limitations when uncertain
- Suggest relevant resources for further learning
- Maintain a conversational, helpful tone

Be a reliable source of networking knowledge and assistance."""
}

# UI color schemes for different vendors
VENDOR_COLOR_SCHEMES = {
    VendorType.CISCO: {
        "primary": "#0066CC",      # Cisco blue
        "secondary": "#FFFFFF",    # White
        "accent": "#FF6600",       # Cisco orange
        "terminal_bg": "#000000",  # Black
        "terminal_fg": "#FFFFFF"   # White
    },
    VendorType.H3C: {
        "primary": "#FF6600",      # H3C orange
        "secondary": "#FFFFFF",    # White
        "accent": "#0066CC",       # Blue
        "terminal_bg": "#1E1E1E",  # Dark gray
        "terminal_fg": "#FFFFFF"   # White
    },
    VendorType.JUNIPER: {
        "primary": "#00CC66",      # Juniper green
        "secondary": "#FFFFFF",    # White
        "accent": "#0066CC",       # Blue
        "terminal_bg": "#0A0A0A",  # Very dark gray
        "terminal_fg": "#00FF00"   # Green
    },
    VendorType.HUAWEI: {
        "primary": "#FF0000",      # Huawei red
        "secondary": "#FFFFFF",    # White
        "accent": "#FFD700",       # Gold
        "terminal_bg": "#1A1A1A",  # Dark gray
        "terminal_fg": "#FFFFFF"   # White
    }
}