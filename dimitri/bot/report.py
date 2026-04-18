#!/usr/bin/env python3
"""PentAGI Report Generator v2 — Professional Pentest Reports"""
import os, json, time, textwrap, html as html_mod
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether, NextPageTemplate,
    PageTemplate, Frame, BaseDocTemplate
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend
from reportlab.pdfgen import canvas as pdfcanvas
import requests, urllib3

urllib3.disable_warnings()

PENTAGI_URL = os.getenv("PENTAGI_URL", "https://localhost:8443")
PENTAGI_TOKEN = os.getenv("PENTAGI_TOKEN")
LLM_URL = os.getenv("LLM_URL", "http://localhost:8080")
REPORTS_DIR = os.getenv("REPORTS_DIR", "/opt/pentagi-telegram/reports")
HEADERS = {"Authorization": f"Bearer {PENTAGI_TOKEN}", "Content-Type": "application/json"}

# ═══════════════════════════════════
#  COLORS
# ═══════════════════════════════════
DARK_BG = colors.HexColor("#0f1923")
ACCENT = colors.HexColor("#e94560")
ACCENT2 = colors.HexColor("#0f3460")
LIGHT_BG = colors.HexColor("#f8f9fa")
TEXT_DARK = colors.HexColor("#1a1a2e")
TEXT_MID = colors.HexColor("#4a4a6a")
TEXT_LIGHT = colors.HexColor("#8a8aaa")
CRITICAL = colors.HexColor("#dc3545")
HIGH = colors.HexColor("#fd7e14")
MEDIUM = colors.HexColor("#ffc107")
LOW = colors.HexColor("#28a745")
INFO_C = colors.HexColor("#17a2b8")
TABLE_HEADER_BG = colors.HexColor("#1a1a2e")

SEVERITY_COLORS = {
    "critical": CRITICAL, "high": HIGH, "medium": MEDIUM,
    "low": LOW, "info": INFO_C, "informational": INFO_C
}
SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]

W, H = A4  # 595.27 x 841.89

def esc(text):
    """Escape text for reportlab Paragraph XML safety"""
    if text is None:
        return ""
    s = str(text)
    if not s:
        return ""
    # Replace & first, then < and >
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Remove null bytes and control chars that break XML
    s = ''.join(c for c in s if ord(c) >= 32 or c in '\n\r\t')
    return s

# ═══════════════════════════════════
#  STYLES
# ═══════════════════════════════════
def get_styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle('SecTitle', fontSize=20, leading=26, textColor=ACCENT,
        spaceBefore=20, spaceAfter=8, fontName='Helvetica-Bold'))
    s.add(ParagraphStyle('SubSec', fontSize=14, leading=18, textColor=ACCENT2,
        spaceBefore=14, spaceAfter=6, fontName='Helvetica-Bold'))
    s.add(ParagraphStyle('Body', fontSize=10, leading=14, textColor=TEXT_DARK,
        alignment=TA_LEFT, spaceAfter=6))
    s.add(ParagraphStyle('BodyJ', fontSize=10, leading=14, textColor=TEXT_DARK,
        alignment=TA_JUSTIFY, spaceAfter=6))
    s.add(ParagraphStyle('FindTitle', fontSize=12, leading=16, textColor=TEXT_DARK,
        spaceBefore=10, spaceAfter=6, fontName='Helvetica-Bold'))
    s.add(ParagraphStyle('CodeBlock', fontSize=8, leading=10, textColor=colors.HexColor("#d4d4d4"),
        backColor=colors.HexColor("#1e1e1e"), borderWidth=0, borderPadding=8,
        spaceAfter=8, spaceBefore=4, fontName='Courier'))
    s.add(ParagraphStyle('TH', fontSize=9, textColor=colors.white,
        fontName='Helvetica-Bold', alignment=TA_CENTER, leading=12))
    s.add(ParagraphStyle('TC', fontSize=9, textColor=TEXT_DARK, alignment=TA_LEFT, leading=12))
    s.add(ParagraphStyle('TCc', fontSize=9, textColor=TEXT_DARK, alignment=TA_CENTER, leading=12))
    s.add(ParagraphStyle('Small', fontSize=8, textColor=TEXT_LIGHT, alignment=TA_LEFT, leading=10))
    s.add(ParagraphStyle('Disclaimer', fontSize=8, textColor=TEXT_MID,
        alignment=TA_LEFT, leading=11, spaceAfter=4))
    s.add(ParagraphStyle('TOCEntry', fontSize=11, leading=16, textColor=TEXT_DARK, spaceAfter=2))
    return s


# ═══════════════════════════════════
#  API
# ═══════════════════════════════════
def pentagi_api(method, path, data=None, params=None):
    url = f"{PENTAGI_URL}/api/v1{path}"
    try:
        r = getattr(requests, method.lower())(url, headers=HEADERS, json=data, params=params, verify=False, timeout=60)
        return r.json() if r.text else {}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


def llm_analyze(prompt):
    try:
        r = requests.post(f"{LLM_URL}/v1/chat/completions", json={
            "model": "qwen3-coder-30b",
            "messages": [
                {"role": "system", "content": "You are a senior penetration tester writing a professional report. Respond ONLY with valid JSON. No markdown, no extra text, no code fences. Every finding MUST have all fields filled. For tools, list ONLY actual security tools (nmap, sqlmap, nuclei, metasploit, burp, nikto, gobuster, ffuf, etc) — NEVER list output files or generic software."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4096, "temperature": 0.3
        }, timeout=300)
        content = r.json()["choices"][0]["message"]["content"]
        if "<think>" in content and "</think>" in content:
            content = content[content.index("</think>") + len("</think>"):].strip()
        if "{" in content:
            start = content.index("{")
            depth = 0
            for i in range(start, len(content)):
                if content[i] == "{": depth += 1
                elif content[i] == "}": depth -= 1
                if depth == 0:
                    return json.loads(content[start:i+1])
        return json.loads(content)
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════
#  COVER PAGE (drawn on canvas)
# ═══════════════════════════════════
class CoverPage:
    def __init__(self, flow_data, report_date):
        self.flow = flow_data
        self.date = report_date
    
    def draw(self, c, doc):
        c.saveState()
        # Full dark background
        c.setFillColor(DARK_BG)
        c.rect(0, 0, W, H, fill=1, stroke=0)
        
        # Accent stripe left
        c.setFillColor(ACCENT)
        c.rect(0, 0, 6, H, fill=1, stroke=0)
        
        # Title block
        c.setFillColor(colors.white)
        c.setFont('Helvetica-Bold', 44)
        c.drawString(50, H - 180, "PENETRATION")
        c.setFillColor(ACCENT)
        c.setFont('Helvetica-Bold', 44)
        c.drawString(50, H - 230, "TEST REPORT")
        
        # Accent line
        c.setStrokeColor(ACCENT)
        c.setLineWidth(3)
        c.line(50, H - 250, W - 50, H - 250)
        
        # Target name
        target = self.flow.get("title", self.flow.get("input", "Security Assessment"))[:80]
        c.setFillColor(colors.HexColor("#cccccc"))
        c.setFont('Helvetica', 16)
        # Word wrap target
        if len(target) > 50:
            c.drawString(50, H - 290, target[:50])
            c.drawString(50, H - 312, target[50:])
            y_after = H - 340
        else:
            c.drawString(50, H - 290, target)
            y_after = H - 320
        
        # Metadata box
        c.setFillColor(colors.HexColor("#1a2332"))
        c.roundRect(50, y_after - 120, 300, 100, 8, fill=1, stroke=0)
        
        c.setFont('Helvetica', 11)
        c.setFillColor(TEXT_LIGHT)
        c.drawString(65, y_after - 45, f"Date:")
        c.drawString(65, y_after - 65, f"Status:")
        c.drawString(65, y_after - 85, f"Classification:")
        
        c.setFillColor(colors.white)
        c.drawString(160, y_after - 45, self.date)
        raw_status = self.flow.get("status", "completed").lower()
        status_map = {"waiting": "COMPLETED", "completed": "COMPLETED", "running": "IN PROGRESS",
                       "failed": "FAILED", "stopped": "STOPPED", "error": "ERROR"}
        status = status_map.get(raw_status, raw_status.upper())
        c.drawString(160, y_after - 65, status)
        c.setFillColor(ACCENT)
        c.setFont('Helvetica-Bold', 11)
        c.drawString(160, y_after - 85, "CONFIDENTIAL")
        
        # Bottom bar
        c.setFillColor(colors.HexColor("#0a0f18"))
        c.rect(0, 0, W, 70, fill=1, stroke=0)
        c.setStrokeColor(ACCENT)
        c.setLineWidth(2)
        c.line(0, 70, W, 70)
        
        c.setFillColor(TEXT_LIGHT)
        c.setFont('Helvetica', 9)
        c.drawString(50, 42, "Generated by PentAGI — Autonomous AI Penetration Testing")
        c.drawString(50, 28, f"Powered by Qwen3 LLM  •  Report ID: FLOW-{self.flow.get('id', '?')}")
        
        c.restoreState()


# ═══════════════════════════════════
#  PAGE TEMPLATE
# ═══════════════════════════════════
def later_pages(c, doc):
    c.saveState()
    # Top accent line
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.5)
    c.line(40, H - 28, W - 40, H - 28)
    # Footer
    c.setFillColor(TEXT_LIGHT)
    c.setFont('Helvetica', 7)
    c.drawString(40, 18, "CONFIDENTIAL — Penetration Test Report")
    c.drawRightString(W - 40, 18, f"Page {doc.page}")
    # Footer line
    c.setStrokeColor(colors.HexColor("#e0e0e0"))
    c.setLineWidth(0.5)
    c.line(40, 30, W - 40, 30)
    c.restoreState()


# ═══════════════════════════════════
#  SECTION BUILDERS
# ═══════════════════════════════════
def section_hr():
    return HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=12)

def severity_badge(severity, styles):
    sev = severity.upper()
    col = SEVERITY_COLORS.get(severity.lower(), INFO_C)
    return Paragraph(f'<font color="#{col.hexval()[2:]}"><b>▌{sev}</b></font>', styles['TC'])

def build_toc(story, styles, page_map):
    story.append(Paragraph("TABLE OF CONTENTS", styles['SecTitle']))
    story.append(section_hr())
    story.append(Spacer(1, 10))
    
    sections = [
        ("1", "Executive Summary"),
        ("2", "Scope & Methodology"),
        ("3", "Risk Rating Methodology"),
        ("4", "Detailed Findings"),
        ("5", "Recommendations"),
        ("6", "Conclusion"),
        ("7", "Disclaimer"),
    ]
    
    tocname_style = ParagraphStyle('tocname', fontSize=11, leading=15, textColor=TEXT_DARK)
    dots_style = ParagraphStyle('tocdots', fontSize=10, textColor=TEXT_LIGHT, alignment=TA_RIGHT)
    
    toc_data = []
    for num, name in sections:
        toc_data.append([
            Paragraph(f'<font color="#e94560"><b>{num}</b></font>', styles['TC']),
            Paragraph(name, tocname_style),
            Paragraph("·" * 40, dots_style),
        ])
    
    t = Table(toc_data, colWidths=[30, 300, 150])
    t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, colors.HexColor("#e8e8e8")),
    ]))
    story.append(t)
    story.append(Spacer(1, 30))
    
    # Document info box
    story.append(Paragraph("Document Information", styles['SubSec']))
    info_data = [
        ["Report Type", "External Penetration Test"],
        ["Classification", "CONFIDENTIAL"],
        ["Distribution", "Authorized recipients only"],
        ["Generated", datetime.now().strftime("%d %B %Y, %H:%M UTC")],
    ]
    info_table = Table(
        [[Paragraph(f'<b>{r[0]}</b>', styles['TC']), Paragraph(r[1], styles['TC'])] for r in info_data],
        colWidths=[140, 340]
    )
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), LIGHT_BG),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e0e0e0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(info_table)
    story.append(PageBreak())


def build_executive_summary(story, styles, flow_data, analysis):
    story.append(Paragraph("1. EXECUTIVE SUMMARY", styles['SecTitle']))
    story.append(section_hr())
    
    summary = analysis.get("executive_summary", "A penetration test was conducted against the target systems.")
    for para in summary.split('\n'):
        if para.strip():
            story.append(Paragraph(esc(para.strip()), styles['BodyJ']))
    story.append(Spacer(1, 10))
    
    # Overall risk
    findings = analysis.get("findings", [])
    sev_count = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
    for f in findings:
        sev = f.get("severity", "info").capitalize()
        if sev in sev_count:
            sev_count[sev] += 1
    
    # Determine overall risk
    if sev_count["Critical"] > 0: overall = ("CRITICAL", CRITICAL)
    elif sev_count["High"] > 0: overall = ("HIGH", HIGH)
    elif sev_count["Medium"] > 0: overall = ("MEDIUM", MEDIUM)
    elif sev_count["Low"] > 0: overall = ("LOW", LOW)
    else: overall = ("INFORMATIONAL", INFO_C)
    
    # Risk box
    risk_data = [[
        Paragraph("OVERALL RISK RATING", ParagraphStyle('rb', fontSize=11, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)),
        Paragraph(f'<font color="#{overall[1].hexval()[2:]}"><b>{overall[0]}</b></font>',
                  ParagraphStyle('rv', fontSize=16, textColor=overall[1], fontName='Helvetica-Bold', alignment=TA_CENTER)),
    ]]
    risk_table = Table(risk_data, colWidths=[240, 240])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), TABLE_HEADER_BG),
        ('BACKGROUND', (1,0), (1,0), LIGHT_BG),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('BOX', (0,0), (-1,-1), 1, TABLE_HEADER_BG),
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 15))
    
    # Findings overview table
    story.append(Paragraph("Findings by Severity", styles['SubSec']))
    
    table_data = [[
        Paragraph("Severity", styles['TH']),
        Paragraph("Count", styles['TH']),
        Paragraph("Description", styles['TH']),
    ]]
    sev_descs = {
        "Critical": "Immediate exploitation possible, severe business impact",
        "High": "Significant risk, should be remediated urgently",
        "Medium": "Moderate risk, plan remediation within 30 days",
        "Low": "Minor risk, remediate during regular maintenance",
        "Info": "Informational finding, no direct risk",
    }
    
    for sev_name in ["Critical", "High", "Medium", "Low", "Info"]:
        count = sev_count[sev_name]
        col = SEVERITY_COLORS.get(sev_name.lower(), INFO_C)
        table_data.append([
            Paragraph(f'<font color="#{col.hexval()[2:]}"><b>● {sev_name}</b></font>', styles['TC']),
            Paragraph(f'<b>{count}</b>', styles['TCc']),
            Paragraph(sev_descs[sev_name], styles['TC']),
        ])
    
    table_data.append([
        Paragraph("<b>TOTAL</b>", styles['TC']),
        Paragraph(f'<b>{len(findings)}</b>', styles['TCc']),
        Paragraph("", styles['TC']),
    ])
    
    t = Table(table_data, colWidths=[100, 60, 320])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_BG),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#dee2e6")),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, LIGHT_BG]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e9ecef")),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    
    # Chart — use horizontal bar chart for clarity
    active_sevs = [(k, v) for k, v in sev_count.items() if v > 0]
    if active_sevs:
        sev_color_map = {"Critical": CRITICAL, "High": HIGH, "Medium": MEDIUM, "Low": LOW, "Info": INFO_C}
        
        # Build bar chart as table (more reliable than reportlab charts)
        story.append(Paragraph("Severity Distribution", styles['SubSec']))
        max_val = max(v for _, v in active_sevs) or 1
        
        bar_data = []
        for name, count in active_sevs:
            col = sev_color_map.get(name, INFO_C)
            bar_width = max(int(count / max_val * 30), 1)
            bar_str = f'<font color="#{col.hexval()[2:]}">{"█" * bar_width}</font> <b>{count}</b>'
            bar_data.append([
                Paragraph(f'<font color="#{col.hexval()[2:]}"><b>{name}</b></font>', styles['TC']),
                Paragraph(bar_str, styles['TC']),
            ])
        
        bt = Table(bar_data, colWidths=[80, 400])
        bt.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#dee2e6")),
        ]))
        story.append(bt)
    
    story.append(PageBreak())


def build_scope(story, styles, flow_data, analysis):
    story.append(Paragraph("2. SCOPE & METHODOLOGY", styles['SecTitle']))
    story.append(section_hr())
    
    story.append(Paragraph("2.1 Scope", styles['SubSec']))
    scope = analysis.get("scope", flow_data.get("input", "N/A"))
    story.append(Paragraph(esc(scope), styles['BodyJ']))
    story.append(Spacer(1, 5))
    
    # Out of scope
    story.append(Paragraph("2.2 Out of Scope", styles['SubSec']))
    out_scope = analysis.get("out_of_scope", "Social engineering, denial of service attacks, and physical security assessments were excluded from this engagement.")
    story.append(Paragraph(esc(out_scope), styles['Body']))
    story.append(Spacer(1, 5))
    
    story.append(Paragraph("2.3 Methodology", styles['SubSec']))
    methodology = analysis.get("methodology",
        "The assessment followed OWASP Testing Guide v4, PTES (Penetration Testing Execution Standard), "
        "and NIST SP 800-115 guidelines. Testing phases: Reconnaissance → Enumeration → Vulnerability Analysis → Exploitation → Post-Exploitation → Reporting.")
    story.append(Paragraph(esc(methodology), styles['BodyJ']))
    story.append(Spacer(1, 5))
    
    # Tools table
    story.append(Paragraph("2.4 Tools Utilized", styles['SubSec']))
    tools = analysis.get("tools", ["Nmap", "SQLMap", "Nuclei", "Metasploit"])
    # Filter out non-tools
    filtered = [t for t in tools if not t.endswith('.txt') and not t.endswith('.log') and not t.endswith('.csv')
                and t.lower() not in ('docker', 'python', 'bash', 'curl', 'wget')]
    if not filtered:
        filtered = ["Nmap", "Custom scripts"]
    
    tool_rows = []
    for i in range(0, len(filtered), 3):
        row = filtered[i:i+3]
        while len(row) < 3:
            row.append("")
        tool_rows.append([Paragraph(f'• {t}' if t else '', styles['TC']) for t in row])
    
    tt = Table(tool_rows, colWidths=[160, 160, 160])
    tt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#dee2e6")),
    ]))
    story.append(tt)
    story.append(PageBreak())


def build_risk_methodology(story, styles):
    story.append(Paragraph("3. RISK RATING METHODOLOGY", styles['SecTitle']))
    story.append(section_hr())
    
    story.append(Paragraph(
        "Findings are rated using the Common Vulnerability Scoring System (CVSS v3.1) combined "
        "with contextual business impact analysis. The following severity levels are used throughout this report:",
        styles['Body']))
    story.append(Spacer(1, 10))
    
    risk_data = [
        [Paragraph("Rating", styles['TH']), Paragraph("CVSS Range", styles['TH']),
         Paragraph("Description", styles['TH'])],
        [Paragraph('<font color="#dc3545"><b>● Critical</b></font>', styles['TC']),
         Paragraph("9.0 – 10.0", styles['TCc']),
         Paragraph("Immediate exploitation likely. Complete system compromise possible. Requires emergency response.", styles['TC'])],
        [Paragraph('<font color="#fd7e14"><b>● High</b></font>', styles['TC']),
         Paragraph("7.0 – 8.9", styles['TCc']),
         Paragraph("Exploitation probable with moderate effort. Significant data exposure or system access. Urgent remediation needed.", styles['TC'])],
        [Paragraph('<font color="#ffc107"><b>● Medium</b></font>', styles['TC']),
         Paragraph("4.0 – 6.9", styles['TCc']),
         Paragraph("Exploitation possible under certain conditions. Limited impact. Remediation within 30 days recommended.", styles['TC'])],
        [Paragraph('<font color="#28a745"><b>● Low</b></font>', styles['TC']),
         Paragraph("0.1 – 3.9", styles['TCc']),
         Paragraph("Minimal risk. Exploitation unlikely or impact negligible. Fix during regular maintenance cycles.", styles['TC'])],
        [Paragraph('<font color="#17a2b8"><b>● Info</b></font>', styles['TC']),
         Paragraph("0.0", styles['TCc']),
         Paragraph("Informational observation. No direct security risk but may indicate areas for improvement.", styles['TC'])],
    ]
    
    t = Table(risk_data, colWidths=[90, 80, 310])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_BG),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#dee2e6")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_BG]),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t)
    story.append(PageBreak())


def build_findings(story, styles, analysis):
    story.append(Paragraph("4. DETAILED FINDINGS", styles['SecTitle']))
    story.append(section_hr())
    
    findings = analysis.get("findings", [])
    if not findings:
        story.append(Paragraph("No significant findings were identified during this assessment.", styles['Body']))
        story.append(PageBreak())
        return
    
    # Sort by severity
    def sev_sort(f):
        s = f.get("severity", "info").lower()
        return SEVERITY_ORDER.index(s) if s in SEVERITY_ORDER else 99
    findings.sort(key=sev_sort)
    
    for i, finding in enumerate(findings, 1):
        severity = finding.get("severity", "info")
        sev_upper = severity.upper()
        sev_color = SEVERITY_COLORS.get(severity.lower(), INFO_C)
        cvss = finding.get("cvss", "")
        
        block = []
        
        # Header bar — fixed width badge
        header_data = [[
            Paragraph(f'<font color="white"><b>{esc(sev_upper)}</b></font>',
                ParagraphStyle(f'sb{i}', fontSize=10, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER, leading=14)),
            Paragraph(f'<b>F-{i:02d}: {esc(finding.get("title", "Finding"))}</b>',
                ParagraphStyle(f'ft{i}', fontSize=11, textColor=TEXT_DARK, fontName='Helvetica-Bold', leading=14)),
        ]]
        ht = Table(header_data, colWidths=[80, 400])
        ht.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), sev_color),
            ('BACKGROUND', (1,0), (1,0), LIGHT_BG),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#dee2e6")),
        ]))
        block.append(ht)
        block.append(Spacer(1, 6))
        
        # CVSS + Severity in a detail row
        if cvss and str(cvss) != "0.0" and severity.lower() != "info":
            block.append(Paragraph(f'<b>CVSS v3.1:</b> {esc(str(cvss))}', styles['Body']))
        
        # Description
        if finding.get("description"):
            block.append(Paragraph('<font color="#e94560"><b>Description</b></font>', styles['Body']))
            block.append(Paragraph(esc(finding["description"]), styles['BodyJ']))
        
        # Impact
        if finding.get("impact"):
            block.append(Paragraph('<font color="#e94560"><b>Impact</b></font>', styles['Body']))
            block.append(Paragraph(esc(finding["impact"]), styles['BodyJ']))
        
        # Evidence
        if finding.get("evidence"):
            block.append(Paragraph('<font color="#e94560"><b>Evidence</b></font>', styles['Body']))
            evidence_text = esc(finding["evidence"][:500])
            block.append(Paragraph(evidence_text, styles['CodeBlock']))
        
        # Remediation
        if finding.get("remediation"):
            block.append(Paragraph('<font color="#28a745"><b>Remediation</b></font>', styles['Body']))
            block.append(Paragraph(esc(finding["remediation"]), styles['BodyJ']))
        
        # References
        refs = finding.get("references", [])
        if refs:
            block.append(Paragraph('<font color="#0f3460"><b>References</b></font>', styles['Body']))
            for ref in refs[:5]:
                block.append(Paragraph(f'• {esc(ref)}', styles['Small']))
        
        block.append(Spacer(1, 15))
        story.append(KeepTogether(block))
    
    story.append(PageBreak())


def build_recommendations(story, styles, analysis):
    story.append(Paragraph("5. RECOMMENDATIONS", styles['SecTitle']))
    story.append(section_hr())
    
    story.append(Paragraph(
        "The following recommendations are prioritized based on risk level and implementation effort. "
        "Items marked as 'Immediate' should be addressed before the next business day.",
        styles['Body']))
    story.append(Spacer(1, 10))
    
    recs = analysis.get("recommendations", [])
    if not recs:
        story.append(Paragraph("No specific recommendations at this time.", styles['Body']))
        story.append(PageBreak())
        return
    
    table_data = [[
        Paragraph("#", styles['TH']),
        Paragraph("Priority", styles['TH']),
        Paragraph("Recommendation", styles['TH']),
        Paragraph("Effort", styles['TH']),
        Paragraph("Related", styles['TH']),
    ]]
    
    priority_colors = {"Immediate": CRITICAL, "High": HIGH, "Medium": MEDIUM, "Low": LOW}
    
    for j, rec in enumerate(recs, 1):
        priority = rec.get("priority", "Medium")
        p_color = priority_colors.get(priority, MEDIUM)
        related = rec.get("related_finding", f"F-{j:02d}")
        effort = rec.get("effort", "Medium")
        effort_color = {"Low": LOW, "Medium": MEDIUM, "High": HIGH}.get(effort, MEDIUM)
        
        table_data.append([
            Paragraph(f'<b>{j}</b>', styles['TCc']),
            Paragraph(f'<font color="#{p_color.hexval()[2:]}"><b>{priority}</b></font>', styles['TCc']),
            Paragraph(esc(rec.get("action", "")), styles['TC']),
            Paragraph(f'<font color="#{effort_color.hexval()[2:]}">{effort}</font>', styles['TCc']),
            Paragraph(related, styles['TCc']),
        ])
    
    t = Table(table_data, colWidths=[25, 70, 275, 55, 55])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_BG),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#dee2e6")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_BG]),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t)
    story.append(PageBreak())


def build_conclusion(story, styles, analysis):
    story.append(Paragraph("6. CONCLUSION", styles['SecTitle']))
    story.append(section_hr())
    
    conclusion = analysis.get("conclusion",
        "This penetration test provided valuable insights into the security posture of the target environment. "
        "The findings and recommendations outlined in this report should be addressed according to their "
        "priority levels to improve the overall security posture. A follow-up assessment is recommended "
        "after remediation efforts have been completed to verify the effectiveness of the implemented controls.")
    story.append(Paragraph(esc(conclusion), styles['BodyJ']))
    story.append(Spacer(1, 15))
    
    # Next steps
    story.append(Paragraph("Next Steps", styles['SubSec']))
    steps = [
        "Review and prioritize findings based on business context.",
        "Implement remediation measures starting with Critical and High severity items.",
        "Schedule a follow-up assessment to validate fixes.",
        "Integrate security testing into the development lifecycle.",
    ]
    for step in steps:
        story.append(Paragraph(f'<b>→</b> {step}', styles['Body']))
    
    story.append(PageBreak())


def build_disclaimer(story, styles):
    story.append(Paragraph("7. DISCLAIMER", styles['SecTitle']))
    story.append(section_hr())
    
    disclaimers = [
        "This report is provided on an 'as-is' basis and is intended solely for the authorized recipient. Unauthorized distribution is prohibited.",
        "The penetration test was conducted within the agreed-upon scope and timeframe. Vulnerabilities outside the defined scope may not have been identified.",
        "The findings represent a point-in-time assessment. New vulnerabilities may emerge after the testing period.",
        "This report contains sensitive security information and should be handled according to the CONFIDENTIAL classification.",
        "The testing team is not responsible for any damages resulting from the use or misuse of information contained in this report.",
        "All testing activities were performed with proper authorization and in compliance with applicable laws and regulations.",
    ]
    
    for d in disclaimers:
        story.append(Paragraph(f'<b>•</b>  {d}', styles['Disclaimer']))
        story.append(Spacer(1, 3))
    
    story.append(Spacer(1, 30))
    
    # Signature block
    story.append(Paragraph("Assessor Certification", styles['SubSec']))
    story.append(Spacer(1, 20))
    
    sig_data = [
        [Paragraph("<b>Lead Assessor:</b>", styles['TC']), Paragraph("PentAGI Autonomous Agent", styles['TC'])],
        [Paragraph("<b>Platform:</b>", styles['TC']), Paragraph("PentAGI + Qwen3-Coder-30B", styles['TC'])],
        [Paragraph("<b>Assessment Type:</b>", styles['TC']), Paragraph("Automated Penetration Test", styles['TC'])],
        [Paragraph("<b>Date:</b>", styles['TC']), Paragraph(datetime.now().strftime("%d %B %Y"), styles['TC'])],
    ]
    sig = Table(sig_data, colWidths=[130, 350])
    sig.setStyle(TableStyle([
        ('LINEBELOW', (0,-1), (-1,-1), 1, TEXT_DARK),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(sig)
    
    story.append(Spacer(1, 40))
    story.append(Paragraph("— End of Report —", ParagraphStyle('eor', fontSize=10, textColor=TEXT_LIGHT, alignment=TA_CENTER)))


# ═══════════════════════════════════
#  MAIN GENERATOR
# ═══════════════════════════════════
def generate_report(flow_id):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    flow_resp = pentagi_api("GET", f"/flows/{flow_id}")
    if flow_resp.get("status") != "success":
        return None, f"Failed to fetch flow: {flow_resp.get('msg', 'unknown')}"
    
    flow_data = flow_resp["data"]
    
    tasks_resp = pentagi_api("GET", f"/flows/{flow_id}/tasks/", params={"page": 1, "pageSize": 100, "type": "init"})
    tasks = []
    if tasks_resp.get("status") == "success" and tasks_resp.get("data"):
        td = tasks_resp["data"]
        tasks = td.get("tasks", []) if isinstance(td, dict) else (td if isinstance(td, list) else [])
    
    logs_resp = pentagi_api("GET", f"/flows/{flow_id}/agentlogs/", params={"page": 1, "pageSize": 100, "type": "init"})
    logs = []
    if logs_resp.get("status") == "success" and logs_resp.get("data"):
        ld = logs_resp["data"]
        logs = ld.get("agentlogs", []) if isinstance(ld, dict) else (ld if isinstance(ld, list) else [])
    
    task_summary = [{"title": t.get("title",""), "status": t.get("status",""), "result": str(t.get("result",""))[:500]} for t in tasks[:20]]
    log_summary = [{"type": l.get("type",""), "result": str(l.get("result",""))[:300]} for l in logs[:20]]
    
    context = f"""Analyze this penetration test and generate a DETAILED structured report.

TARGET: {flow_data.get('title', flow_data.get('input', 'Unknown'))}
STATUS: {flow_data.get('status', 'Unknown')}

TASKS:
{json.dumps(task_summary, indent=2)}

LOGS:
{json.dumps(log_summary, indent=2)}

Generate JSON with EXACT structure (fill ALL fields, be DETAILED and SPECIFIC):
{{
    "executive_summary": "3-4 paragraphs. Be specific about what was tested and found.",
    "scope": "Detailed scope description with IPs/ports/services tested.",
    "out_of_scope": "What was NOT tested.",
    "methodology": "Specific methodology steps taken.",
    "tools": ["ONLY real security tools like nmap, sqlmap, nuclei, metasploit, burp, nikto, gobuster, ffuf. NEVER list files or generic software."],
    "findings": [
        {{
            "title": "Clear finding title",
            "severity": "critical|high|medium|low|info",
            "description": "Detailed description of the vulnerability.",
            "impact": "Specific business/technical impact.",
            "evidence": "Actual technical evidence, command output, or proof.",
            "cvss": "X.X (use 0.0 ONLY for info, never leave empty)",
            "remediation": "Specific, actionable remediation steps.",
            "references": ["https://cwe.mitre.org/...", "https://owasp.org/..."]
        }}
    ],
    "recommendations": [
        {{
            "priority": "Immediate|High|Medium|Low",
            "action": "Specific actionable recommendation.",
            "effort": "Low|Medium|High",
            "related_finding": "F-01"
        }}
    ],
    "conclusion": "2 paragraphs summarizing overall security posture and key takeaways."
}}"""
    
    analysis = llm_analyze(context)
    if "error" in analysis:
        analysis = {
            "executive_summary": f"A penetration test was conducted against the target system (Flow #{flow_id}). Status: {flow_data.get('status', 'unknown')}.",
            "scope": flow_data.get("input", "N/A"),
            "out_of_scope": "Social engineering, denial of service, and physical security testing.",
            "methodology": "OWASP Testing Guide v4, PTES, NIST SP 800-115.",
            "tools": ["Nmap"], "findings": [], "recommendations": [],
            "conclusion": "Assessment completed. See findings for details."
        }
    
    report_date = datetime.now().strftime("%d/%m/%Y %H:%M")
    filename = f"pentest-report-flow{flow_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    # Custom doc with cover page
    cover = CoverPage(flow_data, report_date)
    
    doc = BaseDocTemplate(filepath, pagesize=A4,
        rightMargin=40, leftMargin=40, topMargin=50, bottomMargin=45)
    
    # Cover frame (full page)
    cover_frame = Frame(0, 0, W, H, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id='cover')
    # Content frame
    content_frame = Frame(40, 45, W - 80, H - 95, id='content')
    
    cover_template = PageTemplate(id='cover', frames=[cover_frame], onPage=cover.draw)
    content_template = PageTemplate(id='content', frames=[content_frame], onPage=later_pages)
    
    doc.addPageTemplates([cover_template, content_template])
    
    styles = get_styles()
    story = []
    
    # Cover page (empty flowable + switch template)
    story.append(NextPageTemplate('content'))
    story.append(PageBreak())
    
    # Content
    build_toc(story, styles, {})
    build_executive_summary(story, styles, flow_data, analysis)
    build_scope(story, styles, flow_data, analysis)
    build_risk_methodology(story, styles)
    build_findings(story, styles, analysis)
    build_recommendations(story, styles, analysis)
    build_conclusion(story, styles, analysis)
    build_disclaimer(story, styles)
    
    doc.build(story)
    return filepath, None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: pentagi-report.py <flow_id>")
        sys.exit(1)
    fid = int(sys.argv[1])
    print(f"Generating report for flow #{fid}...")
    fp, err = generate_report(fid)
    if err:
        print(f"Error: {err}")
        sys.exit(1)
    print(f"Report saved: {fp}")
