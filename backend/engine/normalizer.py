import re
import unicodedata
import hashlib
from typing import Dict, List, Set, Optional

# Basic morphological lemmatizer rules to guarantee 100% deterministic normalization without external neural models
SUFFIX_REPLACEMENTS = [
    (r"ies$", "y"),
    (r"sses$", "ss"),
    (r"s$", ""),
    (r"ing$", ""),
    (r"ed$", ""),
    (r"tion$", "te"),
    (r"ment$", ""),
    (r"al$", ""),
]

def normalize_text_unicode(text: str) -> str:
    """Normalize unicode characters, quotes, dashes and line breaks."""
    if not text:
        return ""
    # Standard NFKC normalization
    text = unicodedata.normalize("NFKC", text)
    # Normalize common typographic punctuation
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    text = text.replace("–", "-").replace("—", "-").replace("•", " ").replace("·", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse tabs and multi-spaces within lines
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    # Strip excessive blank lines (max 2 consecutive)
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return cleaned.strip()

def normalize_for_matching(text: str) -> str:
    """Normalize text specifically for deterministic keyword and token comparison."""
    if not text:
        return ""
    text = normalize_text_unicode(text).lower()
    # Replace punctuation (except +, #, - which are part of C++, C#, CI/CD) with space
    text = re.sub(r"[^\w\s\+#\./-]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def deterministic_lemmatize(token: str) -> str:
    """Apply simple deterministic suffix stripping for canonical form."""
    token = token.lower().strip()
    if len(token) <= 3:
        return token
    # Keep known technical terms untouched
    if token in {"c++", "c#", "ci/cd", "k8s", "aws", "gcp", "sql", "r"}:
        return token
    for pattern, replacement in SUFFIX_REPLACEMENTS:
        if re.search(pattern, token) and len(token) > len(pattern) + 2:
            return re.sub(pattern, replacement, token)
    return token

def tokenize_and_lemmatize(text: str) -> List[str]:
    """Tokenize text into lower-cased lemmatized tokens."""
    normalized = normalize_for_matching(text)
    # Split into words/tokens
    raw_tokens = re.findall(r"[a-zA-Z0-9+#.-]+", normalized)
    return [deterministic_lemmatize(t) for t in raw_tokens if len(t) > 1 or t in {"c", "r"}]

def compute_content_hash(resume_text: str, jd_text: str = "", scoring_version: str = "1.0.0") -> str:
    """Compute SHA-256 fingerprint for caching and duplicate deduplication."""
    norm_resume = normalize_for_matching(resume_text)
    norm_jd = normalize_for_matching(jd_text)
    payload = f"V={scoring_version}|R={norm_resume}|JD={norm_jd}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
