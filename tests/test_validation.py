import pytest


def test_validation_empty_payload(client):
    res = client.post("/api/v1/jobs", json={})
    assert res.status_code == 422
    data = res.json()
    assert "detail" in data


def test_validation_empty_title_or_issuer(client):
    # Empty title
    res = client.post("/api/v1/jobs", json={
        "title": "   ",
        "issuer_name": "Valid Issuer",
        "recipients": [{"name": "John Doe", "email": "john@example.com"}]
    })
    assert res.status_code == 422

    # Empty issuer
    res = client.post("/api/v1/jobs", json={
        "title": "Valid Title",
        "issuer_name": "  ",
        "recipients": [{"name": "John Doe", "email": "john@example.com"}]
    })
    assert res.status_code == 422


def test_validation_empty_recipients_list(client):
    res = client.post("/api/v1/jobs", json={
        "title": "Web Development",
        "issuer_name": "Code Academy",
        "recipients": []
    })
    assert res.status_code == 422


def test_validation_invalid_recipient_email(client):
    res = client.post("/api/v1/jobs", json={
        "title": "Web Development",
        "issuer_name": "Code Academy",
        "recipients": [
            {"name": "Valid User", "email": "valid@example.com"},
            {"name": "Invalid User", "email": "not-an-email-address"}
        ]
    })
    assert res.status_code == 422
    errors = res.json()["detail"]
    assert any("email" in str(e["loc"]) for e in errors)


def test_validation_blank_recipient_name(client):
    res = client.post("/api/v1/jobs", json={
        "title": "Web Development",
        "issuer_name": "Code Academy",
        "recipients": [
            {"name": "   ", "email": "valid@example.com"}
        ]
    })
    assert res.status_code == 422
