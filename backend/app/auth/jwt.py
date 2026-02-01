from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from pydantic import BaseModel
from uuid import UUID

from app.config import get_settings

settings = get_settings()


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: str
    org_id: str
    email: str
    role: str
    exp: Optional[datetime] = None


def create_access_token(data: TokenData) -> str:
    """Create a JWT access token."""
    to_encode = {
        "user_id": str(data.user_id),
        "org_id": str(data.org_id),
        "email": data.email,
        "role": data.role,
    }
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode["exp"] = expire
    
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenData(
            user_id=str(payload["user_id"]),
            org_id=str(payload["org_id"]),
            email=payload["email"],
            role=payload["role"],
            exp=datetime.fromtimestamp(payload["exp"]),
        )
    except JWTError:
        return None
