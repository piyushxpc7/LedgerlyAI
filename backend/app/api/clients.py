from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client
from app.models.user import User
from app.auth import get_current_user
from app.schemas import ClientCreate, ClientUpdate, ClientResponse

router = APIRouter()


@router.get("", response_model=List[ClientResponse])
async def list_clients(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all clients for the current organization.
    """
    clients = db.query(Client).filter(Client.org_id == current_user.org_id).all()
    return clients


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    request: ClientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new client for the organization.
    """
    client = Client(
        org_id=current_user.org_id,
        name=request.name,
        gstin=request.gstin,
        pan=request.pan,
        fy=request.fy,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    
    return client


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific client by ID.
    """
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.org_id == current_user.org_id,
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    request: ClientUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a client's information.
    """
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.org_id == current_user.org_id,
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)
    
    db.commit()
    db.refresh(client)
    
    return client


# --- Document Routes (Client-Scoped) ---

import os
import uuid as uuid_lib
from app.models.document import Document, DocumentType, DocumentStatus
from app.schemas import DocumentResponse
from app.config import get_settings

settings = get_settings()

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


@router.post("/{client_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    client_id: UUID,
    file: UploadFile = File(...),
    doc_type: DocumentType = Form(DocumentType.OTHER),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a document for a client.
    Accepts PDF, CSV, XLSX files. Max size 10MB.
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
        
    # Validate file size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    
    if size > 10 * 1024 * 1024: # 10MB limit
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 10MB.",
        )
    
    # Save file
    storage_url = save_file(file, current_user.org_id, str(client_id))
    
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


@router.get("/{client_id}/documents", response_model=List[DocumentResponse])
async def list_client_documents(
    client_id: UUID,
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
