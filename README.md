# Auriic Free ATS Resume Checker (https://ats.auriic.co)

A high-performance, 100% deterministic ATS resume checker and lead generation engine purpose-built for **Auriic Services** ([auriic.co](https://auriic.co)) — supporting US job seekers, OPT/STEM OPT candidates, H-1B professionals, and experienced talent across 8 major industry sectors.

---

## 🚀 Key Features

- **Dual Scoring Modes**:
  - **Mode A (Resume Only)**: 100-pt General ATS Health Score (format, sections, experience metrics, verbs, skills, credentials).
  - **Mode B (Resume + Job Description)**: 100-pt JD Match ATS Score (hard skills, seniority, experience, education, vocabulary alignment).
- **100% Deterministic Engine**:
  - Zero non-deterministic LLM scoring. Identical input guarantees identical scores and breakdowns every single run.
  - Normalization pipeline (Unicode NFKC, whitespace collapse, suffix lemmatization) with SHA-256 fingerprint caching (`scoring_version: 1.0.0`).
- **Multi-Format Parsing**:
  - High-fidelity extraction from PDF (PyMuPDF with pdfplumber fallback), DOCX (python-docx), and TXT.
  - Detects and flags multi-column layouts, tables, missing text layers, and unreadable scanned PDFs without silent OCR.
- **Privacy by Design & Compliance**:
  - Automatic PII redaction of SSN, DOB, and passport numbers prior to storage.
  - Unchecked consent checkboxes: consenting leads captured into `ats_leads` & `ats_submissions` with email deduplication; non-consenting uploads stored purely as anonymized analytics metrics (`is_anonymous = 1`).
  - 12-month auto-purge data retention and public "Right to Be Forgotten" deletion endpoint.
- **Auriic Brand Identity**:
  - Official brand colors (Emerald `#027A68`, Gold `#C89C36`, Light `#F0F4F3`).
  - Official Auriic logo in UI and embedded in generated PDF diagnostic reports.
  - Admin portal links and references hidden from public view (staff route accessed securely via `#staff`).

---

## 🛠️ Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Canvas Confetti.
- **Backend**: Python 3.12, FastAPI, PyMuPDF, pdfplumber, python-docx, RapidFuzz, scikit-learn, ReportLab.
- **Database**: SQLite with WAL mode & serverless `/tmp` fallback (PostgreSQL ready).
- **Deployment**: Vercel Serverless / Docker.

---

## 🌐 Deploying to Vercel (Production)

This repository is pre-configured for **Vercel** with `vercel.json` and serverless API handlers in `/api`:

1. **Import Repository in Vercel**:
   - Go to [vercel.com/dashboard](https://vercel.com/dashboard)
   - Click **Add New...** → **Project**
   - Import `auriics/auriic-ats-tool`
2. **Project Settings**:
   - **Framework Preset**: `Vite`
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Output Directory**: `frontend/dist`
3. **Environment Variables**:
   Add the following in Vercel **Settings** → **Environment Variables**:
   - `AURIIC_STORAGE_SECRET`: Secure HMAC secret string (e.g. `auriic_prod_secret_2026_xyz`)
   - `AURIIC_ADMIN_PASSWORD`: Admin portal password (default: `AuriicAdmin2026!`)
   - `AURIIC_ADMIN_TOTP_SECRET`: 32-character base32 secret (e.g. `JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP`)
4. **Custom Domain**:
   - In Vercel Project Settings → **Domains**, add `ats.auriic.co`.

---

## 💻 Local Development

```bash
# Clone the repository
git clone https://github.com/auriics/auriic-ats-tool.git
cd auriic-ats-tool

# 1. Setup Backend
python3.12 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=. uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Setup Frontend
cd frontend
npm install
npm run dev -- --port 5173
```

- Web UI: `http://localhost:5173`
- API Docs: `http://localhost:8000/docs`
- Hidden Staff Portal: `http://localhost:5173/#staff`

---

## 🧪 Testing

```bash
PYTHONPATH=. pytest backend/tests/test_determinism.py
PYTHONPATH=. pytest backend/tests/test_parser.py
PYTHONPATH=. pytest backend/tests/test_leads_and_privacy.py
```
