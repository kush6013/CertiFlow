from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class RecipientInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Full name of recipient")
    email: EmailStr = Field(..., description="Valid email address of recipient")
    custom_attributes: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional recipient metadata e.g. grade, score, course track"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Recipient name cannot be blank or only whitespace")
        return clean


class BulkJobCreateRequest(BaseModel):
    title: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Certificate title / event / course name",
        examples=["Advanced Full Stack Engineering Certificate"]
    )
    issuer_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Organization or person issuing the certificate",
        examples=["Global Tech Institute"]
    )
    issue_date: Optional[str] = Field(
        default=None,
        description="Date of issuance (e.g. '2026-10-07' or 'October 7, 2026'). Defaults to today.",
        examples=["2026-10-07"]
    )
    description: Optional[str] = Field(
        default="For demonstrated excellence and successful completion of all program requirements.",
        max_length=1000,
        description="Certificate body description text"
    )
    recipients: List[RecipientInput] = Field(
        ...,
        min_length=1,
        description="List of recipients to generate certificates for"
    )

    @field_validator("title", "issuer_name")
    @classmethod
    def strip_text(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Field cannot be empty or only whitespace")
        return clean


class CertificateResponse(BaseModel):
    id: str
    job_id: str
    recipient_name: str
    recipient_email: str
    custom_attributes: Dict[str, Any]
    status: str
    error_message: Optional[str] = None
    certificate_code: str
    download_url: Optional[str] = None
    created_at: Optional[str] = None
    generated_at: Optional[str] = None


class JobSummaryResponse(BaseModel):
    id: str
    title: str
    issuer_name: str
    issue_date: str
    description: Optional[str] = None
    status: str
    total_count: int
    success_count: int
    failed_count: int
    progress_percent: float
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    updated_at: Optional[str] = None


class JobDetailResponse(JobSummaryResponse):
    certificates: List[CertificateResponse] = []


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    message: str
    total_count: int
    check_status_url: str


class CertificateVerificationResponse(BaseModel):
    valid: bool
    certificate_code: str
    recipient_name: Optional[str] = None
    title: Optional[str] = None
    issuer_name: Optional[str] = None
    issue_date: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None
    generated_at: Optional[str] = None
    message: str
