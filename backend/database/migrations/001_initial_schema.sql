-- 001_initial_schema.sql
-- Auriic ATS Checker Schema (SQLite & PostgreSQL Compatible)

CREATE TABLE IF NOT EXISTS ats_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    consent_given BOOLEAN NOT NULL DEFAULT 0,
    consent_marketing BOOLEAN NOT NULL DEFAULT 0,
    consent_text_version TEXT NOT NULL DEFAULT '1.0',
    consent_timestamp TIMESTAMP,
    ip_hash TEXT,
    lead_status TEXT NOT NULL DEFAULT 'new',
    lead_score_category TEXT DEFAULT 'cold',
    lead_score_reason TEXT,
    assigned_to TEXT,
    notes TEXT,
    deleted_at TIMESTAMP,
    purge_after TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ats_leads_email ON ats_leads(email);
CREATE INDEX IF NOT EXISTS idx_ats_leads_created_at ON ats_leads(created_at);
CREATE INDEX IF NOT EXISTS idx_ats_leads_industry ON ats_leads(detected_industry);
CREATE INDEX IF NOT EXISTS idx_ats_leads_status ON ats_leads(lead_status);
CREATE INDEX IF NOT EXISTS idx_ats_leads_score_cat ON ats_leads(lead_score_category);

CREATE TABLE IF NOT EXISTS ats_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mode TEXT NOT NULL, -- 'A' or 'B'
    scoring_version TEXT NOT NULL,
    ats_score REAL NOT NULL,
    score_label TEXT NOT NULL,
    category_scores TEXT, -- JSON
    top_missing_keywords TEXT, -- JSON
    job_description_text TEXT,
    jd_title TEXT,
    resume_file_path TEXT,
    extracted_text TEXT,
    resume_hash TEXT NOT NULL,
    deductions_json TEXT, -- JSON
    is_anonymous BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY(lead_id) REFERENCES ats_leads(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ats_sub_lead_id ON ats_submissions(lead_id);
CREATE INDEX IF NOT EXISTS idx_ats_sub_created_at ON ats_submissions(created_at);
CREATE INDEX IF NOT EXISTS idx_ats_sub_score ON ats_submissions(ats_score);
CREATE INDEX IF NOT EXISTS idx_ats_sub_hash ON ats_submissions(resume_hash);

CREATE TABLE IF NOT EXISTS ats_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target_lead_id INTEGER,
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_ats_audit_actor ON ats_audit_logs(actor);
CREATE INDEX IF NOT EXISTS idx_ats_audit_action ON ats_audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_ats_audit_timestamp ON ats_audit_logs(timestamp);

CREATE TABLE IF NOT EXISTS ats_deletion_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    verification_token TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, verified, completed
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ats_del_token ON ats_deletion_requests(verification_token);
CREATE INDEX IF NOT EXISTS idx_ats_del_email ON ats_deletion_requests(email);
