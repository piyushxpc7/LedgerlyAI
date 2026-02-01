from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.org import Org
from app.models.user import User, UserRole
from app.auth import hash_password, verify_password, create_access_token, TokenData, get_current_user
from app.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new organization with admin user.
    This creates a new org and the first admin user.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create organization
    org = Org(name=request.org_name)
    db.add(org)
    db.flush()
    
    # Create admin user
    user = User(
        org_id=org.id,
        email=request.email,
        password_hash=hash_password(request.password),
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate token
    token_data = TokenData(
        user_id=user.id,
        org_id=org.id,
        email=user.email,
        role=user.role.value,
    )
    access_token = create_access_token(token_data)
    
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.
    Returns a JWT access token.
    """
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    token_data = TokenData(
        user_id=user.id,
        org_id=user.org_id,
        email=user.email,
        role=user.role.value,
    )
    access_token = create_access_token(token_data)
    
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get the current authenticated user's information.
    """
    return current_user
