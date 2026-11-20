import os
import io
import fitz # PyMuPDF
import docx
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_resumes")
os.makedirs(SAMPLE_DIR, exist_ok=True)

# 20 Resumes Data across 8 Industries + Bad Cases
RESUMES = {
    # 1. IT - Senior Software Engineer (Clean, Good)
    "01_it_senior_software_engineer.txt": """Alex Rivera
San Francisco, CA | (555) 234-5678 | alex.rivera@email.com | linkedin.com/in/alexrivera-dev

PROFESSIONAL SUMMARY
Senior Software Engineer with 8+ years of experience designing, architecting, and scaling distributed cloud microservices in Python, Go, and React. Proven track record optimizing high-throughput APIs serving 10M+ daily active users.

TECHNICAL SKILLS
Languages: Python, Go, TypeScript, JavaScript, SQL
Frameworks & Libraries: React, Node.js, FastAPI, Next.js, Redux
Cloud & Infrastructure: AWS, Docker, Kubernetes, Terraform, CI/CD, Linux
Databases: PostgreSQL, Redis, MongoDB

WORK EXPERIENCE
Senior Software Engineer | CloudScale Inc. | 2021 - Present
- Architected and deployed microservices handling 25,000 requests/second, reducing system latency by 35%.
- Spearheaded migration from monolithic architecture to Kubernetes on AWS, cutting monthly infrastructure cloud costs by $140,000.
- Mentored a distributed team of 8 junior and mid-level engineers, enforcing strict CI/CD and TDD testing standards.
- Designed real-time event streaming pipeline using Redis and Kafka, boosting data sync reliability to 99.99%.

Software Engineer | DevTech Solutions | 2017 - 2021
- Developed full-stack web applications using React and Python FastAPI, delivering 14 major customer-facing features on schedule.
- Optimized slow PostgreSQL database queries and table indices, accelerating dashboard load times by 48%.
- Automated end-to-end regression testing suites, decreasing production release defect rates by 22%.

EDUCATION
Bachelor of Science in Computer Science | University of California, Berkeley | 2017

CERTIFICATIONS
AWS Certified Solutions Architect - Associate
""",

    # 2. IT - Junior DevOps Engineer
    "02_it_junior_devops.txt": """Samantha Chen
Austin, TX | (555) 345-6789 | samantha.chen@email.com | linkedin.com/in/samanthachen-ops

PROFESSIONAL SUMMARY
DevOps & Cloud Engineer with 2 years of hands-on experience automating CI/CD pipelines, containerizing workloads, and managing cloud environments on AWS.

TECHNICAL SKILLS
Cloud: AWS, GCP, Azure
Tools: Docker, Kubernetes, Terraform, Jenkins, GitHub Actions, Ansible
Scripting & OS: Python, Bash, Shell, Linux, Git

WORK EXPERIENCE
Junior DevOps Engineer | NexaCorp Systems | 2023 - Present
- Configured automated GitHub Actions workflows for 12 microservices, reducing deployment cycle time by 40%.
- Provisioned repeatable cloud infrastructure across staging and production using Terraform on AWS.
- Monitored cluster health using Prometheus and Grafana, identifying bottlenecks and resolving 95% of alerts within SLA.

Cloud Support Specialist | HostTech LLC | 2022 - 2023
- Resolved 250+ enterprise customer tickets regarding Linux server configurations and SSL certificates.
- Automated daily backup verification routines using Python scripts, saving 5 hours of manual work weekly.

EDUCATION
Bachelor of Science in Information Technology | University of Texas at Austin | 2022
""",

    # 3. IT - Bad Case: Missing Headings & No Metrics
    "03_it_bad_unstructured.txt": """David Miller
david.m@email.com

I have worked as a programmer for a few years.
Did some work in React and JavaScript.
Responsible for fixing bugs in the web application.
Helped the team when needed.
Worked at Software Co from 2021 to 2023.
Went to state college.
""",

    # 4. Healthcare - Registered Nurse (ICU, BSN)
    "04_healthcare_registered_nurse.txt": """Elena Rostova, BSN, RN
Chicago, IL | (555) 456-7890 | elena.rostova.rn@email.com | linkedin.com/in/elenarostova-rn

PROFESSIONAL SUMMARY
Compassionate, board-certified Critical Care Registered Nurse (RN) with 6+ years of ICU and emergency department experience. Dedicated to evidence-based patient advocacy, acute trauma triage, and clinical excellence under pressure.

CLINICAL SKILLS & LICENSES
Licensure: Registered Nurse (RN), Illinois License #RN-998877
Certifications: BLS, ACLS, CPR, PALS, CCRN
Clinical Competencies: Critical Care Nursing, Patient Triage, IV Therapy, Medication Administration, Ventilator Management, Arterial Lines, Phlebotomy, Wound Care, Infection Control
Systems: Epic EHR, Cerner, HIPAA Compliance

WORK EXPERIENCE
Critical Care Registered Nurse (ICU) | Chicago General Hospital | 2020 - Present
- Administered comprehensive acute care for 12-bed Intensive Care Unit patients with 1:1 and 1:2 nurse-to-patient acuity ratios.
- Executed continuous cardiac telemetry, titrating vasoactive infusions (Levophed, Propofol) with zero medication errors across 2,400 clinical hours.
- Championed unit-wide Central Line-Associated Bloodstream Infection (CLABSI) reduction initiative, lowering infection rates by 62%.
- Facilitated daily multidisciplinary rounds with attending physicians, intensivists, and respiratory therapists to optimize patient care plans.

Staff Nurse - Medical/Surgical | Mercy Memorial Hospital | 2018 - 2020
- Provided post-operative recovery care, telemetry monitoring, and pain management for up to 6 acute medical patients per shift.
- Documented vital signs, physician orders, and treatment responses accurately in Epic EHR in full compliance with HIPAA standards.

EDUCATION
Bachelor of Science in Nursing (BSN) | University of Illinois at Chicago | 2018
Summa Cum Laude, GPA 3.92
""",

    # 5. Healthcare - Clinical Research Associate
    "05_healthcare_clinical_research.txt": """Marcus Brody
Boston, MA | (555) 567-8901 | marcus.brody@email.com | linkedin.com/in/marcusbrody-cra

PROFESSIONAL SUMMARY
Detail-oriented Clinical Research Associate with 5+ years managing Phase II and Phase III oncology clinical trials in accordance with FDA regulations, ICH-GCP guidelines, and institutional review boards.

CORE COMPETENCIES
Clinical Operations, GCP Compliance, FDA Regulations, Electronic Data Capture (EDC), Protocol Deviation Tracking, Informed Consent Verification, Site Monitoring, Patient Recruitment, Triage, Clinical Documentation

WORK EXPERIENCE
Senior Clinical Research Coordinator | Dana-Farber Cancer Institute | 2021 - Present
- Monitored 8 active Phase III clinical oncology trials across 3 trial sites, enrolling 185 patient participants.
- Audited trial site regulatory binders, achieving 100% inspection readiness and zero major FDA audit findings.
- Streamlined patient screening workflows, accelerating trial participant accrual timelines by 28%.

Clinical Research Assistant | Boston Biotech Lab | 2019 - 2021
- Maintained EDC databases for Phase II pharmacokinetics studies, resolving 450+ data queries within strict 24-hour windows.
- Conducted informed consent reviews and coordinated biospecimen collection logistics.

EDUCATION
Master of Science in Clinical Research Management | Boston University | 2019
Bachelor of Science in Biology | University of Massachusetts | 2017
""",

    # 6. Healthcare - Bad Case: Tables & PII
    "06_healthcare_bad_pii.txt": """Sarah Jenkins
DOB: 04/15/1982 | SSN: 123-45-6789 | Passport No: A12345678
Miami, FL | (555) 678-9012 | sarah.j@email.com

SUMMARY
Nurse looking for a job in a clinic or hospital.

EXPERIENCE
Nurse at Local Clinic
Did nursing tasks and assisted doctors.
Responsible for checking in patients and giving vaccines.
Worked there 2020 to 2023.
""",

    # 7. Banking & Finance - Senior Financial Analyst (CPA)
    "07_finance_senior_analyst.txt": """Jonathan Pierce, CPA
New York, NY | (555) 789-0123 | j.pierce.cpa@email.com | linkedin.com/in/jonathanpierce-finance

PROFESSIONAL SUMMARY
Certified Public Accountant (CPA) and Senior Financial Analyst with 7+ years of experience leading corporate budgeting, FP&A, discounted cash flow (DCF) modeling, and executive financial reporting for Fortune 500 financial institutions.

CORE COMPETENCIES
Financial Modeling (DCF, LBO, 3-Statement), FP&A, GAAP, Financial Statement Analysis, Variance Analysis, Budgeting & Forecasting, P&L Management, Sarbanes-Oxley (SOX), Internal Controls, Excel (Macros, VBA, PowerQuery), SAP Financials, QuickBooks, SQL

WORK EXPERIENCE
Senior Financial Analyst | Goldman Sachs Group | 2021 - Present
- Formulated annual operating expense budget of $85M across 4 enterprise business divisions with 98.5% forecast accuracy.
- Built complex dynamic financial forecast models in Excel/VBA, identifying $4.2M in annual recurring operational savings.
- Prepared monthly executive board financial packages, synthesizing variance analyses and capital expenditure ROI calculations.
- Ensured 100% compliance with GAAP, SOX Section 404, and SEC reporting guidelines during external Big 4 audits.

Financial Analyst | Morgan Stanley | 2018 - 2021
- Analyzed quarterly financial performance for $350M asset portfolio, highlighting cash burn deviations and revenue trends.
- Automated monthly revenue reconciliation processes using SQL and Excel macros, reducing reporting turnaround by 3 days.

EDUCATION
Master of Business Administration (MBA) in Finance | NYU Stern School of Business | 2018
Bachelor of Science in Accounting | Fordham University | 2016

CERTIFICATIONS
Certified Public Accountant (CPA) - New York State License
""",

    # 8. Banking & Finance - Corporate Accountant
    "08_finance_accountant.txt": """Rachel Sterling
Charlotte, NC | (555) 890-1234 | rachel.sterling@email.com | linkedin.com/in/rachelsterling-acc

PROFESSIONAL SUMMARY
Corporate Staff Accountant with 4 years of experience managing full-cycle general ledger accounting, monthly balance sheet reconciliations, and accounts payable/receivable operations.

TECHNICAL SKILLS
Accounting & Software: General Ledger, GAAP, Accounts Payable (AP), Accounts Receivable (AR), Bank Reconciliation, QuickBooks, NetSuite, Excel (Pivot Tables, VLOOKUP)

WORK EXPERIENCE
Staff Accountant | Bank of America | 2022 - Present
- Reconciled 45 balance sheet accounts monthly, resolving reconciling items exceeding $10,000 within 48 hours.
- Processed semi-monthly payroll allocations and journal entries for 600+ regional corporate employees.
- Assisted internal audit team with SOX testing documentation, ensuring full compliance with internal controls.

Junior Accountant | Piedmont Financial Services | 2020 - 2022
- Managed accounts payable pipeline processing 300+ vendor invoices weekly totaling $1.5M monthly.
- Prepared 1099 tax distribution schedules and supported year-end corporate tax filings.

EDUCATION
Bachelor of Science in Accounting | University of North Carolina at Charlotte | 2020
""",

    # 9. Manufacturing - Plant Operations & Lean Six Sigma
    "09_manufacturing_plant_manager.txt": """Robert Kowalski
Detroit, MI | (555) 901-2345 | r.kowalski@email.com | linkedin.com/in/robertkowalski-mfg

PROFESSIONAL SUMMARY
Results-driven Plant Operations Manager and Lean Six Sigma Black Belt with 10+ years directing automotive component manufacturing facilities. Proven history eliminating scrap waste, improving OEE by 28%, and driving zero-incident OSHA safety cultures.

CORE COMPETENCIES
Lean Manufacturing, Six Sigma Black Belt, Kaizen, 5S Methodology, Root Cause Analysis (RCA), Overall Equipment Effectiveness (OEE), CNC Machining, PLC Automation, Production Scheduling, Quality Control (ISO 9001), OSHA Compliance, Preventive Maintenance, P&L Responsibility

WORK EXPERIENCE
Plant Operations Manager | Magna International | 2019 - Present
- Directed operations across a 220,000 sq. ft. Tier-1 automotive metal stamping facility overseeing 180 union operators and 8 supervisors.
- Spearheaded Lean Six Sigma continuous improvement projects, reducing material scrap by 34% and saving $820,000 annually.
- Increased plant-wide Overall Equipment Effectiveness (OEE) from 64% to 82% via standardized changeover procedures (SMED).
- Achieved 1.2 million consecutive man-hours without an OSHA recordable incident, earning corporate safety recognition.

Production Supervisor | American Axle & Manufacturing | 2015 - 2019
- Supervised daily shifts of 45 CNC machining operators, consistently meeting or exceeding daily build targets by 105%.
- Implemented preventative maintenance routines that minimized unexpected equipment downtime by 24%.

EDUCATION
Bachelor of Science in Mechanical Engineering | Michigan State University | 2015

CERTIFICATIONS
Lean Six Sigma Black Belt (LSSBB) - ASQ Certified
OSHA 30-Hour General Industry Safety Certification
""",

    # 10. Manufacturing - CNC Machinist & Quality Inspector
    "10_manufacturing_machinist.txt": """Carlos Mendez
Cleveland, OH | (555) 012-3456 | carlos.mendez.cnc@email.com | linkedin.com/in/carlosmendez-cnc

PROFESSIONAL SUMMARY
Skilled CNC Machinist and Quality Inspector with 5 years of precision manufacturing experience operating 3-axis and 5-axis CNC mills and lathes to tight aerospace tolerances (+/- 0.0002 inches).

SKILLS & PROFICIENCIES
CNC Programming (G-Code, M-Code), 5-Axis Milling, Lathes, Haas, Fanuc, Mastercam, Blueprint Reading, GD&T, CMM Inspection, Calipers, Micrometers, ISO 9001 Standards, OSHA Safety

WORK EXPERIENCE
CNC Machinist & Quality Inspector | Precision Aerospace Machining | 2021 - Present
- Programmed, set up, and operated 4 Haas 5-axis CNC milling machines producing titanium aerospace turbine components.
- Performed first-article quality inspections using Coordinate Measuring Machines (CMM) and optical comparators with zero part rejections across 18 consecutive months.
- Optimized tool path feeds and speeds, shortening production cycle duration by 15% per batch.

Machinist Apprentice | Ohio Precision Tooling | 2019 - 2021
- Read complex geometric dimensioning and tolerancing (GD&T) blueprints to fabricate custom tooling jigs.
- Performed daily preventative fluid maintenance and equipment calibration on industrial machinery.

EDUCATION
Associate of Applied Science in Precision Machining Technology | Cuyahoga Community College | 2019
""",

    # 11. Logistics & Supply Chain - Global Supply Chain Manager
    "11_logistics_supply_chain_manager.txt": """Vikram Patel
Atlanta, GA | (555) 123-9876 | v.patel@email.com | linkedin.com/in/vikrampatel-supplychain

PROFESSIONAL SUMMARY
Strategic Supply Chain and Logistics Director with 9+ years optimizing end-to-end global supply chain networks, procurement, and warehouse operations across North America and Asia-Pacific.

CORE COMPETENCIES
Supply Chain Optimization, Warehouse Management Systems (WMS), Transportation Management Systems (TMS), ERP (SAP S/4HANA, Oracle), Global Freight Forwarding, 3PL Management, Demand Forecasting, Inventory Optimization, Procurement, Vendor Contract Negotiation, Customs Compliance

WORK EXPERIENCE
Senior Supply Chain Manager | Home Depot Supply Chain | 2020 - Present
- Managed multi-site distribution logistics managing $180M in annual inventory across 4 regional fulfillment hubs.
- Renegotiated contracts with ocean and intermodal 3PL carriers, securing $3.5M in annual freight savings while maintaining 98.7% on-time delivery rates.
- Implemented Manhattan Associates WMS across 2 facilities, increasing warehouse pick-and-pack efficiency by 32%.
- Reduced carrying costs and safety stock inventory by 18% utilizing predictive demand planning algorithms.

Logistics Coordinator | Expeditors International | 2016 - 2020
- Coordinated international air and ocean import shipments, ensuring compliance with US Customs Border Protection (CBP).
- Resolved customs brokerage exceptions and logistics delays, cutting port dwell times by 2.5 days on average.

EDUCATION
Master of Science in Supply Chain Management | Georgia Institute of Technology | 2016
Bachelor of Business Administration | University of Georgia | 2014

CERTIFICATIONS
Certified Supply Chain Professional (CSCP) - APICS / ASCM
""",

    # 12. Logistics - Warehouse Operations Supervisor
    "12_logistics_warehouse_supervisor.txt": """Brian O'Connor
Memphis, TN | (555) 234-8765 | brian.oconnor@email.com | linkedin.com/in/brianoconnor-logistics

PROFESSIONAL SUMMARY
Action-oriented Warehouse Operations Supervisor with 6 years experience directing high-volume e-commerce fulfillment centers.

TECHNICAL SKILLS
Warehouse Operations, Inventory Control, WMS (Manhattan, RedPrairie), Cycle Counting, Forklift Certified (OSHA), Fleet Coordination, Dispatch, Inbound/Outbound Logistics, Cross-Docking, Safety Compliance

WORK EXPERIENCE
Warehouse Shift Supervisor | FedEx Ground Hub | 2021 - Present
- Supervised shift of 55 warehouse package handlers and forklift operators processing 80,000 parcels per shift.
- Improved package sorting throughput by 19% through ergonomic workstation realignment and load leveling.
- Maintained 99.8% inventory order fulfillment accuracy and enforced zero-tolerance OSHA forklift safety rules.

Lead Inventory Specialist | XPO Logistics | 2018 - 2021
- Performed daily cycle counting and root-cause analysis on inventory discrepancies, maintaining 99.4% record accuracy.
- Managed receiving docks and cross-docking operations for 40 tractor-trailer loads daily.

EDUCATION
Associate Degree in Business Administration | Southwest Tennessee Community College | 2018
""",

    # 13. Construction & Civil - Civil Project Engineer (PE)
    "13_construction_civil_engineer.txt": """Daniel Vance, PE
Dallas, TX | (555) 345-7654 | daniel.vance.pe@email.com | linkedin.com/in/danielvance-pe

PROFESSIONAL SUMMARY
Licensed Professional Engineer (PE) and Civil Project Engineer with 8+ years experience leading commercial site development, municipal water infrastructure, and structural concrete construction projects valued up to $65M.

CORE COMPETENCIES
Civil Engineering, Structural Design, AutoCAD Civil 3D, Revit, BIM, Project Scheduling (Primavera P6, Procore), Cost Estimation, OSHA 30, Blueprints Reading, Site Supervision, Geotechnical Analysis, Stormwater Pollution Prevention (SWPPP), Subcontractor Management

WORK EXPERIENCE
Senior Civil Project Engineer | Turner Construction Company | 2020 - Present
- Engineered and managed civil site works for a $52M multi-story mixed-use commercial development delivered 3 weeks ahead of schedule.
- Reviewed and stamped structural calculation sheets, grading plans, and drainage utility designs in full adherence to municipal building codes.
- Oversaw 14 site subcontractors, resolving 180+ Requests for Information (RFIs) and architectural submittals without change-order cost creep.
- Enforced strict site-wide OSHA safety regulations, logging 450 injury-free jobsite workdays.

Project Engineer | Balfour Beatty US | 2016 - 2020
- Coordinated reinforced concrete pouring inspections and grading earthwork operations for highway interchange expansion project.
- Prepared accurate material quantity take-offs using Civil 3D, keeping concrete and asphalt variance under 2.5%.

EDUCATION
Bachelor of Science in Civil Engineering | Texas A&M University | 2016
Magna Cum Laude

CERTIFICATIONS & LICENSES
Professional Engineer (PE) - Texas Board of Professional Engineers, License #PE-134592
OSHA 30-Hour Construction Safety Certification
""",

    # 14. Construction - Assistant Superintendent
    "14_construction_superintendent.txt": """Kevin Martinez
Phoenix, AZ | (555) 456-6543 | kevin.martinez@email.com | linkedin.com/in/kevinmartinez-construct

PROFESSIONAL SUMMARY
Proactive Assistant Construction Superintendent with 5 years experience on commercial construction jobsites.

TECHNICAL SKILLS
Jobsite Supervision, Subcontractor Coordination, Procore, Blueprint Reading, Quality Inspection, Scheduling, Safety Audits (OSHA), MEP Coordination, Daily Logs, Material Deliveries

WORK EXPERIENCE
Assistant Superintendent | Sundt Construction | 2021 - Present
- Directed daily on-site trade coordination for electrical, plumbing, and drywall contractors on a 140,000 sq. ft. healthcare facility.
- Conducted daily morning safety tool-box talks and job hazard analyses (JHAs) for 60+ on-site craft workers.
- Managed material deliveries and crane staging schedules, eliminating contractor trade stacking delays.

Field Engineer | Hensel Phelps | 2019 - 2021
- Performed quality assurance inspections for rebar placement and concrete slab moisture tests prior to pouring.
- Maintained detailed daily progress photos and deficiency tracking punch lists in Procore.

EDUCATION
Bachelor of Science in Construction Management | Arizona State University | 2019
""",

    # 15. Energy & Utilities - Power Systems Electrical Engineer
    "15_energy_electrical_engineer.txt": """Amina Al-Mansoor
Houston, TX | (555) 567-5432 | amina.almansoor@email.com | linkedin.com/in/amina-almansoor-energy

PROFESSIONAL SUMMARY
Senior Power Systems Electrical Engineer with 7+ years experience designing high-voltage (HV) substations, electrical power distribution grids, and SCADA protection systems for renewable and utility operators.

TECHNICAL SKILLS
Power Systems Design, High Voltage Substations (69kV - 345kV), SCADA, ETAP, Relay Protection & Coordination (SEL, GE), National Electrical Code (NEC), IEEE Standards, Renewable Energy Grid Interconnection, PLC Automation

WORK EXPERIENCE
Substation Electrical Engineer | CenterPoint Energy | 2020 - Present
- Designed electrical single-line diagrams (SLD) and physical layouts for three new 138kV greenfield transmission substations.
- Programmed and validated SEL microprocessor protection relays via ETAP short-circuit and arc-flash hazard studies.
- Commissioned SCADA remote terminal units (RTU) over DNP3 protocols, enhancing substation real-time monitoring uptime to 99.98%.
- Supervised field testing of high-voltage power transformers and gas-insulated switchgear (GIS).

Electrical Systems Engineer | NextEra Energy Resources | 2017 - 2020
- Modeled utility-scale solar photovoltaic (PV) interconnection studies for 250MW solar farm projects connected to ERCOT grid.
- Optimized collector system cable sizing, reducing transmission line electrical losses by 3.2%.

EDUCATION
Master of Science in Electrical Engineering (Power Systems) | University of Houston | 2017
Bachelor of Science in Electrical Engineering | Texas Tech University | 2015

CERTIFICATIONS
Engineer In Training (EIT) - Texas Board of Professional Engineers
""",

    # 16. Energy - Renewable Solar Project Manager
    "16_energy_solar_manager.txt": """Jason Briggs
Denver, CO | (555) 678-4321 | jason.briggs@email.com | linkedin.com/in/jasonbriggs-solar

PROFESSIONAL SUMMARY
Renewable Energy Project Manager with 5 years experience directing commercial and utility-scale solar photovoltaic (PV) and battery energy storage systems (BESS) installation projects.

TECHNICAL SKILLS
Solar PV, Battery Energy Storage (BESS), EPC Contracts, Interconnection Applications, Substation Coordination, Permitting, PVSyst, Project Scheduling, Quality Control, Vendor Management

WORK EXPERIENCE
Solar Project Manager | Invenergy LLC | 2022 - Present
- Directed EPC construction execution for 80MW solar PV farm from civil groundbreaking through commercial operation date (COD).
- Managed project budgets of $65M, delivering project 4% under financial contingency allowances.
- Coordinated with local utility authorities and environmental agencies to secure necessary zoning and interconnection approvals.

Project Coordinator | SunPower Corporation | 2019 - 2022
- Tracked component procurement milestones for Tier-1 solar modules and central inverters across 14 commercial rooftop installations.
- Managed subcontractor commissioning punch lists to expedite mechanical completion.

EDUCATION
Bachelor of Science in Energy Management | Colorado School of Mines | 2019
""",

    # 17. Retail - Multi-Unit Store General Manager
    "17_retail_store_general_manager.txt": """Claire Sullivan
Seattle, WA | (555) 789-3210 | claire.sullivan@email.com | linkedin.com/in/clairesullivan-retail

PROFESSIONAL SUMMARY
Accomplished Retail Store General Manager with 9+ years experience driving revenue growth, customer retention, and merchandising excellence for multi-million-dollar retail stores.

CORE COMPETENCIES
Store Operations, P&L Accountability, Visual Merchandising, Point of Sale (POS), Inventory Management, Staff Recruitment & Training, Loss Prevention, Sales Forecasting, Customer Experience (CX), Omnichannel Fulfillment, KPI Optimization

WORK EXPERIENCE
Store General Manager | Nordstrom Flagship | 2019 - Present
- Managed total P&L operations for flagship retail store generating $24M in annual gross sales across 6 merchandise departments.
- Led and mentored a high-performing retail team of 4 department managers and 65 sales associates, decreasing annual employee turnover by 26%.
- Achieved highest regional sales growth (+14.5% year-over-year) by optimizing floor merchandise layouts and staff cross-selling training.
- Reduced store inventory shrinkage from 1.8% to 0.7% via enhanced inventory audits and loss-prevention protocols.

Assistant Store Manager | Target Corporation | 2015 - 2019
- Supervised floor operations, omnichannel ship-from-store fulfillment, and customer service desks.
- Scheduled weekly labor hours within a 98% payroll budget efficiency target.

EDUCATION
Bachelor of Arts in Business Administration & Marketing | University of Washington | 2015
""",

    # 18. Retail - E-Commerce Buyer & Merchandiser
    "18_retail_ecommerce_buyer.txt": """Morgan Hayes
Los Angeles, CA | (555) 890-2109 | morgan.hayes@email.com | linkedin.com/in/morganhayes-buyer

PROFESSIONAL SUMMARY
Data-driven E-Commerce Merchandiser and Apparel Buyer with 5 years experience curating high-performing product catalogs, managing vendor relationships, and driving gross margin expansion.

TECHNICAL SKILLS
Assortment Planning, Vendor Negotiation, Shopify Plus, Google Analytics, Retail Math, Inventory Allocation, Gross Margin Return on Investment (GMROI), Trend Forecasting, SKU Rationalization

WORK EXPERIENCE
E-Commerce Merchandiser & Buyer | Revolve Clothing | 2021 - Present
- Managed $8M open-to-buy (OTB) budget for contemporary women's apparel categories, driving 22% category sales growth.
- Analyzed website funnel metrics in Google Analytics to optimize product page sorting, boosting checkout conversion rates by 1.8%.
- Negotiated vendor terms with 40+ domestic and international brands, expanding average product margin by 320 basis points.

Assistant Buyer | Macy's Merchandising Group | 2019 - 2021
- Prepared weekly sales, inventory, and markdown reports, identifying underperforming SKUs and recommending promotional strategies.
- Coordinated sample intake and product photography styling workflows for seasonal digital catalog launches.

EDUCATION
Bachelor of Science in Merchandising Management | Fashion Institute of Design & Merchandising (FIDM) | 2019
""",

    # 19. Bad Case: Scanned Image PDF (Will generate via ReportLab/canvas with image only)
    # Handled specially in generation loop

    # 20. Bad Case: Extreme Multi-column layout with embedded tables
    "20_bad_multicolumn_tables.txt": """Emily Watson | emily.w@email.com | (555) 999-0000
COLUMN 1 (Left Margin)          COLUMN 2 (Right Margin)
Languages: Java, C++            Work: Company A, 2022
Tools: Git, Linux               Job: Built websites
Frameworks: Spring              Tasks: Managed servers
Projects: None                  School: College of Tech, 2021
Table 1: Skill | Rating | Years
Java   | 5/5    | 2
C++    | 4/5    | 1
"""
}

def generate_all_sample_resumes():
    print("Generating sample resumes across 8 industries...")
    # Write text files
    for filename, text_content in RESUMES.items():
        filepath = os.path.join(SAMPLE_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text_content.strip())

    # Generate a few DOCX files
    doc_samples = [
        ("01_it_senior_software_engineer.docx", RESUMES["01_it_senior_software_engineer.txt"]),
        ("04_healthcare_registered_nurse.docx", RESUMES["04_healthcare_registered_nurse.txt"]),
        ("07_finance_senior_analyst.docx", RESUMES["07_finance_senior_analyst.txt"]),
        ("09_manufacturing_plant_manager.docx", RESUMES["09_manufacturing_plant_manager.txt"]),
    ]
    for doc_name, content in doc_samples:
        doc_path = os.path.join(SAMPLE_DIR, doc_name)
        d = docx.Document()
        for line in content.split("\n"):
            if line.strip():
                d.add_paragraph(line.strip())
        d.save(doc_path)

    # Generate PDF files using ReportLab & PyMuPDF
    pdf_samples = [
        ("01_it_senior_software_engineer.pdf", RESUMES["01_it_senior_software_engineer.txt"]),
        ("04_healthcare_registered_nurse.pdf", RESUMES["04_healthcare_registered_nurse.txt"]),
        ("11_logistics_supply_chain_manager.pdf", RESUMES["11_logistics_supply_chain_manager.txt"]),
        ("13_construction_civil_engineer.pdf", RESUMES["13_construction_civil_engineer.txt"]),
    ]
    for pdf_name, content in pdf_samples:
        pdf_path = os.path.join(SAMPLE_DIR, pdf_name)
        c = canvas.Canvas(pdf_path, pagesize=letter)
        y = 750
        for line in content.split("\n"):
            if y < 50:
                c.showPage()
                y = 750
            if line.strip():
                c.setFont("Helvetica", 9)
                c.drawString(40, y, line.strip()[:95])
            y -= 14
        c.save()

    # Generate Bad Scanned Image PDF (has images but NO text layer)
    scanned_pdf_path = os.path.join(SAMPLE_DIR, "19_bad_scanned_image_no_text.pdf")
    doc_scan = fitz.open()
    page = doc_scan.new_page(width=595, height=842)
    # Draw a colored rectangle and shape simulating an image with no text
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(50, 50, 545, 792))
    shape.finish(color=(0.8, 0.8, 0.8), fill=(0.95, 0.95, 0.95))
    shape.commit()
    doc_scan.save(scanned_pdf_path)
    doc_scan.close()

    print(f"Sample resumes generated successfully in: {SAMPLE_DIR}")

if __name__ == "__main__":
    generate_all_sample_resumes()
