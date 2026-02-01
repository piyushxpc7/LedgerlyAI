import os
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.report import Report
from app.models.client import Client
from app.models.user import User
from app.auth.deps import get_current_user_optional_token
from app.schemas import ReportResponse

router = APIRouter()


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific report by ID.
    Returns the markdown content.
    """
    report = db.query(Report).join(Client).filter(
        Report.id == report_id,
        Client.org_id == current_user.org_id,
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    
    return report


@router.get("/{report_id}/markdown")
async def get_report_markdown(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get report content as raw markdown.
    """
    report = db.query(Report).join(Client).filter(
        Report.id == report_id,
        Client.org_id == current_user.org_id,
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    
    return Response(
        content=report.content_md,
        media_type="text/markdown",
        headers={"Content-Disposition": f"inline; filename=report-{report_id}.md"},
    )


@router.get("/{report_id}/download")
async def download_report_pdf(
    report_id: UUID,
    current_user: User = Depends(get_current_user_optional_token),
    db: Session = Depends(get_db),
):
    """
    Download report as PDF.
    If PDF doesn't exist, generates it on-the-fly.
    """
    report = db.query(Report).join(Client).filter(
        Report.id == report_id,
        Client.org_id == current_user.org_id,
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    
    # Check if PDF exists
    if report.content_pdf_url and os.path.exists(report.content_pdf_url):
        return FileResponse(
            report.content_pdf_url,
            media_type="application/pdf",
            filename=f"report-{report_id}.pdf",
        )
    
    # Generate PDF on-the-fly
    from app.services.pdf_generator import generate_pdf_from_markdown
    
    pdf_path = generate_pdf_from_markdown(
        report.content_md,
        str(report.id),
        str(report.client_id),
    )
    
    # Update report with PDF path
    report.content_pdf_url = pdf_path
    db.commit()
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"report-{report_id}.pdf",
    )
