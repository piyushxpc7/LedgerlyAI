from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from uuid import UUID
from enum import Enum


# ===== Enums =====
class UserRole(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"


class DocumentType(str, Enum):
    BANK = "bank"
    INVOICE = "invoice"
    GST = "gst"
    TDS = "tds"
    OTHER = "other"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class TransactionSource(str, Enum):
    BANK = "bank"
    INVOICE = "invoice"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class IssueSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "med"
    HIGH = "high"


class IssueCategory(str, Enum):
    MISSING_INVOICE = "missing_invoice"
    DUPLICATE = "duplicate"
    MISMATCH = "mismatch"
    GST_MISMATCH = "gst_mismatch"
    OTHER = "other"


class IssueStatus(str, Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    RESOLVED = "resolved"


class ReportType(str, Enum):
    WORKING_PAPERS = "working_papers"
    COMPLIANCE_SUMMARY = "compliance_summary"


# ===== Auth Schemas =====
class RegisterRequest(BaseModel):
    org_name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    org_id: UUID
    email: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.STAFF


# ===== Org Schemas =====
class OrgResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Client Schemas =====
class ClientCreate(BaseModel):
    name: str
    gstin: Optional[str] = None
    pan: Optional[str] = None
    fy: Optional[str] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    fy: Optional[str] = None


class ClientResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    gstin: Optional[str]
    pan: Optional[str]
    fy: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Document Schemas =====
class DocumentResponse(BaseModel):
    id: UUID
    org_id: UUID
    client_id: UUID
    type: DocumentType
    filename: str
    status: DocumentStatus
    uploaded_at: datetime
    meta: Optional[dict] = None

    class Config:
        from_attributes = True


class DocumentTypeUpdate(BaseModel):
    type: DocumentType


# ===== Transaction Schemas =====
class TransactionResponse(BaseModel):
    id: UUID
    client_id: UUID
    source: TransactionSource
    txn_date: datetime
    amount: float
    description: Optional[str]
    counterparty: Optional[str]
    reference_id: Optional[str]
    meta_json: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


# ===== GST Summary Schemas =====
class GSTSummaryResponse(BaseModel):
    id: UUID
    client_id: UUID
    period: str
    taxable_value: float
    tax_amount: float
    meta_json: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Reconciliation Run Schemas =====
class RunCreate(BaseModel):
    pass  # No fields needed to create a run


class RunResponse(BaseModel):
    id: UUID
    client_id: UUID
    status: RunStatus
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    metrics_json: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Issue Schemas =====
class IssueResponse(BaseModel):
    id: UUID
    client_id: UUID
    run_id: UUID
    severity: IssueSeverity
    category: IssueCategory
    title: str
    details_json: Optional[dict]
    status: IssueStatus
    created_at: datetime

    class Config:
        from_attributes = True


class IssueStatusUpdate(BaseModel):
    status: IssueStatus


# ===== Report Schemas =====
class ReportResponse(BaseModel):
    id: UUID
    client_id: UUID
    run_id: UUID
    type: ReportType
    content_md: str
    content_pdf_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Audit Log Schemas =====
class AuditLogResponse(BaseModel):
    id: UUID
    org_id: UUID
    user_id: Optional[UUID]
    action: str
    target_type: str
    target_id: Optional[UUID]
    meta_json: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Pagination =====
class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    per_page: int
