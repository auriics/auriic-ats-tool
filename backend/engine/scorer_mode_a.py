import os
import re
from typing import Dict, List, Any, Optional
from backend.engine.industry_detector import detect_industry
from backend.config.loader import load_scoring_config

def get_scoring_config() -> Dict[str, Any]:
    return load_scoring_config()

def score_mode_a(parse_result: Dict[str, Any], user_industry_override: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute 100% Deterministic Mode A Scoring (General ATS Health Score).
    Total points: 100, divided into 6 fixed categories.
    """
    config = get_scoring_config()
    scoring_version = config.get("scoring_version", "1.0.0")
    weights = config["mode_a"]["weights"]

    deductions = []
    top_fixes = []

    # Detect Industry
    raw_text = parse_result.get("raw_text", "")
    industry_info = detect_industry(raw_text, user_industry_override)
    industry_id = industry_info["industry_id"]
    industry_name = industry_info["industry_name"]
    industry_skills = config.get("industries", {}).get(industry_id, {}).get("skills", [])

    # =========================================================================
    # 1. File and Format Readability (Max: 25 pts)
    # =========================================================================
    max_cat1 = weights["file_format_readability"]
    score_cat1 = max_cat1
    cat1_deductions = []

    # Scanned check
    if parse_result.get("is_scanned"):
        pts = 25
        score_cat1 -= pts
        cat1_deductions.append({
            "category": "File and Format Readability",
            "points_lost": pts,
            "severity": "CRITICAL",
            "reason": "Unreadable document text layer (scanned image).",
            "evidence": "Document contains images but virtually zero parseable text characters.",
            "recommendation": "Save and export your resume directly as a clean text-based PDF or DOCX file, not an image scan."
        })
    else:
        # Multi-column check
        if parse_result.get("has_multi_column"):
            pts = 8
            score_cat1 -= pts
            cat1_deductions.append({
                "category": "File and Format Readability",
                "points_lost": pts,
                "severity": "HIGH",
                "reason": "Multi-column layout detected.",
                "evidence": "Text blocks split into parallel left and right horizontal columns.",
                "recommendation": "Convert to a clean, single-column vertical layout. ATS parsers read left-to-right across columns, scrambling your sentences."
            })

        # Table check
        if parse_result.get("has_tables"):
            pts = 6
            score_cat1 -= pts
            cat1_deductions.append({
                "category": "File and Format Readability",
                "points_lost": pts,
                "severity": "HIGH",
                "reason": "Embedded tables or grid structure detected.",
                "evidence": "Found table cells or bordered grid sections.",
                "recommendation": "Remove tables and use standard tab stops or bullet indents for clean ATS parsing."
            })

        # Header/footer contact issue
        if parse_result.get("header_footer_contact"):
            pts = 5
            score_cat1 -= pts
            cat1_deductions.append({
                "category": "File and Format Readability",
                "points_lost": pts,
                "severity": "MEDIUM",
                "reason": "Contact info placed inside header/footer margins.",
                "evidence": "Phone or email located in top/bottom 8% margin boundaries.",
                "recommendation": "Move contact details into the main document body. Standard ATS parsers strip headers and footers to avoid repetitive margin clutter."
            })

        # Page count check
        page_count = parse_result.get("page_count", 1)
        if page_count > 3:
            pts = 6
            score_cat1 -= pts
            cat1_deductions.append({
                "category": "File and Format Readability",
                "points_lost": pts,
                "severity": "MEDIUM",
                "reason": f"Excessive resume length ({page_count} pages).",
                "evidence": f"Total document page count is {page_count}.",
                "recommendation": "Trim resume to 1-2 pages (or 3 pages maximum for executive/15+ year careers)."
            })
        elif page_count == 3:
            pts = 2
            score_cat1 -= pts
            cat1_deductions.append({
                "category": "File and Format Readability",
                "points_lost": pts,
                "severity": "LOW",
                "reason": "Resume spans 3 pages.",
                "evidence": f"Document length is {page_count} pages.",
                "recommendation": "Condense older roles to keep resume to 2 tight pages for standard recruiters."
            })

        # Font/icon issues
        font_issues = parse_result.get("font_issues", [])
        if font_issues:
            pts = 4
            score_cat1 -= pts
            cat1_deductions.append({
                "category": "File and Format Readability",
                "points_lost": pts,
                "severity": "LOW",
                "reason": "Non-standard icon fonts detected.",
                "evidence": ", ".join(font_issues[:2]),
                "recommendation": "Replace graphic icon fonts (phone, email icons) with plain text labels ('Email:', 'Phone:')."
            })

    score_cat1 = max(0, score_cat1)
    deductions.extend(cat1_deductions)

    # =========================================================================
    # 2. Contact and Basic Info (Max: 10 pts)
    # =========================================================================
    max_cat2 = weights["contact_basic_info"]
    score_cat2 = max_cat2
    cat2_deductions = []

    contact = parse_result.get("contact_info", {})
    if not contact.get("email"):
        pts = 3
        score_cat2 -= pts
        cat2_deductions.append({
            "category": "Contact and Basic Info",
            "points_lost": pts,
            "severity": "CRITICAL",
            "reason": "Missing email address.",
            "evidence": "No valid email address pattern found in document body.",
            "recommendation": "Add a professional email address (e.g., name@gmail.com) at the top of your resume."
        })

    if not contact.get("phone"):
        pts = 3
        score_cat2 -= pts
        cat2_deductions.append({
            "category": "Contact and Basic Info",
            "points_lost": pts,
            "severity": "HIGH",
            "reason": "Missing phone number.",
            "evidence": "No standard 10-digit or international telephone number pattern identified.",
            "recommendation": "Add your primary phone number with US area code (e.g., (555) 123-4567)."
        })

    if not contact.get("location"):
        pts = 2
        score_cat2 -= pts
        cat2_deductions.append({
            "category": "Contact and Basic Info",
            "points_lost": pts,
            "severity": "MEDIUM",
            "reason": "Missing location (City, State).",
            "evidence": "No 'City, State' pattern detected in contact area.",
            "recommendation": "Add your general location (e.g. 'Dallas, TX' or 'San Jose, CA'). Full street address is not needed."
        })

    if not contact.get("linkedin"):
        pts = 2
        score_cat2 -= pts
        cat2_deductions.append({
            "category": "Contact and Basic Info",
            "points_lost": pts,
            "severity": "MEDIUM",
            "reason": "Missing LinkedIn profile URL.",
            "evidence": "No 'linkedin.com/in/...' profile link found.",
            "recommendation": "Include a customized LinkedIn profile URL to build recruiter trust."
        })

    score_cat2 = max(0, score_cat2)
    deductions.extend(cat2_deductions)

    # =========================================================================
    # 3. Section Structure (Max: 20 pts)
    # =========================================================================
    max_cat3 = weights["section_structure"]
    score_cat3 = max_cat3
    cat3_deductions = []

    sections = parse_result.get("sections", {})
    
    if "experience" not in sections:
        pts = 7
        score_cat3 -= pts
        cat3_deductions.append({
            "category": "Section Structure",
            "points_lost": pts,
            "severity": "CRITICAL",
            "reason": "Missing standard Work Experience section heading.",
            "evidence": "Could not identify standard headings like 'Work Experience', 'Professional Experience', or 'Employment History'.",
            "recommendation": "Use a clear standard heading: 'PROFESSIONAL EXPERIENCE'."
        })

    if "education" not in sections:
        pts = 5
        score_cat3 -= pts
        cat3_deductions.append({
            "category": "Section Structure",
            "points_lost": pts,
            "severity": "HIGH",
            "reason": "Missing standard Education section heading.",
            "evidence": "Could not identify headings like 'Education' or 'Academic Background'.",
            "recommendation": "Add a dedicated section titled 'EDUCATION' outlining your degrees and institutions."
        })

    if "skills" not in sections:
        pts = 5
        score_cat3 -= pts
        cat3_deductions.append({
            "category": "Section Structure",
            "points_lost": pts,
            "severity": "HIGH",
            "reason": "Missing dedicated Skills section heading.",
            "evidence": "Could not find a distinct section named 'Skills', 'Technical Skills', or 'Core Competencies'.",
            "recommendation": "Add a prominent 'TECHNICAL SKILLS' or 'CORE COMPETENCIES' section for direct ATS indexing."
        })

    if "summary" not in sections:
        pts = 3
        score_cat3 -= pts
        cat3_deductions.append({
            "category": "Section Structure",
            "points_lost": pts,
            "severity": "LOW",
            "reason": "Missing Professional Summary section.",
            "evidence": "No 'Summary', 'Professional Summary', or 'Profile' section identified.",
            "recommendation": "Add a 2-3 sentence 'PROFESSIONAL SUMMARY' stating your target role, years of experience, and primary strengths."
        })

    score_cat3 = max(0, score_cat3)
    deductions.extend(cat3_deductions)

    # =========================================================================
    # 4. Experience Quality (Max: 20 pts)
    # =========================================================================
    max_cat4 = weights["experience_quality"]
    score_cat4 = max_cat4
    cat4_deductions = []

    exp_analysis = parse_result.get("experience_analysis", {})
    verb_ratio = exp_analysis.get("action_verb_ratio", 0.0)
    quant_ratio = exp_analysis.get("quantified_ratio", 0.0)
    has_dates = exp_analysis.get("has_dates", False)

    if not has_dates:
        pts = 5
        score_cat4 -= pts
        cat4_deductions.append({
            "category": "Experience Quality",
            "points_lost": pts,
            "severity": "HIGH",
            "reason": "Missing or inconsistent employment dates.",
            "evidence": "Fewer than 2 standard 4-digit year mentions (e.g., 2021 - 2024) found in experience text.",
            "recommendation": "Format dates clearly for every role (e.g., 'MM/YYYY - MM/YYYY' or 'Month Year - Present')."
        })

    # Action verbs check (target 70%)
    if verb_ratio < 0.40:
        pts = 5
        score_cat4 -= pts
        cat4_deductions.append({
            "category": "Experience Quality",
            "points_lost": pts,
            "severity": "MEDIUM",
            "reason": f"Low proportion of action-driven bullet points ({int(verb_ratio*100)}%).",
            "evidence": f"Only {exp_analysis.get('action_verb_bullets_count', 0)} of {exp_analysis.get('total_bullets', 0)} bullets begin with an action verb.",
            "recommendation": "Begin every bullet point with strong past-tense action verbs (e.g., 'Architected', 'Spearheaded', 'Optimized', 'Negotiated')."
        })
    elif verb_ratio < 0.65:
        pts = 2
        score_cat4 -= pts
        cat4_deductions.append({
            "category": "Experience Quality",
            "points_lost": pts,
            "severity": "LOW",
            "reason": f"Moderate action verb usage ({int(verb_ratio*100)}%).",
            "evidence": f"{exp_analysis.get('action_verb_bullets_count', 0)} of {exp_analysis.get('total_bullets', 0)} bullets use active verbs.",
            "recommendation": "Replace passive openers like 'Responsible for' or 'Assisted with' with direct action verbs."
        })

    # Quantified impact check (target 30%)
    if quant_ratio == 0:
        pts = 7
        score_cat4 -= pts
        cat4_deductions.append({
            "category": "Experience Quality",
            "points_lost": pts,
            "severity": "HIGH",
            "reason": "Zero quantified accomplishments detected.",
            "evidence": "No metrics, dollar amounts ($), percentages (%), or quantifiable KPIs detected in job bullets.",
            "recommendation": "Quantify outcomes with numbers (e.g., 'Reduced processing latency by 35%', 'Managed a $1.2M annual budget')."
        })
    elif quant_ratio < 0.25:
        pts = 3
        score_cat4 -= pts
        cat4_deductions.append({
            "category": "Experience Quality",
            "points_lost": pts,
            "severity": "MEDIUM",
            "reason": f"Limited quantified metrics ({int(quant_ratio*100)}% of bullets).",
            "evidence": f"Only {exp_analysis.get('quantified_bullets_count', 0)} bullets contain measurable statistics.",
            "recommendation": "Aim for at least 1-2 quantified metrics per role to prove tangible business impact."
        })

    score_cat4 = max(0, score_cat4)
    deductions.extend(cat4_deductions)

    # =========================================================================
    # 5. Skills and Keywords (Max: 15 pts)
    # =========================================================================
    max_cat5 = weights["skills_and_keywords"]
    score_cat5 = max_cat5
    cat5_deductions = []

    skills_text = sections.get("skills", "")
    if not skills_text or len(skills_text.strip()) < 15:
        pts = 5
        score_cat5 -= pts
        cat5_deductions.append({
            "category": "Skills and Keywords",
            "points_lost": pts,
            "severity": "HIGH",
            "reason": "Skills section is empty or too short.",
            "evidence": f"Skills section contains only {len(skills_text.strip())} characters.",
            "recommendation": "List 10-20 specific tools, frameworks, languages, and methodologies relevant to your industry."
        })

    # Industry skill density
    raw_lower = raw_text.lower()
    matched_industry_skills = [s for s in industry_skills if s.lower() in raw_lower]
    
    if len(matched_industry_skills) < 4:
        pts = 6
        score_cat5 -= pts
        cat5_deductions.append({
            "category": "Skills and Keywords",
            "points_lost": pts,
            "severity": "HIGH",
            "reason": f"Low density of core {industry_name} skills.",
            "evidence": f"Found only {len(matched_industry_skills)} key skills matching the detected industry ({', '.join(matched_industry_skills) if matched_industry_skills else 'None'}).",
            "recommendation": f"Incorporate core {industry_name} competencies such as: {', '.join(industry_skills[:6])}."
        })
    elif len(matched_industry_skills) < 8:
        pts = 2
        score_cat5 -= pts
        cat5_deductions.append({
            "category": "Skills and Keywords",
            "points_lost": pts,
            "severity": "LOW",
            "reason": f"Moderate {industry_name} skill coverage.",
            "evidence": f"Detected {len(matched_industry_skills)} industry skills.",
            "recommendation": f"Expand technical depth by including additional relevant tools (e.g. {', '.join([s for s in industry_skills if s not in matched_industry_skills][:4])})."
        })

    # Keyword stuffing check
    words = re.findall(r"[a-zA-Z]+", raw_text.lower())
    if words:
        from collections import Counter
        word_counts = Counter(words)
        stuffed_words = [w for w, c in word_counts.items() if c > 18 and len(w) > 4 and w not in {"experience", "managed", "worked", "including", "responsible"}]
        if stuffed_words:
            pts = 4
            score_cat5 -= pts
            cat5_deductions.append({
                "category": "Skills and Keywords",
                "points_lost": pts,
                "severity": "MEDIUM",
                "reason": "Potential keyword stuffing detected.",
                "evidence": f"Words repeated excessively: {', '.join(stuffed_words[:3])}.",
                "recommendation": "Vary your vocabulary. ATS systems and human screeners penalize repetitive keyword packing."
            })

    score_cat5 = max(0, score_cat5)
    deductions.extend(cat5_deductions)

    # =========================================================================
    # 6. Education and Certifications (Max: 10 pts)
    # =========================================================================
    max_cat6 = weights["education_certifications"]
    score_cat6 = max_cat6
    cat6_deductions = []

    edu_info = parse_result.get("education_info", {})
    if not edu_info.get("has_education") or not edu_info.get("degrees_found"):
        pts = 7
        score_cat6 -= pts
        cat6_deductions.append({
            "category": "Education and Certifications",
            "points_lost": pts,
            "severity": "HIGH",
            "reason": "No recognized degree level detected.",
            "evidence": "Could not identify standard degree designations (BS, MS, BA, MBA, PhD, Associate).",
            "recommendation": "Clearly state your degree type, major field of study, institution name, and graduation year."
        })

    certs = parse_result.get("certifications", [])
    if not certs and "certifications" not in sections:
        pts = 3
        score_cat6 -= pts
        cat6_deductions.append({
            "category": "Education and Certifications",
            "points_lost": pts,
            "severity": "LOW",
            "reason": "No professional licenses or certifications listed.",
            "evidence": "Certifications section absent or empty.",
            "recommendation": "Add any relevant licenses (e.g. CPA, RN, PE, PMP, OSHA, AWS, Scrum Master) to boost ATS score."
        })

    score_cat6 = max(0, score_cat6)
    deductions.extend(cat6_deductions)

    # =========================================================================
    # Compute Final Total and Rating
    # =========================================================================
    overall_score = round(score_cat1 + score_cat2 + score_cat3 + score_cat4 + score_cat5 + score_cat6, 1)
    overall_score = min(100.0, max(0.0, overall_score))

    if overall_score >= 85:
        label = "Excellent"
    elif overall_score >= 70:
        label = "Good"
    elif overall_score >= 50:
        label = "Fair"
    else:
        label = "Needs Work"

    # Prioritize Top 5 Fixes
    # Sort deductions by severity: CRITICAL > HIGH > MEDIUM > LOW, then by points_lost
    severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    sorted_deductions = sorted(
        deductions,
        key=lambda d: (severity_rank.get(d["severity"], 0), d["points_lost"]),
        reverse=True
    )
    top_fixes = sorted_deductions[:5]

    return {
        "mode": "A",
        "scoring_version": scoring_version,
        "overall_score": overall_score,
        "label": label,
        "detected_industry": industry_id,
        "detected_industry_name": industry_name,
        "is_industry_override": industry_info.get("is_override", False),
        "industry_confidence": industry_info.get("confidence", 0.0),
        "category_breakdown": {
            "file_format_readability": {"earned": score_cat1, "possible": max_cat1},
            "contact_basic_info": {"earned": score_cat2, "possible": max_cat2},
            "section_structure": {"earned": score_cat3, "possible": max_cat3},
            "experience_quality": {"earned": score_cat4, "possible": max_cat4},
            "skills_and_keywords": {"earned": score_cat5, "possible": max_cat5},
            "education_certifications": {"earned": score_cat6, "possible": max_cat6},
        },
        "deductions": deductions,
        "top_fixes": top_fixes,
        "matched_industry_skills": matched_industry_skills,
        "pii_alerts": parse_result.get("pii_alerts", []),
        "disclaimer": "This score is an estimate based on common ATS screening criteria across US corporate and agency platforms. No automated tool can guarantee interviews, staffing placement, or employment outcomes. Auriic Services makes no warranties or guarantees regarding job offers or visa sponsorship.",
    }
