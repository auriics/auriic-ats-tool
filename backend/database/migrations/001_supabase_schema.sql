-- ====================================================================
-- AURIIC FREE ATS RESUME CHECKER - SUPABASE POSTGRESQL SCHEMA
-- Run this in the Supabase Dashboard -> SQL Editor -> Click 'Run'
-- ====================================================================

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
    mode TEXT NOT NULL, -- 'A' (Health) or 'B' (JD Match)
    scoring_version TEXT NOT NULL,
    ats_score DOUBLE PRECISION NOT NULL,
    score_label TEXT NOT NULL,
    category_scores TEXT, -- JSON breakdown
    top_missing_keywords TEXT, -- JSON array
    job_description_text TEXT,
    jd_title TEXT,
    resume_file_path TEXT,
    extracted_text TEXT,
    resume_hash TEXT NOT NULL,
    deductions_json TEXT, -- JSON array
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

CREATE INDEX IF NOT EXISTS idx_ats_audit_actor ON ats_audit_logs(actor);
CREATE INDEX IF NOT EXISTS idx_ats_audit_action ON ats_audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_ats_audit_timestamp ON ats_audit_logs(timestamp);

-- 4. Table: ats_deletion_requests (Right to be Forgotten)
CREATE TABLE IF NOT EXISTS ats_deletion_requests (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    verification_token TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, verified, completed
    requested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ats_del_token ON ats_deletion_requests(verification_token);
CREATE INDEX IF NOT EXISTS idx_ats_del_email ON ats_deletion_requests(email);
