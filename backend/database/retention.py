import os
from datetime import datetime
from typing import Dict, Any, List
from backend.database.db import query_all, query_one, execute
from backend.services.storage_service import delete_stored_file

def purge_expired_records() -> Dict[str, Any]:
    """
    Auto-purge resumes and extracted text after 12 months (365 days)
    unless the lead status is qualified or converted.
    Retains anonymized score records only.
    """
    now_iso = datetime.utcnow().isoformat()
    # Find leads eligible for purge
    sql_find = """
        SELECT id, email FROM ats_leads
        WHERE purge_after <= ?
          AND lead_status NOT IN ('qualified', 'converted')
          AND deleted_at IS NULL
    """
    expired_leads = query_all(sql_find, (now_iso,))
    purged_count = 0

    for lead in expired_leads:
        lead_id = lead["id"]
        success = purge_lead_pii(lead_id, actor="system_retention_job")
        if success:
            purged_count += 1

    return {
        "status": "success",
        "purged_leads_count": purged_count,
        "timestamp": now_iso,
    }

def purge_lead_pii(lead_id: int, actor: str = "admin") -> bool:
    """
    Permanently delete stored resume file, clear PII and extracted text for a lead.
    Preserves an anonymized submission score record for historical analytics.
    """
    # 1. Fetch file paths for this lead's submissions
    submissions = query_all("SELECT id, resume_file_path FROM ats_submissions WHERE lead_id = ?", (lead_id,))
    for sub in submissions:
        file_path = sub.get("resume_file_path")
        if file_path:
            delete_stored_file(file_path)

    now_iso = datetime.utcnow().isoformat()

    # 2. Anonymize submissions
    execute("""
        UPDATE ats_submissions SET
            resume_file_path = NULL,
            extracted_text = NULL,
            job_description_text = NULL,
            is_anonymous = TRUE
        WHERE lead_id = ?
    """, (lead_id,))

    # 3. Scrub lead record
    execute("""
        UPDATE ats_leads SET
            full_name = '[PURGED_USER]',
            email = '[PURGED_' || id || '@deleted.auriic.internal]',
            phone = NULL,
            location = NULL,
            linkedin_url = NULL,
            deleted_at = ?
        WHERE id = ?
    """, (now_iso, lead_id))

    # 4. Audit Log
    execute("""
        INSERT INTO ats_audit_logs (actor, action, target_lead_id, details)
        VALUES (?, 'purge_lead_pii', ?, 'Permanently removed resume files, extracted text, and contact details.')
    """, (actor, lead_id))

    return True
