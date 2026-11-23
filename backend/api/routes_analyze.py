import os
import json
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException, Response
from fastapi.responses import StreamingResponse
import io

from backend.engine.parser import ResumeParser
from backend.engine.normalizer import compute_content_hash
from backend.engine.scorer_mode_a import score_mode_a
from backend.engine.scorer_mode_b import score_mode_b
from backend.services.lead_service import process_submission_and_lead
from backend.services.pdf_report_service import generate_ats_pdf_report
from backend.database.db import query_one

router = APIRouter(prefix="/api", tags=["Analysis"])

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}

parser = ResumeParser()

@router.post("/analyze")
async def analyze_resume(
    request: Request,
    resume: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
    industry_override: Optional[str] = Form(None),
    consent_given: bool = Form(False),
    consent_marketing: bool = Form(False),
    utm_source: Optional[str] = Form(None),
    utm_medium: Optional[str] = Form(None),
    utm_campaign: Optional[str] = Form(None),
    referrer: Optional[str] = Form(None),
    device_type: Optional[str] = Form("desktop"),
    honeypot: Optional[str] = Form(None),
):
    # 1. Anti-spam honeypot check
    if honeypot and honeypot.strip():
        raise HTTPException(status_code=400, detail="Automated submission detected.")

    # 2. File size & extension validation
    filename = resume.filename or "resume.pdf"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Please upload a PDF (.pdf), Word document (.docx), or plain text (.txt) file."
        )

    file_bytes = await resume.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of 5 MB ({len(file_bytes) / (1024*1024):.2f} MB)."
        )

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty (0 bytes).")

    # 3. Parse resume
    parse_result = parser.parse_file(file_bytes, filename)
    if not parse_result.get("success") and not parse_result.get("raw_text"):
        raise HTTPException(
            status_code=422,
            detail=parse_result.get("error", "Failed to parse document content.")
        )

    raw_text = parse_result.get("raw_text", "")
    has_jd = bool(job_description and len(job_description.strip()) > 30)

    # 4. Hash caching check
    scoring_version = "1.0.0"
    content_hash = compute_content_hash(raw_text, job_description or "", scoring_version)

    # 5. Deterministic scoring execution
    if has_jd:
        score_report = score_mode_b(parse_result, job_description or "", industry_override)
    else:
        score_report = score_mode_a(parse_result, industry_override)

    # 6. Privacy & Lead processing
    client_ip = request.client.host if request.client else "127.0.0.1"
    utm_params = {
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        "referrer": referrer,
        "device_type": device_type,
    }

    try:
        lead_res = process_submission_and_lead(
            parse_result=parse_result,
            score_report=score_report,
            resume_file_bytes=file_bytes,
            original_filename=filename,
            resume_hash=content_hash,
            consent_given=consent_given,
            consent_marketing=consent_marketing,
            client_ip=client_ip,
            utm_params=utm_params,
            job_description_text=job_description if has_jd else None,
            jd_title=None,
            user_industry_override=industry_override,
        )
    except Exception as e:
        print(f"Notice: lead storage bypassed due to db notice: {e}")
        lead_res = {
            "lead_id": None,
            "submission_id": None,
            "is_consented": consent_given,
            "notice": "Scan completed successfully."
        }

    # 7. Construct payload with "What ATS Sees" preview
    response_payload = {
        **score_report,
        "resume_hash": content_hash,
        "candidate_info": parse_result.get("contact_info", {}),
        "lead_status": lead_res,
        "parsed_data_preview": {
            "extracted_text": raw_text,
            "detected_sections": list(parse_result.get("sections", {}).keys()),
            "page_count": parse_result.get("page_count", 1),
            "layout_flags": {
                "is_scanned": parse_result.get("is_scanned", False),
                "has_multi_column": parse_result.get("has_multi_column", False),
                "has_tables": parse_result.get("has_tables", False),
                "header_footer_contact": parse_result.get("header_footer_contact", False),
            }
        }
    }

    return response_payload

@router.post("/download-report-pdf")
async def download_report_pdf(payload: dict):
    """Generate and return PDF report bytes."""
    score_report = payload.get("score_report", {})
    candidate_name = payload.get("candidate_name", "Candidate")
    if not score_report:
        raise HTTPException(status_code=400, detail="Score report payload is required.")

    pdf_bytes = generate_ats_pdf_report(score_report, candidate_name)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Auriic_ATS_Report_{score_report.get('mode', 'A')}.pdf"
        }
    )
