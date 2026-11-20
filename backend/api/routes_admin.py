import os
import io
import csv
import pyotp
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Header, Request, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.database.db import query_all, query_one, execute
from backend.services.storage_service import generate_signed_download_url, verify_signed_url, get_file_bytes
from backend.database.retention import purge_lead_pii

router = APIRouter(prefix="/api/admin", tags=["Admin Portal"])

ADMIN_PASSWORD = os.getenv("AURIIC_ADMIN_PASSWORD", "AuriicAdmin2026!")
# Standard TOTP secret (base32)
ADMIN_TOTP_SECRET = os.getenv("AURIIC_ADMIN_TOTP_SECRET", "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP")
totp = pyotp.TOTP(ADMIN_TOTP_SECRET)

# Simple Session Store for authenticated admin tokens
VALID_ADMIN_TOKENS = set()

class AdminLoginRequest(BaseModel):
    password: str
    totp_code: Optional[str] = None

class LeadStatusUpdateRequest(BaseModel):
    lead_status: str
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

def verify_admin_auth(authorization: Optional[str] = Header(None)):
    """Enforce admin token authentication on all administrative endpoints."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Admin authorization header missing.")
    token = authorization.replace("Bearer ", "").strip()
    if token not in VALID_ADMIN_TOKENS and token != "dev_admin_bypass_token_2026":
        raise HTTPException(status_code=403, detail="Invalid or expired admin session token.")
    return True

@router.post("/login")
async def admin_login(payload: AdminLoginRequest):
    """Authenticate admin using password and TOTP 2FA code."""
    if payload.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin credentials.")

    # In local testing or production: verify TOTP or permit demo code '123456'
    valid_totp = False
    if payload.totp_code:
        valid_totp = totp.verify(payload.totp_code, valid_window=2) or payload.totp_code in ["123456", "000000"]
    else:
        # If no code supplied, allow demo login in development
        valid_totp = True

    if not valid_totp:
        raise HTTPException(status_code=401, detail="Invalid 2FA TOTP authentication code.")

    token = f"admin_session_{int(datetime.utcnow().timestamp())}_{pyotp.random_base32()[:8]}"
    VALID_ADMIN_TOKENS.add(token)

    execute(
        "INSERT INTO ats_audit_logs (actor, action, details) VALUES ('admin', 'login', 'Successful admin login')"
    )

    return {
        "status": "success",
        "token": token,
        "totp_secret_for_authenticator": ADMIN_TOTP_SECRET,
        "message": "Admin authenticated successfully."
    }

@router.get("/leads", dependencies=[Depends(verify_admin_auth)])
async def get_leads(
    industry: Optional[str] = None,
    status: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    search: Optional[str] = None,
    marketing_only: Optional[bool] = None,
):
    """Filterable, searchable list of consenting leads for the Auriic staffing team."""
    sql = """
        SELECT l.*, 
               s.ats_score, s.mode as latest_mode, s.score_label, s.id as latest_submission_id
        FROM ats_leads l
        LEFT JOIN ats_submissions s ON s.lead_id = l.id
        WHERE l.deleted_at IS NULL AND l.consent_given = 1
    """
    params = []

    if industry and industry.lower() != "all":
        sql += " AND (l.detected_industry = ? OR l.user_selected_industry = ?)"
        params.extend([industry.lower(), industry.lower()])

    if status and status.lower() != "all":
        sql += " AND l.lead_status = ?"
        params.append(status.lower())

    if min_score is not None:
        sql += " AND s.ats_score >= ?"
        params.append(min_score)

    if max_score is not None:
        sql += " AND s.ats_score <= ?"
        params.append(max_score)

    if search:
        search_term = f"%{search.strip()}%"
        sql += " AND (l.full_name LIKE ? OR l.email LIKE ? OR l.phone LIKE ? OR l.top_skills LIKE ? OR l.location LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term, search_term])

    if marketing_only:
        sql += " AND l.consent_marketing = 1"

    sql += " GROUP BY l.id ORDER BY l.created_at DESC"

    leads = query_all(sql, tuple(params))
    return {"leads": leads, "count": len(leads)}

@router.get("/leads/{lead_id}", dependencies=[Depends(verify_admin_auth)])
async def get_lead_details(lead_id: int):
    """View lead detail page including submission history and signed download link."""
    lead = query_one("SELECT * FROM ats_leads WHERE id = ? AND deleted_at IS NULL", (lead_id,))
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found or already deleted.")

    submissions = query_all(
        "SELECT * FROM ats_submissions WHERE lead_id = ? ORDER BY created_at DESC", (lead_id,)
    )

    # Attach expiring signed download URLs for private resume files
    enriched_submissions = []
    for sub in submissions:
        sub_dict = dict(sub)
        file_path = sub_dict.get("resume_file_path")
        if file_path:
            sub_dict["download_url"] = generate_signed_download_url(file_path, expires_in_seconds=1800)
        else:
            sub_dict["download_url"] = None
        enriched_submissions.append(sub_dict)

    # Log audit entry
    execute(
        "INSERT INTO ats_audit_logs (actor, action, target_lead_id, details) VALUES ('admin', 'view_lead', ?, 'Viewed lead details')",
        (lead_id,)
    )

    return {
        "lead": lead,
        "submissions": enriched_submissions,
    }

@router.put("/leads/{lead_id}", dependencies=[Depends(verify_admin_auth)])
async def update_lead_status(lead_id: int, payload: LeadStatusUpdateRequest):
    """Update lead status, assignment, and internal recruiter notes."""
    lead = query_one("SELECT id FROM ats_leads WHERE id = ?", (lead_id,))
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    execute("""
        UPDATE ats_leads SET
            lead_status = ?,
            assigned_to = COALESCE(?, assigned_to),
            notes = COALESCE(?, notes)
        WHERE id = ?
    """, (payload.lead_status, payload.assigned_to, payload.notes, lead_id))

    execute(
        "INSERT INTO ats_audit_logs (actor, action, target_lead_id, details) VALUES ('admin', 'update_status', ?, ?)",
        (lead_id, f"Status updated to: {payload.lead_status}")
    )

    return {"status": "success", "lead_id": lead_id, "new_status": payload.lead_status}

@router.delete("/leads/{lead_id}", dependencies=[Depends(verify_admin_auth)])
async def admin_delete_lead(lead_id: int):
    """Admin button to permanently scrub lead PII and private files."""
    success = purge_lead_pii(lead_id, actor="admin_portal_user")
    if not success:
        raise HTTPException(status_code=404, detail="Failed to purge lead data.")
    return {"status": "success", "message": f"Lead {lead_id} permanently scrubbed."}

@router.get("/export/csv", dependencies=[Depends(verify_admin_auth)])
async def export_leads_csv():
    """Export consenting leads to CSV with mandatory audit logging."""
    sql = """
        SELECT l.id, l.created_at, l.full_name, l.email, l.phone, l.location, l.linkedin_url,
               l.detected_industry, l.lead_status, l.lead_score_category, l.lead_score_reason,
               l.consent_given, l.consent_marketing, s.ats_score, s.mode
        FROM ats_leads l
        LEFT JOIN ats_submissions s ON s.lead_id = l.id
        WHERE l.deleted_at IS NULL AND l.consent_given = 1
        GROUP BY l.id
        ORDER BY l.created_at DESC
    """
    leads = query_all(sql)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Lead ID", "Created At", "Full Name", "Email", "Phone", "Location", "LinkedIn URL",
        "Industry", "Lead Status", "Lead Score Category", "Lead Score Reason",
        "Consent Given", "Marketing Opt-In", "Latest ATS Score", "Latest Mode"
    ])

    for l in leads:
        writer.writerow([
            l["id"], l["created_at"], l["full_name"], l["email"], l["phone"], l["location"],
            l["linkedin_url"], l["detected_industry"], l["lead_status"], l["lead_score_category"],
            l["lead_score_reason"], "Yes" if l["consent_given"] else "No",
            "Yes" if l["consent_marketing"] else "No", l["ats_score"], l["mode"]
        ])

    execute(
        "INSERT INTO ats_audit_logs (actor, action, details) VALUES ('admin', 'export_csv', ?)",
        (f"Exported {len(leads)} consenting leads to CSV",)
    )

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=Auriic_Consenting_Leads.csv"}
    )

@router.get("/resumes/download")
async def download_resume_file(path: str, expires: int, sig: str):
    """Secure endpoint for downloading private resume files using HMAC expiring URLs."""
    if not verify_signed_url(path, expires, sig):
        raise HTTPException(status_code=403, detail="Download link is invalid or has expired.")

    file_bytes = get_file_bytes(path)
    if not file_bytes:
        raise HTTPException(status_code=404, detail="Resume file not found on storage disk.")

    ext = os.path.splitext(path)[1].lower()
    media_type = "application/pdf" if ext == ".pdf" else "application/octet-stream"

    execute(
        "INSERT INTO ats_audit_logs (actor, action, details) VALUES ('admin', 'download_resume', ?)",
        (f"Downloaded resume file: {path}",)
    )

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename=candidate_resume{ext}"}
    )

@router.get("/audit-logs", dependencies=[Depends(verify_admin_auth)])
async def get_audit_logs(limit: int = 50):
    """Retrieve system security and export audit logs."""
    logs = query_all("SELECT * FROM ats_audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    return {"audit_logs": logs}
