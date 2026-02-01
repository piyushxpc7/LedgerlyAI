from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.auth import get_current_user, require_admin, hash_password
from app.schemas import UserResponse, UserCreateRequest

router = APIRouter()


@router.get("", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all users in the current organization.
    """
    users = db.query(User).filter(User.org_id == current_user.org_id).all()
    return users


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new user in the organization (admin only).
    """
    # Check if email already exists
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    user = User(
        org_id=admin_user.org_id,
        email=request.email,
        password_hash=hash_password(request.password),
        role=UserRole(request.role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user
