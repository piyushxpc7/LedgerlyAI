"""
Celery task for document ingestion.
"""
import structlog
from app.tasks.celery_app import celery_app
from app.workflows.ingestion_graph import run_ingestion
from app.database import SessionLocal
from app.models.document import Document, DocumentStatus
from uuid import UUID

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_ingestion_task(self, document_id: str):
    """
    Celery task to run document ingestion workflow.
    Supports retries on failure.
    """
    logger.info("Starting ingestion task", document_id=document_id, task_id=self.request.id)
    
    try:
        result = run_ingestion(document_id)
        
        if result.get("status") == "failed":
            logger.error(
                "Ingestion failed",
                document_id=document_id,
                error=result.get("error"),
            )
            # Retry on failure
            raise self.retry(exc=Exception(result.get("error")))
        
        logger.info(
            "Ingestion completed",
            document_id=document_id,
            status=result.get("status"),
            records_count=result.get("records_count"),
        )
        
        return result
    
    except Exception as exc:
        logger.error(
            "Ingestion task error",
            document_id=document_id,
            error=str(exc),
        )
        
        # Update document status to failed after max retries
        if self.request.retries >= self.max_retries:
            db = SessionLocal()
            try:
                doc = db.query(Document).filter(Document.id == UUID(document_id)).first()
                if doc:
                    doc.status = DocumentStatus.FAILED
                    doc.meta = {"error": str(exc)}
                    db.commit()
            finally:
                db.close()
        
        raise
