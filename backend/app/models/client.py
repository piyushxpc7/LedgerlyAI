from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
# SQLite compatible - using String for UUIDs
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Client(Base):
    """Client entity belonging to an org."""
    
    __tablename__ = "clients"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    gstin = Column(String(15), nullable=True)  # 15-char GSTIN
    pan = Column(String(10), nullable=True)    # 10-char PAN
    fy = Column(String(7), nullable=True)      # FY format: 2023-24
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    org = relationship("Org", back_populates="clients")
    documents = relationship("Document", back_populates="client", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="client", cascade="all, delete-orphan")
    gst_summaries = relationship("GSTSummary", back_populates="client", cascade="all, delete-orphan")
    reconciliation_runs = relationship("ReconciliationRun", back_populates="client", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="client", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="client", cascade="all, delete-orphan")
