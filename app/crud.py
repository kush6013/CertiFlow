import secrets
from pathlib import Path
from datetime import datetime, date, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import GenerationJob, CertificateRecord, JobStatus, CertificateStatus
from app.schemas import BulkJobCreateRequest


def generate_unique_cert_code() -> str:
    """Generates an alphanumeric certificate verification code, e.g., CERT-A1B2-C3D4."""
    part1 = secrets.token_hex(2).upper()
    part2 = secrets.token_hex(2).upper()
    return f"CERT-{part1}-{part2}"


def create_job_with_recipients(db: Session, job_data: BulkJobCreateRequest) -> GenerationJob:
    """
    Persists a new GenerationJob and all initial CertificateRecord entries in PENDING state.
    """
    issue_date_str = job_data.issue_date or date.today().isoformat()

    job = GenerationJob(
        title=job_data.title,
        issuer_name=job_data.issuer_name,
        issue_date=issue_date_str,
        description=job_data.description,
        status=JobStatus.PENDING,
        total_count=len(job_data.recipients),
        success_count=0,
        failed_count=0,
    )
    db.add(job)
    db.flush()  # Populates job.id

    for recipient in job_data.recipients:
        cert_code = generate_unique_cert_code()
        # Ensure code uniqueness if clash (rare with 32-bit hex space)
        while db.query(CertificateRecord).filter(CertificateRecord.certificate_code == cert_code).first():
            cert_code = generate_unique_cert_code()

        cert_record = CertificateRecord(
            job_id=job.id,
            recipient_name=recipient.name,
            recipient_email=str(recipient.email),
            custom_attributes=recipient.custom_attributes or {},
            status=CertificateStatus.PENDING,
            certificate_code=cert_code,
            file_path=None,
        )
        db.add(cert_record)

    db.commit()
    db.refresh(job)
    return job


def get_job_by_id(db: Session, job_id: str) -> Optional[GenerationJob]:
    return db.query(GenerationJob).filter(GenerationJob.id == job_id).first()


def delete_job(db: Session, job_id: str) -> bool:
    """
    Deletes a job, cascade-deletes certificate records, and removes generated PDF files from disk.
    """
    job = get_job_by_id(db, job_id)
    if not job:
        return False

    # Remove generated PDF files associated with this job
    for cert in job.certificates:
        if cert.file_path:
            try:
                p = Path(cert.file_path)
                if p.exists():
                    p.unlink()
            except OSError:
                pass

    db.delete(job)
    db.commit()
    return True


def list_jobs(db: Session, skip: int = 0, limit: int = 50) -> List[GenerationJob]:
    return (
        db.query(GenerationJob)
        .order_by(GenerationJob.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_certificate_by_id(db: Session, certificate_id: str) -> Optional[CertificateRecord]:
    return db.query(CertificateRecord).filter(CertificateRecord.id == certificate_id).first()


def get_certificate_by_code(db: Session, certificate_code: str) -> Optional[CertificateRecord]:
    return (
        db.query(CertificateRecord)
        .filter(CertificateRecord.certificate_code == certificate_code)
        .first()
    )


def mark_job_processing(db: Session, job_id: str):
    job = get_job_by_id(db, job_id)
    if job:
        now = datetime.now(timezone.utc)
        job.status = JobStatus.PROCESSING
        if not job.started_at:
            job.started_at = now
        job.updated_at = now
        db.commit()


def mark_certificate_processing(db: Session, certificate_id: str):
    cert = get_certificate_by_id(db, certificate_id)
    if cert:
        cert.status = CertificateStatus.PROCESSING
        db.commit()


def mark_certificate_success(db: Session, certificate_id: str, file_path: str):
    cert = get_certificate_by_id(db, certificate_id)
    if cert:
        cert.status = CertificateStatus.SUCCESS
        cert.file_path = file_path
        cert.error_message = None
        cert.generated_at = datetime.now(timezone.utc)
        db.commit()


def mark_certificate_failed(db: Session, certificate_id: str, error_message: str):
    cert = get_certificate_by_id(db, certificate_id)
    if cert:
        cert.status = CertificateStatus.FAILED
        cert.error_message = error_message
        cert.generated_at = datetime.now(timezone.utc)
        db.commit()


def finalize_job(db: Session, job_id: str) -> GenerationJob:
    """
    Calculates final counts and sets job status:
    COMPLETED, PARTIAL_SUCCESS, or FAILED.
    """
    job = get_job_by_id(db, job_id)
    if not job:
        return None

    now = datetime.now(timezone.utc)
    successes = (
        db.query(CertificateRecord)
        .filter(CertificateRecord.job_id == job_id, CertificateRecord.status == CertificateStatus.SUCCESS)
        .count()
    )
    failures = (
        db.query(CertificateRecord)
        .filter(CertificateRecord.job_id == job_id, CertificateRecord.status == CertificateStatus.FAILED)
        .count()
    )

    job.success_count = successes
    job.failed_count = failures
    job.completed_at = now
    job.updated_at = now

    if failures == 0 and successes > 0:
        job.status = JobStatus.COMPLETED
    elif successes > 0 and failures > 0:
        job.status = JobStatus.PARTIAL_SUCCESS
    else:
        job.status = JobStatus.FAILED

    db.commit()
    db.refresh(job)
    return job
