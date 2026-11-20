# Production Deployment Guide: Vercel (Frontend) + Supabase (Database) + Free Backend

This guide walks you through deploying the **Auriic Free ATS Resume Checker** with a 100% free cloud architecture:
- **Frontend**: [Vercel](https://vercel.com) (hosted on `https://ats.auriic.co`)
- **Database**: [Supabase](https://supabase.com) (PostgreSQL Free Tier — 500MB DB, automatic backups)
- **Backend**: Free Python Web Service on [Render](https://render.com) (or [Koyeb](https://koyeb.com))

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
                        │             VERCEL (Frontend)                │
                        │          React 18 + Vite + Tailwind          │
                        └──────────────────────┬───────────────────────┘
                                               │ API Requests (/api/*)
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │          RENDER / KOYEB (Backend)            │
                        │           FastAPI (Python 3.12)              │
                        │     PyMuPDF + RapidFuzz + Scoring Engine     │
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
   - Go to [supabase.com](https://supabase.com) and click **Sign In** (or Sign Up with GitHub).
   - Click **New Project**.
   - **Name**: `auriic-ats-db`
   - **Database Password**: Set a strong password (save this!).
   - **Region**: Choose **East US (N. Virginia)** or the region closest to your users.
   - Click **Create new project**.

2. **Run the Database Schema**:
   - In your Supabase project dashboard, click **SQL Editor** (left menu icon).
   - Click **+ New query**.
   - Copy the entire SQL script from this file in your repository:
     `backend/database/migrations/001_supabase_schema.sql`
   - Paste it into the SQL Editor and click the green **Run** button (bottom right).
   - You should see `Success. No rows returned`.
   - Click **Table Editor** on the left menu: you will now see `ats_leads`, `ats_submissions`, `ats_audit_logs`, and `ats_deletion_requests`.

3. **Get Your Connection String**:
   - In Supabase, go to **Project Settings** (gear icon) → **Database**.
   - Scroll down to **Connection string**.
   - Select the **URI** tab:
     ```text
     postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
     ```
     *(Or select **Connection Pooling** (Port 6543) if preferred).*
   - Replace `[YOUR-PASSWORD]` with your actual database password.
   - **Copy this URL** — you will use it as `DATABASE_URL`.

---

## STEP 2: Deploy the Backend for FREE on Render — ~3 Minutes

[Render](https://render.com) provides a free Python Web Service that runs FastAPI with full PyMuPDF and ReportLab support without serverless timeout limits.

1. **Sign Up / Log In**:
   - Go to [render.com](https://render.com) and sign in with GitHub.

2. **Create New Web Service**:
   - In Render Dashboard, click **New +** → **Web Service**.
   - Select **Build and deploy from a Git repository**.
   - Connect your repository: `auriics/auriic-ats-tool`.

3. **Configure the Service**:
   - **Name**: `auriic-ats-backend`
   - **Region**: US East (Ohio or Oregon)
   - **Branch**: `main`
   - **Root Directory**: *(leave blank)*
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r backend/requirements.txt
     ```
   - **Start Command**:
     ```bash
     PYTHONPATH=. uvicorn backend.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type**: Select **Free** ($0/month).

4. **Add Environment Variables**:
   Click **Advanced** → **Add Environment Variable** and add:

   | Key | Value |
   | :--- | :--- |
   | `DATABASE_URL` | Your Supabase connection string from Step 1 |
   | `AURIIC_STORAGE_SECRET` | Any random 32-character string (e.g. `auriic_prod_hmac_2026_xyz987654321`) |
   | `AURIIC_ADMIN_PASSWORD` | `AuriicAdmin2026!` (or your chosen staff password) |
   | `AURIIC_ADMIN_TOTP_SECRET` | `JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP` |
   | `PYTHON_VERSION` | `3.12.0` |

5. **Deploy**:
   - Click **Create Web Service**.
   - Render will build dependencies and start FastAPI.
   - Once live, you will get your backend URL, for example:
     `https://auriic-ats-backend.onrender.com`
   - Test it by visiting: `https://auriic-ats-backend.onrender.com/docs` (you will see the interactive Swagger API documentation).

---

## STEP 3: Deploy Frontend on Vercel (`ats.auriic.co`) — ~2 Minutes

1. **Open Vercel**:
   - Go to [vercel.com/dashboard](https://vercel.com/dashboard).
   - Open your project that has `ats.auriic.co` attached.
   - Go to **Settings** → **Git** and ensure `auriics/auriic-ats-tool` is connected.

2. **Build Settings**:
   In Vercel **Settings** → **General**:
   - **Framework Preset**: `Vite`
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Output Directory**: `frontend/dist`

3. **Add Environment Variable for Backend URL**:
   In Vercel **Settings** → **Environment Variables**:
   - **Key**: `VITE_API_BASE`
   - **Value**: `https://auriic-ats-backend.onrender.com` *(your Render backend URL from Step 2)*
   - Click **Save**.

4. **Trigger Deployment**:
   - Go to the **Deployments** tab in Vercel.
   - Click **Redeploy** on the latest commit (or push a commit to `main`).
   - Vercel will build the frontend and deploy to `https://ats.auriic.co`.

---

## STEP 4: Verification & Live Testing

1. **Visit `https://ats.auriic.co`**:
   - Check that the official AURIIC logo displays clearly in the header.
   - Note the Data Storage Consent notice in the clean footer.
   - Verify that NO "Admin" links are visible anywhere on the public page.

2. **Test Mode A (General ATS Health Score)**:
   - Upload any sample resume (PDF, DOCX, or TXT).
   - Check the consent box.
   - Click **Analyze Resume Compatibility**.
   - Confirm score, breakdown, deduction evidence, and prioritized fixes appear.
   - Click **Download PDF Report** to verify the branded ReportLab PDF downloads with the logo.

3. **Verify Data in Supabase**:
   - Open your [Supabase Dashboard](https://supabase.com).
   - Click **Table Editor** → `ats_leads`.
   - You will see the candidate's name, email, phone, detected industry, skills, and lead score category (`HOT`, `WARM`, `COLD`) saved permanently!
   - Click `ats_submissions` to see the full breakdown and score history.

4. **Access the Hidden Staff Portal**:
   - In your browser, navigate to: `https://ats.auriic.co/#staff`
   - Enter your staff password (`AuriicAdmin2026!`) and TOTP 2FA code.
   - View the lead pipeline, filter by industry, download reports, or export to CSV.

---

## 💡 Keeping the Free Backend Awake (Optional Tip)

Render's free tier spins down after 15 minutes of inactivity and takes ~30 seconds to wake up on the first request. To keep it warm 24/7 for free:
- Go to [cron-job.org](https://cron-job.org) or [uptimerobot.com](https://uptimerobot.com) (free).
- Create a ping monitor for `https://auriic-ats-backend.onrender.com/docs` every 10 minutes.
- This ensures your ATS checker backend responds instantly with zero cold-start delay!
