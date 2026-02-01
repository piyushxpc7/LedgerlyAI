"""
Celery task for reconciliation.
"""
import structlog
from app.tasks.celery_app import celery_app
from app.workflows.reconciliation_graph import run_reconciliation
from app.database import SessionLocal
from app.models.reconciliation_run import ReconciliationRun, RunStatus
from uuid import UUID

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def run_reconciliation_task(self, client_id: str, run_id: str):
    """
    Celery task to run reconciliation workflow.
    Supports retries on failure.
    """
    logger.info(
        "Starting reconciliation task",
        client_id=client_id,
        run_id=run_id,
        task_id=self.request.id,
    )
    
    try:
        result = run_reconciliation(client_id, run_id)
        
        if result.get("status") == "failed":
            logger.error(
                "Reconciliation failed",
                client_id=client_id,
                run_id=run_id,
                error=result.get("error"),
            )
            raise self.retry(exc=Exception(result.get("error")))
        
        logger.info(
            "Reconciliation completed",
            client_id=client_id,
            run_id=run_id,
            status=result.get("status"),
            metrics=result.get("metrics"),
        )
        
        return result
    
    except Exception as exc:
        logger.error(
            "Reconciliation task error",
            client_id=client_id,
            run_id=run_id,
            error=str(exc),
        )
        
        # Update run status to failed after max retries
        if self.request.retries >= self.max_retries:
            db = SessionLocal()
            try:
                run = db.query(ReconciliationRun).filter(ReconciliationRun.id == UUID(run_id)).first()
                if run:
                    run.status = RunStatus.FAILED
                    run.metrics_json = {"error": str(exc)}
                    db.commit()
            finally:
                db.close()
        
        raise
