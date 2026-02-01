from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
# SQLite compatible - using String for UUIDs
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class AuditLog(Base):
    """Audit log for tracking user actions."""
    
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)  # e.g., "create", "update", "delete"
    target_type = Column(String(50), nullable=False)  # e.g., "client", "document"
    target_id = Column(String(36), nullable=True)
    meta_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    org = relationship("Org", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
