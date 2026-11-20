-- 001_rollback_schema.sql
-- Rollback for Auriic ATS Checker Schema

DROP INDEX IF EXISTS idx_ats_del_email;
DROP INDEX IF EXISTS idx_ats_del_token;
DROP TABLE IF EXISTS ats_deletion_requests;

DROP INDEX IF EXISTS idx_ats_audit_timestamp;
DROP INDEX IF EXISTS idx_ats_audit_action;
DROP INDEX IF EXISTS idx_ats_audit_actor;
DROP TABLE IF EXISTS ats_audit_logs;

DROP INDEX IF EXISTS idx_ats_sub_hash;
DROP INDEX IF EXISTS idx_ats_sub_score;
DROP INDEX IF EXISTS idx_ats_sub_created_at;
DROP INDEX IF EXISTS idx_ats_sub_lead_id;
DROP TABLE IF EXISTS ats_submissions;

DROP INDEX IF EXISTS idx_ats_leads_score_cat;
DROP INDEX IF EXISTS idx_ats_leads_status;
DROP INDEX IF EXISTS idx_ats_leads_industry;
DROP INDEX IF EXISTS idx_ats_leads_created_at;
DROP INDEX IF EXISTS idx_ats_leads_email;
DROP TABLE IF EXISTS ats_leads;
