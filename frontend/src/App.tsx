import React, { useState, useRef, useEffect, useMemo } from 'react';
import {
  Upload,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  ArrowRight,
  Download,
  Eye,
  EyeOff,
  RefreshCw,
  ExternalLink,
  Lock,
  Search,
  Trash2,
  Filter,
  FileText,
  Check,
  ChevronRight,
  X,
  AlertCircle,
  Building2,
  User,
  Phone,
  Mail,
  MapPin,
  Linkedin,
  FileCheck,
  Layers,
  BarChart3,
  HelpCircle,
  ArrowUpRight,
  LogOut,
  Briefcase,
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  // Form input states
  const [mode, setMode] = useState<'A' | 'B'>('A');
  const [industryOverride, setIndustryOverride] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState<string>('');
  const [consentGiven, setConsentGiven] = useState<boolean>(false);
  const [consentMarketing, setConsentMarketing] = useState<boolean>(false);

  // Execution states
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisStep, setAnalysisStep] = useState<string>('');
  const [analysisProgress, setAnalysisProgress] = useState<number>(0);
  const [report, setReport] = useState<ATSReport | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showRawText, setShowRawText] = useState<boolean>(false);
  const [copiedRawText, setCopiedRawText] = useState<boolean>(false);

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
  const [isAdminLoggingIn, setIsAdminLoggingIn] = useState<boolean>(false);
  const [adminLoginError, setAdminLoginError] = useState<string | null>(null);

  // Deletion form states
  const [deleteEmail, setDeleteEmail] = useState<string>('');
  const [deleteToken, setDeleteToken] = useState<string>('');
  const [deleteMessage, setDeleteMessage] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  // Keyword filter in Report
  const [keywordFilter, setKeywordFilter] = useState<'all' | 'Missing' | 'Found' | 'Partial'>('all');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Listen for hash changes for staff access (e.g. #staff or #portal)
  useEffect(() => {
    const handleHash = () => {
      if (window.location.hash === '#staff' || window.location.hash === '#portal') {
        setActiveTab('admin');
      }
    };
    handleHash();
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, []);

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
    setAnalysisProgress(15);
    setAnalysisStep('Reading document encoding and verifying text layers...');

    const timer1 = setTimeout(() => {
      setAnalysisProgress(45);
      setAnalysisStep('Extracting contact headers, work history, and skills...');
    }, 600);

    const timer2 = setTimeout(() => {
      setAnalysisProgress(80);
      setAnalysisStep('Evaluating deterministic ATS heuristics & industry keywords...');
    }, 1300);

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

      setAnalysisProgress(100);
      setAnalysisStep('Finalizing score report...');

      const data: ATSReport = await response.json();
      setReport(data);

      setTimeout(() => {
        document.getElementById('report-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 150);
    } catch (err: any) {
      setErrorMessage(err.message || 'An error occurred during analysis.');
    } finally {
      clearTimeout(timer1);
      clearTimeout(timer2);
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

  // Copy raw text handler
  const handleCopyRawText = () => {
    if (report?.parsed_data_preview?.extracted_text) {
      navigator.clipboard.writeText(report.parsed_data_preview.extracted_text);
      setCopiedRawText(true);
      setTimeout(() => setCopiedRawText(false), 2000);
    }
  };

  // Admin login handler
  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsAdminLoggingIn(true);
    setAdminLoginError(null);
    try {
      const response = await fetch(`${API_BASE}/api/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: adminUsername, password: adminPassword }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Invalid username or password.');
      }
      const data = await response.json();
      setAdminToken(data.token);
      loadAdminLeads(data.token);
    } catch (err: any) {
      setAdminLoginError(err.message || 'Login failed.');
    } finally {
      setIsAdminLoggingIn(false);
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
    setIsDeleting(true);
    setDeleteMessage(null);
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
    } finally {
      setIsDeleting(false);
    }
  };

  const handleConfirmDeletion = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsDeleting(true);
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
    } finally {
      setIsDeleting(false);
    }
  };

  // Filtered Leads in Admin
  const filteredLeads = useMemo(() => {
    return adminLeads.filter((l) => {
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
    });
  }, [adminLeads, adminIndustryFilter, adminStatusFilter, adminSearch]);

  // Lead metrics in Admin
  const adminMetrics = useMemo(() => {
    const total = adminLeads.length;
    const scores = adminLeads.map((l) => l.ats_score).filter((s) => typeof s === 'number');
    const avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;
    const warmOrHot = adminLeads.filter((l) => l.lead_score_category === 'hot' || l.lead_score_category === 'warm').length;
    const newCount = adminLeads.filter((l) => l.lead_status === 'new').length;
    return { total, avgScore, warmOrHot, newCount };
  }, [adminLeads]);

  return (
    <div className="min-h-screen flex flex-col bg-[#F8FAFC] text-[#0F172A] font-sans antialiased selection:bg-[#027A68]/15 selection:text-[#027A68]">
      {/* Top Application Header */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-xs border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo & Product Indicator */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setActiveTab('checker');
                window.location.hash = '';
              }}
              className="flex items-center gap-3 text-left focus:outline-hidden"
            >
              <img
                src="/auriic-logo.png"
                alt="Auriic Logo"
                className="h-8 sm:h-9 w-auto object-contain"
              />
              <div className="hidden sm:flex items-center gap-2 pl-3 border-l border-slate-200">
                <span className="text-xs font-semibold text-slate-800 tracking-tight">
                  ATS Resume Diagnostic
                </span>
                <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-emerald-50 text-[#027A68] border border-emerald-200/60">
                  v1.0 Free
                </span>
              </div>
            </button>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1 text-sm font-medium text-slate-600">
            <button
              onClick={() => {
                setActiveTab('checker');
                window.location.hash = '';
              }}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                activeTab === 'checker'
                  ? 'text-[#027A68] bg-emerald-50/70 font-semibold'
                  : 'hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              Resume Diagnostic
            </button>
            <button
              onClick={() => setActiveTab('privacy')}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                activeTab === 'privacy'
                  ? 'text-[#027A68] bg-emerald-50/70 font-semibold'
                  : 'hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              Privacy & Retention
            </button>
            <button
              onClick={() => setActiveTab('delete')}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                activeTab === 'delete'
                  ? 'text-rose-700 bg-rose-50 font-semibold'
                  : 'hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              Delete My Data
            </button>
            <button
              onClick={() => {
                setActiveTab('admin');
                window.location.hash = '#staff';
              }}
              className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
                activeTab === 'admin'
                  ? 'text-[#027A68] bg-emerald-50/70 font-semibold'
                  : 'hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Lock className="w-3.5 h-3.5" />
              <span>Staff Portal</span>
            </button>
          </nav>

          {/* CTA & Mobile Menu Toggle */}
          <div className="flex items-center gap-2.5">
            <a
              href="https://auriic.co"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#027A68] hover:bg-[#01584B] text-white text-xs font-semibold shadow-xs transition-colors"
            >
              <span>Consultation</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </a>

            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 focus:outline-hidden"
              aria-label="Toggle navigation"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Filter className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-slate-200 bg-white px-4 pt-2 pb-4 space-y-1">
            <button
              onClick={() => {
                setActiveTab('checker');
                setMobileMenuOpen(false);
                window.location.hash = '';
              }}
              className="w-full text-left px-3 py-2 text-sm font-medium text-slate-700 rounded-md hover:bg-slate-100"
            >
              Resume Diagnostic
            </button>
            <button
              onClick={() => {
                setActiveTab('privacy');
                setMobileMenuOpen(false);
              }}
              className="w-full text-left px-3 py-2 text-sm font-medium text-slate-700 rounded-md hover:bg-slate-100"
            >
              Privacy & Retention
            </button>
            <button
              onClick={() => {
                setActiveTab('delete');
                setMobileMenuOpen(false);
              }}
              className="w-full text-left px-3 py-2 text-sm font-medium text-slate-700 rounded-md hover:bg-slate-100"
            >
              Delete My Data
            </button>
            <button
              onClick={() => {
                setActiveTab('admin');
                setMobileMenuOpen(false);
                window.location.hash = '#staff';
              }}
              className="w-full text-left px-3 py-2 text-sm font-medium text-slate-700 rounded-md hover:bg-slate-100 flex items-center gap-2"
            >
              <Lock className="w-4 h-4 text-slate-400" />
              <span>Staff Portal</span>
            </button>
          </div>
        )}
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* CHECKER VIEW */}
        {activeTab === 'checker' && (
          <div className="space-y-8">
            {/* Hero / Page Overview */}
            <div className="text-center max-w-3xl mx-auto space-y-3 pt-2 pb-1">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                <ShieldCheck className="w-3.5 h-3.5 text-[#027A68]" />
                <span>Deterministic ATS Rules Engine • 8 US Industries</span>
              </div>
              <h1 className="text-2xl sm:text-4xl font-bold tracking-tight text-slate-900">
                US Recruiter ATS Diagnostic
              </h1>
              <p className="text-sm sm:text-base text-slate-600 leading-relaxed">
                Evaluates resume layout, font encodings, action verbs, quantified metrics, and hard skills parity against standard enterprise Applicant Tracking Systems (Workday, Greenhouse, Taleo, Lever, iCIMS).
              </p>
            </div>

            {/* Diagnostic Control Card */}
            <div className="saas-card bg-white p-5 sm:p-7 max-w-3xl mx-auto border border-slate-200 rounded-xl shadow-xs">
              <form onSubmit={handleAnalyze} className="space-y-6">
                {/* 1. Mode Selector (Segmented Tab Style) */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      Evaluation Mode
                    </label>
                    <span className="text-[11px] text-slate-500">
                      {mode === 'A' ? 'No Job Description required' : 'Requires target Job Description'}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-1 bg-slate-100/80 rounded-lg border border-slate-200">
                    <button
                      type="button"
                      onClick={() => setMode('A')}
                      className={`p-3.5 rounded-md text-left transition-all flex flex-col justify-between ${
                        mode === 'A'
                          ? 'bg-white shadow-xs border border-slate-200/90 text-slate-900'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/40'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold flex items-center gap-1.5 text-slate-900">
                          <Layers className="w-3.5 h-3.5 text-[#027A68]" />
                          Mode A: General ATS Health
                        </span>
                        {mode === 'A' && <Check className="w-4 h-4 text-[#027A68]" />}
                      </div>
                      <p className="text-[11px] text-slate-500 leading-normal">
                        Scans structure, action verbs, impact metrics, section headers, and formatting hygiene.
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setMode('B')}
                      className={`p-3.5 rounded-md text-left transition-all flex flex-col justify-between ${
                        mode === 'B'
                          ? 'bg-white shadow-xs border border-slate-200/90 text-slate-900'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/40'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold flex items-center gap-1.5 text-slate-900">
                          <Briefcase className="w-3.5 h-3.5 text-[#027A68]" />
                          Mode B: Target Job Match
                        </span>
                        {mode === 'B' && <Check className="w-4 h-4 text-[#027A68]" />}
                      </div>
                      <p className="text-[11px] text-slate-500 leading-normal">
                        Compares skills, required keywords, seniority, and title alignment against a target job post.
                      </p>
                    </button>
                  </div>
                </div>

                {/* 2. Industry Group Dropdown */}
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                    Target Industry Domain
                  </label>
                  <div className="relative">
                    <select
                      value={industryOverride}
                      onChange={(e) => setIndustryOverride(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 bg-white text-sm text-slate-800 focus:border-[#027A68] focus:ring-1 focus:ring-[#027A68] transition-colors"
                    >
                      <option value="">Auto-Detect from Resume Content (Default)</option>
                      <option value="it">Information Technology & Software Engineering</option>
                      <option value="healthcare">Healthcare, Clinical & Nursing</option>
                      <option value="finance">Banking, Corporate Finance & Accounting</option>
                      <option value="manufacturing">Manufacturing & Industrial Engineering</option>
                      <option value="logistics">Supply Chain, Logistics & Operations</option>
                      <option value="construction">Construction & Civil Engineering</option>
                      <option value="energy">Energy, Utilities & Oil/Gas</option>
                      <option value="retail">Retail, Consumer Goods & E-Commerce</option>
                    </select>
                  </div>
                </div>

                {/* 3. File Upload Area */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      Upload Resume Document
                    </label>
                    <span className="text-[11px] text-slate-500">PDF, DOCX, TXT • Max 5 MB</span>
                  </div>

                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    accept=".pdf,.docx,.doc,.txt"
                    className="hidden"
                  />

                  {file ? (
                    <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/70 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-[#027A68]">
                          <FileText className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="text-xs font-bold text-slate-900 truncate max-w-xs sm:max-w-md">
                            {file.name}
                          </p>
                          <p className="text-[11px] text-slate-500">
                            {(file.size / 1024).toFixed(1)} KB • Ready for scan
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-md transition-colors"
                      >
                        Change File
                      </button>
                    </div>
                  ) : (
                    <div
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={handleDrop}
                      onClick={() => fileInputRef.current?.click()}
                      className="border-2 border-dashed border-slate-300 hover:border-[#027A68] bg-slate-50/40 hover:bg-slate-50/80 rounded-xl p-7 text-center cursor-pointer transition-colors"
                    >
                      <Upload className="w-8 h-8 text-[#027A68] mx-auto mb-2 opacity-80" />
                      <p className="text-sm font-semibold text-slate-800">
                        Drop resume here, or <span className="text-[#027A68] underline">browse files</span>
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        Compatible with standard PDF, Microsoft Word (.docx), or plain text (.txt)
                      </p>
                    </div>
                  )}
                </div>

                {/* 4. Mode B Job Description Input */}
                {mode === 'B' && (
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
                        Target Job Description
                      </label>
                      <span className="text-[11px] text-slate-500">Min 30 characters</span>
                    </div>
                    <textarea
                      rows={5}
                      value={jobDescription}
                      onChange={(e) => setJobDescription(e.target.value)}
                      placeholder="Paste the full job posting text including responsibilities, hard skill requirements, and qualifications..."
                      className="w-full p-3 rounded-lg border border-slate-300 text-sm focus:border-[#027A68] focus:ring-1 focus:ring-[#027A68] placeholder:text-slate-400"
                    />
                  </div>
                )}

                {/* 5. Privacy & Consent Gate */}
                <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/90 space-y-2.5">
                  <div className="flex items-start gap-2.5">
                    <input
                      type="checkbox"
                      id="consent-main"
                      checked={consentGiven}
                      onChange={(e) => setConsentGiven(e.target.checked)}
                      className="mt-0.5 h-4 w-4 rounded border-slate-300 text-[#027A68] focus:ring-[#027A68]"
                    />
                    <label htmlFor="consent-main" className="text-xs text-slate-700 font-medium leading-relaxed">
                      <strong className="text-slate-900">Data Storage Consent:</strong> I agree that Auriic Services may store my resume and contact details and contact me regarding career services and placement opportunities.{' '}
                      <button
                        type="button"
                        onClick={() => setActiveTab('privacy')}
                        className="text-[#027A68] underline font-semibold hover:text-[#01584B]"
                      >
                        Privacy Policy
                      </button>.
                    </label>
                  </div>

                  <div className="flex items-start gap-2.5">
                    <input
                      type="checkbox"
                      id="consent-marketing"
                      checked={consentMarketing}
                      onChange={(e) => setConsentMarketing(e.target.checked)}
                      className="mt-0.5 h-4 w-4 rounded border-slate-300 text-[#027A68] focus:ring-[#027A68]"
                    />
                    <label htmlFor="consent-marketing" className="text-xs text-slate-600 leading-relaxed">
                      (Optional) Send me US hiring trends, salary reports, and OPT/H-1B job search insights.
                    </label>
                  </div>

                  <p className="text-[11px] text-slate-500 pt-1 border-t border-slate-200">
                    * If left unchecked, your resume is analyzed in temporary memory. Zero files or contact details are retained.
                  </p>
                </div>

                {errorMessage && (
                  <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    <span>{errorMessage}</span>
                  </div>
                )}

                {/* Submit Action */}
                <button
                  type="submit"
                  disabled={isAnalyzing}
                  className="w-full py-3 px-4 rounded-lg bg-[#027A68] hover:bg-[#01584B] text-white font-semibold text-sm transition-all shadow-xs flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>{analysisStep || 'Analyzing Document...'}</span>
                    </>
                  ) : (
                    <>
                      <span>Run ATS Diagnostic</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* DIAGNOSTIC REPORT SECTION */}
            {report && (
              <div id="report-section" className="space-y-6 max-w-4xl mx-auto pt-4">
                {/* PII Alert if detected */}
                {report.pii_alerts && report.pii_alerts.length > 0 && (
                  <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 space-y-1.5">
                    <div className="flex items-center gap-2 text-xs font-bold text-amber-800">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      <span>Sensitive Personal Identifiers Auto-Redacted</span>
                    </div>
                    <p className="text-xs text-amber-800">
                      Never include SSNs, dates of birth, or passport numbers on a US resume. We auto-redacted these items prior to scoring:
                    </p>
                    <ul className="text-xs space-y-1 list-disc pl-5 text-amber-800">
                      {report.pii_alerts.map((alert, idx) => (
                        <li key={idx}>
                          <strong>{alert.type}:</strong> {alert.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Score Summary Overview Card */}
                <div className="saas-card bg-white p-6 sm:p-7 border border-slate-200 rounded-xl shadow-xs">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 pb-6 border-b border-slate-100">
                    <div>
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-emerald-50 text-[#027A68] border border-emerald-100 mb-2">
                        Mode {report.mode}: {report.mode === 'A' ? 'General ATS Health' : 'Target Job Match'}
                      </div>
                      <h2 className="text-xl sm:text-2xl font-bold text-slate-900">
                        ATS Compatibility Score
                      </h2>
                      <p className="text-xs text-slate-500 mt-1">
                        Industry: <strong>{report.detected_industry_name}</strong> • Scoring Engine: <strong>v{report.scoring_version}</strong>
                      </p>
                    </div>

                    {/* Numeric Gauge Block */}
                    <div className="flex items-center gap-4 self-center sm:self-auto">
                      <div className="text-center">
                        <div className="text-4xl sm:text-5xl font-black text-[#027A68] tracking-tight">
                          {Math.round(report.overall_score)}
                          <span className="text-lg font-normal text-slate-400">/100</span>
                        </div>
                        <span
                          className={`inline-block px-2.5 py-0.5 mt-1 text-[11px] font-bold uppercase rounded-full ${
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

                  {/* Category Breakdown Progress Bars */}
                  <div className="pt-6 space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Category Scoring Breakdown
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {Object.entries(report.category_breakdown).map(([catKey, scores]) => {
                        const pct = Math.round((scores.earned / scores.possible) * 100);
                        return (
                          <div key={catKey} className="p-3.5 rounded-lg bg-slate-50/70 border border-slate-200/80 space-y-1.5">
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-semibold text-slate-800 capitalize">
                                {catKey.replace(/_/g, ' ')}
                              </span>
                              <span className="font-mono text-slate-600 text-[11px]">
                                {scores.earned.toFixed(1)} / {scores.possible} pts
                              </span>
                            </div>
                            <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
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

                {/* Top Action Items ("Fix This First") */}
                <div className="saas-card bg-white p-6 border border-slate-200 rounded-xl space-y-4">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-[#C89C36]" />
                    <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900">
                      Prioritized Improvements ({report.top_fixes?.length || 0} items)
                    </h3>
                  </div>

                  {report.top_fixes && report.top_fixes.length > 0 ? (
                    <div className="space-y-3">
                      {report.top_fixes.map((fix, idx) => (
                        <div
                          key={idx}
                          className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/60 space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span
                              className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded ${
                                fix.severity === 'CRITICAL'
                                  ? 'bg-rose-100 text-rose-800'
                                  : fix.severity === 'HIGH'
                                  ? 'bg-amber-100 text-amber-800'
                                  : 'bg-blue-100 text-blue-800'
                              }`}
                            >
                              {fix.severity} • -{fix.points_lost} pts
                            </span>
                            <span className="text-[11px] text-slate-500">{fix.category}</span>
                          </div>
                          <p className="text-xs font-semibold text-slate-900">{fix.reason}</p>
                          <p className="text-xs text-slate-600">
                            <strong className="text-slate-800">Recommendation:</strong> {fix.recommendation}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium">
                      No critical deductions found. Your resume formatting adheres cleanly to standard recruiter heuristics.
                    </div>
                  )}
                </div>

                {/* Mode B Keyword Alignment Table */}
                {report.mode === 'B' && report.keyword_table && (
                  <div className="saas-card bg-white p-6 border border-slate-200 rounded-xl space-y-4">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                      <div>
                        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900">
                          Job Description Keyword Alignment
                        </h3>
                        <p className="text-xs text-slate-500">
                          {report.keyword_table.length} requirements extracted from target job description
                        </p>
                      </div>

                      {/* Keyword Filter Tabs */}
                      <div className="flex items-center gap-1 p-0.5 bg-slate-100 rounded-lg text-xs">
                        {(['all', 'Missing', 'Partial', 'Found'] as const).map((status) => (
                          <button
                            key={status}
                            type="button"
                            onClick={() => setKeywordFilter(status)}
                            className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                              keywordFilter === status
                                ? 'bg-white text-slate-900 font-semibold shadow-xs'
                                : 'text-slate-600 hover:text-slate-900'
                            }`}
                          >
                            {status === 'all' ? 'All' : status}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="overflow-x-auto border border-slate-200 rounded-lg">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 border-b border-slate-200 font-semibold text-slate-600">
                          <tr>
                            <th className="py-2.5 px-3">Keyword / Skill</th>
                            <th className="py-2.5 px-3">Type</th>
                            <th className="py-2.5 px-3">Status</th>
                            <th className="py-2.5 px-3">Resume Location Found</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {report.keyword_table
                            .filter((row) => (keywordFilter === 'all' ? true : row.status === keywordFilter))
                            .map((row, idx) => (
                              <tr key={idx} className="hover:bg-slate-50/70">
                                <td className="py-2.5 px-3 font-medium text-slate-900">{row.keyword}</td>
                                <td className="py-2.5 px-3">
                                  <span
                                    className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                      row.type === 'Required'
                                        ? 'bg-purple-50 text-purple-700 border border-purple-200'
                                        : 'bg-slate-100 text-slate-600'
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
                                <td className="py-2.5 px-3 text-slate-600">{row.location_found || 'Not found'}</td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Evidence-Backed Deductions List */}
                <div className="saas-card bg-white p-6 border border-slate-200 rounded-xl space-y-4">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900">
                    Comprehensive Deduction Evidence ({report.deductions.length} total)
                  </h3>
                  <div className="space-y-3">
                    {report.deductions.map((d, idx) => (
                      <div key={idx} className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-[#027A68]">{d.category}</span>
                          <span className="font-bold text-rose-600">-{d.points_lost} pts</span>
                        </div>
                        <p className="text-xs font-semibold text-slate-900">{d.reason}</p>
                        <div className="p-2 rounded bg-white border border-slate-200/80 text-[11px] text-slate-600 font-mono">
                          <strong>Evidence:</strong> {d.evidence}
                        </div>
                        <p className="text-xs text-slate-700">
                          <strong>Fix:</strong> {d.recommendation}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* "What the ATS Sees" Inspector */}
                <div className="saas-card bg-white p-6 border border-slate-200 rounded-xl space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900">
                        ATS Parsing Layer Inspector
                      </h3>
                      <p className="text-xs text-slate-500">
                        Inspect the exact plain-text extraction layer and layout flags seen by recruiter software.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowRawText(!showRawText)}
                      className="px-3 py-1.5 text-xs font-semibold rounded-md border border-slate-200 hover:bg-slate-50 text-slate-700 flex items-center gap-1.5 transition-colors"
                    >
                      {showRawText ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      <span>{showRawText ? 'Hide Text' : 'View Text'}</span>
                    </button>
                  </div>

                  {report.parsed_data_preview && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
                        <span className="text-slate-500 block text-[11px]">Scanned Image:</span>
                        <span className="font-semibold text-slate-900">
                          {report.parsed_data_preview.layout_flags.is_scanned ? 'Detected (High Risk)' : 'Clean Text Layer'}
                        </span>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
                        <span className="text-slate-500 block text-[11px]">Multi-Column:</span>
                        <span className="font-semibold text-slate-900">
                          {report.parsed_data_preview.layout_flags.has_multi_column ? 'Yes (Potential Scramble)' : 'Single Column'}
                        </span>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
                        <span className="text-slate-500 block text-[11px]">Tables Present:</span>
                        <span className="font-semibold text-slate-900">
                          {report.parsed_data_preview.layout_flags.has_tables ? 'Yes (Verify Cells)' : 'No Tables'}
                        </span>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
                        <span className="text-slate-500 block text-[11px]">Page Count:</span>
                        <span className="font-semibold text-slate-900">
                          {report.parsed_data_preview.page_count} page(s)
                        </span>
                      </div>
                    </div>
                  )}

                  {showRawText && report.parsed_data_preview && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span>Extracted Plain Text Representation</span>
                        <button
                          type="button"
                          onClick={handleCopyRawText}
                          className="text-[#027A68] hover:underline font-semibold"
                        >
                          {copiedRawText ? 'Copied!' : 'Copy to Clipboard'}
                        </button>
                      </div>
                      <div className="p-4 bg-slate-900 text-slate-200 font-mono text-xs rounded-lg overflow-x-auto max-h-72 leading-relaxed">
                        <pre>{report.parsed_data_preview.extracted_text}</pre>
                      </div>
                    </div>
                  )}
                </div>

                {/* PDF Download & Consultation CTA Card */}
                <div className="saas-card p-6 bg-slate-900 text-white rounded-xl space-y-4">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div>
                      <h3 className="text-base sm:text-lg font-bold text-white">
                        Export Report & Consultation
                      </h3>
                      <p className="text-xs sm:text-sm text-slate-300">
                        Save your PDF diagnostic summary or speak with an Auriic career placement advisor.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleDownloadPDF}
                      className="px-4 py-2.5 bg-white hover:bg-slate-100 text-slate-900 font-semibold text-xs rounded-lg transition-colors flex items-center gap-2"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download PDF Report</span>
                    </button>
                  </div>

                  <div className="pt-3 border-t border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
                    <p className="text-slate-400">
                      Looking for US staffing, H-1B sponsor placements, or personalized resume rebuilding?
                    </p>
                    <a
                      href="https://auriic.co"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[#C89C36] hover:text-[#EEDBA8] font-semibold"
                    >
                      <span>Book Free Consultation at auriic.co</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>

                {/* Disclaimer */}
                <p className="text-xs text-slate-400 text-center italic max-w-2xl mx-auto">
                  {report.disclaimer}
                </p>
              </div>
            )}
          </div>
        )}

        {/* PRIVACY POLICY VIEW */}
        {activeTab === 'privacy' && (
          <div className="saas-card p-6 sm:p-10 bg-white max-w-3xl mx-auto space-y-6 rounded-xl border border-slate-200">
            <button
              onClick={() => setActiveTab('checker')}
              className="text-xs font-semibold text-[#027A68] hover:underline flex items-center gap-1"
            >
              ← Return to Resume Checker
            </button>
            <div className="space-y-1">
              <h1 className="text-2xl font-bold text-slate-900">
                Auriic ATS Checker Privacy Policy
              </h1>
              <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">
                Effective Date: November 2026
              </p>
            </div>
            <div className="space-y-4 text-sm text-slate-700 leading-relaxed">
              <h2 className="font-bold text-slate-900 text-sm">1. Privacy by Design & Zero-Storage by Default</h2>
              <p>
                When you use the Auriic Free ATS Checker without providing affirmative consent, your document is processed exclusively in transient volatile memory. We store only an irreversible SHA-256 cryptographic hash and numerical score. No resume files, contact details, or resume texts are saved.
              </p>

              <h2 className="font-bold text-slate-900 text-sm">2. Consented Data Collection</h2>
              <p>
                If you elect to check the affirmative consent box, Auriic Services stores your parsed contact information (name, email, phone, location, LinkedIn profile) and an encrypted copy of your resume in private, non-public storage to provide career counseling and staffing services.
              </p>

              <h2 className="font-bold text-slate-900 text-sm">3. Automated Redaction of Sensitive PII</h2>
              <p>
                Our parsing engine automatically scans for and redacts Social Security Numbers (SSNs), dates of birth, and passport numbers before persistence. We strongly advise job seekers never to put government identifiers on resumes.
              </p>

              <h2 className="font-bold text-slate-900 text-sm">4. Retention & 12-Month Auto-Purge</h2>
              <p>
                Consented candidate files and extracted text are auto-purged from our active systems after twelve (12) months unless you enter an active recruitment or coaching engagement with Auriic Services.
              </p>

              <h2 className="font-bold text-slate-900 text-sm">5. Right to Be Forgotten (Data Deletion)</h2>
              <p>
                You have the absolute right to have your data permanently deleted at any time. Simply navigate to our <strong>Delete My Data</strong> tab to initiate instant automated removal.
              </p>
            </div>
          </div>
        )}

        {/* DELETE MY DATA VIEW */}
        {activeTab === 'delete' && (
          <div className="saas-card p-6 sm:p-10 bg-white max-w-xl mx-auto space-y-6 rounded-xl border border-slate-200">
            <button
              onClick={() => setActiveTab('checker')}
              className="text-xs font-semibold text-[#027A68] hover:underline flex items-center gap-1"
            >
              ← Return to Resume Checker
            </button>
            <div className="space-y-1">
              <h1 className="text-xl font-bold text-slate-900">
                Self-Service Data Deletion
              </h1>
              <p className="text-xs text-slate-600">
                Permanently scrub your resume file, extracted text, and contact details from Auriic Services databases.
              </p>
            </div>

            <form onSubmit={handleRequestDeletion} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={deleteEmail}
                  onChange={(e) => setDeleteEmail(e.target.value)}
                  placeholder="name@email.com"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm focus:border-rose-600 focus:ring-1 focus:ring-rose-600"
                />
              </div>

              <button
                type="submit"
                disabled={isDeleting}
                className="w-full py-2.5 px-4 bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs rounded-lg transition-colors shadow-xs disabled:opacity-50"
              >
                {isDeleting ? 'Generating Token...' : 'Request Verification Token'}
              </button>
            </form>

            {deleteToken && (
              <form onSubmit={handleConfirmDeletion} className="space-y-4 pt-4 border-t border-slate-200">
                <div className="p-3 bg-slate-50 rounded-lg text-xs font-mono text-slate-700 break-all border border-slate-200">
                  Verification Token: <strong>{deleteToken}</strong>
                </div>
                <button
                  type="submit"
                  disabled={isDeleting}
                  className="w-full py-2.5 px-4 bg-slate-900 hover:bg-black text-white font-semibold text-xs rounded-lg transition-colors shadow-xs disabled:opacity-50"
                >
                  Confirm Permanent Deletion
                </button>
              </form>
            )}

            {deleteMessage && (
              <div className="p-3 rounded-lg bg-slate-100 text-slate-800 text-xs font-medium border border-slate-200">
                {deleteMessage}
              </div>
            )}
          </div>
        )}

        {/* STAFF PORTAL VIEW */}
        {activeTab === 'admin' && (
          <div className="space-y-6 max-w-7xl mx-auto">
            {!adminToken ? (
              /* Enterprise Sign-in Box */
              <div className="saas-card p-6 sm:p-8 bg-white max-w-md mx-auto space-y-5 rounded-xl border border-slate-200 shadow-xs">
                <div className="space-y-1 text-center">
                  <div className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-200 text-[#027A68] mx-auto flex items-center justify-center">
                    <Lock className="w-5 h-5" />
                  </div>
                  <h2 className="text-xl font-bold text-slate-900 pt-2">Auriic Staff Sign In</h2>
                  <p className="text-xs text-slate-500">
                    Candidate pipeline and ATS submission management
                  </p>
                </div>

                {adminLoginError && (
                  <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{adminLoginError}</span>
                  </div>
                )}

                <form onSubmit={handleAdminLogin} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                      Staff ID / Username
                    </label>
                    <input
                      type="text"
                      required
                      value={adminUsername}
                      onChange={(e) => setAdminUsername(e.target.value)}
                      placeholder="Param Parmar"
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:border-[#027A68] focus:ring-1 focus:ring-[#027A68]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                      Password
                    </label>
                    <input
                      type="password"
                      required
                      value={adminPassword}
                      onChange={(e) => setAdminPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:border-[#027A68] focus:ring-1 focus:ring-[#027A68]"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isAdminLoggingIn}
                    className="w-full py-2.5 px-4 bg-[#027A68] hover:bg-[#01584B] text-white font-semibold text-xs rounded-lg shadow-xs transition-colors disabled:opacity-50"
                  >
                    {isAdminLoggingIn ? 'Authenticating...' : 'Sign In to Portal'}
                  </button>
                </form>
              </div>
            ) : (
              /* Staff Leads Dashboard */
              <div className="space-y-6">
                {/* Header with Title & Export Actions */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                  <div>
                    <h2 className="text-xl font-bold text-slate-900">Candidate Leads Dashboard</h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Reviewing consenting candidates for Auriic career placements and resume counseling.
                    </p>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <button
                      onClick={() => loadAdminLeads(adminToken!)}
                      className="px-3 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-colors"
                      title="Refresh Leads"
                    >
                      <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
                      <span>Refresh</span>
                    </button>
                    <a
                      href={`${API_BASE}/api/admin/export/csv?token=${encodeURIComponent(adminToken || '')}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3.5 py-2 bg-[#027A68] hover:bg-[#01584B] text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-xs transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Export CSV</span>
                    </a>
                    <button
                      onClick={() => setAdminToken(null)}
                      className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Sign Out</span>
                    </button>
                  </div>
                </div>

                {/* Dashboard KPI Metric Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
                  <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
                    <span className="text-[11px] font-semibold uppercase text-slate-500 block">Total Candidates</span>
                    <span className="text-2xl font-bold text-slate-900">{adminMetrics.total}</span>
                    <span className="text-[11px] text-slate-400 block mt-0.5">Consented leads</span>
                  </div>

                  <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
                    <span className="text-[11px] font-semibold uppercase text-slate-500 block">Average ATS Score</span>
                    <span className="text-2xl font-bold text-[#027A68]">{adminMetrics.avgScore} <span className="text-xs font-normal text-slate-400">/100</span></span>
                    <span className="text-[11px] text-slate-400 block mt-0.5">Applicant average</span>
                  </div>

                  <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
                    <span className="text-[11px] font-semibold uppercase text-slate-500 block">Warm / Hot Leads</span>
                    <span className="text-2xl font-bold text-amber-600">{adminMetrics.warmOrHot}</span>
                    <span className="text-[11px] text-slate-400 block mt-0.5">High placement potential</span>
                  </div>

                  <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
                    <span className="text-[11px] font-semibold uppercase text-slate-500 block">New Pipeline Leads</span>
                    <span className="text-2xl font-bold text-blue-600">{adminMetrics.newCount}</span>
                    <span className="text-[11px] text-slate-400 block mt-0.5">Awaiting first contact</span>
                  </div>
                </div>

                {/* Filter & Search Toolbar */}
                <div className="bg-white p-3.5 rounded-xl border border-slate-200 flex flex-col sm:flex-row items-center gap-3">
                  <div className="relative flex-1 w-full">
                    <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                    <input
                      type="text"
                      value={adminSearch}
                      onChange={(e) => setAdminSearch(e.target.value)}
                      placeholder="Search candidates by name, email, phone, location, skills..."
                      className="w-full pl-9 pr-3.5 py-2 rounded-lg border border-slate-200 text-xs focus:border-[#027A68] focus:ring-1 focus:ring-[#027A68]"
                    />
                  </div>

                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <select
                      value={adminIndustryFilter}
                      onChange={(e) => setAdminIndustryFilter(e.target.value)}
                      className="px-3 py-2 border border-slate-200 rounded-lg text-xs bg-white text-slate-700"
                    >
                      <option value="all">All Industries</option>
                      <option value="it">IT & Software</option>
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
                      className="px-3 py-2 border border-slate-200 rounded-lg text-xs bg-white text-slate-700"
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

                {/* Responsive Leads Data Table */}
                <div className="saas-card bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 border-b border-slate-200 font-semibold text-slate-600">
                        <tr>
                          <th className="py-3 px-4">Candidate</th>
                          <th className="py-3 px-4">Phone / Location</th>
                          <th className="py-3 px-4">Industry</th>
                          <th className="py-3 px-4">ATS Score</th>
                          <th className="py-3 px-4">Pipeline Status</th>
                          <th className="py-3 px-4">Priority</th>
                          <th className="py-3 px-4 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {filteredLeads.length === 0 ? (
                          <tr>
                            <td colSpan={7} className="py-8 text-center text-slate-400">
                              No candidates match your current search and filter criteria.
                            </td>
                          </tr>
                        ) : (
                          filteredLeads.map((l) => (
                            <tr key={l.id} className="hover:bg-slate-50/60 transition-colors">
                              <td className="py-3 px-4">
                                <div className="flex items-center gap-2.5">
                                  <div className="w-7 h-7 rounded-full bg-slate-100 text-slate-700 font-bold flex items-center justify-center text-[10px] flex-shrink-0 border border-slate-200">
                                    {l.full_name ? l.full_name.charAt(0).toUpperCase() : 'C'}
                                  </div>
                                  <div>
                                    <span className="font-bold text-slate-900 block leading-tight">{l.full_name || 'Anonymous'}</span>
                                    <span className="text-[11px] text-slate-500">{l.email}</span>
                                  </div>
                                </div>
                              </td>
                              <td className="py-3 px-4 text-slate-600">
                                <span className="block">{l.phone || '—'}</span>
                                <span className="text-[11px] text-slate-400 truncate max-w-[160px] block">{l.location || '—'}</span>
                              </td>
                              <td className="py-3 px-4">
                                <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-slate-100 text-slate-700">
                                  {l.detected_industry || 'General'}
                                </span>
                              </td>
                              <td className="py-3 px-4">
                                <span className="font-mono font-bold text-slate-900">
                                  {l.ats_score ? Math.round(l.ats_score) : '—'}
                                </span>
                              </td>
                              <td className="py-3 px-4">
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                    l.lead_status === 'new'
                                      ? 'bg-blue-50 text-blue-700 border border-blue-200'
                                      : l.lead_status === 'contacted'
                                      ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                      : l.lead_status === 'qualified'
                                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                      : 'bg-slate-100 text-slate-600'
                                  }`}
                                >
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
                                      : 'bg-slate-100 text-slate-600'
                                  }`}
                                >
                                  {l.lead_score_category}
                                </span>
                              </td>
                              <td className="py-3 px-4 text-right">
                                <button
                                  onClick={() => viewLeadDetail(l.id)}
                                  className="px-2.5 py-1 text-xs font-semibold bg-white hover:bg-slate-100 text-slate-800 border border-slate-200 rounded-md transition-colors"
                                >
                                  Review
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Candidate Detail Modal / Slide-over */}
                {adminSelectedLead && (
                  <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5 border border-slate-200 shadow-xl">
                      <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                        <div>
                          <h3 className="text-lg font-bold text-slate-900">
                            {adminSelectedLead.lead.full_name}
                          </h3>
                          <p className="text-xs text-slate-500">{adminSelectedLead.lead.email}</p>
                        </div>
                        <button
                          onClick={() => setAdminSelectedLead(null)}
                          className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                        <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200/80">
                          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Phone</span>
                          <span className="font-medium text-slate-900">{adminSelectedLead.lead.phone || 'Not provided'}</span>
                        </div>
                        <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200/80">
                          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Location</span>
                          <span className="font-medium text-slate-900">{adminSelectedLead.lead.location || 'Not provided'}</span>
                        </div>
                        <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200/80">
                          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Lead Priority</span>
                          <span className="font-bold uppercase text-[#027A68]">
                            {adminSelectedLead.lead.lead_score_category}
                          </span>
                        </div>
                      </div>

                      {adminSelectedLead.lead.lead_score_reason && (
                        <div className="p-3 bg-amber-50/60 border border-amber-200/80 rounded-lg text-xs text-amber-900">
                          <strong>Recruiter Scoring Rationale:</strong> {adminSelectedLead.lead.lead_score_reason}
                        </div>
                      )}

                      {/* Submission History & Direct Resume Download */}
                      <div className="space-y-2.5">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Submission History</h4>
                        {adminSelectedLead.submissions.map((sub: any, idx: number) => (
                          <div key={idx} className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between text-xs">
                            <div>
                              <span className="font-bold text-slate-900">Mode {sub.mode} • Score: {Math.round(sub.ats_score)}/100</span>
                              <span className="text-slate-500 block text-[11px]">{sub.created_at}</span>
                            </div>
                            {sub.download_url && (
                              <a
                                href={sub.download_url}
                                target="_blank"
                                rel="noreferrer"
                                className="px-3 py-1.5 bg-[#027A68] hover:bg-[#01584B] text-white font-semibold rounded-md flex items-center gap-1.5 transition-colors"
                              >
                                <Download className="w-3.5 h-3.5" />
                                <span>Download Resume File</span>
                              </a>
                            )}
                          </div>
                        ))}
                      </div>

                      {/* Pipeline Status & Staff Notes */}
                      <div className="space-y-3 pt-3 border-t border-slate-200">
                        <div>
                          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">Update Status</label>
                          <select
                            value={adminNewStatus}
                            onChange={(e) => setAdminNewStatus(e.target.value)}
                            className="w-full p-2 border border-slate-300 rounded-lg text-xs bg-white text-slate-800"
                          >
                            <option value="new">New</option>
                            <option value="contacted">Contacted</option>
                            <option value="qualified">Qualified</option>
                            <option value="converted">Converted</option>
                            <option value="not_interested">Not Interested</option>
                          </select>
                        </div>

                        <div>
                          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">Recruiter Internal Notes</label>
                          <textarea
                            rows={3}
                            value={adminNotes}
                            onChange={(e) => setAdminNotes(e.target.value)}
                            placeholder="Add placement notes, visa status, or candidate callback details..."
                            className="w-full p-2 border border-slate-300 rounded-lg text-xs"
                          />
                        </div>

                        <div className="flex items-center justify-between pt-2">
                          <button
                            type="button"
                            onClick={() => deleteLeadAdmin(adminSelectedLead.lead.id)}
                            className="px-3 py-2 text-rose-600 hover:bg-rose-50 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            <span>Delete Lead & Scrub Files</span>
                          </button>

                          <button
                            type="button"
                            onClick={() => updateLeadStatus(adminSelectedLead.lead.id)}
                            className="px-4 py-2 bg-[#027A68] hover:bg-[#01584B] text-white rounded-lg text-xs font-semibold transition-colors"
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

      {/* Application Footer */}
      <footer className="bg-white border-t border-slate-200 mt-16 py-8 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-4 text-center">
          {/* Data Storage Consent Notice */}
          <div className="max-w-3xl mx-auto text-[11px] sm:text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-200/80">
            <strong>Data Storage Notice:</strong> By submitting your resume with affirmative consent, you permit Auriic Services to securely store contact details and resume files for placement services and career counseling.{' '}
            <button
              onClick={() => setActiveTab('privacy')}
              className="text-[#027A68] font-semibold underline hover:text-[#01584B]"
            >
              Review Privacy & Auto-Purge Terms.
            </button>
          </div>

          <p className="font-semibold text-slate-700">
            © 2026 Auriic Services. All rights reserved.
          </p>
          <p className="text-[11px] text-slate-500 max-w-2xl mx-auto leading-relaxed">
            Auriic Services provides personalized career coaching, resume optimization, and US staffing for students, OPT/STEM OPT candidates, H-1B holders, and experienced professionals across IT and non-IT sectors.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 text-[#027A68] font-semibold text-xs pt-1">
            <button onClick={() => { setActiveTab('checker'); window.location.hash = ''; }} className="hover:underline">
              Resume Diagnostic
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
            <button onClick={() => { setActiveTab('admin'); window.location.hash = '#staff'; }} className="hover:underline">
              Staff Portal
            </button>
            <span>•</span>
            <a href="https://auriic.co" target="_blank" rel="noopener noreferrer" className="hover:underline">
              auriic.co
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
