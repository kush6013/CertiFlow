import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from app.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class CertificateStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    issuer_name = Column(String(255), nullable=False)
    issue_date = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    total_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    certificates = relationship(
        "CertificateRecord",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="CertificateRecord.created_at"
    )

    def to_dict(self):
        progress = 0.0
        if self.total_count > 0:
            progress = round(((self.success_count + self.failed_count) / self.total_count) * 100, 1)

        return {
            "id": self.id,
            "title": self.title,
            "issuer_name": self.issuer_name,
            "issue_date": self.issue_date,
            "description": self.description,
            "status": self.status.value if isinstance(self.status, JobStatus) else self.status,
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "progress_percent": progress,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CertificateRecord(Base):
    __tablename__ = "certificates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("generation_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    recipient_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    custom_attributes = Column(JSON, default=dict, nullable=False)
    
    status = Column(SQLEnum(CertificateStatus), default=CertificateStatus.PENDING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    
    certificate_code = Column(String(64), unique=True, nullable=False, index=True)
    file_path = Column(String(512), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    job = relationship("GenerationJob", back_populates="certificates")

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "recipient_name": self.recipient_name,
            "recipient_email": self.recipient_email,
            "custom_attributes": self.custom_attributes or {},
            "status": self.status.value if isinstance(self.status, CertificateStatus) else self.status,
            "error_message": self.error_message,
            "certificate_code": self.certificate_code,
            "file_path": self.file_path,
            "has_file": bool(self.file_path),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }
