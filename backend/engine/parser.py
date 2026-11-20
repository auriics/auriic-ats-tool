import os
import io
import re
from typing import Dict, List, Any, Optional, Tuple
import yaml

from backend.engine.normalizer import normalize_text_unicode, normalize_for_matching
from backend.engine.pii_sanitizer import sanitize_and_redact_pii

# Load config for heading definitions and action verbs
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "scoring_config.yaml")

def get_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# Regex Patterns for contact info extraction
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
PHONE_REGEX = re.compile(r"(?:\+?1[-.\s]*)?(?:\(?\b[2-9][0-9]{2}\)?[-.\s]*)[2-9][0-9]{2}[-.\s]*[0-9]{4}\b")
LINKEDIN_REGEX = re.compile(r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:in|profile)\/([a-zA-Z0-9_\-]+)\/?", re.IGNORECASE)
LOCATION_REGEX = re.compile(r"\b([A-Z][a-zA-Z\s.-]+),\s*([A-Z]{2})\b(?:\s+(\d{5}(?:-\d{4})?))?")

# Degree regex patterns
DEGREE_PATTERNS = [
    re.compile(r"\b(?:Ph\.?D\.?|Doctor of Philosophy|Doctorate)\b", re.IGNORECASE),
    re.compile(r"\b(?:Master(?:'s)?(?:\s+of\s+[A-Za-z]+)?|M\.?S\.?|M\.?A\.?|M\.?B\.?A\.?|M\.?Eng\.?)\b", re.IGNORECASE),
    re.compile(r"\b(?:Bachelor(?:'s)?(?:\s+of\s+[A-Za-z]+)?|B\.?S\.?|B\.?A\.?|B\.?B\.?A\.?|B\.?Eng\.?|B\.?Tech\.?)\b", re.IGNORECASE),
    re.compile(r"\b(?:Associate(?:'s)?(?:\s+Degree)?|A\.?S\.?|A\.?A\.?)\b", re.IGNORECASE),
]

# Action verbs and metric patterns
METRIC_REGEX = re.compile(r"(\$\s*[\d,.]+[kKmMbB]?|\b\d+(?:\.\d+)?%|\b[\d,]+(?:\.\d+)?\s*(?:users|clients|leads|students|patients|projects|tickets|dollars|revenue|sales|calls|units|hours|minutes|team members)\b|\b\d{2,}\b)", re.IGNORECASE)

class ResumeParser:
    def __init__(self):
        self.config = get_config()
        self.section_headings = self.config.get("section_headings", {})
        self.action_verbs = set(self.config.get("action_verbs", []))

    def parse_file(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Parse PDF, DOCX, or TXT file into extracted text, structured sections and layout flags."""
        filename_lower = filename.lower()
        if filename_lower.endswith(".pdf"):
            return self._parse_pdf(file_bytes, filename)
        elif filename_lower.endswith((".docx", ".doc")):
            return self._parse_docx(file_bytes, filename)
        elif filename_lower.endswith(".txt"):
            return self._parse_txt(file_bytes, filename)
        else:
            # Fallback attempt plain text
            return self._parse_txt(file_bytes, filename)

    def _parse_txt(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except Exception as e:
                return self._error_result(f"Failed to decode text file: {str(e)}")

        norm_text = normalize_text_unicode(text)
        return self._build_parse_result(
            raw_text=norm_text,
            page_count=max(1, len(norm_text.split("\n\n")) // 15),
            layout_issues=[],
            is_scanned=False,
            has_multi_column=False,
            has_tables=False,
            header_footer_contact=False,
            font_issues=[],
        )

    def _parse_docx(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            full_text = []
            has_tables = len(doc.tables) > 0
            
            # Paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text.strip())

            # Tables text
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_text:
                        full_text.append(" | ".join(row_text))

            # Header / Footer inspection
            header_text = []
            for section in doc.sections:
                for p in section.header.paragraphs:
                    if p.text.strip():
                        header_text.append(p.text.strip())
                for p in section.footer.paragraphs:
                    if p.text.strip():
                        header_text.append(p.text.strip())

            combined_text = "\n".join(full_text)
            norm_text = normalize_text_unicode(combined_text)
            
            # Check if contact info appears in header/footer but not in body
            header_combined = " ".join(header_text)
            header_has_email = bool(EMAIL_REGEX.search(header_combined))
            body_has_email = bool(EMAIL_REGEX.search(norm_text))
            header_footer_contact = header_has_email and not body_has_email

            if header_text and not body_has_email:
                norm_text = "\n".join(header_text) + "\n" + norm_text

            layout_issues = []
            if has_tables:
                layout_issues.append("Document uses embedded tables which can scramble ATS text extraction order.")

            approx_pages = max(1, len(norm_text.split("\n")) // 45)

            return self._build_parse_result(
                raw_text=norm_text,
                page_count=approx_pages,
                layout_issues=layout_issues,
                is_scanned=False,
                has_multi_column=False,
                has_tables=has_tables,
                header_footer_contact=header_footer_contact,
                font_issues=[],
            )
        except Exception as e:
            return self._error_result(f"Could not parse DOCX file: {str(e)}")

    def _parse_pdf(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Extract text from PDF using PyMuPDF (fitz) with pdfplumber fallback and layout inspection."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            
            page_count = len(doc)
            if page_count == 0:
                return self._error_result("The uploaded PDF has 0 pages.")

            extracted_pages_text = []
            total_images = 0
            has_multi_column = False
            has_tables = False
            header_footer_contact = False
            font_issues = []
            layout_issues = []

            for page_num in range(page_count):
                page = doc[page_num]
                page_rect = page.rect
                page_width = page_rect.width
                page_height = page_rect.height

                # Extract images count
                images = page.get_images()
                total_images += len(images)

                # Extract text blocks
                blocks = page.get_text("blocks")
                # Block format: (x0, y0, x1, y1, text, block_no, block_type)
                
                left_col_blocks = 0
                right_col_blocks = 0
                page_text_lines = []

                for b in blocks:
                    if b[6] == 0:  # Text block
                        x0, y0, x1, y1, b_text = b[0], b[1], b[2], b[3], b[4]
                        page_text_lines.append(b_text.strip())

                        # Check header/footer area (top 8% or bottom 8%)
                        is_in_header_footer = (y0 < 0.08 * page_height) or (y1 > 0.92 * page_height)
                        if is_in_header_footer and (EMAIL_REGEX.search(b_text) or PHONE_REGEX.search(b_text)):
                            header_footer_contact = True

                        # Column detection
                        if x0 < 0.45 * page_width and x1 > 0.20 * page_width:
                            left_col_blocks += 1
                        elif x0 > 0.50 * page_width:
                            right_col_blocks += 1

                if left_col_blocks >= 2 and right_col_blocks >= 2:
                    has_multi_column = True

                # Check fonts
                font_list = page.get_fonts()
                for f in font_list:
                    font_name = f[3]
                    if font_name and any(u in font_name.lower() for u in ["symbol", "dingbat", "wingding"]):
                        font_issues.append(f"Non-standard icon font detected: {font_name}")

                extracted_pages_text.append("\n".join(page_text_lines))

            combined_text = "\n\n".join(extracted_pages_text).strip()

            # Scanned document detection: images present but text layer empty or negligible
            total_text_length = len(combined_text)
            is_scanned = (total_images > 0 and total_text_length < (page_count * 60)) or (total_text_length < 30)

            # Check tables via pdfplumber fallback / verification
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(file_bytes)) as p_doc:
                    for p in p_doc.pages:
                        extracted_tables = p.extract_tables()
                        if extracted_tables and len(extracted_tables) > 0:
                            has_tables = True
                            break
            except Exception:
                pass

            if is_scanned:
                layout_issues.append("Document appears to be a scanned image with no readable text layer. Most ATS systems will reject this.")
            if has_multi_column:
                layout_issues.append("Multi-column layout detected. Many ATS parsers read horizontally across columns, scrambling content order.")
            if has_tables:
                layout_issues.append("Table structures detected. ATS parsers frequently fail to align columns and rows in resume tables.")
            if header_footer_contact:
                layout_issues.append("Contact details appear inside the document header/footer margins. ATS scanners routinely ignore header/footer zones.")

            norm_text = normalize_text_unicode(combined_text)

            return self._build_parse_result(
                raw_text=norm_text,
                page_count=page_count,
                layout_issues=layout_issues,
                is_scanned=is_scanned,
                has_multi_column=has_multi_column,
                has_tables=has_tables,
                header_footer_contact=header_footer_contact,
                font_issues=font_issues,
            )

        except Exception as e:
            # Fallback to pdfplumber if PyMuPDF experienced an issue
            return self._fallback_pdfplumber(file_bytes, filename, str(e))

    def _fallback_pdfplumber(self, file_bytes: bytes, filename: str, fitz_error: str) -> Dict[str, Any]:
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages_text = [p.extract_text() or "" for p in pdf.pages]
                combined_text = "\n\n".join(pages_text).strip()
                page_count = len(pdf.pages)
                norm_text = normalize_text_unicode(combined_text)
                is_scanned = len(norm_text) < (page_count * 60)
                return self._build_parse_result(
                    raw_text=norm_text,
                    page_count=page_count,
                    layout_issues=["Extracted using secondary engine due to complex formatting."] if not is_scanned else ["Document has no readable text layer."],
                    is_scanned=is_scanned,
                    has_multi_column=False,
                    has_tables=False,
                    header_footer_contact=False,
                    font_issues=[],
                )
        except Exception as e:
            return self._error_result(f"PDF extraction error: {fitz_error} | Fallback error: {str(e)}")

    def _build_parse_result(
        self,
        raw_text: str,
        page_count: int,
        layout_issues: List[str],
        is_scanned: bool,
        has_multi_column: bool,
        has_tables: bool,
        header_footer_contact: bool,
        font_issues: List[str],
    ) -> Dict[str, Any]:
        """Segment sections, extract entities, identify action verbs and metrics."""
        # Sanitize PII before persisting or returning
        clean_text, pii_alerts = sanitize_and_redact_pii(raw_text)

        # Contact extraction
        contact_info = self._extract_contact_info(clean_text)

        # Section extraction
        sections = self._extract_sections(clean_text)

        # Experience analysis (bullets, verbs, quantified metrics)
        experience_analysis = self._analyze_experience(sections.get("experience", clean_text))

        # Education extraction
        education_info = self._extract_education(sections.get("education", clean_text))

        # Skills extraction
        detected_skills = self._extract_skills(sections.get("skills", clean_text), clean_text)

        # Certifications extraction
        certifications_list = self._extract_certifications(sections.get("certifications", clean_text), clean_text)

        return {
            "success": True,
            "raw_text": clean_text,
            "page_count": page_count,
            "is_scanned": is_scanned,
            "has_multi_column": has_multi_column,
            "has_tables": has_tables,
            "header_footer_contact": header_footer_contact,
            "font_issues": font_issues,
            "layout_issues": layout_issues,
            "pii_alerts": pii_alerts,
            "contact_info": contact_info,
            "sections": sections,
            "experience_analysis": experience_analysis,
            "education_info": education_info,
            "detected_skills": detected_skills,
            "certifications": certifications_list,
        }

    def _extract_contact_info(self, text: str) -> Dict[str, Any]:
        email_match = EMAIL_REGEX.search(text)
        phone_match = PHONE_REGEX.search(text)
        linkedin_match = LINKEDIN_REGEX.search(text)
        location_match = LOCATION_REGEX.search(text)

        # Guess name from the first non-empty lines
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        candidate_name = ""
        for line in lines[:5]:
            if not EMAIL_REGEX.search(line) and not PHONE_REGEX.search(line) and not LINKEDIN_REGEX.search(line):
                # Avoid headers like "RESUME"
                if len(line.split()) in [2, 3, 4] and not any(k in line.lower() for k in ["summary", "engineer", "manager", "curriculum", "resume", "cv"]):
                    candidate_name = line
                    break
        if not candidate_name and lines:
            candidate_name = lines[0]

        return {
            "name": candidate_name[:60] if candidate_name else "Candidate",
            "email": email_match.group(0) if email_match else None,
            "phone": phone_match.group(0).strip() if phone_match else None,
            "linkedin": linkedin_match.group(0) if linkedin_match else None,
            "location": f"{location_match.group(1).strip()}, {location_match.group(2)}" if location_match else None,
        }

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Partition resume into recognized ATS sections using synonym dictionary."""
        lines = text.split("\n")
        sections = {}
        current_section = "header"
        sections[current_section] = []

        # Inverted index from heading synonym -> standard section name
        synonym_to_section = {}
        for section_name, synonyms in self.section_headings.items():
            for syn in synonyms:
                synonym_to_section[syn.lower()] = section_name

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            cleaned_heading = re.sub(r"[:\-_|#*]", "", stripped).strip().lower()
            if cleaned_heading in synonym_to_section and len(stripped.split()) <= 4:
                current_section = synonym_to_section[cleaned_heading]
                if current_section not in sections:
                    sections[current_section] = []
                continue

            sections[current_section].append(line)

        return {sec: "\n".join(content_lines).strip() for sec, content_lines in sections.items() if content_lines}

    def _analyze_experience(self, exp_text: str) -> Dict[str, Any]:
        """Examine bullet points for action verbs, quantified results, and dates."""
        lines = exp_text.split("\n")
        bullet_points = []
        for line in lines:
            line_str = line.strip()
            if line_str.startswith(("-", "•", "*", "–", "—", ">", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")) or (len(line_str) > 25 and not line_str.endswith(":")):
                cleaned_bullet = re.sub(r"^[-•*–—>0-9.]+\s*", "", line_str)
                if len(cleaned_bullet) > 15:
                    bullet_points.append(cleaned_bullet)

        if not bullet_points and len(lines) > 2:
            bullet_points = [l.strip() for l in lines if len(l.strip()) > 25]

        total_bullets = len(bullet_points)
        verb_bullets = []
        quantified_bullets = []
        action_verbs_found = []

        for bullet in bullet_points:
            words = re.findall(r"[a-zA-Z]+", bullet.lower())
            first_word = words[0] if words else ""
            
            # Check action verb in first 2 words
            has_verb = False
            for w in words[:2]:
                if w in self.action_verbs:
                    has_verb = True
                    action_verbs_found.append(w)
                    break
            if has_verb:
                verb_bullets.append(bullet)

            # Check quantified metric
            if METRIC_REGEX.search(bullet):
                quantified_bullets.append(bullet)

        action_verb_ratio = round(len(verb_bullets) / max(1, total_bullets), 2)
        quantified_ratio = round(len(quantified_bullets) / max(1, total_bullets), 2)

        # Date consistency check
        date_matches = re.findall(r"\b(?:19|20)\d{2}\b", exp_text)
        has_dates = len(date_matches) >= 2

        return {
            "total_bullets": total_bullets,
            "action_verb_bullets_count": len(verb_bullets),
            "action_verb_ratio": action_verb_ratio,
            "quantified_bullets_count": len(quantified_bullets),
            "quantified_ratio": quantified_ratio,
            "has_dates": has_dates,
            "action_verbs_detected": list(set(action_verbs_found))[:15],
            "sample_quantified_bullets": quantified_bullets[:3],
        }

    def _extract_education(self, edu_text: str) -> Dict[str, Any]:
        degrees_found = []
        for pat in DEGREE_PATTERNS:
            match = pat.search(edu_text)
            if match:
                degrees_found.append(match.group(0))

        # Check for GPA mention
        gpa_match = re.search(r"\b(?:GPA|Grade Point Average)\s*[:\-]?\s*([0-4]\.\d{1,2})\b", edu_text, re.IGNORECASE)
        gpa = gpa_match.group(1) if gpa_match else None

        # Check for graduation year
        grad_year_match = re.search(r"\b(?:19|20)\d{2}\b", edu_text)
        grad_year = grad_year_match.group(0) if grad_year_match else None

        return {
            "has_education": len(degrees_found) > 0 or len(edu_text.strip()) > 30,
            "degrees_found": degrees_found,
            "gpa": gpa,
            "grad_year": grad_year,
            "text": edu_text[:300],
        }

    def _extract_skills(self, skills_section_text: str, full_text: str) -> List[str]:
        """Extract skills mentioned in skills section or throughout text."""
        # Split on commas, bullets, pipes, or newlines
        raw_candidates = re.split(r"[,|\n•*–—/]", skills_section_text)
        skills = []
        for c in raw_candidates:
            token = c.strip()
            if 1 < len(token) < 35 and not any(k in token.lower() for k in ["skills", "proficiencies", "competencies"]):
                skills.append(token)
        return skills[:40]

    def _extract_certifications(self, cert_section_text: str, full_text: str) -> List[str]:
        raw_candidates = re.split(r"[,|\n•*–—]", cert_section_text)
        certs = []
        for c in raw_candidates:
            token = c.strip()
            if 2 < len(token) < 50:
                certs.append(token)
        return certs[:15]

    def _error_result(self, error_message: str) -> Dict[str, Any]:
        return {
            "success": False,
            "error": error_message,
            "raw_text": "",
            "page_count": 0,
            "is_scanned": False,
            "has_multi_column": False,
            "has_tables": False,
            "header_footer_contact": False,
            "font_issues": [],
            "layout_issues": [error_message],
            "pii_alerts": [],
            "contact_info": {"name": "", "email": None, "phone": None, "linkedin": None, "location": None},
            "sections": {},
            "experience_analysis": {"total_bullets": 0, "action_verb_ratio": 0, "quantified_ratio": 0, "has_dates": False, "action_verbs_detected": [], "sample_quantified_bullets": []},
            "education_info": {"has_education": False, "degrees_found": []},
            "detected_skills": [],
            "certifications": [],
        }
