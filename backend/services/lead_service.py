import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import yaml

from backend.database.db import query_one, query_all, execute
from backend.services.storage_service import save_resume_file
from backend.config.loader import load_scoring_config

def get_config() -> Dict[str, Any]:
    return load_scoring_config()

def hash_ip(ip_address: Optional[str]) -> str:
    """Hash client IP with a salt for privacy-preserving rate limiting and audit records."""
    if not ip_address:
        return ""
    salt = "auriic_ip_privacy_salt_2026"
    return hashlib.sha256(f"{salt}:{ip_address}".encode()).hexdigest()

def classify_lead_for_team(
    ats_score: float,
    consent_given: bool,
    email: Optional[str],
    phone: Optional[str],
    industry_id: str
) -> Tuple[str, str]:
    """
    Deterministic rule-based lead scoring for Auriic team:
    - Hot: low ATS score (<60) + consented + valid phone & email + target industry
    - Warm: ATS score 60-74.99 + consented
    - Cold: all other consented
    """
    if not consent_given:
        return "none", "User did not consent to data storage or outreach."

    has_email = bool(email and "@" in email)
    has_phone = bool(phone and len(phone.strip()) >= 7)

    config = get_config()
    lead_rules = config.get("lead_scoring", {})

    if ats_score < 60.0 and has_email and has_phone:
        return "hot", lead_rules.get("hot", {}).get(
            "reason",
            "Urgent resume rebuild candidate: ATS score below 60 with complete phone and email contact info."
        )
    elif 60.0 <= ats_score < 75.0:
        return "warm", lead_rules.get("warm", {}).get(
            "reason",
            "Moderate ATS compatibility (60-74): viable candidate needing targeted keyword optimization."
        )
    else:
        return "cold", lead_rules.get("cold", {}).get(
            "reason",
            "High ATS compatibility (75+): candidate ready for direct agency placement."
        )

def process_submission_and_lead(
    parse_result: Dict[str, Any],
    score_report: Dict[str, Any],
    resume_file_bytes: Optional[bytes],
    original_filename: str,
    resume_hash: str,
    consent_given: bool,
    consent_marketing: bool,
    client_ip: Optional[str],
    utm_params: Optional[Dict[str, str]] = None,
    job_description_text: Optional[str] = None,
    jd_title: Optional[str] = None,
    user_industry_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Handle privacy-compliant lead capture:
    - If user does NOT consent: Store ONLY anonymous record (hash, score, scoring_version, mode, industry).
      No file, no text, no contact data!
    - If user DOES consent: Store full lead, link repeat submissions to single person, save private file.
    """
    mode = score_report.get("mode", "A")
    ats_score = score_report.get("overall_score", 0.0)
    score_label = score_report.get("label", "Needs Work")
    scoring_version = score_report.get("scoring_version", "1.0.0")
    detected_industry = score_report.get("detected_industry", "it")

    now_iso = datetime.utcnow().isoformat()
    ip_hash_val = hash_ip(client_ip)
    utm = utm_params or {}

    # Case 1: NON-CONSENTING USER -> ANONYMOUS RECORD ONLY
    if not consent_given:
        sub_sql = """
            INSERT INTO ats_submissions (
                lead_id, created_at, mode, scoring_version, ats_score, score_label,
                category_scores, top_missing_keywords, job_description_text, jd_title,
                resume_file_path, extracted_text, resume_hash, deductions_json, is_anonymous
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """
        sub_id = execute(sub_sql, (
            None,
            now_iso,
            mode,
            scoring_version,
            ats_score,
            score_label,
            json.dumps(score_report.get("category_breakdown", {})),
            json.dumps(score_report.get("top_missing_keywords", [])),
            None,  # Do not store JD text
            jd_title,
            None,  # Do not store file
            None,  # Do not store extracted text
            resume_hash,
            json.dumps(score_report.get("deductions", [])),
        ))

        return {
            "lead_id": None,
            "submission_id": sub_id,
            "is_consented": False,
            "message": "Anonymous scan completed. No personal information or resume file stored."
        }

    # Case 2: CONSENTING USER -> PERSIST LEAD & FILE
    contact = parse_result.get("contact_info", {})
    email = contact.get("email") or f"unspecified_{resume_hash[:10]}@candidate.auriic.internal"
    full_name = contact.get("name") or "Candidate"
    phone = contact.get("phone")
    location = contact.get("location")
    linkedin = contact.get("linkedin")

    lead_score_category, lead_score_reason = classify_lead_for_team(
        ats_score=ats_score,
        consent_given=True,
        email=email,
        phone=phone,
        industry_id=detected_industry,
    )

    # Save private resume file
    storage_path = None
    if resume_file_bytes:
        storage_path = save_resume_file(resume_file_bytes, original_filename, resume_hash)

    # 12-Month retention purge date
    purge_date = (datetime.utcnow() + timedelta(days=365)).isoformat()

    degrees = parse_result.get("education_info", {}).get("degrees_found") or []
    detected_degree = degrees[0] if len(degrees) > 0 else None

    # Check for existing lead by email
    existing_lead = query_one("SELECT id FROM ats_leads WHERE email = ?", (email,))

    if existing_lead:
        lead_id = existing_lead["id"]
        # Update existing lead with latest metadata without creating duplicate lead row
        update_sql = """
            UPDATE ats_leads SET
                full_name = COALESCE(?, full_name),
                phone = COALESCE(?, phone),
                location = COALESCE(?, location),
                linkedin_url = COALESCE(?, linkedin_url),
                detected_industry = ?,
                user_selected_industry = ?,
                detected_job_titles = ?,
                top_skills = ?,
                education_level = ?,
                certifications = ?,
                lead_score_category = ?,
                lead_score_reason = ?,
                consent_marketing = ?,
                consent_timestamp = ?
            WHERE id = ?
        """
        execute(update_sql, (
            full_name,
            phone,
            location,
            linkedin,
            detected_industry,
            user_industry_override,
            json.dumps([parse_result.get("experience_analysis", {}).get("action_verbs_detected", [])]),
            json.dumps(parse_result.get("detected_skills", [])[:15]),
            detected_degree,
            json.dumps(parse_result.get("certifications", [])),
            lead_score_category,
            lead_score_reason,
            1 if consent_marketing else 0,
            now_iso,
            lead_id,
        ))
    else:
        # Insert new lead
        insert_lead_sql = """
            INSERT INTO ats_leads (
                created_at, full_name, email, phone, location, linkedin_url,
                detected_industry, user_selected_industry, detected_job_titles,
                top_skills, years_of_experience, education_level, certifications,
                utm_source, utm_medium, utm_campaign, referrer, device_type,
                consent_given, consent_marketing, consent_text_version, consent_timestamp,
                ip_hash, lead_status, lead_score_category, lead_score_reason, purge_after
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?)
        """
        lead_id = execute(insert_lead_sql, (
            now_iso,
            full_name,
            email,
            phone,
            location,
            linkedin,
            detected_industry,
            user_industry_override,
            json.dumps([]),
            json.dumps(parse_result.get("detected_skills", [])[:15]),
            parse_result.get("experience_analysis", {}).get("years_of_experience", 0),
            detected_degree,
            json.dumps(parse_result.get("certifications", [])),
            utm.get("utm_source"),
            utm.get("utm_medium"),
            utm.get("utm_campaign"),
            utm.get("referrer"),
            utm.get("device_type", "desktop"),
            1,
            1 if consent_marketing else 0,
            "1.0",
            now_iso,
            ip_hash_val,
            lead_score_category,
            lead_score_reason,
            purge_date,
        ))

    # Record submission linked to lead
    sub_sql = """
        INSERT INTO ats_submissions (
            lead_id, created_at, mode, scoring_version, ats_score, score_label,
            category_scores, top_missing_keywords, job_description_text, jd_title,
            resume_file_path, extracted_text, resume_hash, deductions_json, is_anonymous
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """
    sub_id = execute(sub_sql, (
        lead_id,
        now_iso,
        mode,
        scoring_version,
        ats_score,
        score_label,
        json.dumps(score_report.get("category_breakdown", {})),
        json.dumps(score_report.get("top_missing_keywords", [])),
        job_description_text,
        jd_title,
        storage_path,
        parse_result.get("raw_text", ""),
        resume_hash,
        json.dumps(score_report.get("deductions", [])),
    ))

    # Audit log entry
    execute(
        "INSERT INTO ats_audit_logs (actor, action, target_lead_id, details) VALUES (?, ?, ?, ?)",
        ("system", "lead_captured", lead_id, f"Mode: {mode}, Score: {ats_score}, Category: {lead_score_category}")
    )

    return {
        "lead_id": lead_id,
        "submission_id": sub_id,
        "is_consented": True,
        "lead_score_category": lead_score_category,
        "lead_score_reason": lead_score_reason,
    }
