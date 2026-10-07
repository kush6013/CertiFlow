# CertiFlow — Bulk Certificate Generation & Verification Platform 🎓

<p align="center">
  <img src="app/static/logo.png" alt="CertiFlow Logo" width="220" style="border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);"/>
</p>

An interview-ready, production-oriented backend API and verification platform built with **Python**, **FastAPI**, **SQLAlchemy**, and **ReportLab**. CertiFlow accepts bulk certificate generation requests for hundreds of recipients, renders high-resolution vector PDF certificates via a predefined professional template, tracks job-level and certificate-level progress asynchronously, isolates individual recipient failures, and provides unified retrieval, ZIP batch packaging, and public verification endpoints.

---

## 📋 Table of Contents
1. [Project Overview](#1-project-overview)
2. [Key Features](#2-key-features)
3. [Architecture Diagram](#3-architecture-diagram)
4. [Technology Stack](#4-technology-stack)
5. [Project Structure](#5-project-structure)
6. [Database Model Explanation](#6-database-model-explanation)
7. [Job Lifecycle](#7-job-lifecycle)
8. [Certificate Lifecycle](#8-certificate-lifecycle)
9. [Setup Instructions](#9-setup-instructions)
10. [Virtual Environment Setup](#10-virtual-environment-setup)
11. [Dependency Installation](#11-dependency-installation)
12. [Running the Application](#12-running-the-application)
13. [Interactive Documentation (Swagger & ReDoc)](#13-interactive-documentation-swagger--redoc)
14. [Running Tests](#14-running-tests)
15. [Example POST Request](#15-example-post-request)
16. [Example Job Status Request](#16-example-job-status-request)
17. [Certificate Download](#17-certificate-download)
18. [Bulk ZIP Download](#18-bulk-zip-download)
19. [Credential Verification](#19-credential-verification)
20. [Important Design Decisions](#20-important-design-decisions)
21. [Failure Isolation Strategy](#21-failure-isolation-strategy)
22. [Why Background Processing is Used](#22-why-background-processing-is-used)
23. [Current Limitations](#23-current-limitations)
24. [Future Scalability Roadmap](#24-future-scalability-roadmap)

---

## 1. Project Overview

Organizations regularly need to issue verified credentials to participants following training programs, conferences, or academic courses. Generating certificates one-by-one introduces high latency, blocks HTTP client connections, and risks whole-batch crashes if a single participant record is malformed.

**CertiFlow** solves this by providing:
- Asynchronous bulk job ingestion returning `202 Accepted` immediately.
- Strict Pydantic V2 schema and email validation upfront.
- Vector PDF rendering with ReportLab that never pixelates on print.
- Isolated recipient-level error handling so valid certificates are always generated.
- In-memory ZIP compilation for convenient batch downloads.
- A public verification endpoint returning credential verification without exposing private recipient emails or filesystem paths.

---

## 2. Key Features

- **Bulk Submission**: Issue hundreds of certificates in one API request.
- **Background Worker Processing**: Dispatched via FastAPI `BackgroundTasks`, releasing the HTTP connection immediately while rendering proceeds in the background.
- **Synchronous Option (`?sync=true`)**: Optional query parameter for integration tests or small batches.
- **Predefined Vector Template**: Print-ready landscape A4 PDF with gold/navy geometric borders, official vector rosette seal, dynamic font scaling for long names, and secure verification footer.
- **Fault Tolerance**: If recipient #3 has corrupted attributes, recipients #1, #2, #4, and #5 still succeed. The job marks `partial_success` with exact error reasons.
- **Security & Privacy**:
  - Unpredictable alphanumeric certificate codes (`CERT-XXXX-XXXX`).
  - Path traversal protection on all file downloads.
  - Verification endpoint omits recipient email and internal storage paths.
- **Comprehensive Test Suite**: 22 automated tests covering input validation, PDF generation, fault tolerance, timestamps, zip bundling, and verification.
- **Interactive Console**: Built-in dashboard with periodic job-status polling for quick manual demonstration.

---

## 3. Architecture Diagram

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
                                  • Closes worker session safely
```

---

## 4. Technology Stack

- **Language**: Python 3.12 (compatible with 3.10+)
- **Framework**: FastAPI (asynchronous ASGI framework, Pydantic V2 integration)
- **Database ORM**: SQLAlchemy 2.0
- **Database Engine**: SQLite (`sqlite:///storage/certificates.db`) with `check_same_thread=False`
- **PDF Engine**: ReportLab (vector graphics, canvas primitives, typography)
- **Testing**: Pytest, pytest-asyncio, HTTPX
- **Server**: Uvicorn ASGI server

---

## 5. Project Structure

```text
p1/
├── app/
│   ├── __init__.py
│   ├── main.py              # Application factory, lifespan, /health & static routes
│   ├── config.py            # Environment settings and paths
│   ├── database.py          # SQLAlchemy engine and session factory
│   ├── models.py            # GenerationJob & CertificateRecord ORM models
│   ├── schemas.py           # Pydantic V2 request & response schemas
│   ├── crud.py              # Database queries, updates & status transitions
│   ├── generator.py         # ReportLab vector PDF certificate engine
│   ├── tasks.py             # Fault-isolated background processing worker
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── jobs.py          # /api/v1/jobs endpoints
│   │       └── certificates.py  # /api/v1/certificates endpoints
│   └── static/
│       ├── index.html       # Web dashboard HTML
│       ├── style.css        # Responsive styling
│       └── app.js           # Client-side polling and modal handlers
├── storage/
│   ├── certificates/        # Generated PDF files
│   └── certificates.db      # SQLite database file
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures and isolated test client
│   ├── test_generator.py    # PDF layout, vector rendering & name scaling tests
│   ├── test_validation.py   # Schema & email validation tests
│   ├── test_jobs.py         # Job creation, timestamps & progress tests
│   ├── test_fault_tolerance.py # Partial failure and fault isolation tests
│   └── test_retrieval.py    # PDF download, ZIP bundle, health & verify tests
├── pytest.ini               # Pytest configuration
├── requirements.txt         # Project dependencies
├── run.py                   # Development server launcher
└── README.md                # Project documentation
```

---

## 6. Database Model Explanation

### `generation_jobs` Table
Tracks a bulk batch submission:
- `id` (String UUID): Primary key.
- `title` (String): Event / Course / Certificate title.
- `issuer_name` (String): Issuing organization.
- `issue_date` (String): Formatted date of issuance.
- `description` (Text): Body description printed on certificates.
- `status` (`JobStatus` Enum): `pending` | `processing` | `completed` | `partial_success` | `failed`.
- `total_count` (Integer): Total recipient count.
- `success_count` (Integer): Number of successfully generated certificates.
- `failed_count` (Integer): Number of failed certificates.
- `created_at` (DateTime UTC): Job creation timestamp.
- `started_at` (DateTime UTC): Timestamp when processing began.
- `completed_at` (DateTime UTC): Timestamp when the entire job finished.
- `updated_at` (DateTime UTC): Last update timestamp.

### `certificates` Table
Tracks each individual recipient credential:
- `id` (String UUID): Primary key.
- `job_id` (String Foreign Key): References parent `generation_jobs.id`.
- `recipient_name` (String): Full name of the recipient.
- `recipient_email` (String): Validated email address.
- `custom_attributes` (JSON): Dictionary of extra metadata (e.g. `{"grade": "A+", "track": "AI"}`).
- `status` (`CertificateStatus` Enum): `pending` | `processing` | `success` | `failed`.
- `error_message` (Text): Reason for failure if generation failed.
- `certificate_code` (String): Unique verification code (e.g. `CERT-A1B2-C3D4`).
- `file_path` (String): Path to the generated PDF.
- `created_at` (DateTime UTC): Creation timestamp.
- `generated_at` (DateTime UTC): Timestamp when PDF was saved.

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

---

## 8. Certificate Lifecycle

Each certificate transitions through its own states:
```text
[ pending ] ──► [ processing ] ──► [ success ] (PDF path saved, generated_at set)
                               └──► [ failed ]  (safe error message captured)
```

---

## 9. Setup Instructions & Prerequisites

- Python 3.10+ (tested on Python 3.12)
- Linux / macOS / Windows

---

## 10. Virtual Environment Setup

```bash
# Clone or navigate to the repository
cd /path/to/p1

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

---

## 11. Dependency Installation

```bash
pip install -r requirements.txt
```

---

## 12. Running the Application

```bash
# Using the convenience runner:
python run.py

# Or directly using uvicorn:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 13. Interactive Documentation (Swagger & ReDoc)

Once running, access:
- **Web Dashboard**: [http://localhost:8000/](http://localhost:8000/)
- **Swagger OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 14. Running Tests

Run the complete test suite:
```bash
pytest -v
```

All 22 unit and integration tests run against isolated temporary databases and mock storage directories, ensuring zero side-effects on local data.

---

## 15. Example POST Request

Submit a bulk certificate generation job:

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

---

## 16. Example Job Status Request

```bash
curl "http://localhost:8000/api/v1/jobs/1431a953-b43b-4775-9e0a-5c67cd68b022"
```

**Response (HTTP 200 OK):**
```json
{
  "id": "1431a953-b43b-4775-9e0a-5c67cd68b022",
  "title": "Full-Stack Software Architecture",
  "issuer_name": "Tech Academy Global",
  "issue_date": "2026-10-07",
  "description": "For demonstrated excellence in distributed systems.",
  "status": "completed",
  "total_count": 2,
  "success_count": 2,
  "failed_count": 0,
  "progress_percent": 100.0,
  "created_at": "2026-10-07T09:55:15.620019",
  "started_at": "2026-10-07T09:55:15.633219",
  "completed_at": "2026-10-07T09:55:15.700241",
  "updated_at": "2026-10-07T09:55:15.700241",
  "certificates": [
    {
      "id": "5fa23d11-e490-482f-8700-112344efaa11",
      "job_id": "1431a953-b43b-4775-9e0a-5c67cd68b022",
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice@example.com",
      "custom_attributes": {"grade": "Distinction", "track": "Backend"},
      "status": "success",
      "error_message": null,
      "certificate_code": "CERT-82F9-CEA1",
      "download_url": "/api/v1/certificates/5fa23d11-e490-482f-8700-112344efaa11/download",
      "created_at": "2026-10-07T09:55:15.625010",
      "generated_at": "2026-10-07T09:55:15.660144"
    }
  ]
}
```

---

## 17. Certificate Download

Download an individual certificate PDF:
```bash
curl -O -J "http://localhost:8000/api/v1/certificates/5fa23d11-e490-482f-8700-112344efaa11/download"
```
Returns `Content-Type: application/pdf` with `Content-Disposition: inline; filename="Alice_Johnson_CERT-82F9-CEA1.pdf"`.

---

## 18. Bulk ZIP Download

Download all successfully generated certificates in a single archive:
```bash
curl -O -J "http://localhost:8000/api/v1/jobs/1431a953-b43b-4775-9e0a-5c67cd68b022/download"
```
Returns `Content-Type: application/zip` containing all generated PDF files.

---

## 19. Credential Verification

Public verification endpoint:
```bash
curl "http://localhost:8000/api/v1/certificates/verify/CERT-82F9-CEA1"
```

**Response (HTTP 200 OK):**
```json
{
  "valid": true,
  "certificate_code": "CERT-82F9-CEA1",
  "recipient_name": "Alice Johnson",
  "title": "Full-Stack Software Architecture",
  "issuer_name": "Tech Academy Global",
  "issue_date": "2026-10-07",
  "custom_attributes": {"grade": "Distinction", "track": "Backend"},
  "generated_at": "2026-10-07T09:55:15.660144",
  "message": "Authentic certificate verified successfully."
}
```

If an invalid code is supplied:
```json
{
  "valid": false,
  "certificate_code": "CERT-INVALID",
  "recipient_name": null,
  "title": null,
  "issuer_name": null,
  "issue_date": null,
  "custom_attributes": null,
  "generated_at": null,
  "message": "Certificate record not found. This credential could not be verified."
}
```

---

## 20. Important Design Decisions

1. **Database Session Safety in Background Tasks**:
   - The background worker does NOT inherit or reuse the request-scoped SQLAlchemy session.
   - When the HTTP request completes, the request session is committed and closed.
   - Only the primitive `job_id` (string UUID) is passed into `background_tasks.add_task(process_bulk_certificate_job, job.id)`.
   - The worker initializes a completely independent `SessionLocal()` and guarantees session closure via a `try...finally` block.
2. **Asynchronous Ingestion (`202 Accepted`)**:
   - Rendering hundreds of PDFs takes multiple seconds. Returning `202 Accepted` immediately gives the client a reliable `job_id` and status URL without risking HTTP gateway timeouts.
3. **Vector ReportLab Graphics over Raster Images**:
   - Vector PDFs scale infinitely without pixelation, generate in milliseconds, and consume only ~4 KB per certificate.
4. **Dynamic Typography Scaling**:
   - Recipient names vary in length. Rather than overflowing borders, names exceeding 26 characters dynamically scale down font sizes while preserving layout symmetry.
5. **Path Traversal Defense**:
   - Storage file paths are strictly validated to ensure they resolve within `STORAGE_DIR`, preventing arbitrary local filesystem disclosures.

---

## 21. Failure Isolation Strategy

Generating 100 certificates should never fail entirely because certificate #42 has an error.
- Every recipient rendering is wrapped in an isolated `try...except` block inside `app/tasks.py`.
- If an exception occurs:
  - That certificate record is updated to `status="failed"`.
  - A descriptive, sanitized error message is stored in `CertificateRecord.error_message`.
  - The loop continues immediately to the next recipient.
- The parent `GenerationJob` reflects the outcome accurately:
  - `completed`: 100% success rate.
  - `partial_success`: At least one certificate succeeded, but at least one failed.
  - `failed`: All certificates in the job failed.

---

## 22. Why Background Processing is Used

Certificate generation is CPU-bound (PDF rasterization, font metric computation) and I/O-bound (disk writes). In a synchronous handler, generating 500 certificates would block the HTTP worker thread for 10-30 seconds, causing gateway timeouts (HTTP 504), starvation of worker threads, and a poor client experience.

Using background processing ensures the API responds in under 50 milliseconds, while the client monitors progress via polling.

---

## 23. Current Limitations

- **Process-Bound Tasks**: FastAPI `BackgroundTasks` run in the same process memory space. If the server process is abruptly restarted during a job, interrupted jobs will remain in `processing` state without automatic resumption.
- **In-Memory ZIP**: Batch downloads compile ZIP files in an in-memory `io.BytesIO` buffer. While efficient for batches of a few hundred certificates (~1-5 MB), very large batches (e.g. 10,000 certificates) would consume significant RAM and should use streaming tempfile archives.
- **Local Filesystem**: PDFs are saved to the local `storage/certificates/` directory.

---

## 24. Future Scalability Roadmap

In a large-scale enterprise deployment, the architecture would evolve as follows:

1. **Durable Task Queue (Celery / RQ with Redis or RabbitMQ)**:
   - Replaces in-process `BackgroundTasks` with distributed workers.
   - Provides persistent message queues, task retries, worker restarts, rate limiting, and priority queues.
2. **PostgreSQL Relational Storage**:
   - Replaces SQLite with a multi-writer, pooled relational database supporting concurrent worker writes and row-level locking.
3. **Cloud Object Storage (AWS S3 / Google Cloud Storage / Cloudflare R2)**:
   - Generated PDFs are uploaded to object storage buckets with presigned download URLs, offloading file bandwidth from the backend servers.
4. **Horizontal Worker Scaling**:
   - Decouple API web nodes from worker nodes, scaling worker nodes dynamically based on queue depth.
