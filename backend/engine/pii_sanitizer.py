import re
from typing import Dict, List, Tuple, Any

# Regular expressions for sensitive data
SSN_REGEX = re.compile(
    r"\b(?:\d{3}-\d{2}-\d{4}|\d{3}\s\d{2}\s\d{4}|(?:SSN|Social Security Number)\s*[:\-]?\s*\d{9})\b",
    re.IGNORECASE,
)

DOB_REGEX = re.compile(
    r"\b(?:DOB|Date of Birth|Birth Date|Birthdate)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})\b",
    re.IGNORECASE,
)

PASSPORT_REGEX = re.compile(
    r"\b(?:Passport(?:\s*(?:No|Number|#))?)\s*[:\-]?\s*([A-PR-WY0-9][0-9]{7,9})\b",
    re.IGNORECASE,
)

VISA_IMMIGRATION_REGEX = re.compile(
    r"\b(?:US Citizen|U\.S\. Citizen|Green Card|Permanent Resident|H-1B|H1B|OPT|STEM OPT|TN Visa|EAD|CPT|Work Authorization)\b",
    re.IGNORECASE,
)

def detect_pii(text: str) -> List[Dict[str, Any]]:
    """Scan resume text for sensitive PII markers that violate ATS and privacy best practices."""
    alerts = []
    lines = text.split("\n")

    for line_idx, line in enumerate(lines, 1):
        # SSN Check
        ssn_match = SSN_REGEX.search(line)
        if ssn_match:
            alerts.append({
                "type": "SSN",
                "severity": "CRITICAL",
                "line_number": line_idx,
                "evidence": ssn_match.group(0),
                "message": "Social Security Number (SSN) detected. Remove immediately to protect personal identity and prevent automated security disqualification."
            })

        # DOB Check
        dob_match = DOB_REGEX.search(line)
        if dob_match:
            alerts.append({
                "type": "DOB",
                "severity": "WARNING",
                "line_number": line_idx,
                "evidence": dob_match.group(0),
                "message": "Date of Birth detected. In the US, resumes must omit DOB to prevent age-based discrimination concerns under EEOC rules."
            })

        # Passport Check
        passport_match = PASSPORT_REGEX.search(line)
        if passport_match:
            alerts.append({
                "type": "PASSPORT",
                "severity": "CRITICAL",
                "line_number": line_idx,
                "evidence": passport_match.group(0),
                "message": "Passport number detected. Government identification numbers must never be included on public or ATS resumes."
            })

    return alerts

def sanitize_and_redact_pii(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Redact sensitive PII from text before persistence while returning detected alert list."""
    alerts = detect_pii(text)

    # Redact sensitive identifiers
    redacted = SSN_REGEX.sub("[REDACTED_SSN]", text)
    redacted = DOB_REGEX.sub("[REDACTED_DOB]", redacted)
    redacted = PASSPORT_REGEX.sub("[REDACTED_PASSPORT]", redacted)

    return redacted, alerts
