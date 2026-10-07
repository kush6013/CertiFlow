import pytest


def test_create_bulk_job_synchronous(client):
    payload = {
        "title": "FastAPI Certification",
        "issuer_name": "Open Source Foundation",
        "issue_date": "2026-10-07",
        "description": "Certificate of Python & FastAPI Mastery",
        "recipients": [
            {
                "name": "Ada Lovelace",
                "email": "ada@example.com",
                "custom_attributes": {"rank": "First Class"}
            },
            {
                "name": "Alan Turing",
                "email": "alan@example.com",
                "custom_attributes": {"rank": "Distinction"}
            }
        ]
    }

    # Test sync creation
    res = client.post("/api/v1/jobs?sync=true", json=payload)
    assert res.status_code == 202
    data = res.json()
    assert "job_id" in data
    assert data["total_count"] == 2
    assert data["status"] in ("completed", "pending")

    # Fetch job detail
    job_id = data["job_id"]
    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    job_detail = status_res.json()
    assert job_detail["id"] == job_id
    assert job_detail["status"] == "completed"
    assert job_detail["total_count"] == 2
    assert job_detail["success_count"] == 2
    assert job_detail["failed_count"] == 0
    assert job_detail["progress_percent"] == 100.0
    assert len(job_detail["certificates"]) == 2

    # Verify each certificate record
    for cert in job_detail["certificates"]:
        assert cert["status"] == "success"
        assert cert["certificate_code"].startswith("CERT-")
        assert cert["download_url"] is not None


def test_create_bulk_job_asynchronous(client):
    payload = {
        "title": "Cloud Computing Essentials",
        "issuer_name": "Cloud Academy",
        "recipients": [
            {"name": "Carol Danvers", "email": "carol@example.com"}
        ]
    }

    # Test async creation
    res = client.post("/api/v1/jobs?sync=false", json=payload)
    assert res.status_code == 202
    data = res.json()
    assert "job_id" in data
    assert data["total_count"] == 1


def test_list_jobs(client):
    # Create two jobs
    for i in range(2):
        client.post("/api/v1/jobs?sync=true", json={
            "title": f"Course Batch {i + 1}",
            "issuer_name": "Test Org",
            "recipients": [{"name": f"Student {i}", "email": f"student{i}@example.com"}]
        })

    res = client.get("/api/v1/jobs?skip=0&limit=10")
    assert res.status_code == 200
    jobs = res.json()
    assert isinstance(jobs, list)
    assert len(jobs) >= 2


def test_get_nonexistent_job(client):
    res = client.get("/api/v1/jobs/non-existent-uuid")
    assert res.status_code == 404


def test_single_recipient_job_completed(client):
    """CASE D: 1 recipient, 1 succeeds -> status completed"""
    payload = {
        "title": "Single Student Award",
        "issuer_name": "Solo Academy",
        "recipients": [
            {"name": "Solo Winner", "email": "winner@example.com"}
        ]
    }
    res = client.post("/api/v1/jobs?sync=true", json=payload)
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    data = status_res.json()
    assert data["status"] == "completed"
    assert data["total_count"] == 1
    assert data["success_count"] == 1
    assert data["failed_count"] == 0
    assert data["progress_percent"] == 100.0


def test_job_timestamps_lifecycle(client):
    """Verifies created_at, started_at, completed_at, updated_at are set."""
    payload = {
        "title": "Timestamp Test Program",
        "issuer_name": "Metrics Org",
        "recipients": [
            {"name": "Timely Student", "email": "timely@example.com"}
        ]
    }
    res = client.post("/api/v1/jobs?sync=true", json=payload)
    job_id = res.json()["job_id"]

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    data = status_res.json()
    assert data["created_at"] is not None
    assert data["started_at"] is not None
    assert data["completed_at"] is not None
    assert data["updated_at"] is not None
