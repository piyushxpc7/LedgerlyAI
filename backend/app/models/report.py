from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text
# SQLite compatible - using String for UUIDs
from sqlalchemy.orm import relationship
import uuid
import enum

from app.database import Base


class ReportType(str, enum.Enum):
    WORKING_PAPERS = "working_papers"
    COMPLIANCE_SUMMARY = "compliance_summary"


class Report(Base):
    """Generated report from reconciliation."""
    
    __tablename__ = "reports"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(String(36), ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), nullable=False)
    type = Column(SQLEnum(ReportType), nullable=False)
    content_md = Column(Text, nullable=False)
    content_pdf_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="reports")
    run = relationship("ReconciliationRun", back_populates="reports")
