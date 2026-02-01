from typing import List
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.reconciliation_run import ReconciliationRun, RunStatus
from app.models.issue import Issue
from app.models.report import Report
from app.models.client import Client
from app.models.user import User
from app.auth import get_current_user
from app.schemas import RunResponse, IssueResponse, ReportResponse

router = APIRouter()


@router.post("/clients/{client_id}/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start a new reconciliation run for a client.
    This enqueues the reconciliation workflow for background processing.
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
    
    # Check for running reconciliation
    running = db.query(ReconciliationRun).filter(
        ReconciliationRun.client_id == client_id,
        ReconciliationRun.status == RunStatus.RUNNING,
    ).first()
    
    if running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A reconciliation is already running for this client",
        )
    
    # Create run record
    run = ReconciliationRun(
        client_id=client_id,
        status=RunStatus.PENDING,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    # Enqueue Celery task
    from app.tasks.reconciliation import run_reconciliation_task
    task = run_reconciliation_task.delay(str(client_id), str(run.id))
    
    return run


@router.get("/clients/{client_id}/runs", response_model=List[RunResponse])
async def list_client_runs(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all reconciliation runs for a client.
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
    
    runs = db.query(ReconciliationRun).filter(
        ReconciliationRun.client_id == client_id
    ).order_by(ReconciliationRun.created_at.desc()).all()
    
    return runs


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific reconciliation run by ID.
    """
    run = db.query(ReconciliationRun).join(Client).filter(
        ReconciliationRun.id == run_id,
        Client.org_id == current_user.org_id,
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    
    return run


@router.get("/{run_id}/issues", response_model=List[IssueResponse])
async def get_run_issues(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all issues detected in a reconciliation run.
    """
    run = db.query(ReconciliationRun).join(Client).filter(
        ReconciliationRun.id == run_id,
        Client.org_id == current_user.org_id,
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    
    issues = db.query(Issue).filter(Issue.run_id == run_id).all()
    return issues


@router.get("/{run_id}/reports", response_model=List[ReportResponse])
async def get_run_reports(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all reports generated for a reconciliation run.
    """
    run = db.query(ReconciliationRun).join(Client).filter(
        ReconciliationRun.id == run_id,
        Client.org_id == current_user.org_id,
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    
    reports = db.query(Report).filter(Report.run_id == run_id).all()
    return reports
