import os
import hmac
import hashlib
import time
import secrets
from typing import Optional, Tuple

if os.environ.get("VERCEL") or not os.access(os.path.dirname(os.path.dirname(__file__)), os.W_OK):
    STORAGE_DIR = "/tmp/auriic_data/storage/resumes"
else:
    STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "storage", "resumes")

SECRET_KEY = os.getenv("AURIIC_STORAGE_SECRET", "auriic_ats_storage_hmac_secret_2026_prod")

def ensure_storage_dir():
    os.makedirs(STORAGE_DIR, exist_ok=True)

def save_resume_file(file_bytes: bytes, original_filename: str, resume_hash: str) -> str:
    """Save resume securely into private storage directory. Returns relative storage path."""
    try:
        ensure_storage_dir()
        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in [".pdf", ".docx", ".doc", ".txt"]:
            ext = ".pdf"
        
        unique_name = f"{resume_hash}_{secrets.token_hex(4)}{ext}"
        target_path = os.path.join(STORAGE_DIR, unique_name)
        
        with open(target_path, "wb") as f:
            f.write(file_bytes)
            
        return os.path.relpath(target_path, start=os.path.dirname(STORAGE_DIR))
    except Exception as e:
        print(f"Storage notice (safe to continue): {e}")
        return ""

def get_file_bytes(relative_path: str) -> Optional[bytes]:
    """Retrieve resume bytes from private storage."""
    target_path = os.path.join(os.path.dirname(STORAGE_DIR), relative_path)
    if os.path.exists(target_path) and os.path.isfile(target_path):
        with open(target_path, "rb") as f:
            return f.read()
    return None

def generate_signed_download_url(relative_path: str, expires_in_seconds: int = 900) -> str:
    """Generate an HMAC-SHA256 signed expiring download URL (default 15 minutes)."""
    expires_at = int(time.time()) + expires_in_seconds
    payload = f"{relative_path}:{expires_at}"
    signature = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"/api/admin/resumes/download?path={relative_path}&expires={expires_at}&sig={signature}"

def verify_signed_url(relative_path: str, expires_at: int, signature: str) -> bool:
    """Verify that the download URL signature is valid and not expired."""
    if int(time.time()) > expires_at:
        return False
    payload = f"{relative_path}:{expires_at}"
    expected_sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_sig, signature)

def delete_stored_file(relative_path: str) -> bool:
    """Permanently delete a resume file for retention or deletion requests."""
    target_path = os.path.join(os.path.dirname(STORAGE_DIR), relative_path)
    if os.path.exists(target_path):
        try:
            os.remove(target_path)
            return True
        except Exception:
            return False
    return False
