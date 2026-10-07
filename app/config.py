import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration (defaults to SQLite, can be configured via DATABASE_URL)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/storage/certificates.db")

# Storage directory for generated certificates
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage" / "certificates")))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# App configuration
APP_TITLE = "CertiFlow — Bulk Certificate Generation & Verification Platform"
APP_DESCRIPTION = (
    "Production-oriented backend API and verification platform to accept bulk certificate "
    "generation requests, render high-resolution vector PDF certificates via a predefined "
    "template, track job-level and certificate-level progress asynchronously, isolate failures, "
    "and provide credential verification."
)
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
