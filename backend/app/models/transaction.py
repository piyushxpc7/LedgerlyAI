from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Numeric, Text, JSON, Date
# SQLite compatible - using String for UUIDs
from sqlalchemy.orm import relationship
import uuid
import enum

from app.database import Base


class TransactionSource(str, enum.Enum):
    BANK = "bank"
    INVOICE = "invoice"


class Transaction(Base):
    """Extracted transaction from bank statement or invoice."""
    
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    source = Column(SQLEnum(TransactionSource), nullable=False)
    txn_date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    description = Column(Text, nullable=True)
    counterparty = Column(String(255), nullable=True)
    reference_id = Column(String(100), nullable=True)  # Invoice number, cheque number, etc.
    meta_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="transactions")
    document = relationship("Document")
