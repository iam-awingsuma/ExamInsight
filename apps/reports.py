# apps/reports.py

import os

from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    HRFlowable,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from sqlalchemy import func

from apps import db
from apps.authentication.models import NGRTA, NGRTB, NGRTC


# --------------------------------------------------
# Small formatting helpers
# --------------------------------------------------

def safe_number(value, decimal_places=0, default="N/A"):
    try:
        return f"{float(value):.{decimal_places}f}"
    except (TypeError, ValueError):
        return default

def safe_pct(part, whole):
    return round((part / whole) * 100.0, 1) if whole else 0.0

def get_ngrt_model_by_exam(exam):
    """
    Return the NGRT model based on the selected report option.

    Allowed values: ngrta, ngrtb, ngrtc
    """
    exam = (exam or "").strip().lower()

    # label, model pairs for each NGRT exam type
    exam_map = {
        "ngrta": ("NGRT-A", NGRTA), "ngrtb": ("NGRT-B", NGRTB), "ngrtc": ("NGRT-C", NGRTC),
    }

    return exam_map.get(exam)

def clean_pdf_text(value, default=""):
    if value is None:
        return default
    return escape(str(value).strip())

def clean_value(value, default="-"):
    """
    Safely display empty/null values in the PDF.
    """
    if value is None:
        return default

    value = str(value).strip()

    if value == "":
        return default

    return value

def format_year_group(yrgrp):
    """
    Converts values like 2-a or 2-A into 2-A.
    """
    yrgrp = clean_value(yrgrp)

    if yrgrp == "-":
        return "Unknown Year Group"

    return yrgrp.upper()

def format_student_name(row):
    """
    Builds full student name from forename and surname.
    """
    forename = clean_value(row.get("forename"), "")
    surname = clean_value(row.get("surname"), "")

    full_name = f"{forename} {surname}".strip()

    return full_name if full_name else "-"

def sort_year_group_key(yrgrp):
    """
    Sorts year groups naturally: 2-A, 2-B, 2-C, etc.
    """
    label = format_year_group(yrgrp)

    try:
        year, section = label.split("-")
        return int(year), section
    except Exception:
        return 999, label
    
# --------------------------------------------------
# Report data builder
# --------------------------------------------------
def build_ngrt_report_data(exam):
    """
    Builds all summary values needed for the selected NGRT PDF report.
    """

    selected = get_ngrt_model_by_exam(exam)

    if not selected:
        return {
            "latest_exam": "Invalid NGRT Option",
            "total_students": 0,
            "avg_sas": 0,
            "avg_stanine": 0,
            "attainment": {
                "below_count": 0,
                "average_count": 0,
                "above_count": 0,
                "below_pct": 0,
                "average_pct": 0,
                "above_pct": 0,
            },
            "progress": {
                "lower_count": 0,
                "expected_count": 0,
                "better_count": 0,
                "lower_pct": 0,
                "expected_pct": 0,
                "better_pct": 0,
            },
            "thresholds": {
                "sas_90_count": 0,
                "sas_110_count": 0,
                "sas_120_count": 0,
                "sas_90_pct": 0,
                "sas_110_pct": 0,
                "sas_120_pct": 0,
            },
            "statements": {
                "attainment": "Invalid NGRT report option selected.",
                "progress": "Invalid NGRT report option selected.",
                "threshold": "Invalid NGRT report option selected.",
            },
        }

    exam_label, model = selected

    total_students = (
        db.session.query(func.count(model.id))
        .filter(model.sas.isnot(None))
        .scalar()
        or 0
    )

    if total_students == 0:
        return {
            "latest_exam": exam_label,
            "total_students": 0,
            "avg_sas": 0,
            "avg_stanine": 0,
            "attainment": {
                "below_count": 0,
                "average_count": 0,
                "above_count": 0,
                "below_pct": 0,
                "average_pct": 0,
                "above_pct": 0,
            },
            "progress": {
                "lower_count": 0,
                "expected_count": 0,
                "better_count": 0,
                "lower_pct": 0,
                "expected_pct": 0,
                "better_pct": 0,
            },
            "thresholds": {
                "sas_90_count": 0,
                "sas_110_count": 0,
                "sas_120_count": 0,
                "sas_90_pct": 0,
                "sas_110_pct": 0,
                "sas_120_pct": 0,
            },
            "statements": {
                "attainment": f"No {exam_label} attainment data is available.",
                "progress": f"No {exam_label} progress data is available.",
                "threshold": f"No {exam_label} SAS threshold data is available.",
            },
        }

    avg_sas = (
        db.session.query(func.avg(model.sas))
        .filter(model.sas.isnot(None))
        .scalar()
        or 0
    )

    avg_stanine = (
        db.session.query(func.avg(model.stanine))
        .filter(model.stanine.isnot(None))
        .scalar()
        or 0
    )

    # ------------------------------------------
    # Attainment distribution by stanine
    # 1-3 below average, 4-6 average, 7-9 above average
    # ------------------------------------------
    below_count = (
        db.session.query(func.count(model.id))
        .filter(model.stanine.between(1, 3))
        .scalar()
        or 0
    )

    average_count = (
        db.session.query(func.count(model.id))
        .filter(model.stanine.between(4, 6))
        .scalar()
        or 0
    )

    above_count = (
        db.session.query(func.count(model.id))
        .filter(model.stanine.between(7, 9))
        .scalar()
        or 0
    )

    below_pct = safe_pct(below_count, total_students)
    average_pct = safe_pct(average_count, total_students)
    above_pct = safe_pct(above_count, total_students)

    # ------------------------------------------
    # Progress distribution
    # NGRT-A have no progress_category
    # ------------------------------------------
    lower_count = 0
    expected_count = 0
    better_count = 0

    if hasattr(model, "progress_category"):
        norm_progress = func.lower(func.trim(model.progress_category))

        lower_count = (
            db.session.query(func.count(model.id))
            .filter(norm_progress == "lower than expected")
            .scalar()
            or 0
        )

        expected_count = (
            db.session.query(func.count(model.id))
            .filter(norm_progress == "expected")
            .scalar()
            or 0
        )

        better_count = (
            db.session.query(func.count(model.id))
            .filter(norm_progress == "better than expected")
            .scalar()
            or 0
        )

    progress_total = lower_count + expected_count + better_count

    lower_pct = safe_pct(lower_count, progress_total)
    expected_pct = safe_pct(expected_count, progress_total)
    better_pct = safe_pct(better_count, progress_total)

    # ------------------------------------------
    # Reading literacy thresholds
    # ------------------------------------------
    sas_90_count = (
        db.session.query(func.count(model.id))
        .filter(model.sas.isnot(None), model.sas >= 90)
        .scalar()
        or 0
    )

    sas_110_count = (
        db.session.query(func.count(model.id))
        .filter(model.sas.isnot(None), model.sas >= 110)
        .scalar()
        or 0
    )

    sas_120_count = (
        db.session.query(func.count(model.id))
        .filter(model.sas.isnot(None), model.sas >= 120)
        .scalar()
        or 0
    )

    sas_90_pct = safe_pct(sas_90_count, total_students)
    sas_110_pct = safe_pct(sas_110_count, total_students)
    sas_120_pct = safe_pct(sas_120_count, total_students)

    # ------------------------------------------
    # AI-style interpretation statements
    # ------------------------------------------
    attainment_bands = [
        ("below average", below_count, below_pct),
        ("average", average_count, average_pct),
        ("above average", above_count, above_pct),
    ]

    dominant_attainment = max(attainment_bands, key=lambda x: x[1])

    attainment_statement = (
        f"The cohort is mainly within the {dominant_attainment[0]} stanine band in {exam_label}, "
        f"with {dominant_attainment[1]} students ({dominant_attainment[2]}%)."
    )

    if progress_total > 0:
        progress_bands = [
            ("Lower than Expected", lower_count, lower_pct),
            ("Expected", expected_count, expected_pct),
            ("Better than Expected", better_count, better_pct),
        ]

        dominant_progress = max(progress_bands, key=lambda x: x[1])

        progress_statement = (
            f"Most students with available progress data in {exam_label} are in the "
            f"'{dominant_progress[0]}' category, representing "
            f"{dominant_progress[1]} students ({dominant_progress[2]}%)."
        )
    else:
        progress_statement = (
            f"No progress category data is available for {exam_label}. "
            "This is expected if the selected dataset does not contain progress-category information."
        )

    threshold_statement = (
        f"In {exam_label}, {sas_90_count} students ({sas_90_pct}%) achieved SAS ≥ 90, "
        f"{sas_110_count} students ({sas_110_pct}%) achieved SAS ≥ 110, and "
        f"{sas_120_count} students ({sas_120_pct}%) achieved SAS ≥ 120."
    )

    return {
        "latest_exam": exam_label,
        "total_students": int(total_students),
        "avg_sas": round(float(avg_sas), 0),
        "avg_stanine": round(float(avg_stanine), 0),
        "attainment": {
            "below_count": int(below_count),
            "average_count": int(average_count),
            "above_count": int(above_count),
            "below_pct": below_pct,
            "average_pct": average_pct,
            "above_pct": above_pct,
        },
        "progress": {
            "lower_count": int(lower_count),
            "expected_count": int(expected_count),
            "better_count": int(better_count),
            "lower_pct": lower_pct,
            "expected_pct": expected_pct,
            "better_pct": better_pct,
        },
        "thresholds": {
            "sas_90_count": int(sas_90_count),
            "sas_110_count": int(sas_110_count),
            "sas_120_count": int(sas_120_count),
            "sas_90_pct": sas_90_pct,
            "sas_110_pct": sas_110_pct,
            "sas_120_pct": sas_120_pct,
        },
        "statements": {
            "attainment": attainment_statement,
            "progress": progress_statement,
            "threshold": threshold_statement,
        },
    }

# header and footer function to be called on each page of the PDF report for consistent branding and formatting
# header and footer function to be called on each page of the PDF report
def add_header_footer(canvas, doc, report_title, logo_path=None):
    """
    Adds a fixed header and footer to every PDF page.
    Works for both portrait and landscape pages.
    """

    canvas.saveState()

    # Use the actual page size of the document
    page_width, page_height = doc.pagesize

    left_margin = doc.leftMargin
    right_margin = doc.rightMargin

    # -----------------------------
    # Header positions
    # -----------------------------
    header_y = page_height - 35
    line_y = page_height - 52

    # Title on upper-left
    canvas.setFillColor(colors.HexColor("#111827"))
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(left_margin, header_y, report_title)

    # Logo on upper-right
    if logo_path and os.path.exists(logo_path):
        logo_width = 1.4 * inch
        logo_height = 0.65 * inch

        logo_x = page_width - right_margin - logo_width
        logo_y = page_height - 50

        canvas.drawImage(
            logo_path,
            logo_x,
            logo_y,
            width=logo_width,
            height=logo_height,
            preserveAspectRatio=True,
            mask="auto",
        )

    # Horizontal line below title/logo
    canvas.setStrokeColor(colors.HexColor("#1F2937"))
    canvas.setLineWidth(0.75)
    canvas.line(left_margin, line_y, page_width - right_margin, line_y)

    # -----------------------------
    # Footer
    # -----------------------------
    footer_line_y = 34
    footer_text_y = 20

    canvas.setStrokeColor(colors.HexColor("#9CA3AF"))
    canvas.setLineWidth(0.5)
    canvas.line(left_margin, footer_line_y, page_width - right_margin, footer_line_y)

    footnote = (
        "ExamInsight: Attainment and Progress Tracking in Year 2 Internal Assessments "
        "and External Benchmark Tests at Pristine Private School."
    )

    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#4B5563"))
    canvas.drawString(left_margin, footer_text_y, footnote)

    canvas.restoreState()

# defines the table style of all tables in the PDF report for a consistent look and feel
def _default_table_style():
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]
    )

# --------------------------------------------------
# PDF builder
# --------------------------------------------------
def build_ngrt_summary_pdf(exam):
    """
    Builds the downloadable ExamInsight NGRT PDF report for NGRT-A, NGRT-B, or NGRT-C.
    """

    report = build_ngrt_report_data(exam)

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=60,
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="SmallText",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
        )
    )

    story = []

    # header title and logo path for consistent branding in header/footer function
    report_title = f"ExamInsight: {report['latest_exam']} Summary Report"

    logo_path = os.path.abspath(
        os.path.join(
            "static",
            "assets",
            "images",
            "examinsight-logo.png"
        )
    )

    # ------------------------------------------
    # Title
    # ------------------------------------------
    generated_date = datetime.now().strftime("%A, %d-%b-%Y")
    story.append(Paragraph(f"<b>Date Generated:</b> {generated_date}", styles["Normal"]))
    story.append(Spacer(1, 14))

    story.append(
        Paragraph(
            f"This report summarizes the selected NGRT assessment dataset: <b>{report['latest_exam']}</b>.",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 12))

    # ------------------------------------------
    # KPI Summary Table
    # ------------------------------------------
    summary_data = [
        ["Metric", "Value"],
        ["Selected NGRT Dataset", report["latest_exam"]],
        ["Total Students", report["total_students"]],
        ["Average SAS", safe_number(report["avg_sas"], 0)],
        ["Average Stanine", safe_number(report["avg_stanine"], 0)],
    ]

    summary_table = Table(summary_data, colWidths=[230, 230])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0BA6DF")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story.append(summary_table)
    story.append(Spacer(1, 4))

    # ------------------------------------------
    # Attainment Table
    # ------------------------------------------
    story.append(Paragraph("Attainment Distribution", styles["Heading2"]))

    att = report["attainment"]

    attainment_data = [
        ["Band", "Stanine Range", "Count", "Percentage"],
        ["Below Average", "1–3", att["below_count"], f'{att["below_pct"]}%'],
        ["Average", "4–6", att["average_count"], f'{att["average_pct"]}%'],
        ["Above Average", "7–9", att["above_count"], f'{att["above_pct"]}%'],
    ]

    attainment_table = Table(attainment_data, colWidths=[130, 110, 100, 120])
    attainment_table.setStyle(_default_table_style())
    story.append(attainment_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph(report["statements"]["attainment"], styles["SmallText"]))
    story.append(Spacer(1, 4))

    # ------------------------------------------
    # Progress Table
    # ------------------------------------------
    story.append(Paragraph("Progress Distribution", styles["Heading2"]))

    prog = report["progress"]

    progress_data = [
        ["Category", "Count", "Percentage"],
        ["Lower than Expected", prog["lower_count"], f'{prog["lower_pct"]}%'],
        ["Expected", prog["expected_count"], f'{prog["expected_pct"]}%'],
        ["Better than Expected", prog["better_count"], f'{prog["better_pct"]}%'],
    ]

    progress_table = Table(progress_data, colWidths=[230, 110, 120])
    progress_table.setStyle(_default_table_style())
    story.append(progress_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph(report["statements"]["progress"], styles["SmallText"]))
    story.append(Spacer(1, 4))

    # ------------------------------------------
    # Reading Threshold Table
    # ------------------------------------------
    story.append(Paragraph("Reading Literacy Thresholds", styles["Heading2"]))

    thr = report["thresholds"]

    threshold_data = [
        ["Threshold", "Count", "Percentage"],
        ["SAS ≥ 90", thr["sas_90_count"], f'{thr["sas_90_pct"]}%'],
        ["SAS ≥ 110", thr["sas_110_count"], f'{thr["sas_110_pct"]}%'],
        ["SAS ≥ 120", thr["sas_120_count"], f'{thr["sas_120_pct"]}%'],
    ]

    threshold_table = Table(threshold_data, colWidths=[230, 110, 120])
    threshold_table.setStyle(_default_table_style())
    story.append(threshold_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph(report["statements"]["threshold"], styles["SmallText"]))

    # Build PDF
    # doc.build(story)
    doc.build(
        story,
        onFirstPage=lambda canvas, doc: add_header_footer(
            canvas,
            doc,
            report_title=report_title,
            logo_path=logo_path,
        ),
        onLaterPages=lambda canvas, doc: add_header_footer(
            canvas,
            doc,
            report_title=report_title,
            logo_path=logo_path,
        ),
    )

    buffer.seek(0)
    return buffer

# Builds the downloadable NGRT listing PDF report showing all students
# def build_ngrt_listing_pdf(combined_data, exam_label):
def build_ngrt_listing_pdf(combined_data, exam_label, selected_yrgrp=None):
    """
    Builds the downloadable NGRT listing PDF report for NGRT-A, NGRT-B, and NGRT-C.
    Generates:
    - full cohort listing report
    - class/year group listing report (2-A, 2-B, etc.)
    """

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=28,
        leftMargin=28,
        topMargin=58,
        bottomMargin=50,
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10,
            textColor=colors.HexColor("#111827"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableText",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#4B587C"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallText",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor("#4B587C"),
        )
    )

    story = []

    """ Header title and logo path """
    # report tile changes depending on selected year group
    if selected_yrgrp:
        yrgrp_label = selected_yrgrp.upper()
        report_title = f"ExamInsight: {exam_label} Listing Report for Year {yrgrp_label}"
        report_description = (
            f"This report lists students from <b>Year {yrgrp_label}</b> with "
            f"available data from <b>{exam_label}</b> external benchmark test."
        )
    else:
        yrgrp_label = None
        report_title = f"ExamInsight: {exam_label} Cohort Listing Report"
        report_description = (
            f"This report lists students with available data from <b>{exam_label}</b> "
            f"external benchmark test."
        )

    logo_path = os.path.abspath(
        os.path.join(
            "static",
            "assets",
            "images",
            "examinsight-logo.png"
        )
    )

    # Do not add the title here because the header already draws it.
    generated_date = datetime.now().strftime("%A, %d-%b-%Y")

    story.append(
        Paragraph(
            f"<b>Date Generated:</b> {generated_date}",
            styles["SmallText"]
        )
    )
    story.append(Spacer(1, 4))

    story.append(
        Paragraph(
            # f"This report lists students with available <b>{exam_label}</b> assessment data.",
            report_description,
            styles["SmallText"]
        )
    )
    story.append(Spacer(1, 10))

    # --------------------------------------------------
    # Empty result message
    # --------------------------------------------------
    if not combined_data:
        if selected_yrgrp:
            empty_message = (
                f"No <b>{exam_label}</b> records found for "
                f"<b>Year {selected_yrgrp.upper()}</b>."
            )
        else:
            empty_message = f"No <b>{exam_label}</b> records found."

        story.append(
            Paragraph(
                empty_message,
                styles["TableText"]
            )
        )

        doc.build(
            story,
            onFirstPage=lambda canvas, doc: add_header_footer(
                canvas,
                doc,
                report_title=report_title,
                logo_path=logo_path,
            ),
            onLaterPages=lambda canvas, doc: add_header_footer(
                canvas,
                doc,
                report_title=report_title,
                logo_path=logo_path,
            ),
        )

        buffer.seek(0)
        return buffer
    
    table_data = [
        [
            Paragraph("STUDENT INFORMATION", styles["TableHeader"]),
            Paragraph("NGRT EXAM", styles["TableHeader"]),
            Paragraph("READER PROFILE & DESCRIPTION", styles["TableHeader"]),
        ]
    ]

    for student, ngrt_result in combined_data:
        student_id = clean_pdf_text(student.student_id)
        forename = clean_pdf_text(student.forename)
        surname = clean_pdf_text(student.surname)
        gender = clean_pdf_text(student.gender)
        nationality = clean_pdf_text(student.nationality)
        status = clean_pdf_text(student.status)
        yrgrp = clean_pdf_text((student.yrgrp or "").upper())
        sped = clean_pdf_text(getattr(student, "sped", ""))

        sen_line = ""
        if sped and sped.lower() != "no":
            sen_line = f"<br/><b>SEN Details:</b> {sped}"

        student_info = Paragraph(
            f"""
            <b>{student_id}</b>&nbsp;&nbsp;
            <font color="#F05A28"><b>{forename} {surname}</b></font><br/>
            {gender}, {nationality}<br/>
            {status}, Year {yrgrp}
            {sen_line}
            """,
            styles["TableText"],
        )

        latest_exam = Paragraph(
            f"""
            {exam_label}<br/>
            SAS: {clean_pdf_text(getattr(ngrt_result, "sas", ""))}<br/>
            Stanine: {clean_pdf_text(getattr(ngrt_result, "stanine", ""))}
            """,
            styles["TableText"],
        )

        reader_profile = clean_pdf_text(getattr(ngrt_result, "reader_profile", ""))
        profile_desc = clean_pdf_text(getattr(ngrt_result, "profile_desc", ""))

        if reader_profile and profile_desc:
            profile_text = f"<b>{reader_profile}</b><br/>{profile_desc}"
        elif profile_desc:
            profile_text = profile_desc
        elif reader_profile:
            profile_text = reader_profile
        else:
            profile_text = "No reader profile description available."

        profile_info = Paragraph(profile_text, styles["TableText"])

        table_data.append([student_info, latest_exam, profile_info])

    table = Table(
        table_data,
        colWidths=[3.9 * inch, 1.25 * inch, 5.0 * inch],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),

                # Body
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),

                # Padding
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 1), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 8),

                # Alternating row colours
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.white,
                    colors.HexColor("#FAFAFA"),
                ]),
            ]
        )
    )

    story.append(table)

    doc.build(
        story,
        onFirstPage=lambda canvas, doc: add_header_footer(
            canvas,
            doc,
            report_title=report_title,
            logo_path=logo_path,
        ),
        onLaterPages=lambda canvas, doc: add_header_footer(
            canvas,
            doc,
            report_title=report_title,
            logo_path=logo_path,
        ),
    )

    buffer.seek(0)
    return buffer