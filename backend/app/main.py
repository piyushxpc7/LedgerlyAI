import uuid
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.api import auth, orgs, users, clients, documents, runs, issues, reports

settings = get_settings()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    if settings.is_production():
        try:
            settings.validate_production()
        except ValueError as e:
            logger.error("Invalid production config", error=str(e))
            raise
    logger.info("Starting Ledgerly API")
    yield
    logger.info("Shutting down Ledgerly API")


app = FastAPI(
    title="Ledgerly API",
    description="""
    Ledgerly - CA Firm Back-Office Automation
    
    ⚠️ **Disclaimer**: This is a preparation & workflow automation tool. 
    It does NOT file tax returns, certify documents, or provide legal opinions.
    """,
    version="1.0.0",
    lifespan=lifespan,
)

from starlette.middleware.sessions import SessionMiddleware

# CORS middleware - origins from config only (no hardcoded localhost in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware (required for OAuth)
app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add request ID to all requests for tracing."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with logging."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled exception",
        request_id=request_id,
        path=request.url.path,
        error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


# Register routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(orgs.router, prefix="/org", tags=["Organizations"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(clients.router, prefix="/clients", tags=["Clients"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(runs.router, prefix="/runs", tags=["Reconciliation Runs"])
app.include_router(issues.router, prefix="/issues", tags=["Issues"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])


@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ledgerly-api",
        "version": "1.0.0",
    }


@app.get("/me", tags=["Authentication"])
async def get_me(request: Request):
    """Get current user info (placeholder - use /auth/me)."""
    from app.auth.deps import get_current_user
    from app.database import get_db
    # This is a convenience redirect, actual implementation in auth router
    return {"message": "Use /auth/me endpoint"}
