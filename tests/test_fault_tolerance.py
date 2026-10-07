import pytest


def test_individual_certificate_failure_handling(client):
    """
    Submits a batch where one recipient triggers an error during generation
    (via simulated failure attribute).
    Verifies that other valid certificates are generated successfully,
    the job is marked PARTIAL_SUCCESS, and error details are isolated to the failed recipient.
    """
    payload = {
        "title": "Fault Tolerance Masterclass",
        "issuer_name": "Resilient Systems Academy",
        "issue_date": "2026-10-07",
        "recipients": [
            {
                "name": "Successful Student A",
                "email": "student.a@example.com",
                "custom_attributes": {"status": "Passed"}
            },
            {
                "name": "Faulty Recipient",
                "email": "faulty.recipient@example.com",
                "custom_attributes": {
                    "_fail_generate": True,
                    "comment": "Simulate rendering engine exception"
                }
            },
            {
                "name": "Successful Student B",
                "email": "student.b@example.com",
                "custom_attributes": {"status": "Distinction"}
            }
        ]
    }

    res = client.post("/api/v1/jobs?sync=true", json=payload)
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    # Retrieve job details
    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    data = status_res.json()

    # The job must finish with PARTIAL_SUCCESS
    assert data["status"] == "partial_success"
    assert data["total_count"] == 3
    assert data["success_count"] == 2
    assert data["failed_count"] == 1
    assert data["progress_percent"] == 100.0

    certs = data["certificates"]
    assert len(certs) == 3

    # Check that successful certificates were created
    successful = [c for c in certs if c["status"] == "success"]
    assert len(successful) == 2
    for cert in successful:
        assert cert["download_url"] is not None
        assert cert["error_message"] is None

    # Check that failed certificate has error details and did not halt execution
    failed = [c for c in certs if c["status"] == "failed"]
    assert len(failed) == 1
    assert failed[0]["recipient_name"] == "Faulty Recipient"
    assert "Simulated certificate rendering failure" in failed[0]["error_message"]
    assert failed[0]["download_url"] is None


def test_all_certificates_failing_sets_status_failed(client):
    """
    If all certificates in a batch fail, job status should be 'failed'.
    """
    payload = {
        "title": "All Failure Test",
        "issuer_name": "Test Authority",
        "recipients": [
            {
                "name": "Failing User 1",
                "email": "fail1@example.com",
                "custom_attributes": {"_fail_generate": True}
            },
            {
                "name": "Failing User 2",
                "email": "fail2@example.com",
                "custom_attributes": {"_fail_generate": True}
            }
        ]
    }

    res = client.post("/api/v1/jobs?sync=true", json=payload)
    job_id = res.json()["job_id"]

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    data = status_res.json()
    assert data["status"] == "failed"
    assert data["success_count"] == 0
    assert data["failed_count"] == 2
