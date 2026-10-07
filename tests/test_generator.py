import pytest
from pathlib import Path
from app.generator import generate_certificate_pdf


def test_generate_certificate_pdf_success(temp_test_dir):
    code = "CERT-TEST-ABCD"
    pdf_path = generate_certificate_pdf(
        certificate_code=code,
        recipient_name="Grace Hopper",
        title="Pioneers in Computing Award",
        issuer_name="Computer History Museum",
        issue_date="2026-10-07",
        description="For fundamental contributions to compiler design.",
        custom_attributes={"honors": "Summa Cum Laude", "cohort": "Founders-1952"},
        output_dir=temp_test_dir
    )

    path = Path(pdf_path)
    assert path.exists(), "Generated certificate PDF file must exist"
    assert path.stat().st_size > 1000, "PDF file must not be empty"

    # Verify PDF magic bytes
    with open(path, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-", "File should be a valid PDF format"


def test_generate_certificate_pdf_handles_long_text(temp_test_dir):
    long_desc = "This is an extraordinarily extensive description of the achievements and accomplishments demonstrated during the intense multi-week engineering boot camp covering advanced paradigms."
    pdf_path = generate_certificate_pdf(
        certificate_code="CERT-LONG-TEXT",
        recipient_name="Alexander Bartholomew Montgomery III",
        title="Enterprise Distributed Systems Mastery & Cloud Native Architecture",
        issuer_name="Global Certification Institute of Advanced Software Engineering",
        issue_date="2026-10-07",
        description=long_desc,
        output_dir=temp_test_dir
    )
    assert Path(pdf_path).exists()


def test_generate_certificate_pdf_simulated_failure(temp_test_dir):
    with pytest.raises(RuntimeError, match="Simulated certificate rendering failure"):
        generate_certificate_pdf(
            certificate_code="CERT-FAIL-TEST",
            recipient_name="Fail User",
            title="Failed Course",
            issuer_name="Institute",
            issue_date="2026-10-07",
            custom_attributes={"_fail_generate": True},
            output_dir=temp_test_dir
        )


def test_generate_certificate_pdf_handles_very_long_recipient_name(temp_test_dir):
    very_long_name = "Her Serene Highness Princess Charlotte Elizabeth Diana of Cambridge-Windsor"
    pdf_path = generate_certificate_pdf(
        certificate_code="CERT-LONG-NAME",
        recipient_name=very_long_name,
        title="Distinguished Honor Award",
        issuer_name="Royal Academy of Sciences",
        issue_date="2026-10-07",
        output_dir=temp_test_dir
    )
    assert Path(pdf_path).exists()
    assert Path(pdf_path).stat().st_size > 1000
