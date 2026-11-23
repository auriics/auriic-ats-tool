import React, { useState, useRef } from 'react';
import {
  Upload,
  CheckCircle,
  AlertTriangle,
  ShieldCheck,
  ArrowRight,
  Download,
  Eye,
  RefreshCw,
  ExternalLink,
  Lock,
  Search,
  Trash2,
  Filter,
} from 'lucide-react';

interface ScoreBreakdown {
  earned: number;
  possible: number;
}

interface Deduction {
  category: string;
  points_lost: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  reason: string;
  evidence: string;
  recommendation: string;
}

interface KeywordItem {
  keyword: string;
  type: string;
  status: 'Found' | 'Partial' | 'Missing';
  location_found: string;
}

interface ATSReport {
  mode: 'A' | 'B';
  scoring_version: string;
  overall_score: number;
  label: 'Excellent' | 'Good' | 'Fair' | 'Needs Work';
  detected_industry: string;
  detected_industry_name: string;
  is_industry_override: boolean;
  category_breakdown: Record<string, ScoreBreakdown>;
  deductions: Deduction[];
  top_fixes: Deduction[];
  keyword_table?: KeywordItem[];
  top_missing_keywords?: string[];
  pii_alerts?: Array<{ type: string; severity: string; line_number: number; evidence: string; message: string }>;
  candidate_info?: { name?: string; email?: string; phone?: string; location?: string; linkedin?: string };
  parsed_data_preview?: {
    extracted_text: string;
    detected_sections: string[];
    page_count: number;
    layout_flags: {
      is_scanned: boolean;
      has_multi_column: boolean;
      has_tables: boolean;
      header_footer_contact: boolean;
    };
  };
  resume_hash: string;
  disclaimer: string;
}

const API_BASE = ((import.meta as any).env?.VITE_API_BASE as string) || '';

export default function App() {
  // Navigation & View states
  const [activeTab, setActiveTab] = useState<'checker' | 'privacy' | 'delete' | 'admin'>('checker');
  
  // Form input states
  const [mode, setMode] = useState<'A' | 'B'>('A');

  // Listen for hash changes for staff access (e.g. #staff)
  React.useEffect(() => {
    const handleHash = () => {
      if (window.location.hash === '#staff' || window.location.hash === '#portal') {
        setActiveTab('admin');
      }
    };
    handleHash();
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, []);
  const [industryOverride, setIndustryOverride] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState<string>('');
  const [consentGiven, setConsentGiven] = useState<boolean>(false);
  const [consentMarketing, setConsentMarketing] = useState<boolean>(false);

  // Execution states
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisStep, setAnalysisStep] = useState<string>('');
  const [report, setReport] = useState<ATSReport | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showRawText, setShowRawText] = useState<boolean>(false);

  // Admin states
  const [adminUsername, setAdminUsername] = useState<string>('');
  const [adminPassword, setAdminPassword] = useState<string>('');
  const [adminToken, setAdminToken] = useState<string | null>(null);
  const [adminLeads, setAdminLeads] = useState<any[]>([]);
  const [adminSearch, setAdminSearch] = useState<string>('');
  const [adminIndustryFilter, setAdminIndustryFilter] = useState<string>('all');
  const [adminStatusFilter, setAdminStatusFilter] = useState<string>('all');
  const [adminSelectedLead, setAdminSelectedLead] = useState<any | null>(null);
  const [adminNotes, setAdminNotes] = useState<string>('');
  const [adminNewStatus, setAdminNewStatus] = useState<string>('new');

  // Deletion form states
  const [deleteEmail, setDeleteEmail] = useState<string>('');
  const [deleteToken, setDeleteToken] = useState<string>('');
  const [deleteMessage, setDeleteMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // File drop & select handlers
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setErrorMessage(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setErrorMessage(null);
    }
  };

  // Submit Analysis
  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setErrorMessage('Please select or upload a resume file (PDF, DOCX, or TXT).');
      return;
    }
    if (mode === 'B' && (!jobDescription || jobDescription.trim().length < 30)) {
      setErrorMessage('Mode B requires pasting a target Job Description (minimum 30 characters).');
      return;
    }

    setIsAnalyzing(true);
    setErrorMessage(null);
    setReport(null);

    // Multi-stage analysis animation
    setAnalysisStep('1. Inspecting document layout, fonts, and text layers...');
    setTimeout(() => setAnalysisStep('2. Extracting contact info, work history, and skills...'), 500);
    setTimeout(() => setAnalysisStep('3. Applying deterministic 8-industry scoring rules...'), 1100);

    try {
      const formData = new FormData();
      formData.append('resume', file);
      if (mode === 'B' && jobDescription.trim()) {
        formData.append('job_description', jobDescription.trim());
      }
      if (industryOverride) {
        formData.append('industry_override', industryOverride);
      }
      formData.append('consent_given', consentGiven ? 'true' : 'false');
      formData.append('consent_marketing', consentMarketing ? 'true' : 'false');

      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned error (${response.status})`);
      }

      const data: ATSReport = await response.json();
      setReport(data);
      // Smooth scroll to report
      setTimeout(() => {
        document.getElementById('report-section')?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } catch (err: any) {
      setErrorMessage(err.message || 'An error occurred during analysis.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Download Branded PDF
  const handleDownloadPDF = async () => {
    if (!report) return;
    try {
      const response = await fetch(`${API_BASE}/api/download-report-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          score_report: report,
          candidate_name: report.candidate_info?.name || 'Candidate',
        }),
      });
      if (!response.ok) throw new Error('Failed to generate PDF.');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Auriic_ATS_Report_${report.mode}_${report.scoring_version}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      alert(`Error downloading PDF: ${err.message}`);
    }
  };

  // Admin login handler
  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE}/api/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: adminUsername, password: adminPassword }),
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Login failed');
      }
      const data = await response.json();
      setAdminToken(data.token);
      loadAdminLeads(data.token);
    } catch (err: any) {
      alert(`Admin Login Error: ${err.message}`);
    }
  };

  const loadAdminLeads = async (token: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/leads`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setAdminLeads(data.leads || []);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const viewLeadDetail = async (leadId: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/leads/${leadId}`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      if (response.ok) {
        const data = await response.json();
        setAdminSelectedLead(data);
        setAdminNotes(data.lead.notes || '');
        setAdminNewStatus(data.lead.lead_status || 'new');
      }
    } catch (err) {
      console.error(err);
    }
  };

  const updateLeadStatus = async (leadId: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/leads/${leadId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${adminToken}`,
        },
        body: JSON.stringify({ lead_status: adminNewStatus, notes: adminNotes }),
      });
      if (response.ok) {
        alert('Lead updated successfully.');
        loadAdminLeads(adminToken!);
        setAdminSelectedLead(null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const deleteLeadAdmin = async (leadId: number) => {
    if (!confirm('Are you sure you want to permanently delete this lead and scrub all files?')) return;
    try {
      const response = await fetch(`${API_BASE}/api/admin/leads/${leadId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      if (response.ok) {
        alert('Lead permanently scrubbed.');
        loadAdminLeads(adminToken!);
        setAdminSelectedLead(null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Data deletion public handlers
  const handleRequestDeletion = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE}/api/privacy/request-deletion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: deleteEmail }),
      });
      const data = await response.json();
      setDeleteToken(data.verification_token || '');
      setDeleteMessage(data.message);
    } catch (err: any) {
      setDeleteMessage(`Error: ${err.message}`);
    }
  };

  const handleConfirmDeletion = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE}/api/privacy/confirm-deletion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: deleteToken }),
      });
      const data = await response.json();
      setDeleteMessage(data.message);
    } catch (err: any) {
      setDeleteMessage(`Error: ${err.message}`);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#F0F4F3] text-[#1A1A1A]">
      {/* Top Navigation */}
      <header className="bg-white border-b border-[#027A68]/15 sticky top-0 z-40 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => setActiveTab('checker')}>
            <img
              src="/auriic-logo.png"
              alt="AURIIC - Connecting Ambitions with Opportunities"
              className="h-10 sm:h-12 w-auto object-contain"
            />
            <span className="hidden sm:inline-block h-6 w-px bg-gray-200 mx-1" />
            <span className="hidden sm:inline-block px-2.5 py-1 rounded-full bg-[#E6F3F1] text-[#027A68] text-xs font-black tracking-wide uppercase">
              Free ATS Checker
            </span>
          </div>

          <a
            href="https://auriic.co"
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-[#027A68] hover:bg-[#01584B] text-white text-xs font-bold rounded-xl transition-all shadow-xs flex items-center gap-1.5"
          >
            <span>Book Consultation</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* CHECKER VIEW */}
        {activeTab === 'checker' && (
          <div className="space-y-8">
            {/* Hero Banner */}
            <div className="text-center max-w-3xl mx-auto space-y-3">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#FEF9EB] border border-[#C89C36]/30 text-[#9E7A26] text-xs font-bold uppercase tracking-wider">
                <ShieldCheck className="w-4 h-4 text-[#C89C36]" />
                100% Deterministic • Zero Randomness • US Standard ATS
              </div>
              <h1 className="text-3xl sm:text-5xl font-black text-[#1A1A1A] tracking-tight">
                Optimize Your Resume for <span className="text-gradient-brand">Real US Recruiters</span>
              </h1>
              <p className="text-base sm:text-lg text-gray-600">
                Built for OPT/STEM OPT candidates, H-1B professionals, and job seekers across <strong>IT and non-IT</strong> industries (Healthcare, Finance, Manufacturing, Supply Chain, Construction, Energy, Retail).
              </p>
            </div>

            {/* Checker Card */}
            <div className="card-surface p-6 sm:p-8 bg-white max-w-4xl mx-auto shadow-sm">
              <form onSubmit={handleAnalyze} className="space-y-6">
                {/* 1. Mode Selector */}
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-2">
                    Select Evaluation Mode
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setMode('A')}
                      className={`p-4 rounded-xl border-2 text-left transition-all ${
                        mode === 'A'
                          ? 'border-[#027A68] bg-[#E6F3F1] ring-1 ring-[#027A68]'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-[#027A68]">Mode A: General ATS Health</span>
                        {mode === 'A' && <CheckCircle className="w-5 h-5 text-[#027A68]" />}
                      </div>
                      <p className="text-xs text-gray-600">
                        Evaluates resume structure, action verbs, quantified metrics, section formatting, and industry density (No JD required).
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setMode('B')}
                      className={`p-4 rounded-xl border-2 text-left transition-all ${
                        mode === 'B'
                          ? 'border-[#027A68] bg-[#E6F3F1] ring-1 ring-[#027A68]'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-[#027A68]">Mode B: Target JD Match</span>
                        {mode === 'B' && <CheckCircle className="w-5 h-5 text-[#027A68]" />}
                      </div>
                      <p className="text-xs text-gray-600">
                        Evaluates hard & soft skills match, required vs preferred keywords, years of experience, and title seniority against a job post.
                      </p>
                    </button>
                  </div>
                </div>

                {/* 2. Industry Override Dropdown */}
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-1">
                    Industry Group
                  </label>
                  <select
                    value={industryOverride}
                    onChange={(e) => setIndustryOverride(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border border-gray-300 bg-white text-sm focus:border-[#027A68] focus:ring-1 focus:ring-[#027A68] transition-colors"
                  >
                    <option value="">Auto-Detect Industry from Resume (Recommended)</option>
                    <option value="it">Information Technology & Software Engineering</option>
                    <option value="healthcare">Healthcare, Clinical & Nursing</option>
                    <option value="finance">Banking, Corporate Finance, Accounting & Insurance</option>
                    <option value="manufacturing">Manufacturing, Industrial & Quality Engineering</option>
                    <option value="logistics">Supply Chain, Logistics & Warehousing</option>
                    <option value="construction">Construction & Civil Engineering</option>
                    <option value="energy">Energy, Power Systems, Oil, Gas & Utilities</option>
                    <option value="retail">Retail, Merchandising & Consumer Goods</option>
                  </select>
                </div>

                {/* 3. File Upload Area */}
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-1">
                    Upload Resume (PDF, DOCX, or TXT • Max 5 MB)
                  </label>
                  <div
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-gray-300 hover:border-[#027A68] bg-[#F9FBFA] rounded-2xl p-6 text-center cursor-pointer transition-colors"
                  >
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileChange}
                      accept=".pdf,.docx,.doc,.txt"
                      className="hidden"
                    />
                    <Upload className="w-10 h-10 text-[#027A68] mx-auto mb-2 opacity-80" />
                    {file ? (
                      <div className="space-y-1">
                        <p className="text-sm font-bold text-[#027A68]">{file.name}</p>
                        <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB • Click to choose a different file</p>
                      </div>
                    ) : (
                      <div className="space-y-1">
                        <p className="text-sm font-semibold text-gray-700">Drag & drop your resume here, or click to browse</p>
                        <p className="text-xs text-gray-500">Supports PDF, Word (.docx), and plain text (.txt)</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* 4. Mode B Job Description Input */}
                {mode === 'B' && (
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">
                      Paste Target Job Description
                    </label>
                    <textarea
                      rows={5}
                      value={jobDescription}
                      onChange={(e) => setJobDescription(e.target.value)}
                      placeholder="Paste the complete job post, responsibilities, and required qualifications here..."
                      className="w-full p-4 rounded-xl border border-gray-300 text-sm focus:border-[#027A68] focus:ring-1 focus:ring-[#027A68]"
                    />
                  </div>
                )}

                {/* 5. Privacy & Consent Gate */}
                <div className="bg-[#FEF9EB] border border-[#C89C36]/30 rounded-2xl p-4 sm:p-5 space-y-3">
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      id="consent-main"
                      checked={consentGiven}
                      onChange={(e) => setConsentGiven(e.target.checked)}
                      className="mt-1 rounded text-[#027A68] focus:ring-[#027A68]"
                    />
                    <label htmlFor="consent-main" className="text-xs sm:text-sm text-gray-800 font-medium">
                      <span className="font-bold text-[#027A68]">I agree to all terms:</span> Data Storage Consent: I agree that Auriic Services may store my resume and contact details and contact me about career services and staffing placements.{' '}
                      <button
                        type="button"
                        onClick={() => setActiveTab('privacy')}
                        className="text-[#027A68] underline font-bold hover:text-[#01584B]"
                      >
                        See Privacy Policy
                      </button>.
                    </label>
                  </div>

                  <div className="flex items-start gap-3 pl-0 sm:pl-0">
                    <input
                      type="checkbox"
                      id="consent-marketing"
                      checked={consentMarketing}
                      onChange={(e) => setConsentMarketing(e.target.checked)}
                      className="mt-1 rounded text-[#027A68] focus:ring-[#027A68]"
                    />
                    <label htmlFor="consent-marketing" className="text-xs sm:text-sm text-gray-700">
                      (Optional) I would like to receive career tips, US market salary reports, and newsletter updates.
                    </label>
                  </div>

                  <p className="text-[11px] text-gray-500 italic pt-1 border-t border-[#C89C36]/20">
                    * If you leave consent unchecked, your resume is analyzed anonymously in temporary memory. Zero files, contact info, or raw resume text will be stored on our servers.
                  </p>
                </div>

                {errorMessage && (
                  <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                    <span>{errorMessage}</span>
                  </div>
                )}

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={isAnalyzing}
                  className="w-full py-4 px-6 rounded-xl bg-[#027A68] hover:bg-[#01584B] text-white font-bold text-base transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      <span>{analysisStep || 'Analyzing Resume...'}</span>
                    </>
                  ) : (
                    <>
                      <span>Run Free ATS Diagnostic</span>
                      <ArrowRight className="w-5 h-5" />
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* DIAGNOSTIC REPORT SECTION */}
            {report && (
              <div id="report-section" className="space-y-8 max-w-4xl mx-auto">
                {/* PII Alert Banner if present */}
                {report.pii_alerts && report.pii_alerts.length > 0 && (
                  <div className="p-4 rounded-2xl bg-amber-50 border-2 border-amber-300 text-amber-900 space-y-2">
                    <div className="flex items-center gap-2 font-bold text-sm">
                      <AlertTriangle className="w-5 h-5 text-amber-600" />
                      <span>Sensitive Personal Data Detected (Auto-Redacted):</span>
                    </div>
                    <ul className="text-xs space-y-1 list-disc pl-5">
                      {report.pii_alerts.map((alert, idx) => (
                        <li key={idx}>
                          <strong>{alert.type}:</strong> {alert.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Score Card Header */}
                <div className="card-surface p-6 sm:p-8 bg-white border border-[#027A68]/20 rounded-3xl shadow-sm">
                  <div className="flex flex-col sm:flex-row items-center justify-between gap-6 border-b border-gray-100 pb-6">
                    <div className="text-center sm:text-left space-y-1">
                      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#E6F3F1] text-[#027A68] text-xs font-bold uppercase">
                        Mode {report.mode}: {report.mode === 'A' ? 'General ATS Health' : 'Target JD Match'}
                      </div>
                      <h2 className="text-2xl sm:text-3xl font-black text-gray-900">
                        ATS Compatibility Score
                      </h2>
                      <p className="text-xs text-gray-500">
                        Industry: <strong>{report.detected_industry_name}</strong> • Engine Version: <strong>v{report.scoring_version}</strong>
                      </p>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-center">
                        <div className="text-5xl sm:text-6xl font-black text-[#027A68]">
                          {Math.round(report.overall_score)}
                          <span className="text-xl text-gray-400 font-normal">/100</span>
                        </div>
                        <span
                          className={`inline-block px-3 py-1 mt-1 text-xs font-extrabold uppercase rounded-full ${
                            report.overall_score >= 85
                              ? 'bg-emerald-100 text-emerald-800'
                              : report.overall_score >= 70
                              ? 'bg-blue-100 text-blue-800'
                              : report.overall_score >= 50
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-rose-100 text-rose-800'
                          }`}
                        >
                          {report.label}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Category Breakdown Bars */}
                  <div className="pt-6 space-y-4">
                    <h3 className="text-sm font-bold uppercase tracking-wider text-gray-500">
                      Category Breakdown
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {Object.entries(report.category_breakdown).map(([catKey, scores]) => {
                        const pct = Math.round((scores.earned / scores.possible) * 100);
                        return (
                          <div key={catKey} className="p-4 rounded-2xl bg-[#F9FBFA] border border-gray-200/80 space-y-2">
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-bold text-gray-700 capitalize">
                                {catKey.replace(/_/g, ' ')}
                              </span>
                              <span className="font-mono font-semibold text-gray-900">
                                {scores.earned.toFixed(1)} / {scores.possible} pts
                              </span>
                            </div>
                            <div className="w-full h-2.5 bg-gray-200 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all duration-500 ${
                                  pct >= 80 ? 'bg-[#027A68]' : pct >= 60 ? 'bg-[#C89C36]' : 'bg-rose-500'
                                }`}
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Top 5 Prioritized Fixes */}
                <div className="card-surface p-6 sm:p-8 bg-white rounded-3xl space-y-4">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-[#C89C36]" />
                    <h3 className="text-lg font-bold text-gray-900">
                      Top Prioritized Action Items ('Fix This First')
                    </h3>
                  </div>
                  {report.top_fixes && report.top_fixes.length > 0 ? (
                    <div className="space-y-3">
                      {report.top_fixes.map((fix, idx) => (
                        <div
                          key={idx}
                          className="p-4 rounded-xl border border-gray-200 bg-[#F9FBFA] space-y-2"
                        >
                          <div className="flex items-center justify-between">
                            <span
                              className={`px-2 py-0.5 text-[11px] font-black uppercase rounded ${
                                fix.severity === 'CRITICAL'
                                  ? 'bg-rose-100 text-rose-800'
                                  : fix.severity === 'HIGH'
                                  ? 'bg-amber-100 text-amber-800'
                                  : 'bg-blue-100 text-blue-800'
                              }`}
                            >
                              {fix.severity} • -{fix.points_lost} pts
                            </span>
                            <span className="text-xs text-gray-500 font-medium">{fix.category}</span>
                          </div>
                          <p className="text-sm font-bold text-gray-900">{fix.reason}</p>
                          <p className="text-xs text-gray-600">
                            <strong>Fix:</strong> {fix.recommendation}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-emerald-700 bg-emerald-50 p-4 rounded-xl">
                      No critical deductions found! Your resume format is clean and optimized.
                    </p>
                  )}
                </div>

                {/* Mode B Keyword Match Matrix (If Mode B) */}
                {report.mode === 'B' && report.keyword_table && (
                  <div className="card-surface p-6 sm:p-8 bg-white rounded-3xl space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-bold text-gray-900">
                        Target Job Description Keyword Alignment
                      </h3>
                      <span className="text-xs text-gray-500">
                        {report.keyword_table.length} extracted requirements
                      </span>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b border-gray-200 bg-gray-50 text-gray-600 font-bold">
                            <th className="py-2.5 px-3">Keyword / Skill</th>
                            <th className="py-2.5 px-3">Requirement Type</th>
                            <th className="py-2.5 px-3">Status</th>
                            <th className="py-2.5 px-3">Resume Location Found</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {report.keyword_table.map((row, idx) => (
                            <tr key={idx} className="hover:bg-gray-50/50">
                              <td className="py-2.5 px-3 font-semibold text-gray-900">{row.keyword}</td>
                              <td className="py-2.5 px-3">
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                    row.type === 'Required'
                                      ? 'bg-purple-100 text-purple-800'
                                      : 'bg-gray-100 text-gray-700'
                                  }`}
                                >
                                  {row.type}
                                </span>
                              </td>
                              <td className="py-2.5 px-3">
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                    row.status === 'Found'
                                      ? 'bg-emerald-100 text-emerald-800'
                                      : row.status === 'Partial'
                                      ? 'bg-blue-100 text-blue-800'
                                      : 'bg-rose-100 text-rose-800'
                                  }`}
                                >
                                  {row.status}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 text-gray-600">{row.location_found}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Evidence-Backed Deductions List */}
                <div className="card-surface p-6 sm:p-8 bg-white rounded-3xl space-y-4">
                  <h3 className="text-lg font-bold text-gray-900">
                    Comprehensive Deduction Evidence ({report.deductions.length} items)
                  </h3>
                  <div className="space-y-3">
                    {report.deductions.map((d, idx) => (
                      <div key={idx} className="p-4 rounded-xl border border-gray-100 bg-[#F9FBFA] space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-[#027A68]">{d.category}</span>
                          <span className="font-bold text-rose-600">-{d.points_lost} pts</span>
                        </div>
                        <p className="text-sm font-semibold text-gray-900">{d.reason}</p>
                        <p className="text-xs text-gray-500 italic bg-white p-2 rounded border border-gray-200/50">
                          <strong>Evidence:</strong> {d.evidence}
                        </p>
                        <p className="text-xs text-gray-700">
                          <strong>Recommendation:</strong> {d.recommendation}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* What ATS Sees Inspector */}
                <div className="card-surface p-6 sm:p-8 bg-white rounded-3xl space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-bold text-gray-900">
                        "This Is What an ATS Sees"
                      </h3>
                      <p className="text-xs text-gray-500">
                        Inspect the exact plain-text extraction layer and layout flags seen by recruiter parsers.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowRawText(!showRawText)}
                      className="px-3 py-1.5 text-xs font-bold rounded-lg border border-gray-300 hover:bg-gray-50 flex items-center gap-1"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>{showRawText ? 'Hide Text' : 'View Text'}</span>
                    </button>
                  </div>

                  {report.parsed_data_preview && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                      <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                        <span className="text-gray-500 block">Scanned Image:</span>
                        <span className="font-bold">{report.parsed_data_preview.layout_flags.is_scanned ? 'Yes (Bad)' : 'No (Clean)'}</span>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                        <span className="text-gray-500 block">Multi-Column:</span>
                        <span className="font-bold">{report.parsed_data_preview.layout_flags.has_multi_column ? 'Yes (Warning)' : 'No'}</span>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                        <span className="text-gray-500 block">Tables Present:</span>
                        <span className="font-bold">{report.parsed_data_preview.layout_flags.has_tables ? 'Yes' : 'No'}</span>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                        <span className="text-gray-500 block">Page Count:</span>
                        <span className="font-bold">{report.parsed_data_preview.page_count} page(s)</span>
                      </div>
                    </div>
                  )}

                  {showRawText && report.parsed_data_preview && (
                    <div className="p-4 bg-gray-900 text-emerald-400 font-mono text-xs rounded-xl overflow-x-auto max-h-80">
                      <pre>{report.parsed_data_preview.extracted_text}</pre>
                    </div>
                  )}
                </div>

                {/* PDF Report Download & Consultation CTA */}
                <div className="p-6 sm:p-8 rounded-3xl bg-gradient-to-r from-[#027A68] to-[#01584B] text-white space-y-4 shadow-lg">
                  <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div className="space-y-1 text-center sm:text-left">
                      <h3 className="text-xl sm:text-2xl font-black">
                        Download Your Diagnostic Report
                      </h3>
                      <p className="text-sm text-emerald-100">
                        Get an offline PDF report with detailed scores and action items.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleDownloadPDF}
                      className="px-6 py-3.5 bg-white text-[#027A68] hover:bg-[#FEF9EB] hover:text-[#9E7A26] font-bold text-sm rounded-xl transition-all shadow-md flex items-center gap-2"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download PDF Report</span>
                    </button>
                  </div>

                  <div className="pt-4 border-t border-emerald-600/50 flex flex-col sm:flex-row items-center justify-between gap-4">
                    <p className="text-xs text-emerald-200">
                      Need expert 1-on-1 resume rebuilding and interview coaching?
                    </p>
                    <a
                      href="https://auriic.co"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-5 py-2.5 bg-[#C89C36] hover:bg-[#9E7A26] text-white font-extrabold text-xs uppercase tracking-wider rounded-xl transition-all flex items-center gap-1.5"
                    >
                      <span>Book Free Consultation</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>

                {/* Legal Disclaimer */}
                <p className="text-xs text-gray-500 text-center italic max-w-2xl mx-auto">
                  {report.disclaimer}
                </p>
              </div>
            )}
          </div>
        )}

        {/* PRIVACY POLICY VIEW */}
        {activeTab === 'privacy' && (
          <div className="card-surface p-6 sm:p-10 bg-white max-w-3xl mx-auto space-y-6">
            <button
              onClick={() => setActiveTab('checker')}
              className="text-xs font-bold text-[#027A68] hover:underline flex items-center gap-1 mb-2"
            >
              ← Back to Resume Checker
            </button>
            <h1 className="text-2xl sm:text-3xl font-black text-[#027A68]">
              Auriic ATS Checker Privacy Policy
            </h1>
            <p className="text-xs text-gray-500 uppercase tracking-wider font-bold">
              Effective Date: November 2026
            </p>
            <div className="space-y-4 text-sm text-gray-700 leading-relaxed">
              <h2 className="font-bold text-gray-900 text-base">1. Privacy by Design & Zero-Storage by Default</h2>
              <p>
                When you use the Auriic Free ATS Checker without providing affirmative consent, your document is processed exclusively in transient volatile memory. We store only an irreversible SHA-256 cryptographic hash and numerical score. No resume files, contact details, or resume texts are saved.
              </p>

              <h2 className="font-bold text-gray-900 text-base">2. Consented Data Collection</h2>
              <p>
                If you elect to check the affirmative consent box, Auriic Services stores your parsed contact information (name, email, phone, location, LinkedIn profile) and an encrypted copy of your resume in private, non-public storage to provide career counseling and staffing services.
              </p>

              <h2 className="font-bold text-gray-900 text-base">3. Automated Redaction of Sensitive PII</h2>
              <p>
                Our parsing engine automatically scans for and redacts Social Security Numbers (SSNs), dates of birth, and passport numbers before persistence. We strongly advise job seekers never to put government identifiers on resumes.
              </p>

              <h2 className="font-bold text-gray-900 text-base">4. Retention & 12-Month Auto-Purge</h2>
              <p>
                Consented candidate files and extracted text are auto-purged from our active systems after twelve (12) months unless you enter an active recruitment or coaching engagement with Auriic Services.
              </p>

              <h2 className="font-bold text-gray-900 text-base">5. Right to Be Forgotten (Data Deletion)</h2>
              <p>
                You have the absolute right to have your data permanently deleted at any time. Simply navigate to our <strong>Delete My Data</strong> tab to initiate instant automated removal.
              </p>
            </div>
          </div>
        )}

        {/* DELETE MY DATA VIEW */}
        {activeTab === 'delete' && (
          <div className="card-surface p-6 sm:p-10 bg-white max-w-xl mx-auto space-y-6">
            <button
              onClick={() => setActiveTab('checker')}
              className="text-xs font-bold text-[#027A68] hover:underline flex items-center gap-1 mb-2"
            >
              ← Back to Resume Checker
            </button>
            <div className="space-y-1">
              <h1 className="text-2xl font-black text-rose-700">
                Self-Service Data Deletion
              </h1>
              <p className="text-sm text-gray-600">
                Permanently scrub your resume file, extracted text, and contact details from Auriic Services.
              </p>
            </div>

            <form onSubmit={handleRequestDeletion} className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-gray-700 mb-1">
                  Enter your email address
                </label>
                <input
                  type="email"
                  required
                  value={deleteEmail}
                  onChange={(e) => setDeleteEmail(e.target.value)}
                  placeholder="name@email.com"
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 text-sm focus:border-rose-600 focus:ring-1 focus:ring-rose-600"
                />
              </div>

              <button
                type="submit"
                className="w-full py-3 px-4 bg-rose-600 hover:bg-rose-700 text-white font-bold text-sm rounded-xl transition-all shadow-md"
              >
                Request Verification Token
              </button>
            </form>

            {deleteToken && (
              <form onSubmit={handleConfirmDeletion} className="space-y-4 pt-4 border-t border-gray-200">
                <div className="p-3 bg-gray-50 rounded-xl text-xs font-mono text-gray-700 break-all">
                  Token: <strong>{deleteToken}</strong>
                </div>
                <button
                  type="submit"
                  className="w-full py-3 px-4 bg-gray-900 hover:bg-black text-white font-bold text-sm rounded-xl transition-all shadow-md"
                >
                  Confirm Permanent Deletion
                </button>
              </form>
            )}

            {deleteMessage && (
              <div className="p-4 rounded-xl bg-gray-100 text-gray-800 text-xs font-medium">
                {deleteMessage}
              </div>
            )}
          </div>
        )}

        {/* ADMIN PORTAL VIEW */}
        {activeTab === 'admin' && (
          <div className="space-y-6 max-w-6xl mx-auto">
            <button
              onClick={() => setActiveTab('checker')}
              className="text-xs font-bold text-[#027A68] hover:underline flex items-center gap-1 mb-2"
            >
              ← Back to Resume Checker
            </button>
            {!adminToken ? (
              <div className="card-surface p-6 sm:p-8 bg-white max-w-md mx-auto space-y-4">
                <div className="flex items-center gap-2">
                  <Lock className="w-5 h-5 text-[#027A68]" />
                  <h2 className="text-xl font-black text-gray-900">Auriic Staff Sign In</h2>
                </div>
                <p className="text-xs text-gray-500">
                  Authorized access for managing candidate leads and ATS submissions.
                </p>

                <form onSubmit={handleAdminLogin} className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Staff ID / Name</label>
                    <input
                      type="text"
                      required
                      value={adminUsername}
                      onChange={(e) => setAdminUsername(e.target.value)}
                      placeholder="Param Parmar"
                      className="w-full px-3 py-2.5 rounded-lg border border-gray-300 text-sm focus:border-[#027A68] focus:ring-1 focus:ring-[#027A68]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-gray-700 mb-1">Password</label>
                    <input
                      type="password"
                      required
                      value={adminPassword}
                      onChange={(e) => setAdminPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3 py-2.5 rounded-lg border border-gray-300 text-sm focus:border-[#027A68] focus:ring-1 focus:ring-[#027A68]"
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full py-3 bg-[#027A68] hover:bg-[#01584B] text-white font-bold text-sm rounded-xl shadow-md transition-all cursor-pointer"
                  >
                    Sign In to Portal
                  </button>
                </form>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Admin Header with Actions */}
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-gray-200">
                  <div>
                    <h2 className="text-xl font-black text-gray-900">Candidate Leads Dashboard</h2>
                    <p className="text-xs text-gray-500">
                      Showing consenting leads for Auriic career coaching and placement.
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <a
                      href={`${API_BASE}/api/admin/export/csv?token=${encodeURIComponent(adminToken || '')}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-4 py-2.5 bg-[#027A68] hover:bg-[#01584B] text-white text-xs font-bold rounded-xl flex items-center gap-1.5 shadow-xs"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Export CSV</span>
                    </a>
                    <button
                      onClick={() => setAdminToken(null)}
                      className="px-4 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-bold rounded-xl"
                    >
                      Sign Out
                    </button>
                  </div>
                </div>

                {/* Filter & Search Bar */}
                <div className="bg-white p-4 rounded-2xl border border-gray-200 flex flex-col sm:flex-row items-center gap-3">
                  <div className="relative flex-1 w-full">
                    <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3.5" />
                    <input
                      type="text"
                      value={adminSearch}
                      onChange={(e) => setAdminSearch(e.target.value)}
                      placeholder="Search candidate by name, email, phone, location, or skill..."
                      className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-300 text-xs focus:border-[#027A68]"
                    />
                  </div>
                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <Filter className="w-4 h-4 text-gray-500" />
                    <select
                      value={adminIndustryFilter}
                      onChange={(e) => setAdminIndustryFilter(e.target.value)}
                      className="px-3 py-2.5 border rounded-xl text-xs bg-white text-gray-700"
                    >
                      <option value="all">All Industries</option>
                      <option value="it">IT</option>
                      <option value="healthcare">Healthcare</option>
                      <option value="finance">Finance</option>
                      <option value="manufacturing">Manufacturing</option>
                      <option value="logistics">Logistics</option>
                      <option value="construction">Construction</option>
                      <option value="energy">Energy</option>
                      <option value="retail">Retail</option>
                    </select>

                    <select
                      value={adminStatusFilter}
                      onChange={(e) => setAdminStatusFilter(e.target.value)}
                      className="px-3 py-2.5 border rounded-xl text-xs bg-white text-gray-700"
                    >
                      <option value="all">All Statuses</option>
                      <option value="new">New</option>
                      <option value="contacted">Contacted</option>
                      <option value="qualified">Qualified</option>
                      <option value="converted">Converted</option>
                      <option value="not_interested">Not Interested</option>
                    </select>
                  </div>
                </div>

                {/* Filterable Table */}
                <div className="card-surface bg-white rounded-2xl overflow-hidden border border-gray-200">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-gray-50 border-b border-gray-200 font-bold text-gray-600">
                        <tr>
                          <th className="py-3 px-4">Name & Email</th>
                          <th className="py-3 px-4">Phone / Location</th>
                          <th className="py-3 px-4">Industry</th>
                          <th className="py-3 px-4">ATS Score</th>
                          <th className="py-3 px-4">Lead Status</th>
                          <th className="py-3 px-4">Lead Score</th>
                          <th className="py-3 px-4 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {adminLeads
                          .filter((l) => {
                            if (adminIndustryFilter !== 'all' && l.detected_industry !== adminIndustryFilter) return false;
                            if (adminStatusFilter !== 'all' && l.lead_status !== adminStatusFilter) return false;
                            if (adminSearch) {
                              const q = adminSearch.toLowerCase();
                              return (
                                (l.full_name && l.full_name.toLowerCase().includes(q)) ||
                                (l.email && l.email.toLowerCase().includes(q)) ||
                                (l.phone && l.phone.toLowerCase().includes(q)) ||
                                (l.location && l.location.toLowerCase().includes(q))
                              );
                            }
                            return true;
                          })
                          .map((l) => (
                          <tr key={l.id} className="hover:bg-gray-50/60">
                            <td className="py-3 px-4">
                              <span className="font-bold text-gray-900 block">{l.full_name}</span>
                              <span className="text-gray-500">{l.email}</span>
                            </td>
                            <td className="py-3 px-4 text-gray-600">
                              <span>{l.phone || 'N/A'}</span>
                              <span className="block text-[11px] text-gray-400">{l.location || 'N/A'}</span>
                            </td>
                            <td className="py-3 px-4 uppercase text-gray-600 font-medium">
                              {l.detected_industry}
                            </td>
                            <td className="py-3 px-4">
                              <span className="font-mono font-bold text-gray-900">
                                {l.ats_score ? Math.round(l.ats_score) : 'N/A'}
                              </span>
                            </td>
                            <td className="py-3 px-4">
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-800 uppercase">
                                {l.lead_status}
                              </span>
                            </td>
                            <td className="py-3 px-4">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                  l.lead_score_category === 'hot'
                                    ? 'bg-rose-100 text-rose-800'
                                    : l.lead_score_category === 'warm'
                                    ? 'bg-amber-100 text-amber-800'
                                    : 'bg-gray-100 text-gray-700'
                                }`}
                              >
                                {l.lead_score_category}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right space-x-2">
                              <button
                                onClick={() => viewLeadDetail(l.id)}
                                className="px-2.5 py-1 text-xs font-bold bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-lg"
                              >
                                View
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Lead Detail Modal */}
                {adminSelectedLead && (
                  <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 sm:p-8 space-y-6 shadow-2xl">
                      <div className="flex items-center justify-between border-b pb-4">
                        <div>
                          <h3 className="text-xl font-black text-gray-900">
                            {adminSelectedLead.lead.full_name}
                          </h3>
                          <p className="text-xs text-gray-500">{adminSelectedLead.lead.email}</p>
                        </div>
                        <button
                          onClick={() => setAdminSelectedLead(null)}
                          className="p-2 text-gray-400 hover:text-gray-700"
                        >
                          ✕
                        </button>
                      </div>

                      <div className="grid grid-cols-2 gap-4 text-xs">
                        <div>
                          <span className="text-gray-500 block">Phone:</span>
                          <span className="font-semibold">{adminSelectedLead.lead.phone || 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-gray-500 block">Location:</span>
                          <span className="font-semibold">{adminSelectedLead.lead.location || 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-gray-500 block">Lead Category:</span>
                          <span className="font-bold uppercase text-[#027A68]">
                            {adminSelectedLead.lead.lead_score_category}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-500 block">Reason:</span>
                          <span className="text-gray-700">{adminSelectedLead.lead.lead_score_reason}</span>
                        </div>
                      </div>

                      {/* Submissions & Resume Downloads */}
                      <div className="space-y-3">
                        <h4 className="text-sm font-bold text-gray-800">Submission History</h4>
                        {adminSelectedLead.submissions.map((sub: any, idx: number) => (
                          <div key={idx} className="p-3 bg-gray-50 rounded-xl border border-gray-200 flex items-center justify-between text-xs">
                            <div>
                              <span className="font-bold">Mode {sub.mode} • Score: {Math.round(sub.ats_score)}</span>
                              <span className="text-gray-500 block text-[11px]">{sub.created_at}</span>
                            </div>
                            {sub.download_url && (
                              <a
                                href={sub.download_url}
                                target="_blank"
                                rel="noreferrer"
                                className="px-3 py-1.5 bg-[#027A68] text-white font-bold rounded-lg hover:bg-[#01584B] flex items-center gap-1"
                              >
                                <Download className="w-3 h-3" />
                                <span>Download File</span>
                              </a>
                            )}
                          </div>
                        ))}
                      </div>

                      {/* Status & Notes */}
                      <div className="space-y-3 pt-4 border-t">
                        <div>
                          <label className="block text-xs font-bold text-gray-700 mb-1">Update Status</label>
                          <select
                            value={adminNewStatus}
                            onChange={(e) => setAdminNewStatus(e.target.value)}
                            className="w-full p-2 border rounded-lg text-xs"
                          >
                            <option value="new">New</option>
                            <option value="contacted">Contacted</option>
                            <option value="qualified">Qualified</option>
                            <option value="converted">Converted</option>
                            <option value="not_interested">Not Interested</option>
                          </select>
                        </div>

                        <div>
                          <label className="block text-xs font-bold text-gray-700 mb-1">Recruiter Notes</label>
                          <textarea
                            rows={3}
                            value={adminNotes}
                            onChange={(e) => setAdminNotes(e.target.value)}
                            className="w-full p-2 border rounded-lg text-xs"
                          />
                        </div>

                        <div className="flex items-center justify-between pt-2">
                          <button
                            type="button"
                            onClick={() => deleteLeadAdmin(adminSelectedLead.lead.id)}
                            className="px-3 py-2 text-rose-600 hover:bg-rose-50 rounded-lg text-xs font-bold flex items-center gap-1"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            <span>Delete Lead & Files</span>
                          </button>

                          <button
                            type="button"
                            onClick={() => updateLeadStatus(adminSelectedLead.lead.id)}
                            className="px-4 py-2 bg-[#027A68] hover:bg-[#01584B] text-white rounded-lg text-xs font-bold"
                          >
                            Save Changes
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Small Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12 py-6 text-center text-xs text-gray-500 space-y-3 px-4">
        {/* Data Storage Consent Notice */}
        <p className="max-w-3xl mx-auto text-[11px] sm:text-xs text-gray-600 bg-[#F9FBFA] p-3 rounded-xl border border-gray-200/80">
          <strong>Data Storage Consent:</strong> I agree that Auriic Services may store my resume and contact details and contact me about career services and staffing placements.{' '}
          <button
            onClick={() => setActiveTab('privacy')}
            className="text-[#027A68] font-bold underline hover:text-[#01584B]"
          >
            See Privacy Policy.
          </button>
        </p>

        <p className="font-semibold text-gray-700">
          © 2026 Auriic Services. All rights reserved.
        </p>
        <p className="text-[11px] text-gray-500 max-w-2xl mx-auto">
          Auriic Services provides personalized career coaching, resume optimization, and US staffing for students, OPT/STEM OPT, H-1B holders, and experienced professionals.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3 text-[#027A68] font-bold text-xs pt-1">
          <button onClick={() => setActiveTab('checker')} className="hover:underline">
            Resume Checker
          </button>
          <span>•</span>
          <button onClick={() => setActiveTab('privacy')} className="hover:underline">
            Privacy Policy
          </button>
          <span>•</span>
          <button onClick={() => setActiveTab('delete')} className="hover:underline">
            Delete My Data
          </button>
          <span>•</span>
          <a href="https://auriic.co" target="_blank" rel="noopener noreferrer" className="hover:underline">
            auriic.co
          </a>
        </div>
      </footer>
    </div>
  );
}
