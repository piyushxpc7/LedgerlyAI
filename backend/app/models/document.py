from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON
# SQLite compatible - using String for UUIDs
from sqlalchemy.orm import relationship
import uuid
import enum

from app.database import Base


class DocumentType(str, enum.Enum):
    BANK = "bank"
    INVOICE = "invoice"
    GST = "gst"
    TDS = "tds"
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Document(Base):
    """Uploaded document entity."""
    
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    type = Column(SQLEnum(DocumentType), default=DocumentType.OTHER, nullable=False)
    filename = Column(String(255), nullable=False)
    storage_url = Column(Text, nullable=False)
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    meta = Column(JSON, nullable=True)  # Stores document summary and metadata
    
    # Relationships
    org = relationship("Org", back_populates="documents")
    client = relationship("Client", back_populates="documents")
    uploaded_by_user = relationship("User", back_populates="uploaded_documents")
    chunks = relationship("DocChunk", back_populates="document", cascade="all, delete-orphan")
