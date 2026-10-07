# CertiFlow — Bulk Certificate Generation & Verification Platform 🎓

An interview-ready, production-oriented backend API and verification platform built with **Python**, **FastAPI**, **SQLAlchemy**, and **ReportLab**. CertiFlow accepts bulk certificate generation requests for lists of recipients, renders high-resolution vector PDF certificates via a predefined template, tracks job-level and certificate-level progress asynchronously, isolates individual recipient failures, and provides unified retrieval, ZIP batch packaging, and public verification endpoints.

---

## 📋 Table of Contents
1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Key Features](#3-key-features)
4. [Architecture](#4-architecture)
5. [Tech Stack](#5-tech-stack)
6. [API Endpoints](#6-api-endpoints)
7. [Job Lifecycle](#7-job-lifecycle)
8. [Certificate Lifecycle](#8-certificate-lifecycle)
9. [Failure Isolation](#9-failure-isolation)
10. [Input Validation](#10-input-validation)
11. [Security Considerations](#11-security-considerations)
12. [Database & Session Handling](#12-database--session-handling)
13. [PDF Generation Quality](#13-pdf-generation-quality)
14. [Automated Testing](#14-automated-testing)
15. [Running Locally](#15-running-locally)
16. [API Examples](#16-api-examples)
17. [Dashboard & Console](#17-dashboard--console)
18. [Current Limitations & Database Migration Note](#18-current-limitations--database-migration-note)
19. [Production Scaling Roadmap](#19-production-scaling-roadmap)
20. [Interview Talking Points](#20-interview-talking-points)

---

## 1. Project Overview

**CertiFlow** is an interview-ready, production-oriented backend application designed to automate credential issuance for events, courses, and workshops. It handles the complete lifecycle from ingestion and schema validation to vector PDF generation, fault-isolated background processing, in-memory ZIP archiving, and public credential verification.

---

## 2. Problem Statement

Organizations regularly need to issue verified credentials to participants following training programs, conferences, or academic courses. Generating certificates one-by-one introduces high latency, blocks HTTP client connections, and risks whole-batch crashes if a single participant record is malformed.

CertiFlow solves this by:
- Ingesting entire participant lists in a single request and returning HTTP `202 Accepted` immediately.
- Processing certificate rendering asynchronously in the background.
- Isolating errors per recipient so corrupted records do not abort valid certificates.
- Offering both individual PDF downloads and batch ZIP archives.
- Providing a secure public verification endpoint that confirms authenticity without exposing recipient emails or filesystem paths.

---

## 3. Key Features

- **Bulk Submission**: Accept lists of recipients with optional custom metadata (e.g. `grade`, `score`, `track`).
- **Asynchronous Processing**: Immediate return of HTTP `202 Accepted` with a `job_id`, queuing rendering via FastAPI `BackgroundTasks`.
- **Synchronous Mode (`?sync=true`)**: Optional query parameter for automated testing and small batches.
- **Predefined Vector Template**: Sharp landscape A4 PDF with gold/navy geometric borders, vector rosette seal, dynamic font scaling for long names, and secure verification footer.
- **Fault Tolerance**: Per-recipient error isolation ensuring partial successes are recorded accurately (`completed`, `partial_success`, `failed`).
- **Path Traversal Protection**: File download paths are strictly validated to prevent access outside the configured storage directory.
- **Comprehensive Test Suite**: 22 automated tests covering input validation, PDF generation, fault tolerance, timestamps, zip bundling, and verification.
- **Interactive Console**: Built-in dashboard with periodic job status polling with live progress updates.

---

## 4. Architecture

```text
HTTP Request (Client / Dashboard)
       │
       ▼
 [FastAPI Router]
  ├─ GET  /health ──────────────────────► Returns {"status": "ok"}
  ├─ POST /api/v1/jobs ────────────────► Validates via Pydantic V2, saves PENDING job,
  │                                      dispatches background worker, returns 202 Accepted
  ├─ GET  /api/v1/jobs/{id} ───────────► Returns progress %, status, timestamps & certificates
  ├─ GET  /api/v1/jobs/{id}/download ──► Streams on-the-fly ZIP archive of all PDFs
  ├─ GET  /api/v1/certificates/{id}/download ──► Streams individual vector PDF
  └─ GET  /api/v1/certificates/verify/{code} ──► Returns public verification details
       │
       ├─────────────────────────────────┐
       ▼                                 ▼
[SQLAlchemy Relational Store]   [Background Worker (tasks.py)]
  • GenerationJob (1)             • Creates a NEW independent DB session
  • CertificateRecord (N)         • For each certificate:
                                      - Transition to PROCESSING
                                      - Call ReportLab PDF generator
                                      - On success: save path, mark SUCCESS
                                      - On exception: log error, mark FAILED
                                  • Transition job to COMPLETED / PARTIAL_SUCCESS / FAILED
                                  • Sets completed_at timestamp
                                  • Closes worker session safely in finally block
```

---

## 5. Tech Stack

- **Language**: Python 3.12 (compatible with 3.10+)
- **Web Framework**: FastAPI (ASGI, Pydantic V2 integration)
- **Database ORM**: SQLAlchemy 2.0
- **Database Engine**: SQLite (`sqlite:///storage/certificates.db`) with `check_same_thread=False`
- **PDF Engine**: ReportLab (vector graphics, canvas primitives, typography)
- **Testing**: Pytest, pytest-asyncio, HTTPX
- **Server**: Uvicorn ASGI server

---

## 6. API Endpoints

| Method | Endpoint | Description | Status Code |
|---|---|---|---|
| `GET` | `/health` | Simple service availability check | `200 OK` |
| `POST` | `/api/v1/jobs` | Submit a bulk certificate generation job | `202 Accepted` |
| `GET` | `/api/v1/jobs` | List all certificate generation jobs (paginated) | `200 OK` |
| `GET` | `/api/v1/jobs/{job_id}` | Check job progress, status, timestamps, and recipient details | `200 OK` |
| `GET` | `/api/v1/jobs/{job_id}/download` | Download all successfully generated certificates as a ZIP | `200 OK` |
| `GET` | `/api/v1/certificates/{id}` | Retrieve individual certificate metadata | `200 OK` |
| `GET` | `/api/v1/certificates/{id}/download` | Download single certificate PDF | `200 OK` |
| `GET` | `/api/v1/certificates/verify/{code}` | Public verification of certificate authenticity | `200 OK` |

Interactive OpenAPI documentation is accessible at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## 7. Job Lifecycle

```text
       [ pending ]
            │
            ▼ (worker picks up job, sets started_at)
      [ processing ]
            │
            ├──────────────────────┬──────────────────────┐
            ▼                      ▼                      ▼
(all certificates pass)  (some pass, some fail)  (all certificates fail)
            │                      │                      │
            ▼                      ▼                      ▼
      [ completed ]       [ partial_success ]         [ failed ]
            │                      │                      │
            └──────────────────────┴──────────────────────┘
                                   │
                                   ▼
                      (sets completed_at timestamp)
```

- **`created_at`**: Set when the job is accepted and saved.
- **`started_at`**: Set when the background worker begins processing certificates.
- **`completed_at`**: Set when all recipients in the batch have been processed.
- **`updated_at`**: Updated on every state transition.

---

## 8. Certificate Lifecycle

Each recipient record maintains an independent lifecycle:

```text
[ pending ] ──► [ processing ] ──► [ success ] (PDF path saved, generated_at set)
                               └──► [ failed ]  (safe error message captured)
```

---

## 9. Failure Isolation

Generating a batch of certificates never fails completely because a single certificate encounters an error:
- Each recipient is processed inside an individual `try...except` boundary in `app/tasks.py`.
- If an exception occurs:
  - That certificate record is updated to `status="failed"`.
  - A descriptive, sanitized error message is stored in `CertificateRecord.error_message`.
  - Remaining recipients continue processing without interruption.
- The parent job status transitions to:
  - `completed`: 100% of certificates generated successfully.
  - `partial_success`: At least one certificate succeeded and at least one failed.
  - `failed`: All certificates in the job failed.

---

## 10. Input Validation

Pydantic V2 models validate input upfront:
- **Title & Issuer Name**: Required, stripped of leading/trailing whitespace, minimum 2 characters.
- **Recipients List**: Non-empty list of recipient objects.
- **Recipient Name**: Required, non-empty, stripped of whitespace.
- **Recipient Email**: Validated according to RFC email specifications via Pydantic `EmailStr`.
- **Custom Attributes**: Optional dictionary for recipient metadata (e.g., `grade`, `track`, `score`).

Malformed payloads are rejected immediately with HTTP `422 Unprocessable Entity` before any database records or background jobs are created.

---

## 11. Security Considerations

- **Path Traversal Defense**: File download routes resolve target paths against `STORAGE_DIR.resolve()`. If a path attempts to escape the storage root, access is denied with HTTP `403 Forbidden`.
- **Credential Privacy**: The public verification endpoint (`/api/v1/certificates/verify/{code}`) reveals only verification details (`valid`, `recipient_name`, `title`, `issuer_name`, `issue_date`). Recipient emails, local filesystem paths, and internal errors are never exposed publicly.
- **Cryptographic Verification Codes**: Certificate codes use random hexadecimal tokens (`CERT-XXXX-XXXX`) generated via Python's `secrets` module, preventing sequential guessing.

---

## 12. Database & Session Handling

A critical engineering decision is the decoupling of database sessions between HTTP request handlers and background tasks:
1. **Request Lifecycle**: The HTTP handler opens a request-scoped database session, saves the `GenerationJob` and `CertificateRecord` rows in `PENDING` state, and commits the transaction.
2. **Worker Scheduling**: Only the primitive `job_id` (string UUID) is passed to `background_tasks.add_task(process_bulk_certificate_job, job.id)`. No SQLAlchemy session or ORM objects are shared across threads.
3. **Worker Lifecycle**: The background worker creates a new, independent `SessionLocal()`, loads the job by ID, processes the batch, and reliably closes the session inside a `finally` block.

---

## 13. PDF Generation Quality

Certificates are rendered using ReportLab vector graphics rather than raster images:
- **Print Quality**: Vector borders, geometric ornaments, and fonts scale cleanly to print resolutions without pixelation.
- **Compact File Size**: Each vector PDF is approximately 4 KB.
- **Dynamic Font Scaling**: Recipient names exceeding 26 characters dynamically scale down font sizes (`name_font_size = max(18, int(34 * 26 / len(recipient_name)))`) and adjust the decorative underline width to prevent text from overflowing outer borders.
- **Long Text Wrapping**: Course descriptions longer than 90 characters are wrapped across multiple balanced lines.

---

## 14. Automated Testing

The project includes 22 automated tests covering all critical workflows:

```bash
.venv/bin/pytest -v
```

**Test Coverage Summary:**
- `test_jobs.py`: Asynchronous job creation (`202 Accepted`), synchronous mode, pagination, non-existent job handling, single-recipient job completion (Case D), and timestamp lifecycle verification.
- `test_validation.py`: Empty payloads, blank titles, empty recipient lists, invalid email formats, and whitespace-only names.
- `test_generator.py`: PDF creation, binary header validation, long descriptions, simulated rendering failures, and dynamic long-name scaling.
- `test_fault_tolerance.py`: Partial failure isolation (Case B) and all-failure handling (Case C).
- `test_retrieval.py`: Individual PDF download, bulk ZIP download and in-memory archive extraction, verification with valid/invalid/padded codes, and `/health` check.

All tests execute in an isolated environment with temporary SQLite databases and storage directories.

---

## 15. Running Locally

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Virtual environment tool (`venv`)

### 1. Setup Environment
```bash
# Clone or navigate to the repository
cd /home/pinkee-sharma/projects/p1

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Start the Server
```bash
# Using the convenience runner:
python run.py

# Or directly via uvicorn:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Web Dashboard**: [http://localhost:8000/](http://localhost:8000/)
- **Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 16. API Examples

### Submit a Bulk Job
```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Full-Stack Software Architecture",
    "issuer_name": "Tech Academy Global",
    "issue_date": "2026-10-07",
    "description": "For demonstrated excellence in distributed systems.",
    "recipients": [
      {
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "custom_attributes": {"grade": "Distinction", "track": "Backend"}
      },
      {
        "name": "Bob Smith",
        "email": "bob@example.com",
        "custom_attributes": {"grade": "Honors", "track": "Cloud"}
      }
    ]
  }'
```

**Response (HTTP 202 Accepted):**
```json
{
  "job_id": "1431a953-b43b-4775-9e0a-5c67cd68b022",
  "status": "pending",
  "message": "Certificate generation job accepted for background processing (2 recipients).",
  "total_count": 2,
  "check_status_url": "/api/v1/jobs/1431a953-b43b-4775-9e0a-5c67cd68b022"
}
```

### Check Job Progress
```bash
curl "http://localhost:8000/api/v1/jobs/1431a953-b43b-4775-9e0a-5c67cd68b022"
```

### Download Individual Certificate
```bash
curl -O -J "http://localhost:8000/api/v1/certificates/<certificate_id>/download"
```

### Download Bulk ZIP Archive
```bash
curl -O -J "http://localhost:8000/api/v1/jobs/<job_id>/download"
```

### Verify Credential
```bash
curl "http://localhost:8000/api/v1/certificates/verify/<certificate_code>"
```

---

## 17. Dashboard & Console

An optional web console is served at `http://localhost:8000/` featuring:
- Preset sample batch loaders (standard batch, bulk batch, mixed fault test).
- Periodic job status polling with live progress updates every 2.5 seconds.
- Modal inspection of recipient certificates with error reasons for failures.
- Direct links for single PDF and batch ZIP downloads.
- Public credential verification dialog.

---

## 18. Current Limitations & Database Migration Note

- **Process-Bound Tasks**: FastAPI `BackgroundTasks` run within the web server process. If the server process is abruptly restarted during a job, interrupted jobs will remain in `processing` state without automatic resumption.
- **In-Memory ZIP**: Batch downloads compile ZIP files in an in-memory `io.BytesIO` buffer. This is suitable for batches of up to a few hundred certificates (~1-5 MB), but very large batches would benefit from streaming disk-backed archives.
- **Local File Storage**: Generated PDFs are stored in the local `storage/certificates/` directory.
- **Database Schema Migrations**: The project currently relies on SQLAlchemy `create_all()` for schema initialization on startup. `create_all()` creates tables that do not exist, but does not perform schema alterations on existing tables. **For production deployments, schema changes should be managed with a migration tool such as Alembic rather than resetting the database.**

---

## 19. Production Scaling Roadmap

To scale CertiFlow for high-volume, multi-tenant production environments, the architecture would evolve as follows:

1. **Durable Task Queue (Celery / RQ with Redis or RabbitMQ)**:
   - Replaces in-process `BackgroundTasks` with distributed workers.
   - Provides persistent message queues, task retries, worker restarts, rate limiting, and priority queues.
2. **PostgreSQL Relational Storage**:
   - Replaces SQLite with a pooled relational database supporting concurrent worker writes and row-level locking.
3. **Cloud Object Storage (AWS S3 / Google Cloud Storage / Cloudflare R2)**:
   - Generated PDFs are uploaded to object storage buckets with presigned download URLs, offloading file bandwidth from the API servers.
4. **Horizontal Worker Scaling**:
   - Decouple API web nodes from PDF worker nodes, scaling worker nodes independently based on queue depth.

---

## 20. Interview Talking Points

When discussing this project during an interview:

### A. Why return HTTP 202 Accepted instead of processing synchronously?
> *"Depending on PDF complexity, batch size, and hardware, synchronous PDF generation can hold HTTP connections open for several seconds and increase timeout risk. Returning HTTP 202 Accepted allows the client to receive a job ID immediately while generation continues in a background task. The client can then poll the status endpoint to monitor progress."*

### B. Why use an independent database session in the background worker?
> *"FastAPI request sessions close when the response finishes. If a background worker shares that session, it causes 'Session is closed' errors. I solved this by passing only the primitive `job_id` into the worker. The worker instantiates its own isolated `SessionLocal()` inside a `try...finally` block, ensuring clean commits and guaranteed closure."*

### C. How does failure isolation work?
> *"Each recipient is processed inside an individual `try...except` boundary. If recipient #2 fails due to invalid parameters or rendering issues, its record is marked `failed` with the exact error message. Processing continues uninterrupted for recipient #3, and the parent job marks `partial_success`. Clients can inspect exactly which certificates succeeded and which failed."*

### D. How would you scale this system for higher workloads?
> *(Future Scaling Roadmap)*:
> *"For a much larger production workload, I would replace process-bound BackgroundTasks with a durable queue such as Celery/RQ backed by Redis/RabbitMQ, migrate from SQLite to PostgreSQL, and move generated files to object storage with scalable download mechanisms."*
