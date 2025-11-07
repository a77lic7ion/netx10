"""
Database Service for NetworkSwitch AI Assistant
"""

import json
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, select, and_, or_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from core.config import AppConfig
from models.device_models import (
    SessionModel, CommandHistoryModel, VendorCommandTemplateModel,
    VendorKnowledgeBaseModel, CrossVendorMappingModel,
    Session, CommandResult, VendorTemplate, CrossVendorMapping
)
from utils.logging import get_logger


class DatabaseService:
    """Database service for managing sessions, commands, and vendor data"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = get_logger("database_service")
        self.engine = None
        self.async_session = None
        
    async def initialize(self) -> bool:
        """Initialize database connection and create tables"""
        try:
            # Create database directory if it doesn't exist
            db_path = Path(self.config.database.url.replace("sqlite:///", ""))
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use aiosqlite for async SQLite support
            async_url = self.config.database.url.replace("sqlite:///", "sqlite+aiosqlite:///")
            
            # Create async engine
            self.engine = create_async_engine(
                async_url,
                echo=self.config.database.echo
            )
            
            # Create async session factory
            self.async_session = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            self.logger.info(f"Database initialized at {self.config.database.url}")
            
            # Initialize default data
            await self._initialize_default_data()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            return False
    
    async def _initialize_default_data(self):
        """Initialize default vendor templates and knowledge base"""
        try:
            async with self.async_session() as session:
                # Check if data already exists
                result = await session.execute(
                    select(VendorCommandTemplateModel).limit(1)
                )
                if result.scalar_one_or_none():
                    return  # Data already initialized
                
                # Initialize Cisco command templates
                cisco_templates = [
                    {
                        "vendor_type": "cisco",
                        "command_category": "system_info",
                        "template_name": "basic_system_info",
                        "template_commands": json.dumps([
                            "show version",
                            "show running-config",
                            "show interfaces status",
                            "show ip interface brief"
                        ]),
                        "description": "Basic system information collection",
                        "parameters": json.dumps({})
                    },
                    {
                        "vendor_type": "cisco",
                        "command_category": "interface_config",
                        "template_name": "interface_basic_config",
                        "template_commands": json.dumps([
                            "interface {interface_name}",
                            "description {description}",
                            "switchport mode {mode}",
                            "switchport access vlan {vlan_id}",
                            "no shutdown"
                        ]),
                        "description": "Basic interface configuration template",
                        "parameters": json.dumps({
                            "interface_name": {"type": "string", "required": True},
                            "description": {"type": "string", "required": False},
                            "mode": {"type": "string", "enum": ["access", "trunk"], "required": True},
                            "vlan_id": {"type": "integer", "required": False}
                        })
                    },
                    {
                        "vendor_type": "cisco",
                        "command_category": "vlan_config",
                        "template_name": "vlan_creation",
                        "template_commands": json.dumps([
                            "vlan {vlan_id}",
                            "name {vlan_name}",
                            "exit"
                        ]),
                        "description": "VLAN creation template",
                        "parameters": json.dumps({
                            "vlan_id": {"type": "integer", "required": True, "min": 1, "max": 4094},
                            "vlan_name": {"type": "string", "required": True, "max_length": 32}
                        })
                    }
                ]
                
                # Insert templates
                for template_data in cisco_templates:
                    template = VendorCommandTemplateModel(**template_data)
                    session.add(template)
                
                # Initialize vendor knowledge base
                knowledge_base_entries = [
                    {
                        "vendor_type": "cisco",
                        "topic": "interface_troubleshooting",
                        "content": "Common interface troubleshooting steps for Cisco devices:",
                        "command_examples": json.dumps([
                            "show interfaces {interface}",
                            "show interfaces {interface} status",
                            "show controllers {interface}",
                            "show run interface {interface}"
                        ]),
                        "best_practices": "Always check interface status, duplex settings, and error counters when troubleshooting connectivity issues.",
                        "common_issues": "Interface down, duplex mismatch, high error counters, cable issues"
                    },
                    {
                        "vendor_type": "cisco",
                        "topic": "vlan_configuration",
                        "content": "VLAN configuration best practices for Cisco switches:",
                        "command_examples": json.dumps([
                            "show vlan brief",
                            "show vlan id {vlan_id}",
                            "show interfaces trunk",
                            "show interfaces switchport"
                        ]),
                        "best_practices": "Use consistent VLAN naming, document VLAN assignments, and verify trunk configurations.",
                        "common_issues": "VLAN not created, ports not assigned, trunk not allowing VLAN"
                    }
                ]
                
                # Insert knowledge base entries
                for kb_data in knowledge_base_entries:
                    kb_entry = VendorKnowledgeBaseModel(**kb_data)
                    session.add(kb_entry)
                
                # Initialize cross-vendor mappings
                cross_vendor_mappings = [
                    {
                        "operation": "show_version",
                        "cisco_commands": json.dumps(["show version"]),
                        "h3c_commands": json.dumps(["display version"]),
                        "juniper_commands": json.dumps(["show version"]),
                        "huawei_commands": json.dumps(["display version"]),
                        "description": "Display system version information"
                    },
                    {
                        "operation": "show_interfaces",
                        "cisco_commands": json.dumps(["show interfaces"]),
                        "h3c_commands": json.dumps(["display interface"]),
                        "juniper_commands": json.dumps(["show interfaces"]),
                        "huawei_commands": json.dumps(["display interface"]),
                        "description": "Display interface information"
                    },
                    {
                        "operation": "save_config",
                        "cisco_commands": json.dumps(["write memory", "copy running-config startup-config"]),
                        "h3c_commands": json.dumps(["save"]),
                        "juniper_commands": json.dumps(["commit"]),
                        "huawei_commands": json.dumps(["save"]),
                        "description": "Save current configuration"
                    }
                ]
                
                # Insert cross-vendor mappings
                for mapping_data in cross_vendor_mappings:
                    mapping = CrossVendorMappingModel(**mapping_data)
                    session.add(mapping)
                
                await session.commit()
                self.logger.info("Default data initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize default data: {e}")
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session context manager"""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Database session error: {e}")
                raise
    
    # Session Management
    async def save_session(self, session_data: Session) -> bool:
        """Create or update a session"""
        try:
            async with self.get_session() as db_session:
                result = await db_session.execute(
                    select(SessionModel).where(SessionModel.session_id == session_data.session_id)
                )
                session_model = result.scalar_one_or_none()

                if session_model:
                    # Update existing session
                    session_model.device_name = session_data.device_name
                    session_model.com_port = session_data.com_port
                    session_model.baud_rate = session_data.baud_rate
                    session_model.vendor_type = session_data.vendor_type
                    session_model.device_model = session_data.device_model
                    session_model.os_version = session_data.os_version
                    session_model.start_time = session_data.start_time
                    session_model.end_time = session_data.end_time
                    session_model.status = session_data.status
                    session_model.vendor_specific_data = session_data.vendor_specific_data
                else:
                    # Create new session
                    session_model = SessionModel(
                        session_id=session_data.session_id,
                        device_name=session_data.device_name,
                        com_port=session_data.com_port,
                        baud_rate=session_data.baud_rate,
                        vendor_type=session_data.vendor_type,
                        device_model=session_data.device_model,
                        os_version=session_data.os_version,
                        start_time=session_data.start_time,
                        status=session_data.status,
                        vendor_specific_data=session_data.vendor_specific_data
                    )
                    db_session.add(session_model)
                return True
        except Exception as e:
            self.logger.error(f"Failed to save session: {e}")
            return False

    async def update_session(self, session_data: Session) -> bool:
        """Update an existing session"""
        return await self.save_session(session_data)
    
    async def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        try:
            async with self.get_session() as db_session:
                result = await db_session.execute(
                    select(SessionModel).where(SessionModel.session_id == session_id)
                )
                session_model = result.scalar_one_or_none()
                
                if session_model:
                    return Session.from_orm(session_model)
                return None
        except Exception as e:
            self.logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def get_active_sessions(self) -> List[Session]:
        """Get all active sessions"""
        try:
            async with self.get_session() as db_session:
                result = await db_session.execute(
                    select(SessionModel).where(SessionModel.status == "active")
                )
                sessions = result.scalars().all()
                return [Session.from_orm(session) for session in sessions]
        except Exception as e:
            self.logger.error(f"Failed to get active sessions: {e}")
            return []
    
    async def update_session_status(self, session_id: str, status: str, end_time: Optional[datetime] = None) -> bool:
        """Update session status"""
        try:
            async with self.get_session() as db_session:
                result = await db_session.execute(
                    select(SessionModel).where(SessionModel.session_id == session_id)
                )
                session_model = result.scalar_one_or_none()
                
                if session_model:
                    session_model.status = status
                    if end_time:
                        session_model.end_time = end_time
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Failed to update session {session_id} status: {e}")
            return False
    
    # Command History Management
    async def add_command_history(self, session_id: str, vendor_type: str, 
                                command_result: CommandResult, command_type: str = "manual") -> bool:
        """Add command to history"""
        try:
            async with self.get_session() as db_session:
                history_entry = CommandHistoryModel(
                    session_id=session_id,
                    vendor_type=vendor_type,
                    command_text=command_result.command,
                    command_type=command_type,
                    output_text=command_result.output,
                    success=command_result.success,
                    vendor_context={"error": command_result.error} if command_result.error else None,
                    timestamp=command_result.timestamp
                )
                db_session.add(history_entry)
                return True
        except Exception as e:
            self.logger.error(f"Failed to add command history: {e}")
            return False
    
    async def get_command_history(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get command history for a session"""
        try:
            async with self.get_session() as db_session:
                result = await db_session.execute(
                    select(CommandHistoryModel)
                    .where(CommandHistoryModel.session_id == session_id)
                    .order_by(CommandHistoryModel.timestamp.desc())
                    .limit(limit)
                )
                history_entries = result.scalars().all()
                
                return [
                    {
                        "command": entry.command_text,
                        "output": entry.output_text,
                        "success": entry.success,
                        "timestamp": entry.timestamp.isoformat(),
                        "command_type": entry.command_type
                    }
                    for entry in history_entries
                ]
        except Exception as e:
            self.logger.error(f"Failed to get command history for session {session_id}: {e}")
            return []
    
    # Vendor Template Management
    async def get_vendor_templates(self, vendor_type: str, category: Optional[str] = None) -> List[VendorTemplate]:
        """Get vendor command templates"""
        try:
            async with self.get_session() as db_session:
                query = select(VendorCommandTemplateModel).where(
                    VendorCommandTemplateModel.vendor_type == vendor_type
                )
                
                if category:
                    query = query.where(VendorCommandTemplateModel.command_category == category)
                
                result = await db_session.execute(query)
                templates = result.scalars().all()
                
                return [VendorTemplate.from_orm(template) for template in templates]
        except Exception as e:
            self.logger.error(f"Failed to get vendor templates for {vendor_type}: {e}")
            return []
    
    async def get_vendor_template(self, template_id: int) -> Optional[VendorTemplate]:
        """Get specific vendor template"""
        try:
            async with self.get_session() as db_session:
                result = await db_session.execute(
                    select(VendorCommandTemplateModel).where(VendorCommandTemplateModel.id == template_id)
                )
                template_model = result.scalar_one_or_none()
                
                if template_model:
                    return VendorTemplate.from_orm(template_model)
                return None
        except Exception as e:
            self.logger.error(f"Failed to get vendor template {template_id}: {e}")
            return None
    
    # Knowledge Base Management
    async def get_knowledge_base_entries(self, vendor_type: str, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get vendor knowledge base entries"""
        try:
            async with self.get_session() as db_session:
                query = select(VendorKnowledgeBaseModel).where(
                    VendorKnowledgeBaseModel.vendor_type == vendor_type
                )
                
                if topic:
                    query = query.where(VendorKnowledgeBaseModel.topic == topic)
                
                result = await db_session.execute(query)
                entries = result.scalars().all()
                
                return [
                    {
                        "id": entry.id,
                        "topic": entry.topic,
                        "content": entry.content,
                        "command_examples": entry.command_examples,
                        "best_practices": entry.best_practices,
                        "common_issues": entry.common_issues,
                        "created_at": entry.created_at.isoformat()
                    }
                    for entry in entries
                ]
        except Exception as e:
            self.logger.error(f"Failed to get knowledge base entries for {vendor_type}: {e}")
            return []
    
    # Cross-Vendor Mapping Management
    async def get_cross_vendor_mappings(self, operation: Optional[str] = None) -> List[CrossVendorMapping]:
        """Get cross-vendor command mappings"""
        try:
            async with self.get_session() as db_session:
                query = select(CrossVendorMappingModel)
                
                if operation:
                    query = query.where(CrossVendorMappingModel.operation == operation)
                
                result = await db_session.execute(query)
                mappings = result.scalars().all()
                
                return [CrossVendorMapping.from_orm(mapping) for mapping in mappings]
        except Exception as e:
            self.logger.error(f"Failed to get cross-vendor mappings: {e}")
            return []
    
    # Statistics and Analytics
    async def get_session_statistics(self) -> Dict[str, Any]:
        """Get session statistics"""
        try:
            async with self.get_session() as db_session:
                # Total sessions
                total_result = await db_session.execute(select(SessionModel))
                total_sessions = len(total_result.scalars().all())
                
                # Active sessions
                active_result = await db_session.execute(
                    select(SessionModel).where(SessionModel.status == "active")
                )
                active_sessions = len(active_result.scalars().all())
                
                # Sessions by vendor
                vendor_stats = {}
                for vendor in ["cisco", "h3c", "juniper", "huawei"]:
                    vendor_result = await db_session.execute(
                        select(SessionModel).where(SessionModel.vendor_type == vendor)
                    )
                    vendor_stats[vendor] = len(vendor_result.scalars().all())
                
                # Command statistics
                command_result = await db_session.execute(select(CommandHistoryModel))
                total_commands = len(command_result.scalars().all())
                
                # Success rate
                success_result = await db_session.execute(
                    select(CommandHistoryModel).where(CommandHistoryModel.success == True)
                )
                successful_commands = len(success_result.scalars().all())
                
                success_rate = (successful_commands / total_commands * 100) if total_commands > 0 else 0
                
                return {
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "sessions_by_vendor": vendor_stats,
                    "total_commands": total_commands,
                    "successful_commands": successful_commands,
                    "command_success_rate": round(success_rate, 2)
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get session statistics: {e}")
            return {}
    
    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up old sessions and their history"""
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            async with self.get_session() as db_session:
                # Find old sessions
                old_sessions_result = await db_session.execute(
                    select(SessionModel).where(SessionModel.end_time < cutoff_date)
                )
                old_sessions = old_sessions_result.scalars().all()
                
                deleted_count = len(old_sessions)
                
                # Delete old sessions (cascade will delete related history)
                for session in old_sessions:
                    await db_session.delete(session)
                
                self.logger.info(f"Cleaned up {deleted_count} old sessions")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old sessions: {e}")
            return 0
    
    async def close(self):
        """Close database connection"""
        try:
            if self.engine:
                await self.engine.dispose()
                self.logger.info("Database connection closed")
        except Exception as e:
            self.logger.error(f"Error closing database connection: {e}")


# Use Base declared in models.device_models so all table metadata is shared
from models.device_models import Base