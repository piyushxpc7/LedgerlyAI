from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.org import Org
from app.models.user import User
from app.auth import get_current_user
from app.schemas import OrgResponse

router = APIRouter()


@router.get("", response_model=OrgResponse)
async def get_org(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the current user's organization.
    """
    org = db.query(Org).filter(Org.id == current_user.org_id).first()
    return org
