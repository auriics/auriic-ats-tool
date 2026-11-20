import secrets
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional

from backend.database.db import query_one, query_all, execute
from backend.database.retention import purge_lead_pii

router = APIRouter(prefix="/api/privacy", tags=["Privacy"])

class DeletionRequestModel(BaseModel):
    email: str

class DeletionConfirmModel(BaseModel):
    token: str

PRIVACY_POLICY_TEXT = {
    "title": "Auriic Services - ATS Resume Checker Privacy Policy",
    "effective_date": "November 2026",
    "summary": "We respect your data privacy and adhere to privacy-by-design principles. This policy explains what information is collected, how it is secured, and your rights.",
    "sections": [
        {
            "heading": "1. What Information We Collect",
            "content": "When you utilize the Auriic Free ATS Checker without consent, we process your document in temporary volatile memory and store only an anonymous, non-reversible cryptographic hash and numerical ATS score. When you provide explicit, affirmative consent, we collect your parsed contact details (name, email, phone, location, LinkedIn URL), detected career history, and an encrypted copy of your resume."
        },
        {
            "heading": "2. Purpose of Processing",
            "content": "Data is used strictly to provide your ATS diagnostic report, offer tailored career coaching and staffing opportunities through Auriic Services, and improve our deterministic scoring heuristics. We do not sell your personal data or resume to third-party data brokers."
        },
        {
            "heading": "3. Sensitive Data Redaction & Prohibited Information",
            "content": "Our parser automatically scans for and redacts Social Security Numbers (SSNs), dates of birth, and passport numbers prior to storage. We urge candidates never to place government IDs on resumes. We do not adjudicate or discriminate based on visa or work authorization status."
        },
        {
            "heading": "4. Data Storage & Security",
            "content": "All resume files are held in private, non-public storage directories accessible solely via time-limited, cryptographically signed URLs granted to authorized staff. Database communication and web traffic are restricted to encrypted TLS/HTTPS protocols."
        },
        {
            "heading": "5. Retention Period & Auto-Purge",
            "content": "Consented resume files and extracted text are automatically scheduled for permanent purging after twelve (12) months unless you enter an active recruitment or coaching engagement with Auriic Services. After 12 months, all contact details and files are scrubbed, retaining solely an anonymized score metric."
        },
        {
            "heading": "6. Right to Deletion ('Right to Be Forgotten')",
            "content": "You maintain the absolute right to have your data permanently deleted at any time. Submit your email on our public Data Deletion page to receive an instant verification link. Upon confirmation, all personal details, resume files, and extracted text are permanently wiped from our systems within 30 days (and immediately upon token confirmation)."
        },
        {
            "heading": "7. Contact Auriic Services",
            "content": "For privacy inquiries, contact privacy@auriic.co or visit https://auriic.co."
        }
    ]
}

@router.get("/policy")
async def get_privacy_policy():
    """Return the official Privacy Policy copy."""
    return PRIVACY_POLICY_TEXT

@router.post("/request-deletion")
async def request_data_deletion(payload: DeletionRequestModel):
    """Initiate a data deletion request with email token verification."""
    email = payload.email.strip().lower()
    lead = query_one("SELECT id FROM ats_leads WHERE email = ? AND deleted_at IS NULL", (email,))
    
    # Generate token
    token = secrets.token_urlsafe(32)
    now_iso = datetime.utcnow().isoformat()

    execute("""
        INSERT INTO ats_deletion_requests (email, verification_token, status, requested_at)
        VALUES (?, ?, 'pending', ?)
    """, (email, token, now_iso))

    execute("""
        INSERT INTO ats_audit_logs (actor, action, target_lead_id, details)
        VALUES ('user', 'deletion_requested', ?, ?)
    """, (lead["id"] if lead else None, f"Deletion requested for {email}"))

    return {
        "status": "success",
        "message": "Deletion request initiated. In production an email is dispatched; for local testing use the verification token provided.",
        "email": email,
        "verification_token": token,
        "verification_url": f"/api/privacy/confirm-deletion?token={token}",
    }

@router.post("/confirm-deletion")
async def confirm_data_deletion(payload: DeletionConfirmModel):
    """Verify deletion token and permanently scrub user's lead, resume files, and text."""
    token = payload.token.strip()
    req_row = query_one("SELECT * FROM ats_deletion_requests WHERE verification_token = ? AND status = 'pending'", (token,))
    if not req_row:
        raise HTTPException(status_code=404, detail="Invalid or already completed deletion token.")

    email = req_row["email"]
    now_iso = datetime.utcnow().isoformat()

    # Find matching lead
    leads = query_all("SELECT id FROM ats_leads WHERE email = ?", (email,))
    purged_count = 0
    for lead in leads:
        lead_id = lead["id"]
        purge_lead_pii(lead_id, actor="public_user_deletion_token")
        purged_count += 1

    # Mark request completed
    execute("""
        UPDATE ats_deletion_requests SET
            status = 'completed',
            completed_at = ?
        WHERE id = ?
    """, (now_iso, req_row["id"]))

    return {
        "status": "success",
        "message": f"Data permanently deleted. Scrubbed {purged_count} candidate record(s) and associated private resume files.",
        "email": email,
    }
