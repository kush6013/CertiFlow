import io
import zipfile
import pytest


def test_retrieve_individual_certificate_and_download(client):
    # Create job
    res = client.post("/api/v1/jobs?sync=true", json={
        "title": "Software Architecture Summit",
        "issuer_name": "DevCon Org",
        "recipients": [
            {"name": "Barbara Liskov", "email": "barbara@example.com"}
        ]
    })
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    job_res = client.get(f"/api/v1/jobs/{job_id}")
    cert_data = job_res.json()["certificates"][0]
    cert_id = cert_data["id"]

    # 1. Get certificate details
    detail_res = client.get(f"/api/v1/certificates/{cert_id}")
    assert detail_res.status_code == 200
    info = detail_res.json()
    assert info["id"] == cert_id
    assert info["recipient_name"] == "Barbara Liskov"
    assert info["status"] == "success"

    # 2. Download certificate PDF
    dl_res = client.get(f"/api/v1/certificates/{cert_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert dl_res.content.startswith(b"%PDF-")


def test_download_job_certificates_as_zip(client):
    # Create job with 2 recipients
    res = client.post("/api/v1/jobs?sync=true", json={
        "title": "Data Engineering Bootcamp",
        "issuer_name": "Data School",
        "recipients": [
            {"name": "Alice Smith", "email": "alice@example.com"},
            {"name": "Bob Jones", "email": "bob@example.com"}
        ]
    })
    job_id = res.json()["job_id"]

    # Download ZIP
    zip_res = client.get(f"/api/v1/jobs/{job_id}/download")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"

    # Inspect zip contents in memory
    zip_bytes = io.BytesIO(zip_res.content)
    with zipfile.ZipFile(zip_bytes, "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) == 2
        for filename in namelist:
            assert filename.endswith(".pdf")
            file_data = zf.read(filename)
            assert file_data.startswith(b"%PDF-")


def test_verify_certificate_endpoint(client):
    # Create job
    res = client.post("/api/v1/jobs?sync=true", json={
        "title": "Cybersecurity Specialist",
        "issuer_name": "Security Council",
        "recipients": [
            {"name": "Margaret Hamilton", "email": "margaret@example.com"}
        ]
    })
    job_id = res.json()["job_id"]
    job_res = client.get(f"/api/v1/jobs/{job_id}")
    cert = job_res.json()["certificates"][0]
    cert_code = cert["certificate_code"]

    # Verify with valid code
    verify_res = client.get(f"/api/v1/certificates/verify/{cert_code}")
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["valid"] is True
    assert v_data["recipient_name"] == "Margaret Hamilton"
    assert v_data["issuer_name"] == "Security Council"

    # Verify with invalid code
    bad_res = client.get("/api/v1/certificates/verify/CERT-INVALID-CODE")
    assert bad_res.status_code == 200
    assert bad_res.json()["valid"] is False


def test_verify_certificate_endpoint_trimmed_code(client):
    res = client.post("/api/v1/jobs?sync=true", json={
        "title": "Quantum Physics Award",
        "issuer_name": "Institute of Physics",
        "recipients": [
            {"name": "Richard Feynman", "email": "feynman@example.com"}
        ]
    })
    job_id = res.json()["job_id"]
    job_res = client.get(f"/api/v1/jobs/{job_id}")
    cert_code = job_res.json()["certificates"][0]["certificate_code"]

    # Verify with code having leading/trailing whitespace
    verify_res = client.get(f"/api/v1/certificates/verify/%20{cert_code}%20")
    assert verify_res.status_code == 200
    assert verify_res.json()["valid"] is True
    assert verify_res.json()["recipient_name"] == "Richard Feynman"


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
