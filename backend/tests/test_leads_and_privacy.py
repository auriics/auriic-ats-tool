import os
import pytest
from backend.database.db import init_db, query_one, query_all, execute
from backend.services.lead_service import process_submission_and_lead, classify_lead_for_team
from backend.services.storage_service import generate_signed_download_url, verify_signed_url
from backend.database.retention import purge_lead_pii, purge_expired_records

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()

def test_non_consenting_upload_stores_no_pii():
    """Verify that a non-consenting upload stores no PII, no file path, and no extracted text."""
    dummy_parse = {
        "raw_text": "John Doe, Software Engineer, email: secret@domain.com, phone: 555-123-4567",
        "contact_info": {"name": "John Doe", "email": "secret@domain.com", "phone": "555-123-4567"},
        "sections": {},
        "experience_analysis": {},
        "education_info": {},
    }
    dummy_score = {
        "mode": "A",
        "overall_score": 72.0,
        "label": "Good",
        "scoring_version": "1.0.0",
        "detected_industry": "it",
        "category_breakdown": {},
        "deductions": [],
    }

    res = process_submission_and_lead(
        parse_result=dummy_parse,
        score_report=dummy_score,
        resume_file_bytes=b"dummy_bytes",
        original_filename="secret_resume.pdf",
        resume_hash="dummy_hash_non_consent_123",
        consent_given=False,
        consent_marketing=False,
        client_ip="192.168.1.1",
    )

    assert res["is_consented"] is False
    assert res["lead_id"] is None

    # Check database: no lead with that email exists
    lead_check = query_one("SELECT * FROM ats_leads WHERE email = 'secret@domain.com'")
    assert lead_check is None

    # Check submission: is_anonymous = 1, extracted_text = null, resume_file_path = null
    sub_id = res["submission_id"]
    sub = query_one("SELECT * FROM ats_submissions WHERE id = ?", (sub_id,))
    assert sub is not None
    assert sub["is_anonymous"] == 1
    assert sub["resume_file_path"] is None
    assert sub["extracted_text"] is None

def test_consenting_upload_and_repeat_upload_deduplication():
    """Verify consenting upload creates 1 lead, and second upload by same email adds submission without duplicate lead."""
    import uuid
    email = f"candidate_unique_{uuid.uuid4().hex[:8]}@auriic.co"
    dummy_parse = {
        "raw_text": f"Candidate Name, email: {email}, phone: 555-987-6543",
        "contact_info": {"name": "Candidate Name", "email": email, "phone": "555-987-6543", "location": "Dallas, TX"},
        "sections": {},
        "experience_analysis": {"years_of_experience": 4},
        "education_info": {"degrees_found": ["BS"]},
        "detected_skills": ["Python", "SQL"],
        "certifications": [],
    }
    dummy_score_1 = {
        "mode": "A",
        "overall_score": 55.0, # Low score -> Hot lead
        "label": "Needs Work",
        "scoring_version": "1.0.0",
        "detected_industry": "it",
        "category_breakdown": {},
        "deductions": [],
    }

    res_1 = process_submission_and_lead(
        parse_result=dummy_parse,
        score_report=dummy_score_1,
        resume_file_bytes=b"sample_content_1",
        original_filename="resume_v1.pdf",
        resume_hash="hash_run_1",
        consent_given=True,
        consent_marketing=True,
        client_ip="10.0.0.1",
    )

    assert res_1["is_consented"] is True
    lead_id_1 = res_1["lead_id"]
    assert res_1["lead_score_category"] == "hot"

    # Second submission with same email (improved score)
    dummy_score_2 = {
        "mode": "B",
        "overall_score": 82.0,
        "label": "Good",
        "scoring_version": "1.0.0",
        "detected_industry": "it",
        "category_breakdown": {},
        "deductions": [],
    }

    res_2 = process_submission_and_lead(
        parse_result=dummy_parse,
        score_report=dummy_score_2,
        resume_file_bytes=b"sample_content_2",
        original_filename="resume_v2.pdf",
        resume_hash="hash_run_2",
        consent_given=True,
        consent_marketing=True,
        client_ip="10.0.0.1",
    )

    lead_id_2 = res_2["lead_id"]
    # Same person!
    assert lead_id_1 == lead_id_2

    # Check total submissions count for this lead
    subs = query_all("SELECT * FROM ats_submissions WHERE lead_id = ?", (lead_id_1,))
    assert len(subs) == 2

    # Verify leads count with this email is exactly 1
    leads = query_all("SELECT * FROM ats_leads WHERE email = ?", (email,))
    assert len(leads) == 1

def test_signed_url_generation_and_expiration():
    rel_path = "resumes/test_sample.pdf"
    signed_url = generate_signed_download_url(rel_path, expires_in_seconds=60)
    assert "sig=" in signed_url
    assert "expires=" in signed_url

    # Check valid signature
    import urllib.parse
    parsed_params = urllib.parse.parse_qs(signed_url.split("?")[1])
    path_param = parsed_params["path"][0]
    expires_param = int(parsed_params["expires"][0])
    sig_param = parsed_params["sig"][0]

    assert verify_signed_url(path_param, expires_param, sig_param) is True
    # Expired timestamp check
    assert verify_signed_url(path_param, expires_param - 200, sig_param) is False

def test_data_deletion_scrubs_all_pii():
    """Verify that purging a lead permanently scrubs email, phone, files, and text."""
    email = "delete_me_soon@auriic.co"
    lead_id = execute("""
        INSERT INTO ats_leads (full_name, email, phone, consent_given, lead_status)
        VALUES ('Target Delete', ?, '555-000-1111', 1, 'new')
    """, (email,))

    sub_id = execute("""
        INSERT INTO ats_submissions (lead_id, mode, scoring_version, ats_score, score_label, resume_hash, extracted_text)
        VALUES (?, 'A', '1.0.0', 65.0, 'Fair', 'hash_del_test', 'Sensitive resume text content here.')
    """, (lead_id,))

    # Trigger purge
    purge_lead_pii(lead_id, actor="test_runner")

    # Verify lead row is scrubbed
    lead = query_one("SELECT * FROM ats_leads WHERE id = ?", (lead_id,))
    assert lead["phone"] is None
    assert "[PURGED_" in lead["email"]
    assert lead["deleted_at"] is not None

    # Verify submission text is cleared
    sub = query_one("SELECT * FROM ats_submissions WHERE id = ?", (sub_id,))
    assert sub["extracted_text"] is None
    assert sub["is_anonymous"] == 1
