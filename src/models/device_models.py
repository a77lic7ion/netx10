"""
Device and Session Models
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class SessionModel(Base):
    """SQLAlchemy model for sessions table"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, unique=True, nullable=False, index=True)
    device_name = Column(String, nullable=True)
    com_port = Column(String, nullable=False)
    baud_rate = Column(Integer, default=9600)
    vendor_type = Column(String, nullable=False, index=True)
    device_model = Column(String, nullable=True)
    os_version = Column(String, nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="active", index=True)
    vendor_specific_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    command_history = relationship("CommandHistoryModel", back_populates="session")


class CommandHistoryModel(Base):
    """SQLAlchemy model for command_history table"""
    __tablename__ = "command_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False, index=True)
    vendor_type = Column(String, nullable=False, index=True)
    command_text = Column(Text, nullable=False)
    command_type = Column(String, default="manual", index=True)
    output_text = Column(Text, nullable=True)
    success = Column(Boolean, default=True, index=True)
    vendor_context = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("SessionModel", back_populates="command_history")


class VendorCommandTemplateModel(Base):
    """SQLAlchemy model for vendor_command_templates table"""
    __tablename__ = "vendor_command_templates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_type = Column(String, nullable=False, index=True)
    command_category = Column(String, nullable=False, index=True)
    template_name = Column(String, nullable=False, index=True)
    template_commands = Column(Text, nullable=False)  # JSON array
    description = Column(Text, nullable=True)
    parameters = Column(JSON, nullable=True)  # JSON schema
    created_at = Column(DateTime, default=datetime.utcnow)


class VendorKnowledgeBaseModel(Base):
    """SQLAlchemy model for vendor_knowledge_base table"""
    __tablename__ = "vendor_knowledge_base"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_type = Column(String, nullable=False, index=True)
    topic = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    command_examples = Column(JSON, nullable=True)  # JSON array
    best_practices = Column(Text, nullable=True)
    common_issues = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CrossVendorMappingModel(Base):
    """SQLAlchemy model for cross_vendor_mappings table"""
    __tablename__ = "cross_vendor_mappings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    operation = Column(String, nullable=False, index=True)
    cisco_commands = Column(Text, nullable=True)
    h3c_commands = Column(Text, nullable=True)
    juniper_commands = Column(Text, nullable=True)
    huawei_commands = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Models for API/Service Layer

class DeviceInfo(BaseModel):
    """Device information model"""
    device_model: Optional[str] = None
    os_version: Optional[str] = None
    serial_number: Optional[str] = None
    hostname: Optional[str] = None
    uptime: Optional[str] = None
    vendor_specific: Optional[Dict[str, Any]] = None


class Session(BaseModel):
    """Session data model"""
    session_id: str
    device_name: Optional[str] = None
    com_port: str
    baud_rate: int = 9600
    vendor_type: str
    device_model: Optional[str] = None
    os_version: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "active"
    vendor_specific_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class CommandResult(BaseModel):
    """Command execution result model"""
    command: str
    output: str
    success: bool = True
    error: Optional[str] = None
    execution_time: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AIQuery(BaseModel):
    """AI query model"""
    query: str
    vendor_type: str
    session_context: Optional[Dict[str, Any]] = None
    command_history: Optional[List[str]] = None
    
    @validator('vendor_type')
    def validate_vendor_type(cls, v):
        from core.constants import VendorType
        if v not in [vendor.value for vendor in VendorType]:
            raise ValueError(f"Invalid vendor type: {v}")
        return v


class AIResponse(BaseModel):
    """AI response model"""
    response: str
    confidence: float = 0.0
    suggested_commands: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    references: Optional[List[str]] = None


class VendorTemplate(BaseModel):
    """Vendor command template model"""
    vendor_type: str
    command_category: str
    template_name: str
    template_commands: List[str]
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class CrossVendorMapping(BaseModel):
    """Cross-vendor command mapping model"""
    operation: str
    cisco_commands: Optional[str] = None
    h3c_commands: Optional[str] = None
    juniper_commands: Optional[str] = None
    huawei_commands: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class ConnectionConfig(BaseModel):
    """Connection configuration model"""
    com_port: str
    baud_rate: int = 9600
    data_bits: int = 8
    parity: str = "N"
    stop_bits: int = 1
    timeout: float = 10.0
    flow_control: bool = False
    
    @validator('baud_rate')
    def validate_baud_rate(cls, v):
        valid_rates = [300, 600, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
        if v not in valid_rates:
            raise ValueError(f"Invalid baud rate: {v}. Must be one of {valid_rates}")
        return v
    
    @validator('data_bits')
    def validate_data_bits(cls, v):
        if v not in [5, 6, 7, 8]:
            raise ValueError("Data bits must be 5, 6, 7, or 8")
        return v
    
    @validator('parity')
    def validate_parity(cls, v):
        if v.upper() not in ['N', 'E', 'O', 'M', 'S']:
            raise ValueError("Parity must be N, E, O, M, or S")
        return v.upper()
    
    @validator('stop_bits')
    def validate_stop_bits(cls, v):
        if v not in [1, 1.5, 2]:
            raise ValueError("Stop bits must be 1, 1.5, or 2")
        return v


class DeviceCapabilities(BaseModel):
    """Device capabilities model"""
    supports_config_mode: bool = True
    supports_commit_rollback: bool = False
    supports_hierarchical_config: bool = False
    supports_multiple_contexts: bool = False
    supports_stacking: bool = False
    supports_virtualization: bool = False
    max_interfaces: Optional[int] = None
    max_vlans: Optional[int] = None
    supported_protocols: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True