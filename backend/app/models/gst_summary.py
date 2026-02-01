from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, JSON
# SQLite compatible - using String for UUIDs
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class GSTSummary(Base):
    """GST summary for a period."""
    
    __tablename__ = "gst_summaries"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    period = Column(String(20), nullable=False)  # e.g., "Apr-2024", "Q1-2024"
    taxable_value = Column(Numeric(15, 2), nullable=False)
    tax_amount = Column(Numeric(15, 2), nullable=False)
    meta_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="gst_summaries")
    document = relationship("Document")
