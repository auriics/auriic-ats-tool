import os
import yaml
import re
import math
from collections import Counter
from typing import Dict, List, Any, Optional, Tuple
from rapidfuzz import fuzz

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

def _pure_tfidf_cosine(text1: str, text2: str) -> float:
    """Pure-Python deterministic TF-IDF cosine similarity fallback."""
    words1 = re.findall(r'\b[a-zA-Z]{2,}\b', text1.lower())
    words2 = re.findall(r'\b[a-zA-Z]{2,}\b', text2.lower())
    if not words1 or not words2:
        return 0.0
    c1 = Counter(words1)
    c2 = Counter(words2)
    vocabulary = set(c1.keys()).union(set(c2.keys()))
    dot = 0.0
    norm1 = 0.0
    norm2 = 0.0
    for word in vocabulary:
        in_docs = (1 if word in c1 else 0) + (1 if word in c2 else 0)
        idf = math.log((2.0 + 1.0) / (in_docs + 1.0)) + 1.0
        w1 = (c1[word] / len(words1)) * idf
        w2 = (c2[word] / len(words2)) * idf
        dot += w1 * w2
        norm1 += w1 * w1
        norm2 += w2 * w2
    denom = math.sqrt(norm1) * math.sqrt(norm2)
    return dot / denom if denom > 0 else 0.0

from backend.engine.normalizer import (
    normalize_text_unicode,
    normalize_for_matching,
    tokenize_and_lemmatize,
    deterministic_lemmatize,
)
from backend.engine.industry_detector import detect_industry

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "scoring_config.yaml")

def get_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# Seniority patterns
SENIORITY_RANKS = {
    "intern": 0,
    "entry": 1,
    "mid": 2,
    "senior": 3,
    "manager_executive": 4,
}

YEARS_EXP_REGEX = re.compile(
    r"\b(?:(\d{1,2})\+?|(\d{1,2})\s*-\s*(\d{1,2}))\s*(?:to\s*(\d{1,2}))?\s*(?:\+)?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+(?:relevant|professional|industry|direct))?\s+experience\b",
    re.IGNORECASE
)

DEGREE_HIERARCHY = {
    "associate": 1,
    "bachelor": 2,
    "master": 3,
    "doctorate": 4,
    "phd": 4,
}

class ModeBScorer:
    def __init__(self):
        self.config = get_config()
        self.synonyms = self.config.get("synonyms", {})
        self.seniority_levels = self.config.get("seniority_levels", {})
        self.weights = self.config["mode_b"]["weights"]
        self.scoring_version = self.config.get("scoring_version", "1.0.0")

    def score(
        self,
        parse_result: Dict[str, Any],
        jd_text: str,
        user_industry_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute deterministic Mode B (Resume + Job Description Match)."""
        clean_jd = normalize_text_unicode(jd_text)
        resume_text = parse_result.get("raw_text", "")
        norm_resume = normalize_for_matching(resume_text)
        resume_tokens = set(tokenize_and_lemmatize(resume_text))
        sections = parse_result.get("sections", {})

        # 1. Extract Skills, Tools, Requirements from JD
        jd_reqs = self._extract_jd_requirements(clean_jd)
        
        # 2. Hard Skills / Keyword Matching (35 pts)
        keyword_table, cat1_score, cat1_deductions = self._match_hard_skills(
            jd_reqs, resume_text, norm_resume, resume_tokens, sections
        )

        # 3. Job Title and Seniority Alignment (15 pts)
        cat2_score, cat2_deductions, seniority_info = self._match_title_and_seniority(
            clean_jd, resume_text, sections
        )

        # 4. Experience Relevance & Years Required (15 pts)
        cat3_score, cat3_deductions, exp_info = self._match_experience_years(
            clean_jd, resume_text, parse_result
        )

        # 5. Education & Certification Requirements (10 pts)
        cat4_score, cat4_deductions = self._match_education_and_certs(
            clean_jd, resume_text, parse_result
        )

        # 6. Soft Skills & Responsibilities Coverage (10 pts)
        cat5_score, cat5_deductions = self._match_soft_skills_and_responsibilities(
            clean_jd, resume_text, sections
        )

        # 7. Formatting & Parseability (10 pts) - derived from Mode A checks
        cat6_score, cat6_deductions = self._evaluate_formatting_parseability(parse_result)

        # 8. Location & Work Auth mentions (5 pts)
        cat7_score, cat7_deductions, loc_auth_info = self._match_location_and_work_auth(
            clean_jd, resume_text, parse_result
        )

        # Aggregate Overall Score
        overall_score = round(
            cat1_score + cat2_score + cat3_score + cat4_score + cat5_score + cat6_score + cat7_score, 1
        )
        overall_score = min(100.0, max(0.0, overall_score))

        if overall_score >= 85:
            label = "Excellent"
        elif overall_score >= 70:
            label = "Good"
        elif overall_score >= 50:
            label = "Fair"
        else:
            label = "Needs Work"

        # Combine all deductions
        all_deductions = (
            cat1_deductions + cat2_deductions + cat3_deductions +
            cat4_deductions + cat5_deductions + cat6_deductions + cat7_deductions
        )

        # Prioritize Top 5 Fixes
        severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        top_fixes = sorted(
            all_deductions,
            key=lambda d: (severity_rank.get(d["severity"], 0), d["points_lost"]),
            reverse=True
        )[:5]

        # Top 5 Missing Keywords for quick display
        missing_keywords = [
            k["keyword"] for k in keyword_table if k["status"] == "Missing"
        ][:5]

        return {
            "mode": "B",
            "scoring_version": self.scoring_version,
            "overall_score": overall_score,
            "label": label,
            "category_breakdown": {
                "hard_skills_keyword_match": {"earned": cat1_score, "possible": self.weights["hard_skills_keyword_match"]},
                "job_title_seniority_alignment": {"earned": cat2_score, "possible": self.weights["job_title_seniority_alignment"]},
                "experience_relevance_years": {"earned": cat3_score, "possible": self.weights["experience_relevance_years"]},
                "education_certification_requirements": {"earned": cat4_score, "possible": self.weights["education_certification_requirements"]},
                "soft_skills_responsibilities_coverage": {"earned": cat5_score, "possible": self.weights["soft_skills_responsibilities_coverage"]},
                "formatting_parseability": {"earned": cat6_score, "possible": self.weights["formatting_parseability"]},
                "location_work_auth_mentions": {"earned": cat7_score, "possible": self.weights["location_work_auth_mentions"]},
            },
            "keyword_table": keyword_table,
            "top_missing_keywords": missing_keywords,
            "deductions": all_deductions,
            "top_fixes": top_fixes,
            "seniority_alignment": seniority_info,
            "experience_match": exp_info,
            "location_and_work_auth": loc_auth_info,
            "pii_alerts": parse_result.get("pii_alerts", []),
            "disclaimer": "This score estimates ATS algorithmic compatibility for the specific job description provided. It does not evaluate hiring authority preference, portfolio quality, or guarantee interview selection.",
        }

    def _extract_jd_requirements(self, jd_text: str) -> Dict[str, Any]:
        """Parse Job Description for required vs preferred skills and tools."""
        lines = jd_text.split("\n")
        required_keywords = []
        preferred_keywords = []

        # Detect sections in JD
        current_zone = "general"
        for line in lines:
            line_clean = line.strip().lower()
            if any(k in line_clean for k in ["required", "requirements", "minimum qualifications", "must have", "what you need"]):
                current_zone = "required"
                continue
            elif any(k in line_clean for k in ["preferred", "nice to have", "desired", "bonus", "plus", "preferred qualifications"]):
                current_zone = "preferred"
                continue
            elif any(k in line_clean for k in ["responsibilities", "what you will do", "duties"]):
                current_zone = "responsibilities"
                continue

            # Extract tech terms / skill candidates
            # Check all known industry skills from config
            for ind_id, ind_data in self.config.get("industries", {}).items():
                for skill in ind_data.get("skills", []):
                    # Word boundary check
                    pattern = r"\b" + re.escape(skill) + r"\b"
                    if re.search(pattern, line, re.IGNORECASE):
                        if current_zone == "preferred":
                            if skill not in preferred_keywords:
                                preferred_keywords.append(skill)
                        else:
                            if skill not in required_keywords:
                                required_keywords.append(skill)

        # If required list is empty, treat all detected as required
        if not required_keywords and preferred_keywords:
            required_keywords = preferred_keywords
            preferred_keywords = []
        elif not required_keywords and not preferred_keywords:
            # Fallback: extract capitalized noun phrases or acronyms
            words = re.findall(r"\b[A-Z][a-zA-Z0-9+#.-]{1,15}\b", jd_text)
            common_filters = {"The", "We", "You", "Our", "Job", "Role", "Team", "Work", "Salary", "Apply", "About", "Company"}
            candidates = [w for w in set(words) if w not in common_filters][:15]
            required_keywords = candidates[:10]
            preferred_keywords = candidates[10:]

        return {
            "required": required_keywords,
            "preferred": preferred_keywords,
        }

    def _match_hard_skills(
        self,
        jd_reqs: Dict[str, Any],
        resume_text: str,
        norm_resume: str,
        resume_tokens: set,
        sections: Dict[str, str]
    ) -> Tuple[List[Dict[str, Any]], float, List[Dict[str, Any]]]:
        """Perform exact, lemmatized, synonym, and fuzzy keyword matching."""
        max_points = self.weights["hard_skills_keyword_match"]
        keyword_table = []
        deductions = []

        required_skills = jd_reqs.get("required", [])
        preferred_skills = jd_reqs.get("preferred", [])

        if not required_skills and not preferred_skills:
            # If JD had no specific skills extracted, award default baseline
            return [], max_points, []

        total_weight = (len(required_skills) * 2.0) + (len(preferred_skills) * 1.0)
        earned_weight = 0.0

        for skill in required_skills:
            status, where_found, pts_factor = self._find_keyword_in_resume(
                skill, resume_text, norm_resume, resume_tokens, sections
            )
            keyword_table.append({
                "keyword": skill,
                "type": "Required",
                "status": status,
                "location_found": where_found or "Not Found",
            })
            earned_weight += (2.0 * pts_factor)

            if status == "Missing":
                deductions.append({
                    "category": "Hard Skills / Keyword Match",
                    "points_lost": round((2.0 / max(1.0, total_weight)) * max_points, 1),
                    "severity": "HIGH",
                    "reason": f"Missing required skill: '{skill}'.",
                    "evidence": f"The job description specifies '{skill}' as a core qualification, but it was not found in your resume.",
                    "recommendation": f"Add '{skill}' to your skills section and illustrate your experience with it in your work history."
                })

        for skill in preferred_skills:
            status, where_found, pts_factor = self._find_keyword_in_resume(
                skill, resume_text, norm_resume, resume_tokens, sections
            )
            keyword_table.append({
                "keyword": skill,
                "type": "Preferred",
                "status": status,
                "location_found": where_found or "Not Found",
            })
            earned_weight += (1.0 * pts_factor)

        # Pro-rated score
        score = round((earned_weight / max(1.0, total_weight)) * max_points, 1)
        score = min(float(max_points), max(0.0, score))
        return keyword_table, score, deductions

    def _find_keyword_in_resume(
        self,
        skill: str,
        resume_text: str,
        norm_resume: str,
        resume_tokens: set,
        sections: Dict[str, str]
    ) -> Tuple[str, str, float]:
        """
        Check for skill:
        1. Exact string match (1.0)
        2. Lemmatized match (1.0)
        3. Configured synonym map match (0.85)
        4. Rapidfuzz token ratio >= 88 (0.75)
        """
        norm_skill = normalize_for_matching(skill)
        
        # 1. Exact match
        pattern = r"\b" + re.escape(skill) + r"\b"
        match = re.search(pattern, resume_text, re.IGNORECASE)
        if match or norm_skill in norm_resume:
            section_name = self._find_containing_section(skill, sections)
            return "Found", f"{section_name} (Exact match)", 1.0

        # 2. Lemmatized token match
        lem_skill = deterministic_lemmatize(norm_skill)
        if lem_skill in resume_tokens:
            section_name = self._find_containing_section(lem_skill, sections)
            return "Found", f"{section_name} (Stem match)", 1.0

        # 3. Synonym map check
        synonym_target = self.synonyms.get(norm_skill)
        if synonym_target:
            if synonym_target in norm_resume or deterministic_lemmatize(synonym_target) in resume_tokens:
                section_name = self._find_containing_section(synonym_target, sections)
                return "Partial", f"{section_name} (Matched via synonym '{synonym_target}')", 0.85

        # Also check reverse synonyms
        for k, v in self.synonyms.items():
            if v == norm_skill and (k in norm_resume or deterministic_lemmatize(k) in resume_tokens):
                section_name = self._find_containing_section(k, sections)
                return "Partial", f"{section_name} (Matched via acronym '{k}')", 0.85

        # 4. RapidFuzz check (partial token set ratio)
        best_ratio = fuzz.partial_token_set_ratio(norm_skill, norm_resume)
        if best_ratio >= 90:
            return "Partial", f"Body Text (Fuzzy match {int(best_ratio)}%)", 0.75

        return "Missing", "", 0.0

    def _find_containing_section(self, keyword: str, sections: Dict[str, str]) -> str:
        kw_lower = keyword.lower()
        for sec_name, content in sections.items():
            if kw_lower in content.lower():
                return sec_name.capitalize()
        return "Body Text"

    def _match_title_and_seniority(
        self,
        jd_text: str,
        resume_text: str,
        sections: Dict[str, str]
    ) -> Tuple[float, List[Dict[str, Any]], Dict[str, Any]]:
        """Evaluate Job Title & Seniority match (15 pts)."""
        max_points = self.weights["job_title_seniority_alignment"]
        deductions = []

        # Detect JD seniority
        jd_seniority = self._detect_seniority(jd_text)
        resume_seniority = self._detect_seniority(sections.get("experience", resume_text))

        score = max_points

        jd_rank = SENIORITY_RANKS.get(jd_seniority, 2)
        res_rank = SENIORITY_RANKS.get(resume_seniority, 2)

        if res_rank < jd_rank:
            # Candidate lower than requested
            diff = jd_rank - res_rank
            pts_lost = min(7.0, diff * 3.5)
            score -= pts_lost
            deductions.append({
                "category": "Job Title and Seniority Alignment",
                "points_lost": pts_lost,
                "severity": "HIGH" if diff >= 2 else "MEDIUM",
                "reason": f"Seniority gap: Job specifies '{jd_seniority.replace('_', ' ').capitalize()}' level, while resume presents '{resume_seniority.replace('_', ' ').capitalize()}' level experience.",
                "evidence": f"Resume title keywords align with {resume_seniority.capitalize()} seniority.",
                "recommendation": f"Highlight leadership, cross-functional ownership, and mentoring experience to align with {jd_seniority.capitalize()} role requirements."
            })
        elif res_rank > jd_rank:
            # Overqualified (slight adjustment)
            pts_lost = 2.0
            score -= pts_lost
            deductions.append({
                "category": "Job Title and Seniority Alignment",
                "points_lost": pts_lost,
                "severity": "LOW",
                "reason": f"Potential overqualification flag: Job is '{jd_seniority}' while resume indicates '{resume_seniority}' background.",
                "evidence": f"Resume indicates executive/senior background.",
                "recommendation": "Tailor title and responsibilities so the recruiter does not view you as likely to decline the pay bracket."
            })

        seniority_info = {
            "jd_seniority": jd_seniority,
            "resume_seniority": resume_seniority,
            "is_aligned": res_rank >= jd_rank,
        }

        return max(0.0, score), deductions, seniority_info

    def _detect_seniority(self, text: str) -> str:
        text_lower = text.lower()
        for level, keywords in reversed(list(self.seniority_levels.items())):
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                    return level
        return "mid"

    def _match_experience_years(
        self,
        jd_text: str,
        resume_text: str,
        parse_result: Dict[str, Any]
    ) -> Tuple[float, List[Dict[str, Any]], Dict[str, Any]]:
        """Evaluate required years of experience vs resume history (15 pts)."""
        max_points = self.weights["experience_relevance_years"]
        deductions = []

        # Find required years in JD
        match = YEARS_EXP_REGEX.search(jd_text)
        required_years = 0
        if match:
            # Capture first numeric group
            num_str = match.group(1) or match.group(2)
            if num_str:
                required_years = int(num_str)

        # Estimate resume years from date spans
        years_found = re.findall(r"\b(19\d{2}|20\d{2})\b", resume_text)
        unique_years = sorted(list(set(int(y) for y in years_found if 1980 <= int(y) <= 2026)))
        
        if len(unique_years) >= 2:
            detected_resume_years = unique_years[-1] - unique_years[0]
        else:
            # Fallback estimation
            detected_resume_years = 2 if len(resume_text.split()) > 200 else 1

        score = max_points
        if required_years > 0:
            if detected_resume_years < required_years:
                gap = required_years - detected_resume_years
                pts_lost = min(float(max_points), gap * 3.0)
                score -= pts_lost
                deductions.append({
                    "category": "Experience Relevance and Years Required",
                    "points_lost": pts_lost,
                    "severity": "HIGH",
                    "reason": f"Years of experience gap: JD requests {required_years}+ years; resume indicates approx {detected_resume_years} years.",
                    "evidence": f"Found career timeline span from {unique_years[0] if unique_years else 'N/A'} to {unique_years[-1] if unique_years else 'N/A'}.",
                    "recommendation": f"Emphasize comprehensive project depth, graduate education, or freelancing to substantiate {required_years} years of subject matter expertise."
                })

        exp_info = {
            "required_years": required_years,
            "detected_resume_years": detected_resume_years,
            "meets_experience_requirement": detected_resume_years >= required_years,
        }

        return max(0.0, score), deductions, exp_info

    def _match_education_and_certs(
        self,
        jd_text: str,
        resume_text: str,
        parse_result: Dict[str, Any]
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Check degree and licensing requirements in JD (10 pts)."""
        max_points = self.weights["education_certification_requirements"]
        score = max_points
        deductions = []

        jd_lower = jd_text.lower()
        res_edu = parse_result.get("education_info", {})
        res_certs = [c.lower() for c in parse_result.get("certifications", [])]

        # Check degree requirement in JD
        jd_degree = None
        for deg_name, rank in reversed(list(DEGREE_HIERARCHY.items())):
            if deg_name in jd_lower:
                jd_degree = deg_name
                break

        if jd_degree:
            res_degrees = [d.lower() for d in res_edu.get("degrees_found", [])]
            res_highest_rank = 0
            for d in res_degrees:
                for k, v in DEGREE_HIERARCHY.items():
                    if k in d:
                        res_highest_rank = max(res_highest_rank, v)

            req_rank = DEGREE_HIERARCHY.get(jd_degree, 2)
            if res_highest_rank < req_rank:
                pts_lost = 5.0
                score -= pts_lost
                deductions.append({
                    "category": "Education and Certification Requirements",
                    "points_lost": pts_lost,
                    "severity": "HIGH",
                    "reason": f"Degree level qualification gap: JD specifies {jd_degree.capitalize()} degree.",
                    "evidence": f"Detected degree qualifications: {', '.join(res_degrees) if res_degrees else 'No degree detected'}.",
                    "recommendation": f"If you hold an equivalent degree or are currently enrolled, clearly format your graduation/completion status."
                })

        # Check required certifications in JD
        cert_checks = ["PMP", "CPA", "RN", "PE", "OSHA", "AWS Certified", "Scrum Master", "CISSP", "Six Sigma"]
        for cert in cert_checks:
            pattern = r"\b" + re.escape(cert) + r"\b"
            if re.search(pattern, jd_text, re.IGNORECASE):
                # JD specifies this cert
                found_in_resume = re.search(pattern, resume_text, re.IGNORECASE) or any(cert.lower() in c for c in res_certs)
                if not found_in_resume:
                    pts_lost = 4.0
                    score -= pts_lost
                    deductions.append({
                        "category": "Education and Certification Requirements",
                        "points_lost": pts_lost,
                        "severity": "CRITICAL",
                        "reason": f"Missing mandatory license / credential: '{cert}'.",
                        "evidence": f"JD specifies '{cert}' as a required credential.",
                        "recommendation": f"Obtain or explicitly list your '{cert}' license number or active status."
                    })

        return max(0.0, score), deductions

    def _match_soft_skills_and_responsibilities(
        self,
        jd_text: str,
        resume_text: str,
        sections: Dict[str, str]
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Compute TF-IDF semantic overlap between JD and Resume Experience (10 pts)."""
        max_points = self.weights["soft_skills_responsibilities_coverage"]
        score = max_points
        deductions = []

        exp_text = sections.get("experience", resume_text)
        if not exp_text.strip() or not jd_text.strip():
            return 5.0, []

        try:
            # Deterministic TF-IDF cosine similarity
            if HAS_SKLEARN:
                vectorizer = TfidfVectorizer(
                    max_features=500,
                    ngram_range=(1, 2),
                    stop_words="english",
                )
                tfidf_matrix = vectorizer.fit_transform([jd_text, exp_text])
                similarity = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
            else:
                similarity = _pure_tfidf_cosine(jd_text, exp_text)
            
            # Map cosine similarity (typically 0.10 to 0.60 for resume vs JD) to points
            # 0.40+ is excellent (10 pts), 0.25-0.40 is good (7-9 pts), <0.20 needs improvement
            if similarity < 0.15:
                pts_lost = 5.0
                score -= pts_lost
                deductions.append({
                    "category": "Soft Skills and Responsibilities Coverage",
                    "points_lost": pts_lost,
                    "severity": "MEDIUM",
                    "reason": "Low vocabulary overlap with JD responsibilities.",
                    "evidence": f"Experience section semantic similarity score is {round(similarity * 100, 1)}%.",
                    "recommendation": "Mirror the exact phrasing and responsibility descriptions used in the job post across your bullet points."
                })
            elif similarity < 0.25:
                pts_lost = 2.0
                score -= pts_lost
                deductions.append({
                    "category": "Soft Skills and Responsibilities Coverage",
                    "points_lost": pts_lost,
                    "severity": "LOW",
                    "reason": "Moderate alignment with target role responsibilities.",
                    "evidence": f"Vocabulary overlap is {round(similarity * 100, 1)}%.",
                    "recommendation": "Incorporate key action verbs and duty descriptions directly from the JD's 'Responsibilities' section."
                })
        except Exception:
            score = 7.0

        return max(0.0, score), deductions

    def _evaluate_formatting_parseability(self, parse_result: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
        """Port format deductions to Mode B (10 pts)."""
        max_points = self.weights["formatting_parseability"]
        score = max_points
        deductions = []

        if parse_result.get("is_scanned"):
            score = 0.0
            deductions.append({
                "category": "Formatting and Parseability",
                "points_lost": max_points,
                "severity": "CRITICAL",
                "reason": "Unreadable scanned document.",
                "evidence": "Document contains no readable text layer.",
                "recommendation": "Export resume as a text-based PDF."
            })
        elif parse_result.get("has_multi_column"):
            score -= 4.0
            deductions.append({
                "category": "Formatting and Parseability",
                "points_lost": 4.0,
                "severity": "HIGH",
                "reason": "Multi-column layout hinders JD parser alignment.",
                "evidence": "Two-column text structure detected.",
                "recommendation": "Use single-column layout."
            })
        elif parse_result.get("has_tables"):
            score -= 3.0
            deductions.append({
                "category": "Formatting and Parseability",
                "points_lost": 3.0,
                "severity": "MEDIUM",
                "reason": "Embedded tables risk parsing alignment errors.",
                "evidence": "Tables detected in document.",
                "recommendation": "Remove table borders and format with standard bullet points."
            })

        return max(0.0, score), deductions

    def _match_location_and_work_auth(
        self,
        jd_text: str,
        resume_text: str,
        parse_result: Dict[str, Any]
    ) -> Tuple[float, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Evaluate Location / Work Auth mentions where the JD states them (5 pts).
        IMPORTANT: Report ONLY, never judge visa status!
        """
        max_points = self.weights["location_work_auth_mentions"]
        score = max_points
        deductions = []

        jd_lower = jd_text.lower()
        res_lower = resume_text.lower()
        loc = parse_result.get("contact_info", {}).get("location")

        # Check if JD specifies location or remote
        is_remote_jd = any(k in jd_lower for k in ["remote", "work from home", "wfh", "anywhere in us"])
        requires_onsite = any(k in jd_lower for k in ["on-site", "onsite", "in-person", "hybrid"])

        # Check work auth mention in JD
        auth_mentioned_in_jd = any(k in jd_lower for k in ["authorized to work", "work authorization", "us citizen", "green card", "visa sponsorship", "sponsorship not available"])
        
        info = {
            "jd_requires_specific_location": requires_onsite and not is_remote_jd,
            "jd_mentions_work_auth": auth_mentioned_in_jd,
            "resume_location": loc or "Not Specified",
            "notes": "Work authorization mentions reported for candidate awareness only; no visa eligibility adjudication performed."
        }

        # If JD requires location and resume does not specify location
        if requires_onsite and not loc:
            pts_lost = 2.0
            score -= pts_lost
            deductions.append({
                "category": "Location / Work Authorization Mentions",
                "points_lost": pts_lost,
                "severity": "LOW",
                "reason": "Job appears to be onsite/hybrid, but resume omits City/State.",
                "evidence": "Job description mentions on-site/hybrid attendance, but resume contact header has no location.",
                "recommendation": "Add your City and State to clarify geographic commute viability for the employer."
            })

        return max(0.0, score), deductions, info

def score_mode_b(
    parse_result: Dict[str, Any],
    jd_text: str,
    user_industry_override: Optional[str] = None
) -> Dict[str, Any]:
    scorer = ModeBScorer()
    return scorer.score(parse_result, jd_text, user_industry_override)
