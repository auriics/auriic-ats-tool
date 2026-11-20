import io
from typing import Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable

def generate_ats_pdf_report(score_report: Dict[str, Any], candidate_name: str = "Candidate") -> bytes:
    """Generate professional, branded ATS Diagnostic PDF Report using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    
    # Custom Brand Colors
    brand_emerald = colors.HexColor("#027A68")
    brand_gold = colors.HexColor("#C89C36")
    brand_dark = colors.HexColor("#1A1A1A")
    brand_gray = colors.HexColor("#555555")
    brand_light_bg = colors.HexColor("#F0F4F3")

    title_style = ParagraphStyle(
        "BrandTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=brand_emerald,
    )

    subtitle_style = ParagraphStyle(
        "BrandSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=brand_gray,
    )

    score_num_style = ParagraphStyle(
        "ScoreNumber",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=36,
        leading=40,
        textColor=brand_emerald,
        alignment=1, # Center
    )

    score_label_style = ParagraphStyle(
        "ScoreLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=brand_gold,
        alignment=1, # Center
    )

    h2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=brand_dark,
        spaceBefore=10,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "BodyText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=brand_dark,
    )

    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Italic"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=brand_gray,
    )

    story = []

    # 1. Header with Auriic Branding
    story.append(Paragraph("AURIIC SERVICES", title_style))
    story.append(Paragraph("Free ATS Resume Compatibility & Optimization Diagnostic", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=brand_emerald, spaceAfter=15))

    # 2. Executive Score Card
    mode_title = "General ATS Health Diagnostic (Mode A)" if score_report.get("mode") == "A" else "Target Job Description Alignment (Mode B)"
    score_val = score_report.get("overall_score", 0.0)
    score_label = score_report.get("label", "Needs Work")
    scoring_ver = score_report.get("scoring_version", "1.0.0")

    card_data = [
        [
            Paragraph(f"<b>Candidate:</b> {candidate_name}<br/><b>Evaluation:</b> {mode_title}<br/><b>Scoring Engine Version:</b> v{scoring_ver}", body_style),
            Paragraph(f"{int(score_val)}<font size=16>/100</font>", score_num_style),
        ],
        [
            "",
            Paragraph(f"Rating: {score_label}", score_label_style)
        ]
    ]

    score_table = Table(card_data, colWidths=[330, 200])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), brand_light_bg),
        ("PADDING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 15))

    # 3. Category Breakdown Table
    story.append(Paragraph("Category Breakdown", h2_style))
    cat_rows = [["Evaluation Category", "Points Earned", "Max Points", "Status"]]
    for cat_name, scores in score_report.get("category_breakdown", {}).items():
        clean_name = cat_name.replace("_", " ").title()
        earned = scores.get("earned", 0)
        possible = scores.get("possible", 0)
        pct = (earned / possible) * 100 if possible > 0 else 100
        status_txt = "Pass" if pct >= 80 else ("Review" if pct >= 60 else "Critical")
        cat_rows.append([clean_name, f"{earned:.1f}", f"{possible:.1f}", status_txt])

    cat_table = Table(cat_rows, colWidths=[260, 90, 90, 90])
    cat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), brand_emerald),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(cat_table)
    story.append(Spacer(1, 15))

    # 4. Top 5 Prioritized Fixes
    story.append(Paragraph("Top Prioritized Action Items ('Fix This First')", h2_style))
    fixes = score_report.get("top_fixes", [])
    if fixes:
        for idx, fix in enumerate(fixes, 1):
            sev = fix.get("severity", "MEDIUM")
            reason = fix.get("reason", "")
            rec = fix.get("recommendation", "")
            story.append(Paragraph(
                f"<b>{idx}. [{sev}] {reason}</b> (Points Lost: -{fix.get('points_lost', 0)})<br/>"
                f"<i>Fix:</i> {rec}",
                body_style
            ))
            story.append(Spacer(1, 5))
    else:
        story.append(Paragraph("No major critical deductions detected. Your document layout is optimal.", body_style))
    story.append(Spacer(1, 10))

    # 5. Mode B Keywords Table (if Mode B)
    kw_table = score_report.get("keyword_table", [])
    if kw_table:
        story.append(Paragraph("Target Job Description Keyword Analysis", h2_style))
        kw_rows = [["Job Requirement", "Type", "Status", "Resume Location"]]
        for item in kw_table[:12]:
            kw_rows.append([
                item.get("keyword", "")[:35],
                item.get("type", "Required"),
                item.get("status", "Missing"),
                item.get("location_found", "")[:30]
            ])
        t_kw = Table(kw_rows, colWidths=[170, 80, 80, 200])
        t_kw.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_kw)
        story.append(Spacer(1, 15))

    # 6. Call to Action
    cta_box = [
        [
            Paragraph(
                "<b>Need Professional Career Coaching & ATS Tailoring?</b><br/>"
                "Auriic Services provides personalized US staffing, career advisory, and interview coaching for students, OPT/STEM OPT, H-1B holders, and senior professionals.<br/>"
                "<b>Schedule your 1-on-1 strategy consultation:</b> <u>https://auriic.co</u>",
                body_style
            )
        ]
    ]
    cta_table = Table(cta_box, colWidths=[530])
    cta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF9C3")),
        ("BORDER", (0, 0), (-1, -1), 1, brand_gold),
        ("PADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(KeepTogether(cta_table))
    story.append(Spacer(1, 10))

    # 7. Disclaimer
    story.append(Paragraph(
        "<b>DISCLAIMER:</b> This diagnostic assessment is an algorithmic estimate based on general Applicant Tracking System (ATS) parsing conventions. "
        "No software can guarantee interviews, recruitment placement, or hiring outcomes. Auriic Services makes no guarantee regarding jobs, employment offers, or immigration sponsorship.",
        disclaimer_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
