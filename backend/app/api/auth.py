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


# --- Google OAuth ---
from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from starlette.responses import RedirectResponse
from app.config import get_settings

settings = get_settings()
oauth = OAuth()

oauth.register(
    name='google',
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@router.get("/login/google")
async def google_login(request: Request):
    """Initiate Google OAuth login."""
    redirect_uri = f"{settings.next_public_api_url}/auth/google" if hasattr(settings, 'next_public_api_url') else "http://localhost:8000/auth/google"
    # Handling potential mismatch in settings name or hardcoding for safety if config not updated perfectly yet
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google", name="google_callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        # If token exchange fails
        return RedirectResponse(f"{settings.frontend_url}/login?error=auth_failed")

    user_info = token.get('userinfo')
    if not user_info:
        user_info = await oauth.google.userinfo(token=token)
        
    email = user_info.get('email')
    if not email:
        return RedirectResponse(f"{settings.frontend_url}/login?error=no_email")

    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Create new user and org
        # Use email domain or name as org name
        org_name = user_info.get('name', 'My Organization') + "'s Org"
        
        org = Org(name=org_name)
        db.add(org)
        db.flush()
        
        import secrets
        random_password = secrets.token_urlsafe(16)
        
        user = User(
            org_id=org.id,
            email=email,
            password_hash=hash_password(random_password), # Set unusable password
            role=UserRole.ADMIN, # First user via Google is Admin of their own org
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Generate JWT
    token_data = TokenData(
        user_id=user.id,
        org_id=user.org_id,
        email=user.email,
        role=user.role.value,
    )
    access_token = create_access_token(token_data)
    
    # Redirect to frontend with token
    return RedirectResponse(f"{settings.frontend_url}/auth/callback?token={access_token}")
