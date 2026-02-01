from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON
# SQLite compatible - using String for UUIDs
from sqlalchemy.orm import relationship
import uuid
import enum

from app.database import Base


class IssueSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "med"
    HIGH = "high"


class IssueCategory(str, enum.Enum):
    MISSING_INVOICE = "missing_invoice"
    DUPLICATE = "duplicate"
    MISMATCH = "mismatch"
    GST_MISMATCH = "gst_mismatch"
    OTHER = "other"


class IssueStatus(str, enum.Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    RESOLVED = "resolved"


class Issue(Base):
    """Detected issue from reconciliation."""
    
    __tablename__ = "issues"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(String(36), ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), nullable=False)
    severity = Column(SQLEnum(IssueSeverity), nullable=False)
    category = Column(SQLEnum(IssueCategory), nullable=False)
    title = Column(String(500), nullable=False)
    details_json = Column(JSON, nullable=True)
    status = Column(SQLEnum(IssueStatus), default=IssueStatus.OPEN, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="issues")
    run = relationship("ReconciliationRun", back_populates="issues")
