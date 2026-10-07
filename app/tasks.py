import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.crud import (
    get_job_by_id,
    mark_job_processing,
    mark_certificate_processing,
    mark_certificate_success,
    mark_certificate_failed,
    finalize_job,
)
from app.generator import generate_certificate_pdf

logger = logging.getLogger("certificate_generator.tasks")


def process_bulk_certificate_job(job_id: str, db: Optional[Session] = None):
    """
    Worker task to process a certificate generation job.
    Fault isolation: A failure on any individual certificate does not abort the job.
    """
    owns_session = False
    if db is None:
        db = SessionLocal()
        owns_session = True
    try:
        job = get_job_by_id(db, job_id)
        if not job:
            logger.error("Job %s not found in background processor.", job_id)
            return

        mark_job_processing(db, job_id)
        logger.info("Started processing bulk certificate job: %s (total: %d)", job_id, job.total_count)

        for cert in job.certificates:
            try:
                mark_certificate_processing(db, cert.id)

                # Extra validation check before generation
                if not cert.recipient_name or not cert.recipient_name.strip():
                    raise ValueError("Recipient name is missing or blank.")

                if not cert.recipient_email or "@" not in cert.recipient_email:
                    raise ValueError(f"Invalid email address: {cert.recipient_email}")

                # Call the certificate template rendering engine
                pdf_path = generate_certificate_pdf(
                    certificate_code=cert.certificate_code,
                    recipient_name=cert.recipient_name,
                    title=job.title,
                    issuer_name=job.issuer_name,
                    issue_date=job.issue_date,
                    description=job.description,
                    custom_attributes=cert.custom_attributes,
                )

                mark_certificate_success(db, cert.id, pdf_path)
                logger.info("Successfully generated certificate %s for %s", cert.certificate_code, cert.recipient_name)

            except Exception as e:
                err_msg = str(e)
                logger.warning("Failed generating certificate for %s (ID: %s): %s", cert.recipient_name, cert.id, err_msg)
                mark_certificate_failed(db, cert.id, err_msg)

        # Finalize job status (COMPLETED, PARTIAL_SUCCESS, or FAILED)
        final_job = finalize_job(db, job_id)
        logger.info(
            "Completed bulk certificate job %s. Status: %s (Success: %d, Failed: %d)",
            job_id,
            final_job.status.value,
            final_job.success_count,
            final_job.failed_count,
        )

    except Exception as exc:
        logger.exception("Critical error in job %s execution: %s", job_id, exc)
    finally:
        if owns_session and db is not None:
            db.close()
