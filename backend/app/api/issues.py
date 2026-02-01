from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.issue import Issue, IssueStatus
from app.models.client import Client
from app.models.user import User
from app.auth import get_current_user
from app.schemas import IssueResponse, IssueStatusUpdate

router = APIRouter()


@router.get("/clients/{client_id}/issues", response_model=List[IssueResponse])
async def list_client_issues(
    client_id: UUID,
    severity: str = None,
    category: str = None,
    issue_status: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all issues for a client with optional filters.
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
    
    query = db.query(Issue).filter(Issue.client_id == client_id)
    
    if severity:
        query = query.filter(Issue.severity == severity)
    if category:
        query = query.filter(Issue.category == category)
    if issue_status:
        query = query.filter(Issue.status == issue_status)
    
    issues = query.order_by(Issue.created_at.desc()).all()
    return issues


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(
    issue_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific issue by ID.
    """
    issue = db.query(Issue).join(Client).filter(
        Issue.id == issue_id,
        Client.org_id == current_user.org_id,
    ).first()
    
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    
    return issue


@router.patch("/{issue_id}", response_model=IssueResponse)
async def update_issue_status(
    issue_id: UUID,
    request: IssueStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an issue's status.
    Transitions: open -> accepted -> resolved
    """
    issue = db.query(Issue).join(Client).filter(
        Issue.id == issue_id,
        Client.org_id == current_user.org_id,
    ).first()
    
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    
    # Validate status transition
    valid_transitions = {
        IssueStatus.OPEN: [IssueStatus.ACCEPTED, IssueStatus.RESOLVED],
        IssueStatus.ACCEPTED: [IssueStatus.RESOLVED, IssueStatus.OPEN],
        IssueStatus.RESOLVED: [IssueStatus.OPEN],
    }
    
    if request.status not in valid_transitions.get(issue.status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {issue.status.value} to {request.status.value}",
        )
    
    issue.status = request.status
    db.commit()
    db.refresh(issue)
    
    return issue
