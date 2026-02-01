import os
import uuid as uuid_lib
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.models.document import Document, DocumentType, DocumentStatus
from app.models.client import Client
from app.models.user import User
from app.auth import get_current_user
from app.schemas import DocumentResponse, DocumentTypeUpdate
from app.workflows.ingestion_graph import run_ingestion  # Direct import

settings = get_settings()
router = APIRouter()


def save_file(file: UploadFile, org_id: str, client_id: str) -> str:
    """Save uploaded file to storage and return the storage URL."""
    # Create storage directory structure
    storage_dir = os.path.join(settings.storage_path, str(org_id), str(client_id))
    os.makedirs(storage_dir, exist_ok=True)
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1].lower()
    unique_filename = f"{uuid_lib.uuid4()}{file_ext}"
    file_path = os.path.join(storage_dir, unique_filename)
    
    # Save file
    with open(file_path, "wb") as f:
        content = file.file.read()
        f.write(content)
    
    return file_path


@router.post("/clients/{client_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    client_id: str,
    file: UploadFile = File(...),
    doc_type: DocumentType = Form(DocumentType.OTHER),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a document for a client.
    Accepts PDF, CSV, XLSX files.
    """
    # Verify client belongs to org
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.org_id == current_user.org_id,
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    
    # Validate file type
    file_ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    if file_ext not in settings.allowed_file_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {settings.allowed_file_types}",
        )
    
    # Save file
    storage_url = save_file(file, current_user.org_id, client_id)
    
    # Create document record
    document = Document(
        org_id=current_user.org_id,
        client_id=client_id,
        type=doc_type,
        filename=file.filename,
        storage_url=storage_url,
        status=DocumentStatus.PENDING,
        uploaded_by=current_user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return document


@router.get("/clients/{client_id}/documents", response_model=List[DocumentResponse])
async def list_client_documents(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all documents for a client.
    """
    # Verify client belongs to org
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.org_id == current_user.org_id,
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    
    documents = db.query(Document).filter(Document.client_id == client_id).all()
    return documents


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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger document ingestion workflow.
    Uses FastAPI BackgroundTasks instead of Celery for local/no-redis environments.
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is already being processed",
        )
    
    # Update status to processing
    document.status = DocumentStatus.PROCESSING
    db.commit()
    
    # Run ingestion using FastAPI BackgroundTasks
    background_tasks.add_task(run_ingestion, document_id)
    
    return {
        "message": "Ingestion started",
        "document_id": document_id,
        "task_id": "background_task",  # Placeholder
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
