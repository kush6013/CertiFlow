import io
import zipfile
import re
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    BulkJobCreateRequest,
    JobCreateResponse,
    JobDetailResponse,
    JobSummaryResponse,
    CertificateResponse,
)
from app.crud import (
    create_job_with_recipients,
    get_job_by_id,
    list_jobs,
)
from app.tasks import process_bulk_certificate_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _sanitize_filename(name: str) -> str:
    """Sanitize strings for safe filenames."""
    return re.sub(r"[^\w\-_.]", "_", name)


def _format_certificate_response(cert, base_url: str = "") -> CertificateResponse:
    download_url = f"/api/v1/certificates/{cert.id}/download" if cert.file_path else None
    return CertificateResponse(
        id=cert.id,
        job_id=cert.job_id,
        recipient_name=cert.recipient_name,
        recipient_email=cert.recipient_email,
        custom_attributes=cert.custom_attributes or {},
        status=cert.status.value if hasattr(cert.status, "value") else str(cert.status),
        error_message=cert.error_message,
        certificate_code=cert.certificate_code,
        download_url=download_url,
        created_at=cert.created_at.isoformat() if cert.created_at else None,
        generated_at=cert.generated_at.isoformat() if cert.generated_at else None,
    )


@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a bulk certificate generation job",
    description="Accepts a bulk recipient list, validates input, queues generation in the background, and returns the job ID."
)
def create_bulk_job(
    job_in: BulkJobCreateRequest,
    background_tasks: BackgroundTasks,
    sync: bool = Query(False, description="Process synchronously instead of in background (useful for test suites or small batches)"),
    db: Session = Depends(get_db)
):
    job = create_job_with_recipients(db, job_in)

    if sync:
        # Run immediately in-thread
        process_bulk_certificate_job(job.id, db=db)
        db.refresh(job)
        message = f"Certificate generation job created and processed synchronously ({job.total_count} recipients)."
    else:
        # Queue in background task runner
        background_tasks.add_task(process_bulk_certificate_job, job.id)
        message = f"Certificate generation job accepted for background processing ({job.total_count} recipients)."

    return JobCreateResponse(
        job_id=job.id,
        status=job.status.value if hasattr(job.status, "value") else str(job.status),
        message=message,
        total_count=job.total_count,
        check_status_url=f"/api/v1/jobs/{job.id}"
    )


@router.get(
    "",
    response_model=List[JobSummaryResponse],
    summary="List all certificate generation jobs"
)
def get_all_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    jobs = list_jobs(db, skip=skip, limit=limit)
    return [
        JobSummaryResponse(
            id=j.id,
            title=j.title,
            issuer_name=j.issuer_name,
            issue_date=j.issue_date,
            description=j.description,
            status=j.status.value if hasattr(j.status, "value") else str(j.status),
            total_count=j.total_count,
            success_count=j.success_count,
            failed_count=j.failed_count,
            progress_percent=round(((j.success_count + j.failed_count) / j.total_count * 100), 1) if j.total_count > 0 else 0,
            created_at=j.created_at.isoformat() if j.created_at else None,
            started_at=j.started_at.isoformat() if j.started_at else None,
            completed_at=j.completed_at.isoformat() if j.completed_at else None,
            updated_at=j.updated_at.isoformat() if j.updated_at else None,
        )
        for j in jobs
    ]


@router.get(
    "/{job_id}",
    response_model=JobDetailResponse,
    summary="Get job status, progress, and certificates"
)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID '{job_id}' not found.")

    progress = 0.0
    if job.total_count > 0:
        progress = round(((job.success_count + job.failed_count) / job.total_count) * 100, 1)

    formatted_certs = [_format_certificate_response(c) for c in job.certificates]

    return JobDetailResponse(
        id=job.id,
        title=job.title,
        issuer_name=job.issuer_name,
        issue_date=job.issue_date,
        description=job.description,
        status=job.status.value if hasattr(job.status, "value") else str(job.status),
        total_count=job.total_count,
        success_count=job.success_count,
        failed_count=job.failed_count,
        progress_percent=progress,
        created_at=job.created_at.isoformat() if job.created_at else None,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        updated_at=job.updated_at.isoformat() if job.updated_at else None,
        certificates=formatted_certs,
    )


@router.get(
    "/{job_id}/download",
    summary="Download all generated certificates as a ZIP archive"
)
def download_job_certificates_zip(job_id: str, db: Session = Depends(get_db)):
    job = get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID '{job_id}' not found.")

    successful_certs = [c for c in job.certificates if c.file_path and c.status.value == "success"]
    if not successful_certs:
        raise HTTPException(
            status_code=400,
            detail="No completed certificates are available to download for this job yet."
        )

    # Build ZIP archive in memory (suitable for moderate bulk job sizes)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for cert in successful_certs:
            safe_name = _sanitize_filename(cert.recipient_name)
            zip_entry_name = f"{safe_name}_{cert.certificate_code}.pdf"
            cert_path = Path(cert.file_path)
            if cert_path.exists():
                zf.write(str(cert_path), arcname=zip_entry_name)

    zip_buffer.seek(0)
    zip_filename = f"{_sanitize_filename(job.title)}_certificates.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )
