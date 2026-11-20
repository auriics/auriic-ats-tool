import os
import pytest
from backend.engine.parser import ResumeParser
from backend.engine.scorer_mode_a import score_mode_a
from backend.engine.scorer_mode_b import score_mode_b
from backend.engine.normalizer import compute_content_hash

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_resumes")

SAMPLE_JD = """
Senior Full-Stack Engineer
Requirements:
- 5+ years of software engineering experience in Python and React.
- Strong knowledge of AWS, Docker, Kubernetes, and PostgreSQL.
- Bachelor's degree in Computer Science or related STEM field.
- Experience building scalable REST APIs and event-driven architectures.
Preferred:
- Knowledge of Go, Redis, and Terraform.
- Experience with CI/CD automation.
"""

def test_mode_a_determinism_50_iterations():
    """Verify that running Mode A scoring 50 times on the exact same resume returns identical score and breakdown."""
    parser = ResumeParser()
    sample_file = os.path.join(SAMPLE_DIR, "01_it_senior_software_engineer.txt")
    with open(sample_file, "rb") as f:
        file_bytes = f.read()

    # Baseline run
    parse_result = parser.parse_file(file_bytes, "01_it_senior_software_engineer.txt")
    baseline_report = score_mode_a(parse_result)
    baseline_score = baseline_report["overall_score"]
    baseline_breakdown = baseline_report["category_breakdown"]
    baseline_deductions_len = len(baseline_report["deductions"])

    # 50 iterations
    for iteration in range(1, 51):
        parsed = parser.parse_file(file_bytes, "01_it_senior_software_engineer.txt")
        report = score_mode_a(parsed)

        assert report["overall_score"] == baseline_score, f"Score discrepancy on iteration {iteration}: {report['overall_score']} != {baseline_score}"
        assert report["category_breakdown"] == baseline_breakdown, f"Breakdown discrepancy on iteration {iteration}"
        assert len(report["deductions"]) == baseline_deductions_len, f"Deductions discrepancy on iteration {iteration}"

def test_mode_b_determinism_50_iterations():
    """Verify that running Mode B scoring 50 times on the exact same resume + JD returns identical score and breakdown."""
    parser = ResumeParser()
    sample_file = os.path.join(SAMPLE_DIR, "01_it_senior_software_engineer.txt")
    with open(sample_file, "rb") as f:
        file_bytes = f.read()

    # Baseline run
    parse_result = parser.parse_file(file_bytes, "01_it_senior_software_engineer.txt")
    baseline_report = score_mode_b(parse_result, SAMPLE_JD)
    baseline_score = baseline_report["overall_score"]
    baseline_breakdown = baseline_report["category_breakdown"]
    baseline_kw_table = baseline_report["keyword_table"]

    # 50 iterations
    for iteration in range(1, 51):
        parsed = parser.parse_file(file_bytes, "01_it_senior_software_engineer.txt")
        report = score_mode_b(parsed, SAMPLE_JD)

        assert report["overall_score"] == baseline_score, f"Mode B score discrepancy on iteration {iteration}"
        assert report["category_breakdown"] == baseline_breakdown, f"Mode B breakdown discrepancy on iteration {iteration}"
        assert report["keyword_table"] == baseline_kw_table, f"Keyword table discrepancy on iteration {iteration}"

def test_sha256_hash_determinism():
    """Verify SHA-256 hash consistency across iterations."""
    text_a = "Senior Software Engineer with Python and AWS experience."
    text_b = "Python developer role with AWS."
    
    hash_1 = compute_content_hash(text_a, text_b, "1.0.0")
    for _ in range(50):
        hash_n = compute_content_hash(text_a, text_b, "1.0.0")
        assert hash_1 == hash_n
