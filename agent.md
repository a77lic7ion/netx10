Multi-Vendor Switch AI Assistant - Complete Production Design Template
📋 Project Overview
Project Name: NetworkSwitch AI Assistant
Platform: Windows Desktop Application
Core Functionality: Serial-based CLI terminal with AI-powered multi-vendor network automation
Target Users: Network engineers, IT administrators managing multi-vendor environments
---
🏗 System Architecture
Enhanced Multi-Vendor Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│ Presentation Layer │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │
│ │ Live CLI │ │ AI Chat │ │ Session Manager │ │
│ │ Terminal │ │ Interface │ │ │ │
│ └─────────────┘ └─────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ Application Layer │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │
│ │ Multi-Vendor│ │ AI Agent │ │ Session Service │ │
│ │ Device Mgr │ │ Engine │ │ │ │
│ └─────────────┘ └─────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┐
┌─────────────────────────────────────────────────────────────────┐
│ Vendor Abstraction Layer │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│ │ Cisco IOS │ │ H3C Commware│ │ Juniper │ │ Huawei │ │
│ │ Handler │ │ Handler │ │ Handler │ │ Handler │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ Data Layer │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │
│ │ SQLite │ │ Command │ │ Vendor-Specific │ │
│ │ Database │ │ History │ │ Config Templates │ │
│ └─────────────┘ └─────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ Hardware Layer │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│ │ Cisco │ │ H3C │ │ Juniper │ │ Huawei │ │
│ │ Switches │ │ Switches │ │ Switches │ │Switches │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
```
---
🛠 Enhanced Technology Stack
Core Framework & Languages
· Primary Language: Python 3.9+
· GUI Framework: PySide6 (Qt for Python)
· Network Communication: Netmiko 4.1.2+ (multi-vendor support)
· AI/ML Framework: LangChain 0.1.0+
· Database: SQLite 3.35+
· Serial Communication: PySerial 3.5+
· Configuration Management: Pydantic 2.0+
· Async Support: Asyncio with QAsync
Vendor-Specific Dependencies
```python
# requirements.txt
PySide6>=6.6.0
netmiko>=4.1.2 # Supports all target vendors
langchain>=0.1.0
langchain-openai>=0.0.5
pyserial>=3.5
sqlalchemy>=2.0.0
pydantic>=2.0.0
structlog>=23.0.0
python-dotenv>=1.0.0
qasync>=0.24.0
rich>=13.0.0
jinja2>=3.0.0 # For configuration templates
pyyaml>=6.0 # For vendor-specific configurations
```
---
📁 Enhanced Project Structure
```
network_switch_ai_assistant/
├── src/
│ ├── main.py
│ ├── core/
│ │ ├── __init__.py
│ │ ├── application.py
│ │ ├── config.py
│ │ └── constants.py
│ ├── ui/
│ │ ├── __init__.py
│ │ ├── main_window.py
│ │ ├── components/
│ │ │ ├── terminal_widget.py
│ │ │ ├── chat_widget.py
│ │ │ ├── session_panel.py
│ │ │ ├── device_connection.py
│ │ │ └── vendor_selection.py # NEW: Vendor selection UI
│ │ └── styles/
│ │ ├── styles.qss
│ │ └── icons/
│ ├── services/
│ │ ├── __init__.py
│ │ ├── device_service.py
│ │ ├── ai_service.py
│ │ ├── session_service.py
│ │ ├── serial_service.py
│ │ └── vendor_detection.py # NEW: Auto vendor detection
│ ├── vendors/ # NEW: Vendor-specific implementations
│ │ ├── __init__.py
│ │ ├── base.py # Base vendor interface
│ │ ├── cisco.py
│ │ ├── h3c.py
│ │ ├── juniper.py
│ │ ├── huawei.py
│ │ └── vendor_registry.py # Vendor registry and factory
│ ├── agents/
│ │ ├── __init__.py
│ │ ├── base_agent.py
│ │ ├── cisco_agent.py
│ │ ├── h3c_agent.py # NEW: H3C specific agent
│ │ ├── juniper_agent.py # NEW: Juniper specific agent
│ │ ├── huawei_agent.py # NEW: Huawei specific agent
│ │ └── prompts/
│ │ ├── base_prompts.py
│ │ ├── cisco_prompts.py
│ │ ├── h3c_prompts.py # NEW
│ │ ├── juniper_prompts.py # NEW
│ │ └── huawei_prompts.py # NEW
│ ├── models/
│ │ ├── __init__.py
│ │ ├── database.py
│ │ ├── device_models.py
│ │ ├── session_models.py
│ │ ├── ai_models.py
│ │ └── vendor_models.py # NEW: Vendor data models
│ ├── database/
│ │ ├── __init__.py
│ │ ├── repository.py
│ │ └── migrations/
│ └── utils/
│ ├── __init__.py
│ ├── logging.py
│ ├── validators.py
│ ├── helpers.py
│ └── vendor_helpers.py # NEW: Vendor-specific utilities
├── config/
│ ├── vendors/ # NEW: Vendor-specific configurations
│ │ ├── cisco.yaml
│ │ ├── h3c.yaml
│ │ ├── juniper.yaml
│ │ └── huawei.yaml
│ ├── default.yaml
│ └── development.yaml
├── templates/ # NEW: Configuration templates
│ ├── cisco/
│ ├── h3c/
│ ├── juniper/
│ └── huawei/
└── resources/
└── vendors/ # NEW: Vendor-specific resources
├── cisco/
├── h3c/
├── juniper/
└── huawei/
```
---
🎨 Enhanced GUI Design
Vendor-Aware Main Window
```
┌─────────────────────────────────────────────────────────────────┐
│ NetworkSwitch AI Assistant [_] [□] [X] │
├─────────────────────────────────────────────────────────────────┤
│ Menu: File Edit View Connection Vendor Tools Help │
├───────┬─────────────────────────────────────────────────────────┤
│ │ 📍 Session Manager 🔍 Search... │
│ │ ┌────────────────┐ │
│ │ │Active Sessions │ │
│ │ │├─ Cisco 2960 │ │
│ Nav │ │├─ H3C S6850 │ Live CLI Terminal │
│ Panel│ │├─ Juniper EX │ ┌─────────────────────────┐ │
│ │ │└─ Huawei CE │ │H3C> system-view │ │
│ │ │ │ │[H3C] interface g1/0/1 │ │
│ │ │📱 Device Info │ │[H3C-GigabitEther1/0/1] │ │
│ │ │├─ COM3:9600 │ │ │ │
│ │ │├─ H3C S6850 │ │ │ │
│ │ │├─ Connected │ │ │ │
│ │ │└─ Commware 7.x │ └─────────────────────────┘ │
│ │ │ │ ⌨ Command Input █ │
│ │ └────────────────┘ [Send] [AI Suggest] [Vendor Help]│
├───────┼─────────────────────────────────────────────────────────┤
│ │ 🤖 AI Assistant (H3C Mode) │
│ │ ┌─────────────────────────────────────────────────────┐ │
│ │ │ User: How do I configure a trunk port? │ │
│ │ │ AI: For H3C trunk configuration: │ │
│ │ │ port link-type trunk │ │
│ │ │ port trunk permit vlan 10 20 │ │
│ │ │ [Apply Commands] [Copy] [Cisco] [Juniper] [Huawei] │ │
│ │ │ │ │
│ │ └─────────────────────────────────────────────────────┘ │
│ │ [💬] Type your question... [Send] │
└───────┴─────────────────────────────────────────────────────────┘
```
New UI Components
1. Vendor Selection Panel
· Vendor icons and selection
· Auto-detection status
· Vendor-specific settings
· Quick vendor switching
2. Vendor-Aware Terminal
· Syntax highlighting per vendor
· Vendor-specific command completion
· Color schemes by vendor
· Vendor-specific prompts
3. Multi-Vendor AI Chat
· Vendor context display
· Cross-vendor command translation
· Vendor-specific best practices
· Comparative configurations
---
🗄 Enhanced Database Schema
Vendor-Aware Tables
```sql
-- Enhanced sessions table with vendor support
CREATE TABLE sessions (
id INTEGER PRIMARY KEY AUTOINCREMENT,
session_id TEXT UNIQUE NOT NULL,
device_name TEXT,
com_port TEXT NOT NULL,
baud_rate INTEGER DEFAULT 9600,
vendor_type TEXT NOT NULL, -- cisco, h3c, juniper, huawei
device_model TEXT,
os_version TEXT,
start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
end_time DATETIME,
status TEXT DEFAULT 'active',
vendor_specific_data TEXT, -- JSON for vendor-specific data
created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- Vendor-specific command templates
CREATE TABLE vendor_command_templates (
id INTEGER PRIMARY KEY AUTOINCREMENT,
vendor_type TEXT NOT NULL,
command_category TEXT NOT NULL, -- interface, routing, security
template_name TEXT NOT NULL,
template_commands TEXT NOT NULL, -- JSON array of commands
description TEXT,
parameters TEXT, -- JSON schema for parameters
created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- Enhanced command history with vendor context
CREATE TABLE command_history (
id INTEGER PRIMARY KEY AUTOINCREMENT,
session_id TEXT NOT NULL,
vendor_type TEXT NOT NULL,
command_text TEXT NOT NULL,
command_type TEXT DEFAULT 'manual',
output_text TEXT,
success BOOLEAN DEFAULT TRUE,
vendor_context TEXT, -- JSON with vendor-specific context
timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
-- Vendor-specific AI knowledge base
CREATE TABLE vendor_knowledge_base (
id INTEGER PRIMARY KEY AUTOINCREMENT,
vendor_type TEXT NOT NULL,
topic TEXT NOT NULL,
content TEXT NOT NULL,
command_examples TEXT, -- JSON array of examples
best_practices TEXT,
common_issues TEXT,
created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- Cross-vendor command mappings
CREATE TABLE cross_vendor_mappings (
id INTEGER PRIMARY KEY AUTOINCREMENT,
operation TEXT NOT NULL, -- create_vlan, configure_interface, etc.
cisco_commands TEXT,
h3c_commands TEXT,
juniper_commands TEXT,
huawei_commands TEXT,
description TEXT,
created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```
---
🔌 Vendor Abstraction Layer
Base Vendor Interface
```python
class BaseVendorHandler(ABC):
"""Abstract base class for all vendor handlers"""
@abstractmethod
async def connect(self, com_port: str, baud_rate: int) -> bool:
pass
@abstractmethod
async def disconnect(self) -> bool:
pass
@abstractmethod
async def send_command(self, command: str, expect_string: str = None) -> str:
pass
@abstractmethod
async def enter_config_mode(self) -> bool:
pass
@abstractmethod
async def exit_config_mode(self) -> bool:
pass
@abstractmethod
async def get_device_info(self) -> DeviceInfo:
pass
@abstractmethod
def get_prompt_patterns(self) -> List[str]:
pass
@abstractmethod
def normalize_command(self, command: str) -> str:
pass
```
Vendor-Specific Implementations
Cisco IOS Handler
```python
class CiscoIOSHandler(BaseVendorHandler):
def enter_config_mode(self) -> bool:
return self.send_command("configure terminal", "config")
def get_prompt_patterns(self) -> List[str]:
return [r'\w+#', r'\w+\(config\)#', r'\w+\(config-\w+\)#']
def normalize_command(self, command: str) -> str:
# Cisco command normalization
return command.strip()
```
H3C Commware Handler
```python
class H3CCommwareHandler(BaseVendorHandler):
def enter_config_mode(self) -> bool:
return self.send_command("system-view", "view")
def get_prompt_patterns(self) -> List[str]:
return [r'<\w+>', r'\[\w+\]', r'\[\w+-\w+\]']
def normalize_command(self, command: str) -> str:
# H3C command normalization
command = command.strip()
if command.startswith('sys'):
command = 'system-view'
return command
```
Juniper JunOS Handler
```python
class JuniperJunOSHandler(BaseVendorHandler):
def enter_config_mode(self) -> bool:
return self.send_command("configure", "configuration")
def get_prompt_patterns(self) -> List[str]:
return [r'\w+@\w+>', r'\w+@\w+#', r'\w+@\w+#\s']
def normalize_command(self, command: str) -> str:
# Juniper command normalization
command = command.strip()
if command == 'config':
command = 'configure'
return command
```
Huawei VRP Handler
```python
class HuaweiVRPHandler(BaseVendorHandler):
def enter_config_mode(self) -> bool:
return self.send_command("system-view", "view")
def get_prompt_patterns(self) -> List[str]:
return [r'<\w+>', r'\[\w+\]', r'\[\w+-\w+\]']
def normalize_command(self, command: str) -> str:
# Huawei command normalization
command = command.strip()
if command.startswith('sys'):
command = 'system-view'
return command
```
---
🤖 Enhanced Multi-Vendor AI Agent System
Vendor-Specific AI Prompts
```python
# prompts/multi_vendor_prompts.py
VENDOR_SPECIFIC_CONTEXTS = {
"cisco": {
"system_prompt": """
You are a Cisco IOS networking expert. Provide accurate Cisco IOS commands.
Key characteristics:
- Configuration mode: configure terminal
- Interface naming: GigabitEthernet0/1, FastEthernet0/0
- VLAN configuration: vlan 10, name Marketing
- Show commands: show running-config, show interface status
""",
"examples": [
{"input": "configure vlan 10", "output": "vlan 10\\nname VLAN10"},
{"input": "show interfaces", "output": "show ip interface brief"}
]
},
"h3c": {
"system_prompt": """
You are an H3C Comware networking expert. Provide accurate H3C commands.
Key characteristics:
- Configuration mode: system-view
- Interface naming: GigabitEthernet1/0/1, Bridge-Aggregation1
- VLAN configuration: vlan 10, description Marketing
- Display commands: display current-configuration, display interface
""",
"examples": [
{"input": "configure vlan 10", "output": "vlan 10\\ndescription VLAN10"},
{"input": "show interfaces", "output": "display interface brief"}
]
},
"juniper": {
"system_prompt": """
You are a Juniper JunOS networking expert. Provide accurate Juniper commands.
Key characteristics:
- Configuration mode: configure
- Interface naming: ge-0/0/1, ae0
- Hierarchical configuration structure
- Show commands: show configuration, show interfaces
- Commit required for changes
""",
"examples": [
{"input": "configure vlan 10", "output": "set vlans VLAN10 vlan-id 10"},
{"input": "show interfaces", "output": "show interfaces terse"}
]
},
"huawei": {
"system_prompt": """
You are a Huawei VRP networking expert. Provide accurate Huawei commands.
Key characteristics:
- Configuration mode: system-view
- Interface naming: GigabitEthernet0/0/1, Eth-Trunk1
- VLAN configuration: vlan 10, description Marketing
- Display commands: display current-configuration, display interface
""",
"examples": [
{"input": "configure vlan 10", "output": "vlan 10\\ndescription VLAN10"},
{"input": "show interfaces", "output": "display interface brief"}
]
}
}
```
Cross-Vendor Command Translation
```python
class CrossVendorTranslator:
"""Translates commands between different vendors"""
def translate_command(self, source_vendor: str, target_vendor: str, command: str) -> str:
# Implement command translation logic
pass
def get_equivalent_commands(self, operation: str) -> Dict[str, str]:
"""Get equivalent commands for the same operation across vendors"""
return {
"cisco": self._get_cisco_command(operation),
"h3c": self._get_h3c_command(operation),
"juniper": self._get_juniper_command(operation),
"huawei": self._get_huawei_command(operation)
}
```
---
⚙ Vendor Configuration Management
Vendor-Specific Configuration Files
```yaml
# config/vendors/cisco.yaml
vendor: "cisco"
display_name: "Cisco IOS"
default_baud_rate: 9600
prompt_patterns:
- '\w+#'
- '\w+\(config\)#'
- '\w+\(config-\w+\)#'
command_aliases:
"conf t": "configure terminal"
"sh": "show"
"int": "interface"
initial_commands:
- "terminal length 0"
- "terminal width 512"
safe_commands:
- "show"
- "display"
dangerous_commands:
- "reload"
- "write erase"
- "delete flash:"
```
```yaml
# config/vendors/h3c.yaml
vendor: "h3c"
display_name: "H3C Comware"
default_baud_rate: 9600
prompt_patterns:
- '<\w+>'
- '\[\w+\]'
- '\[\w+-\w+\]'
command_aliases:
"sys": "system-view"
"dis": "display"
"int": "interface"
initial_commands:
- "screen-length disable"
safe_commands:
- "display"
- "ping"
dangerous_commands:
- "reboot"
- "reset saved-configuration"
```
---
🎯 Enhanced AI Agent Capabilities
Multi-Vendor AI Capabilities
```python
MULTI_VENDOR_AI_CAPABILITIES = {
"vendor_specific_expertise": {
"cisco": [
"IOS/XE command syntax",
"Cisco best practices",
"Catalyst/Nexus differences"
],
"h3c": [
"Comware 5/7 differences",
"H3C security configurations",
"IRF stacking configurations"
],
"juniper": [
"JunOS hierarchical config",
"Commit/rollback operations",
"MX/EX/QFX series differences"
],
"huawei": [
"VRP 5/8 differences",
"Huawei security features",
"CSS stacking configurations"
]
},
"cross_vendor_operations": [
"Command translation between vendors",
"Comparative configuration analysis",
"Migration assistance between platforms",
"Multi-vendor best practices"
],
"vendor_detection": [
"Auto-detection from banner",
"Prompt pattern recognition",
"Command response analysis"
]
}
```
---
🔄 Enhanced Workflows
1. Multi-Vendor Device Connection
```
User Action → Select COM Port → Auto Vendor Detection →
Load Vendor Handler → Initialize Connection →
Vendor-Specific Setup → Update UI with Vendor Context
```
2. Vendor-Aware AI Assistance
```
User Query → Detect Current Vendor → Load Vendor-Specific AI →
Generate Vendor-Appropriate Commands →
Optional Cross-Vendor Translation → User Review → Execution
```
3. Cross-Vendor Configuration Migration
```
Source Vendor Config → Parse Configuration →
Map to Target Vendor → Generate Equivalent Commands →
Validate Syntax → Apply to Target Device
```
---
Enhanced Testing Strategy
Vendor-Specific Test Cases
1. Vendor Detection Tests
· Banner parsing for each vendor
· Prompt pattern recognition
· Auto-detection accuracy
2. Vendor Command Tests
· Command normalization per vendor
· Configuration mode entry/exit
· Vendor-specific syntax validation
3. Cross-Vendor Translation Tests
· Command equivalence validation
· Configuration migration accuracy
· Syntax preservation
Test Device Simulation
· Cisco IOS simulator
· H3C Comware simulator
· Juniper JunOS simulator
· Huawei VRP simulator
---
📦 Enhanced Deployment
Vendor-Specific Resources
· Vendor-specific icons and branding
· Platform-specific documentation
· Vendor-appropriate default configurations
· Vendor-specific template libraries
Installation Packages
· Single installer with all vendor support
· Modular installation (vendor plugins)
· Vendor-specific quick start guides
---
🚀 Enhanced Development Roadmap
Phase 1: Multi-Vendor Foundation (Weeks 1-4)
· Vendor abstraction layer
· Base vendor interfaces
· Vendor registry system
· Basic vendor detection
Phase 2: Core Vendor Implementations (Weeks 5-8)
· Cisco IOS full implementation
· H3C Comware implementation
· Juniper JunOS implementation
· Huawei VRP implementation
Phase 3: AI Multi-Vendor Support (Weeks 9-12)
· Vendor-specific AI agents
· Cross-vendor translation
· Comparative analysis features
· Migration assistance tools
Phase 4: Advanced Features (Weeks 13-16)
· Configuration templating
· Bulk operations across vendors
· Vendor-specific analytics
· Advanced migration tools
Phase 5: Polish & Deployment (Weeks 17-20)
· Comprehensive multi-vendor testing
· Performance optimization
· Vendor-specific documentation
· Final packaging and distribution
---
⚠ Multi-Vendor Risk Mitigation
Technical Risks
1. Vendor Command Variations
· Comprehensive command validation
· Vendor-specific syntax checking
· Safe mode for dangerous operations
2. Configuration Differences
· Thorough testing of equivalent configurations
· Validation of migrated configurations
· Rollback capabilities
3. Platform Compatibility
· Version-specific feature support
· Hardware platform differences
· OS version compatibility matrices
Vendor-Specific Considerations
· H3C: IRF vs standalone configurations
· Juniper: Commit/rollback workflow differences
· Huawei: VRP version compatibility
· Cisco: IOS/IOS-XE/NX-OS differences