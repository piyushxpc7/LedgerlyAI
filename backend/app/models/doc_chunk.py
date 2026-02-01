from sqlalchemy import Column, Text, ForeignKey, JSON, String
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class DocChunk(Base):
    """Document chunk with vector embedding for semantic search."""
    
    __tablename__ = "doc_chunks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    # Store embedding as JSON string for SQLite compatibility (use pgvector in production)
    embedding = Column(Text, nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
