import os
import pytest
from backend.engine.parser import ResumeParser
from backend.engine.pii_sanitizer import detect_pii, sanitize_and_redact_pii
from backend.engine.industry_detector import detect_industry

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_resumes")

def test_parser_txt():
    parser = ResumeParser()
    path = os.path.join(SAMPLE_DIR, "01_it_senior_software_engineer.txt")
    with open(path, "rb") as f:
        res = parser.parse_file(f.read(), "01_it_senior_software_engineer.txt")
    assert res["success"] is True
    assert res["contact_info"]["email"] == "alex.rivera@email.com"
    assert "experience" in res["sections"]
    assert "skills" in res["sections"]
    assert res["experience_analysis"]["action_verb_ratio"] > 0.5

def test_parser_docx():
    parser = ResumeParser()
    path = os.path.join(SAMPLE_DIR, "04_healthcare_registered_nurse.docx")
    with open(path, "rb") as f:
        res = parser.parse_file(f.read(), "04_healthcare_registered_nurse.docx")
    assert res["success"] is True
    assert res["contact_info"]["email"] == "elena.rostova.rn@email.com"
    assert "experience" in res["sections"]

def test_parser_pdf():
    parser = ResumeParser()
    path = os.path.join(SAMPLE_DIR, "01_it_senior_software_engineer.pdf")
    with open(path, "rb") as f:
        res = parser.parse_file(f.read(), "01_it_senior_software_engineer.pdf")
    assert res["success"] is True
    assert "alex.rivera@email.com" in res["raw_text"]

def test_scanned_image_pdf_detection():
    parser = ResumeParser()
    path = os.path.join(SAMPLE_DIR, "19_bad_scanned_image_no_text.pdf")
    with open(path, "rb") as f:
        res = parser.parse_file(f.read(), "19_bad_scanned_image_no_text.pdf")
    assert res["is_scanned"] is True
    assert any("scanned" in issue.lower() for issue in res["layout_issues"])

def test_pii_detection_and_redaction():
    text_with_pii = """
    Candidate: Jane Doe
    SSN: 123-45-6789
    DOB: 05/12/1988
    Passport No: A98765432
    Experience: 5 years in marketing.
    """
    alerts = detect_pii(text_with_pii)
    types_detected = [a["type"] for a in alerts]
    assert "SSN" in types_detected
    assert "DOB" in types_detected
    assert "PASSPORT" in types_detected

    redacted_text, _ = sanitize_and_redact_pii(text_with_pii)
    assert "123-45-6789" not in redacted_text
    assert "[REDACTED_SSN]" in redacted_text
    assert "[REDACTED_DOB]" in redacted_text
    assert "[REDACTED_PASSPORT]" in redacted_text

def test_industry_detection_across_domains():
    text_it = "Senior Python engineer specialized in AWS, Docker, Kubernetes, microservices and CI/CD."
    assert detect_industry(text_it)["industry_id"] == "it"

    text_health = "Critical care Registered Nurse RN with BLS, ACLS, CPR, ICU patient triage and Epic EHR."
    assert detect_industry(text_health)["industry_id"] == "healthcare"

    text_fin = "Certified Public Accountant CPA managing balance sheet reconciliation, GAAP, SOX, and FP&A."
    assert detect_industry(text_fin)["industry_id"] == "finance"

    text_mfg = "Plant operations manager leading Lean Six Sigma, Kaizen, CNC machining, and ISO 9001 quality control."
    assert detect_industry(text_mfg)["industry_id"] == "manufacturing"

    text_log = "Global supply chain director optimizing warehouse WMS, freight dispatch, TMS, and 3PL carriers."
    assert detect_industry(text_log)["industry_id"] == "logistics"

    text_const = "Licensed Professional Engineer PE managing civil site construction, AutoCAD Civil 3D, and OSHA 30."
    assert detect_industry(text_const)["industry_id"] == "construction"

    text_energy = "Electrical power systems engineer designing high-voltage substations, SCADA, and solar grid PV."
    assert detect_industry(text_energy)["industry_id"] == "energy"

    text_ret = "Retail store general manager driving POS sales, visual merchandising, and inventory turnover."
    assert detect_industry(text_ret)["industry_id"] == "retail"
