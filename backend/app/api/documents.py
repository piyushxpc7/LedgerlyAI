import os
import uuid as uuid_lib
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.models.document import Document, DocumentType, DocumentStatus
from app.models.user import User
from app.auth import get_current_user
from app.schemas import DocumentResponse, DocumentTypeUpdate, IngestionResponse
from app.tasks.ingestion import run_ingestion_task # Import Celery task

settings = get_settings()
router = APIRouter()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific document by ID.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    return document


@router.patch("/{document_id}/type", response_model=DocumentResponse)
async def update_document_type(
    document_id: str,
    request: DocumentTypeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update document type classification.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    document.type = request.type
    db.commit()
    db.refresh(document)
    
    return document


@router.post("/{document_id}/run-ingestion", response_model=dict)
async def run_ingestion_endpoint(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger document ingestion workflow via Celery.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    if document.status == DocumentStatus.PROCESSING:
        # In production setup we might allow re-run if it's been stuck, but for now strict check
        pass
    
    # Update status to processing
    document.status = DocumentStatus.PROCESSING
    db.commit()
    
    # Run ingestion using Celery task
    task = run_ingestion_task.delay(document_id)
    
    return {
        "message": "Ingestion started",
        "document_id": document_id,
        "task_id": str(task.id),
    }


@router.get("/{document_id}/status", response_model=dict)
async def get_document_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get document processing status.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    return {
        "document_id": document.id,
        "status": document.status.value,
        "filename": document.filename,
        "type": document.type.value,
    }
