import os
import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.crud import get_certificate_by_id, get_certificate_by_code
from app.schemas import CertificateResponse, CertificateVerificationResponse
from app.models import CertificateStatus
from app.config import STORAGE_DIR

router = APIRouter(prefix="/certificates", tags=["Certificates"])


def _sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\-_.]", "_", name)


@router.get(
    "/{certificate_id}",
    response_model=CertificateResponse,
    summary="Get individual certificate details"
)
def get_certificate_details(certificate_id: str, db: Session = Depends(get_db)):
    cert = get_certificate_by_id(db, certificate_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' not found."
        )

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


@router.get(
    "/{certificate_id}/download",
    summary="Download certificate PDF"
)
def download_certificate(certificate_id: str, db: Session = Depends(get_db)):
    cert = get_certificate_by_id(db, certificate_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' not found."
        )

    if cert.status != CertificateStatus.SUCCESS or not cert.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificate is not ready for download. Current status: {cert.status.value}. Error: {cert.error_message or 'None'}"
        )

    file_path = Path(cert.file_path).resolve()
    storage_root = STORAGE_DIR.resolve()
    try:
        file_path.relative_to(storage_root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to certificate file path is restricted."
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate PDF file is missing from storage."
        )

    download_name = f"{_sanitize_filename(cert.recipient_name)}_{cert.certificate_code}.pdf"

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=download_name,
        headers={"Content-Disposition": f'inline; filename="{download_name}"'}
    )


@router.get(
    "/verify/{certificate_code}",
    response_model=CertificateVerificationResponse,
    summary="Verify authenticity of a certificate using its verification code"
)
def verify_certificate(certificate_code: str, db: Session = Depends(get_db)):
    clean_code = certificate_code.strip()
    cert = get_certificate_by_code(db, clean_code)
    if not cert:
        return CertificateVerificationResponse(
            valid=False,
            certificate_code=clean_code,
            message="Certificate record not found. This credential could not be verified."
        )

    if cert.status != CertificateStatus.SUCCESS:
        return CertificateVerificationResponse(
            valid=False,
            certificate_code=clean_code,
            recipient_name=cert.recipient_name,
            message=f"Certificate is unverified. Status: {cert.status.value}."
        )

    # Filter out internal keys starting with underscore
    clean_attrs = {k: v for k, v in (cert.custom_attributes or {}).items() if not k.startswith("_")}

    return CertificateVerificationResponse(
        valid=True,
        certificate_code=cert.certificate_code,
        recipient_name=cert.recipient_name,
        title=cert.job.title if cert.job else None,
        issuer_name=cert.job.issuer_name if cert.job else None,
        issue_date=cert.job.issue_date if cert.job else None,
        custom_attributes=clean_attrs,
        generated_at=cert.generated_at.isoformat() if cert.generated_at else None,
        message="Authentic certificate verified successfully."
    )
