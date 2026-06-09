"""
Enterprise Agentic RAG Assistant
PDF Generation Utility — creates styled PDF analysis reports using ReportLab.
"""

from __future__ import annotations

import io
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_resume_analysis_pdf(data: dict[str, Any]) -> bytes:
    """
    Generate a professional PDF report summarizing the Resume vs JD analysis.
    """
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )
        
        story: list[Any] = []
        styles = getSampleStyleSheet()
        
        # ── Color Palette ──
        primary_color = colors.HexColor("#1e3a8a")     # Slate Blue
        secondary_color = colors.HexColor("#0f766e")   # Teal
        text_color = colors.HexColor("#1e293b")        # Dark Slate Text
        light_bg = colors.HexColor("#f8fafc")          # Off-white background
        border_color = colors.HexColor("#cbd5e1")      # Border grey
        
        # ── Custom Paragraph Styles ──
        title_style = ParagraphStyle(
            name="ReportTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=primary_color,
            spaceAfter=15,
            alignment=0, # Left-aligned
        )
        
        subtitle_style = ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=25,
        )
        
        h2_style = ParagraphStyle(
            name="ReportH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=primary_color,
            spaceBefore=15,
            spaceAfter=8,
            keepWithNext=True,
        )
        
        body_style = ParagraphStyle(
            name="ReportBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            textColor=text_color,
            spaceAfter=6,
            leading=14,
        )
        
        bullet_style = ParagraphStyle(
            name="ReportBullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=text_color,
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=6,
            leading=14,
        )

        # ── 1. Document Title & Subtitle ──
        story.append(Paragraph("AI CAREER INTELLIGENCE", title_style))
        story.append(Paragraph("Resume vs Job Description Match & Fit Analysis Report", subtitle_style))
        story.append(Spacer(1, 10))
        
        # ── 2. Overall Metrics Table ──
        story.append(Paragraph("Match Summary & Scores", h2_style))
        
        table_data = [
            [
                Paragraph("<b>Metric Dimension</b>", body_style),
                Paragraph("<b>Match Percentage / Score</b>", body_style)
            ],
            [
                Paragraph("Overall Match Score", body_style),
                Paragraph(f"<b>{data.get('match_score', 0)}%</b>", body_style)
            ],
            [
                Paragraph("Skill Match Percentage", body_style),
                Paragraph(f"{data.get('skill_match_pct', 0)}%", body_style)
            ],
            [
                Paragraph("Project Match Percentage", body_style),
                Paragraph(f"{data.get('project_match_pct', 0)}%", body_style)
            ],
            [
                Paragraph("Education Match Percentage", body_style),
                Paragraph(f"{data.get('education_match_pct', 0)}%", body_style)
            ],
            [
                Paragraph("Interview Readiness Score", body_style),
                Paragraph(f"<b>{data.get('interview_readiness_score', 0)}%</b>", body_style)
            ]
        ]
        
        # Layout metrics table (504 pt is max width inside letter margins)
        t = Table(table_data, colWidths=[300, 204])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('BACKGROUND', (0, 1), (-1, -1), light_bg),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
        
        # ── 3. Key Strengths ──
        story.append(Paragraph("Candidate Key Strengths", h2_style))
        strengths = data.get("strengths", [])
        if strengths:
            for s in strengths:
                story.append(Paragraph(f"• {s}", bullet_style))
        else:
            story.append(Paragraph("No specific strengths noted relative to the JD requirements.", body_style))
        story.append(Spacer(1, 12))
        
        # ── 4. Missing Skills & Gaps ──
        story.append(Paragraph("Missing Skills & Gap Analysis", h2_style))
        missing = data.get("missing_skills", [])
        if missing:
            for m in missing:
                story.append(Paragraph(f"• {m}", bullet_style))
        else:
            story.append(Paragraph("No critical missing skills identified. Alignment is high!", body_style))
        story.append(Spacer(1, 12))
        
        # ── 5. Actionable Recommendations ──
        story.append(Paragraph("Actionable Recommendations", h2_style))
        recs = data.get("recommendations", [])
        if recs:
            for r in recs:
                story.append(Paragraph(f"• {r}", bullet_style))
        else:
            story.append(Paragraph("No immediate resume modifications recommended.", body_style))
        
        story.append(PageBreak())
        
        # ── 6. Page 2: Extracted Profile Information ──
        story.append(Paragraph("Extracted Candidate Profile Data", title_style))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph("Education History", h2_style))
        edu = data.get("extracted_education", "Not specified in resume.")
        story.append(Paragraph(str(edu).replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph("Professional Experience", h2_style))
        exp = data.get("extracted_experience", "Not specified in resume.")
        story.append(Paragraph(str(exp).replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph("Extracted Projects", h2_style))
        projs = data.get("extracted_projects", [])
        if projs:
            if isinstance(projs, list):
                for p in projs:
                    story.append(Paragraph(f"• {p}", bullet_style))
            else:
                story.append(Paragraph(str(projs).replace("\n", "<br/>"), body_style))
        else:
            story.append(Paragraph("No technical projects parsed.", body_style))
        
        # Build PDF Document
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info("Successfully generated resume analysis PDF report.")
        return pdf_bytes
    except Exception as exc:
        logger.error(f"Failed to generate analysis PDF report: {exc}", exc_info=True)
        return b""
