# Production Deployment Guide: All-in-One on Vercel + Supabase Database

This guide explains how to deploy the **Auriic Free ATS Resume Checker** with **Frontend AND Backend running together on Vercel ONLY**, connected to a persistent **Supabase PostgreSQL** database.

- **Frontend**: [Vercel](https://vercel.com) (React 18 + Vite static build)
- **Backend**: [Vercel](https://vercel.com) (Python 3.12 FastAPI Serverless Function at `/api/*`)
- **Database**: [Supabase](https://supabase.com) (Free PostgreSQL database — 500MB, automatic backups, persistent)
- **Domain**: `https://ats.auriic.co` (All on one single domain, NO CORS errors, NO second host)

---

## 🏛️ Architecture Overview

```
                        ┌──────────────────────────────────────────────┐
                        │              Custom Domain                   │
                        │           https://ats.auriic.co              │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │               VERCEL (All-in-One)            │
                        │                                              │
                        │  1. Frontend: React 18 + Vite (dist/)        │
                        │  2. Backend:  FastAPI in /api/index.py       │
                        │     (PyMuPDF + RapidFuzz + ReportLab)        │
                        └──────────────────────┬───────────────────────┘
                                               │ DATABASE_URL (SSL)
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │            SUPABASE (Database)               │
                        │       PostgreSQL 15+ (Persistent)            │
                        │   Tables: ats_leads, ats_submissions, etc.   │
                        └──────────────────────────────────────────────┘
```

---

## STEP 1: Set Up Supabase (Database) — ~2 Minutes

1. **Create Free Project**:
   - Go to [supabase.com](https://supabase.com) and sign in.
   - Click **New Project**:
     - **Name**: `auriic-ats-db`
     - **Database Password**: Choose a strong password and save it!
     - **Region**: Select **East US** (or closest to your users).
     - Click **Create new project**.

2. **Run the Database Schema**:
   - Click **SQL Editor** on the left menu (terminal icon `>_`).
   - Click **+ New query**.
   - Copy and paste the entire script from `backend/database/migrations/001_supabase_schema.sql` into the SQL Editor:
     ```sql
     -- 1. Table: ats_leads (One row per person, keyed by email)
     CREATE TABLE IF NOT EXISTS ats_leads (
         id BIGSERIAL PRIMARY KEY,
         created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
         full_name TEXT NOT NULL,
         email TEXT NOT NULL UNIQUE,
         phone TEXT,
         location TEXT,
         linkedin_url TEXT,
         detected_industry TEXT,
         user_selected_industry TEXT,
         detected_job_titles TEXT,
         top_skills TEXT,
         years_of_experience INTEGER DEFAULT 0,
         education_level TEXT,
         certifications TEXT,
         utm_source TEXT,
         utm_medium TEXT,
         utm_campaign TEXT,
         referrer TEXT,
         device_type TEXT,
         consent_given BOOLEAN NOT NULL DEFAULT FALSE,
         consent_marketing BOOLEAN NOT NULL DEFAULT FALSE,
         consent_text_version TEXT NOT NULL DEFAULT '1.0',
         consent_timestamp TIMESTAMPTZ,
         ip_hash TEXT,
         lead_status TEXT NOT NULL DEFAULT 'new',
         lead_score_category TEXT DEFAULT 'cold',
         lead_score_reason TEXT,
         assigned_to TEXT,
         notes TEXT,
         deleted_at TIMESTAMPTZ,
         purge_after TIMESTAMPTZ
     );

     CREATE INDEX IF NOT EXISTS idx_ats_leads_email ON ats_leads(email);
     CREATE INDEX IF NOT EXISTS idx_ats_leads_created_at ON ats_leads(created_at);
     CREATE INDEX IF NOT EXISTS idx_ats_leads_industry ON ats_leads(detected_industry);
     CREATE INDEX IF NOT EXISTS idx_ats_leads_status ON ats_leads(lead_status);
     CREATE INDEX IF NOT EXISTS idx_ats_leads_score_cat ON ats_leads(lead_score_category);

     -- 2. Table: ats_submissions (Multiple scans per lead)
     CREATE TABLE IF NOT EXISTS ats_submissions (
         id BIGSERIAL PRIMARY KEY,
         lead_id BIGINT REFERENCES ats_leads(id) ON DELETE CASCADE,
         created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
         mode TEXT NOT NULL,
         scoring_version TEXT NOT NULL,
         ats_score DOUBLE PRECISION NOT NULL,
         score_label TEXT NOT NULL,
         category_scores TEXT,
         top_missing_keywords TEXT,
         job_description_text TEXT,
         jd_title TEXT,
         resume_file_path TEXT,
         extracted_text TEXT,
         resume_hash TEXT NOT NULL,
         deductions_json TEXT,
         is_anonymous BOOLEAN NOT NULL DEFAULT FALSE
     );

     CREATE INDEX IF NOT EXISTS idx_ats_sub_lead_id ON ats_submissions(lead_id);
     CREATE INDEX IF NOT EXISTS idx_ats_sub_created_at ON ats_submissions(created_at);
     CREATE INDEX IF NOT EXISTS idx_ats_sub_score ON ats_submissions(ats_score);
     CREATE INDEX IF NOT EXISTS idx_ats_sub_hash ON ats_submissions(resume_hash);

     -- 3. Table: ats_audit_logs (Staff activity logging)
     CREATE TABLE IF NOT EXISTS ats_audit_logs (
         id BIGSERIAL PRIMARY KEY,
         timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
         actor TEXT NOT NULL,
         action TEXT NOT NULL,
         target_lead_id BIGINT,
         details TEXT
     );

     -- 4. Table: ats_deletion_requests (Right to be Forgotten)
     CREATE TABLE IF NOT EXISTS ats_deletion_requests (
         id BIGSERIAL PRIMARY KEY,
         email TEXT NOT NULL,
         verification_token TEXT NOT NULL UNIQUE,
         status TEXT NOT NULL DEFAULT 'pending',
         requested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
         completed_at TIMESTAMPTZ
     );
     ```
   - Click the green **Run** button (bottom right).
   - In the left menu, click **Table Editor**: you will see `ats_leads`, `ats_submissions`, `ats_audit_logs`, and `ats_deletion_requests`.

3. **Copy your Database Connection String**:
   - Go to **Project Settings** (gear icon) → **Database**.
   - Under **Connection string**, select the **URI** tab:
     ```text
     postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
     ```
     *(Or choose **Connection Pooling** port 6543 if preferred).*
   - Replace `[YOUR-PASSWORD]` with the password you set in step 1.
   - **Copy this URL** — this is your `DATABASE_URL`.

---

## STEP 2: Deploy Frontend + Backend on Vercel Only — ~2 Minutes

Because the repository includes `vercel.json` and `api/index.py`, Vercel builds BOTH the React frontend and the Python serverless API inside the exact same project!

1. **Open Vercel Dashboard**:
   - Go to [vercel.com/dashboard](https://vercel.com/dashboard).
   - Open your project where domain `ats.auriic.co` is attached.
   - (Or click **Add New...** → **Project** → select `auriics/auriic-ats-tool`).

2. **Verify Project Settings**:
   In Vercel **Settings** → **General**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `./` (leave default)
   - **Build Command**: `cd frontend && npm install && npm run build` *(pre-configured in `vercel.json`)*
   - **Output Directory**: `frontend/dist` *(pre-configured in `vercel.json`)*

3. **Add Environment Variables**:
   In Vercel **Settings** → **Environment Variables**, add the following 4 variables:

   | Key | Value | Purpose |
   | :--- | :--- | :--- |
   | `DATABASE_URL` | Your Supabase connection string from Step 1 | Connects backend to Supabase PostgreSQL |
   | `AURIIC_STORAGE_SECRET` | `auriic_prod_hmac_2026_xyz987654321` | Signs HMAC download URLs |
   | `AURIIC_ADMIN_PASSWORD` | `AuriicAdmin2026!` | Password for staff access |
   | `AURIIC_ADMIN_TOTP_SECRET` | `JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP` | 2FA Authenticator secret |

4. **Deploy**:
   - Go to the **Deployments** tab in Vercel.
   - Click **Redeploy** on the latest commit (or push a commit to `main`).
   - Vercel will:
     1. Build the React frontend into `frontend/dist`.
     2. Install Python packages from `requirements.txt`.
     3. Package `api/index.py` as a serverless function with `backend/**` assets.
     4. Point `https://ats.auriic.co` to the build.

---

## STEP 3: Verify the Live System

1. **Visit `https://ats.auriic.co`**:
   - The UI loads directly with the official AURIIC logo.
   - Test **Mode A** (upload a resume, check consent, click Analyze).
   - Test **Mode B** (upload a resume + paste a job description).
   - Click **Download PDF Report** to verify the branded PDF report downloads.
2. **Verify Permanent Data in Supabase**:
   - Open your [Supabase Dashboard](https://supabase.com).
   - Click **Table Editor** → `ats_leads`: You will see the applicant's name, email, phone, detected industry, skills, and lead score (`HOT`/`WARM`/`COLD`) stored permanently!
   - Click `ats_submissions`: You will see the score history, category breakdown, and full extracted text.
3. **Access Staff Portal**:
   - Go to `https://ats.auriic.co/#staff`.
   - Log in with `AuriicAdmin2026!` and 2FA code to view leads, filter candidates, and export CSVs.
