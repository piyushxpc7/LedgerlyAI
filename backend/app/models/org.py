from datetime import datetime
from sqlalchemy import Column, String, DateTime
# SQLite compatible - using String for UUIDs
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Org(Base):
    """Organization (CA Firm) entity."""
    
    __tablename__ = "orgs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="org", cascade="all, delete-orphan")
    clients = relationship("Client", back_populates="org", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="org", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="org", cascade="all, delete-orphan")
