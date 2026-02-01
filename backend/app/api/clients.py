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
