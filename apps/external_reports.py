# apps/reports.py

import os
from openai import OpenAI

from io import BytesIO
import tempfile
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.units import inch, mm, cm
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
    Flowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from sqlalchemy import func

from apps import db
from apps.authentication.models import NGRTA, NGRTB, NGRTC, Students

logo_path = os.path.abspath(
        os.path.join(
            "static",
            "assets",
            "images",
            "examinsight-logo.png"
        )
    )

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
        "and External Benchmark Tests at Pristine Private School. | Page %d" % doc.page
    )

    canvas.setFont("Helvetica", 7)
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

    # Title not added here, the header already draws it.
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
            Paragraph("PROGRESS CATEGORY / READER PROFILE & DESCRIPTION", styles["TableHeader"]),
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

        progress_category = clean_pdf_text(getattr(ngrt_result, "progress_category", ""))
        reader_profile = clean_pdf_text(getattr(ngrt_result, "reader_profile", ""))
        profile_desc = clean_pdf_text(getattr(ngrt_result, "profile_desc", ""))

        progcat = (progress_category or "").upper()

        if progress_category and reader_profile and profile_desc:
            profile_text = f"<b>{progcat}</b><br/>{reader_profile}<br/>{profile_desc}"

        elif progress_category:
            profile_text = f"<b>{progcat}</b>"
        elif profile_desc:
            profile_text = profile_desc
        elif reader_profile:
            profile_text = reader_profile
        else:
            profile_text = "No progress category, reader profile, or description available."

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


#***********************************************
#******* Extl Assmt - Individual Report *******#
#***********************************************

# =========================================================
# ExamInsight colours
# =========================================================

EI_BLUE = colors.HexColor("#0BA6DF")
EI_ORANGE = colors.HexColor("#FF6600")
EI_DARK = colors.HexColor("#1F2937")
EI_MUTED = colors.HexColor("#667085")
EI_LIGHT = colors.HexColor("#F8FAFC")
EI_BORDER = colors.HexColor("#D0D5DD")
EI_GREEN = colors.HexColor("#16A34A")
EI_RED = colors.HexColor("#DC2626")
EI_YELLOW = colors.HexColor("#F59E0B")

PAGE_WIDTH, PAGE_HEIGHT = A4

# =========================================================
# NGRT model map
# =========================================================

NGRT_MODELS = {
    "ngrta": {
        "model": NGRTA,
        "label": "NGRT-A"
    },
    "ngrtb": {
        "model": NGRTB,
        "label": "NGRT-B"
    },
    "ngrtc": {
        "model": NGRTC,
        "label": "NGRT-C"
    }
}

LATEST_PRIORITY = ["ngrtc", "ngrtb", "ngrta"]


# =========================================================
# Safe helper functions
# =========================================================

# safe functions to handle None or invalid values when building the PDF report
def safe_text(value, default="-"):
    """
    Returns a safe text value for PDF display.
    """
    if value is None:
        return default

    value = str(value).strip()

    return value if value else default

# safe functions to handle proper float values when building the PDF report
def safe_float(value, default=0):
    """
    Converts a value safely into float.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

# safe functions to handle proper integer values when building the PDF report
def safe_int(value, default=0):
    """
    Converts a value safely into integer.
    """
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default

# helper function to concatenate forename and surname
def full_name(student):
    """
    Builds full name using Students.forename and Students.surname.
    """
    return f"{student.forename or ''} {student.surname or ''}".strip()

# helper function to get SAS value from either SAS or sas field name in the NGRT models
def get_sas(result):
    """
    Handles either SAS or sas field name.
    """
    if not result:
        return None

    return getattr(result, "SAS", None) or getattr(result, "sas", None)

# helper function to determine stanine band based on stanine value
def get_stanine_band(stanine):
    """
    Returns NGRT stanine band.
    """
    value = safe_int(stanine)

    if value <= 3:
        return "Below Average"

    if value <= 6:
        return "Average"

    return "Above Average"

# helper function to display threshold label based on SAS value
def get_threshold_status(sas):
    """
    Returns SAS threshold achievement.
    """
    sas = safe_float(sas)

    return [
        ["SAS >= 90", "Working within reach of age-related expectations", "Achieved" if sas >= 90 else "Target"],
        ["SAS >= 110", "Above-average reading attainment", "Achieved" if sas >= 110 else "Target"],
        ["SAS >= 120", "High-performing reader requiring enrichment", "Achieved" if sas >= 120 else "Target"],
    ]
    
# =========================================================
# Data functions
# =========================================================

# helper function to query the Students table for a given student_id
def get_student(student_id):
    """
    Gets one student using Students.student_id.
    """
    return Students.query.filter_by(student_id=student_id).first()

# helper function to query the appropriate NGRT model for a given student_id and exam_key (ngrta, ngrtb, ngrtc)
def get_student_ngrt(student_id, exam_key):
    """
    Gets one NGRT result for one student.
    """
    model = NGRT_MODELS[exam_key]["model"]

    return model.query.filter(model.student_id == student_id).first()

# helper function to get the latest NGRT result for a student based on priority order (NGRT-C > NGRT-B > NGRT-A)
def get_latest_ngrt_result(student_id):
    """
    Gets the latest available NGRT result.
    Priority:
    NGRT-C -> NGRT-B -> NGRT-A
    """
    for exam_key in LATEST_PRIORITY:
        result = get_student_ngrt(student_id, exam_key)

        if result:
            return exam_key, result

    return None, None

# helper function to build a list of all available NGRT results for a student across NGRT-A, NGRT-B, and NGRT-C
def get_ngrt_history(student_id):
    """
    Gets NGRT-A, NGRT-B, and NGRT-C history for the student.
    """
    history = []

    for exam_key in ["ngrta", "ngrtb", "ngrtc"]:
        result = get_student_ngrt(student_id, exam_key)

        if result:
            history.append({
                "exam_key": exam_key,
                "exam_label": NGRT_MODELS[exam_key]["label"],
                "sas": safe_float(get_sas(result)),
                "stanine": safe_float(getattr(result, "stanine", None)),
                "reading_age": safe_text(getattr(result, "reading_age", None)),
                "progress": safe_text(getattr(result, "progress_category", None))
            })

    return history

# helper function to compute class average and cohort average for a student based on the latest available NGRT exam
def get_class_and_cohort_average(student, latest_exam_key):
    """
    Computes student class average and cohort average using latest NGRT model.
    """
    model = NGRT_MODELS[latest_exam_key]["model"]

    student_yrgrp = safe_text(student.yrgrp, "").lower()

    class_students = Students.query.filter(db.func.lower(Students.yrgrp) == student_yrgrp).all()
    class_ids = [s.student_id for s in class_students]

    class_results = model.query.filter(model.student_id.in_(class_ids)).all()
    cohort_results = model.query.all()

    def average_sas(rows):
        values = [safe_float(get_sas(row), None) for row in rows]
        values = [value for value in values if value is not None]
        return sum(values) / len(values) if values else 0

    def average_stanine(rows):
        values = [safe_float(getattr(row, "stanine", None), None) for row in rows]
        values = [value for value in values if value is not None]
        return sum(values) / len(values) if values else 0

    return {
        "class_avg_sas": average_sas(class_results),
        "cohort_avg_sas": average_sas(cohort_results),
        "class_avg_stanine": average_stanine(class_results),
        "cohort_avg_stanine": average_stanine(cohort_results),
    }

# helper function to build a clean dictionary of all relevant student information 
# and latest NGRT result for use in the individual PDF report
def build_individual_report_data(student_id):
    """
    Creates one clean dictionary for the PDF.
    """
    student = get_student(student_id)

    if not student:
        return None

    latest_exam_key, latest_result = get_latest_ngrt_result(student_id)

    if not latest_result:
        return None

    latest_sas = safe_float(get_sas(latest_result))
    latest_stanine = safe_float(getattr(latest_result, "stanine", None))

    profile = (
        getattr(latest_result, "profile_desc", None)
        or getattr(latest_result, "reader_profile", None)
        or "Reader profile is not available for this student."
    )

    data = {
        "student_id": student.student_id,
        "name": full_name(student),
        "yrgrp": safe_text(student.yrgrp).upper(),
        "gender": safe_text(student.gender),
        "nationality": safe_text(getattr(student, "nationality", None)),
        "status": safe_text(getattr(student, "status", None)),
        "sped": safe_text(getattr(student, "sped", None)),
        "latest_exam_key": latest_exam_key,
        "latest_exam_label": NGRT_MODELS[latest_exam_key]["label"],
        "sas": latest_sas,
        "stanine": latest_stanine,
        "reading_age": safe_text(getattr(latest_result, "reading_age", None)),
        "progress": safe_text(getattr(latest_result, "progress_category", None)),
        "band": get_stanine_band(latest_stanine),
        "reader_profile": profile,
        "history": get_ngrt_history(student_id),
        "thresholds": get_threshold_status(latest_sas),
        "date_generated": datetime.now().strftime("%A, %d-%B-%Y"),
    }

    data["averages"] = get_class_and_cohort_average(student, latest_exam_key)

    return data


# =========================================================
# Custom visual elements
# =========================================================
# custom Flowable classes to draw KPI boxes, stanine scale,
# and SAS line chart in the individual PDF report
class KPIBox(Flowable):
    """
    Draws a KPI card.
    """
    def __init__(self, title, value, subtitle, width=4.2 * cm, height=2.4 * cm):
        Flowable.__init__(self)
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.width = width
        self.height = height

    def draw(self):
        self.canv.setFillColor(colors.white)
        self.canv.setStrokeColor(EI_BORDER)
        self.canv.roundRect(0, 0, self.width, self.height, 8, stroke=1, fill=1)

        # KPI title at the top
        self.canv.setFillColor(EI_MUTED)
        self.canv.setFont("Helvetica", 7)
        self.canv.drawCentredString(self.width / 2, self.height - 16, self.title)

        # KPI value in the middle with wrapping
        value_style = ParagraphStyle(
            name="KPIValueWrapped",
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=14,
            textColor=EI_DARK,
            alignment=TA_CENTER,
        )

        value_paragraph = Paragraph(str(self.value), value_style)

        # Leave padding on left and right
        available_width = self.width - 12

        # Limit available height so it does not overlap title/subtitle
        available_height = self.height - 32

        wrapped_width, wrapped_height = value_paragraph.wrap(
            available_width,
            available_height
        )

        # Center the wrapped value between title and subtitle
        x = 6
        y = (self.height / 2) - (wrapped_height / 2) - 2

        value_paragraph.drawOn(self.canv, x, y)

        # KPI subtitle at the bottom
        self.canv.setFillColor(EI_MUTED)
        self.canv.setFont("Helvetica", 6.5)
        self.canv.drawCentredString(self.width / 2, 10, self.subtitle)

# custom Flowable to draw the stanine scale with the student's stanine marked
class StanineScale(Flowable):
    """
    Draws stanine 1-9 scale and marks the student stanine.
    """
    def __init__(self, stanine, width=17 * cm, height=2.2 * cm):
        Flowable.__init__(self)
        self.stanine = safe_int(stanine)
        self.width = width
        self.height = height

    def draw(self):
        segment = self.width / 9

        for i in range(1, 10):
            x = (i - 1) * segment

            if i <= 3:
                fill = colors.HexColor("#FEE2E2")
            elif i <= 6:
                fill = colors.HexColor("#FEF3C7")
            else:
                fill = colors.HexColor("#DCFCE7")

            self.canv.setFillColor(fill)
            self.canv.setStrokeColor(colors.white)
            self.canv.rect(x, 28, segment, 20, stroke=1, fill=1)

            self.canv.setFillColor(EI_DARK)
            self.canv.setFont("Helvetica-Bold", 8)
            self.canv.drawCentredString(x + segment / 2, 34, str(i))

        if 1 <= self.stanine <= 9:
            marker_x = (self.stanine - 0.5) * segment

            self.canv.setFillColor(EI_BLUE)
            self.canv.circle(marker_x, 58, 5, stroke=0, fill=1)

            self.canv.setFillColor(colors.white)
            self.canv.setFont("Helvetica-Bold", 6)
            self.canv.drawCentredString(marker_x, 56, "S")

            self.canv.setFillColor(EI_MUTED)
            self.canv.setFont("Helvetica", 7)
            self.canv.drawCentredString(marker_x, 68, "Student stanine")

        self.canv.setFillColor(EI_MUTED)
        self.canv.setFont("Helvetica", 7)
        self.canv.drawCentredString(segment * 1.5, 13, "Below Average")
        self.canv.drawCentredString(segment * 4.5, 13, "Average")
        self.canv.drawCentredString(segment * 7.5, 13, "Above Average")

# custom Flowable to draw a simple line chart showing the student's SAS progress across NGRT-A, NGRT-B, and NGRT-C
class SimpleSASLineChart(Flowable):
    """
    Draws a simple SAS progress line chart.
    """
    def __init__(self, history, width=17 * cm, height=6.5 * cm):
        Flowable.__init__(self)
        self.history = history
        self.width = width
        self.height = height

    def draw(self):
        if not self.history:
            return

        labels = [item["exam_label"] for item in self.history]
        values = [item["sas"] for item in self.history]

        x0 = 45
        y0 = 35
        chart_w = self.width - 70
        # give enough vertical space for the title
        chart_h = self.height - 75

        y_min = 60
        y_max = 140

        # Chart title
        self.canv.setFillColor(EI_BLUE)
        self.canv.setFont("Helvetica-Bold", 9)
        self.canv.drawString(0, self.height - 12, "SAS Progress over NGRT Assessments")

        # Chart border
        self.canv.setStrokeColor(EI_BORDER)
        self.canv.rect(x0, y0, chart_w, chart_h, stroke=1, fill=0)

        # Y-axis labels and grid
        for y_value in [60, 70, 80, 90, 100, 110, 120, 130, 140]:
            y = y0 + ((y_value - y_min) / (y_max - y_min)) * chart_h

            self.canv.setStrokeColor(colors.HexColor("#E5E7EB"))
            self.canv.line(x0, y, x0 + chart_w, y)

            self.canv.setFillColor(EI_MUTED)
            self.canv.setFont("Helvetica", 6.5)
            self.canv.drawRightString(x0 - 5, y - 2, str(y_value))

        # SAS 100 guide
        y100 = y0 + ((100 - y_min) / (y_max - y_min)) * chart_h
        self.canv.setStrokeColor(EI_ORANGE)
        self.canv.setDash(3, 3)
        self.canv.line(x0, y100, x0 + chart_w, y100)
        self.canv.setDash()

        points = []

        for i, value in enumerate(values):
            if len(values) == 1:
                x = x0 + chart_w / 2
            else:
                x = x0 + (i / (len(values) - 1)) * chart_w

            y = y0 + ((value - y_min) / (y_max - y_min)) * chart_h
            points.append((x, y))

        self.canv.setStrokeColor(EI_BLUE)
        self.canv.setLineWidth(2)

        for i in range(len(points) - 1):
            self.canv.line(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])

        for i, point in enumerate(points):
            x, y = point

            self.canv.setFillColor(EI_BLUE)
            self.canv.circle(x, y, 4, stroke=0, fill=1)

            self.canv.setFillColor(EI_DARK)
            self.canv.setFont("Helvetica-Bold", 7)
            self.canv.drawCentredString(x, y + 9, f"{values[i]:.0f}")

            self.canv.setFillColor(EI_MUTED)
            self.canv.setFont("Helvetica", 7)
            self.canv.drawCentredString(x, y0 - 14, labels[i])

        self.canv.setFillColor(EI_MUTED)
        self.canv.setFont("Helvetica", 7)
        self.canv.drawString(x0 + chart_w - 65, y100 + 4, "SAS 100 guide")

# custom Flowable to draw a simple bar chart comparing the student's latest SAS with the class average and cohort average for that NGRT exam
class SimpleComparisonBarChart(Flowable):
    """
    Draws Student vs Class Avg vs Cohort Avg chart.
    """
    def __init__(self, student_sas, class_avg, cohort_avg, width=17 * cm, height=6.5 * cm):
        Flowable.__init__(self)
        self.labels = ["Student", "Class Avg", "Cohort Avg"]
        self.values = [student_sas, class_avg, cohort_avg]
        self.width = width
        self.height = height

    def draw(self):
        x0 = 45
        y0 = 35
        chart_w = self.width - 70
        chart_h = self.height - 75

        y_min = 80
        y_max = 140

        self.canv.setFillColor(EI_BLUE)
        self.canv.setFont("Helvetica-Bold", 9)
        self.canv.drawString(0, self.height - 12, "SAS: Student vs Class and Cohort Comparison")

        self.canv.setStrokeColor(EI_BORDER)
        self.canv.rect(x0, y0, chart_w, chart_h, stroke=1, fill=0)

        for y_value in [80, 90, 100, 110, 120, 130, 140]:
            y = y0 + ((y_value - y_min) / (y_max - y_min)) * chart_h
            self.canv.setStrokeColor(colors.HexColor("#E5E7EB"))
            self.canv.line(x0, y, x0 + chart_w, y)

            self.canv.setFillColor(EI_MUTED)
            self.canv.setFont("Helvetica", 6.5)
            self.canv.drawRightString(x0 - 5, y - 2, str(y_value))

        bar_gap = 35
        bar_w = 45

        for i, value in enumerate(self.values):
            x = x0 + 55 + i * (bar_w + bar_gap)
            bar_h = ((value - y_min) / (y_max - y_min)) * chart_h

            self.canv.setFillColor(EI_BLUE if i == 0 else colors.HexColor("#A7DDF4"))
            self.canv.rect(x, y0, bar_w, bar_h, stroke=0, fill=1)

            self.canv.setFillColor(EI_DARK)
            self.canv.setFont("Helvetica-Bold", 7)
            self.canv.drawCentredString(x + bar_w / 2, y0 + bar_h + 6, f"{value:.0f}")

            self.canv.setFillColor(EI_MUTED)
            self.canv.setFont("Helvetica", 7)
            self.canv.drawCentredString(x + bar_w / 2, y0 - 14, self.labels[i])


# =========================================================
# PDF table helpers
# =========================================================
# helper function to create a consistent section title style for the PDF report
def section_title(text, styles):
    return Paragraph(text, styles["SectionTitle"])

# Student information table displaing student details and latest NGRT exam info
def make_student_info_table(data):
    rows = [
        ["Student Name", data["name"], "Student ID", data["student_id"]],
        ["Year Group", data["yrgrp"], "Gender", data["gender"]],
        ["Latest Assessment", data["latest_exam_label"], "Date Generated", data["date_generated"]],
    ]

    table = Table(rows, colWidths=[3.2 * cm, 5.2 * cm, 3.2 * cm, 5.2 * cm])

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F1F5F9")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), EI_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    return table

# KPI table displaying SAS, Stanine, Reading Age, and Progress Category
def make_kpi_table(data):
    kpis = [
        KPIBox("Standard Age Score", f"{data['sas']:.0f}", "SAS around 100 is average"),
        KPIBox("Stanine", f"{data['stanine']:.0f}", "Average range: 4-6"),
        KPIBox("Reading Age", data["reading_age"], "Estimated reading level"),
        KPIBox("Progress Category", data["progress"], "Latest NGRT"),
    ]

    table = Table([kpis], colWidths=[4.25 * cm, 4.25 * cm, 4.25 * cm, 4.25 * cm])

    table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))

    return table

# Reading literacy thresholds table displaying SAS thresholds, 
# their meaning, and whether the student achieved them or not
def make_threshold_table(data):
    rows = [["Reading Literacy Thresholds", "Meaning", "Status"]] + data["thresholds"]

    table = Table(rows, colWidths=[5.0 * cm, 8.2 * cm, 4.0 * cm])

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), EI_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.8),
        ("GRID", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    return table

# Table to display the student's NGRT history with exam label, SAS, Stanine,
# Reading Age, and Progress Category for each assessment taken
def make_history_table(data):
    rows = [["External Benchmark Test", "SAS", "Stanine", "Reading Age", "Progress Category"]]

    for item in data["history"]:
        rows.append([
            item["exam_label"],
            f"{item['sas']:.0f}",
            f"{item['stanine']:.0f}",
            item["reading_age"],
            item["progress"]
        ])

    table = Table(rows, colWidths=[5.0 * cm, 2.2 * cm, 2.2 * cm, 3.0 * cm, 4.6 * cm])

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), EI_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("ALIGN", (1, 1), (2, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    return table

# Helper to create a titled bullet point list for sections like "Strengths" and "Next Steps"
def paragraph_list(title, items, styles):
    """
    Creates a titled bullet list.
    """
    content = [Paragraph(title, styles["BoxTitle"])]

    for item in items:
        content.append(Paragraph(f"- {item}", styles["SmallText"]))

    return content


# =========================================================
# Interpretation helpers
# =========================================================

# Rule-based interpretation of SAS score with friendly language and practical next steps
def get_sas_description(sas):
    """
    Returns a friendly SAS interpretation based on the student's score.
    """
    sas = safe_float(sas)

    if sas >= 120:
        return (
            "The SAS result indicates exceptionally high reading performance. "
            "This suggests that the student is working well above the typical age-related range. "
            "The student may benefit from enrichment activities, challenging texts, and higher-order comprehension tasks."
        )

    if sas >= 110:
        return (
            "The SAS result indicates strong reading performance above the expected range. "
            "This suggests that the student is likely showing secure reading accuracy, fluency, vocabulary understanding, and comprehension. "
            "The student should continue to be challenged with texts that extend thinking and deepen understanding."
        )

    if sas >= 90:
        return (
            "The SAS result indicates a secure foundation for age-related reading. "
            "This suggests that the student is approaching or working within the expected reading range. "
            "The student may still benefit from regular reading practice, vocabulary development, and guided comprehension support."
        )

    return (
        "The SAS result indicates that the student may need targeted reading support. "
        "This suggests that the student may find some age-related texts challenging without additional guidance. "
        "The student would benefit from regular guided reading, vocabulary development, fluency practice, and structured comprehension support."
    )

# =============================================================================
# OpenAI interpretation function for SAS and score interpretation with fallback
# =============================================================================
def generate_ai_sas_interpretation(data):
    """
    Uses OpenAI to generate a friendly SAS description/interpretation.
    Falls back to the rule-based interpretation if the AI call fails.
    """
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""
    Write a friendly and teacher-useful interpretation of the student's performance based on the provided data.

    Student name: {data.get("name")}
    Gender: {data.get("gender")}
    Latest assessment: {data.get("latest_exam_label")}
    SAS: {data.get("sas")}
    Stanine: {data.get("stanine")}
    Stanine band: {data.get("band")}
    Reading age: {data.get("reading_age")}
    Progress category: {data.get("progress")}

    Requirements:
    - Write exactly 10 concise sentences.
    - Keep each sentence short, around 12 to 18 words.
    - Use a professional school report tone.
    - Avoid overly negative language.
    - Talk about the student's Stanine and Stanine band in relation to the SAS score.
    - Include what the profile suggests about the student's reading development.
    - Relate the SAS score to age-related expectations.
    - Include practical next-step support.
    - Do not use bullet points.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an educational data analyst writing professional tone student profile based on Stanine, stanine band, and SAS score interpretations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_tokens=380
    )

    return response.choices[0].message.content.strip()

# Main interpretation function for the student's score
def score_interpretation(data):
    try:
        sas_interpretation = generate_ai_sas_interpretation(data)
        return sas_interpretation
    except Exception:
        sas_description = get_sas_description(data["sas"])
        return (
            f"{data['name']} achieved a SAS of {data['sas']:.0f} and a stanine of "
            f"{data['stanine']:.0f} in the latest external benchmark assessment, {data['latest_exam_label']}. "
            f"This places the student within the {data['band'].lower()} stanine range. "
            f"{sas_description} "
            f"The student's reading age is {data['reading_age']}, which provides an estimate of the reading level demonstrated during the assessment. "
            f"These results should be considered alongside classroom reading evidence, teacher observations, and ongoing guided reading performance."
        )

# Interpretation of the student's progress over time based on historical NGRT data
def progress_interpretation(data):
    if len(data["history"]) < 2:
        return "Interpretation: There is currently limited historical NGRT data available for this student."

    first = data["history"][0]["sas"]
    latest = data["history"][-1]["sas"]

    if latest > first:
        return (
            f"<b>Interpretation:</b> {data['name']} has improved from {data['history'][0]['exam_label']} "
            f"to {data['history'][-1]['exam_label']} and is moving closer to the age-related average benchmark. "
            "This positive movement suggests that the student is developing greater confidence and consistency in reading. "
            "Continued guided reading, vocabulary practice, and regular comprehension discussions will help sustain this progress. "
            "Continue to monitor the student's fluency and understanding to ensure that progress is maintained over time."
        )

    if latest == first:
        return (
            f"<b>Interpretation:</b> {data['name']} has maintained a stable SAS across the available NGRT assessments. "
            "This suggests that the student's reading performance has remained consistent over time. "
            "The student may benefit from targeted support to help move beyond the current level and make further gains. "
            "Regular reading practice, vocabulary development, and focused comprehension tasks can help strengthen future progress."
        )

    return (
        f"<b>Interpretation:</b> {data['name']} has a lower SAS in the latest assessment compared with the first available result. "
        "This should be reviewed alongside classroom reading evidence, teacher observations, and guided reading performance. "
        "The result may indicate a need for closer monitoring and more targeted reading support. "
        "Short, regular reading activities focusing on fluency, vocabulary, and comprehension may help rebuild confidence. "
        "Track progress carefully in future assessments to check whether support is having a positive impact."
    )

# ===========================================================
# OpenAI interpretation function for strengths with fallback
# ===========================================================
def generate_ai_strengths_interpretation(data):
    """
    Uses OpenAI to generate student strengths based on NGRT data.
    Falls back to the rule-based strengths list if the AI call fails.
    """

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Prepare history as readable text for the AI prompt.
        history_text = ""

        for item in data.get("history", []):
            history_text += (
                f"{item.get('exam_label')}: "
                f"SAS {item.get('sas')}, "
                f"Stanine {item.get('stanine')}, "
                f"Reading Age {item.get('reading_age')}, "
                f"Progress {item.get('progress')}\n"
            )

        prompt = f"""
        Write strengths for a student's NGRT external benchmark report.

        Student name: {data.get("name")}
        Gender: {data.get("gender")}
        Latest assessment: {data.get("latest_exam_label")}
        SAS: {data.get("sas")}
        Stanine: {data.get("stanine")}
        Stanine band: {data.get("band")}
        Reading age: {data.get("reading_age")}
        Progress category: {data.get("progress")}

        NGRT history:
        {history_text}

        Requirements:
        - Write exactly 3 concise strengths.
        - Each strength should be one sentence.
        - Use a professional school report tone.
        - Be positive and evidence-based.
        - Mention attainment, progress, or reading development where appropriate.
        - Avoid overly negative language.
        - Do not number the strengths.
        - Do not use bullet points.
        - Return each strength on a new line.
        - Start each line with "-"
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an educational data analyst writing strengths for student reading assessment reports."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=180
        )

        # Convert AI response into a clean Python list.
        ai_text = response.choices[0].message.content.strip()

        strengths_list = [
            line.strip("-• ").strip()
            for line in ai_text.splitlines()
            if line.strip()
        ]

        return strengths_list[:3]

    except Exception:
        return strengths(data)
    
# Interpretation of the student's strengths based on their latest NGRT data and historical progress, 
# using rule-based logic to identify key positive aspects of their reading performance
def strengths(data):
    items = []

    if data["stanine"] >= 4:
        items.append("Working within the average stanine range.")
    else:
        items.append("Assessment data clearly identifies reading support needs.")

    if len(data["history"]) >= 2 and data["history"][-1]["sas"] >= data["history"][0]["sas"]:
        items.append("Shows steady improvement across the assessment cycle.")

    if data["progress"].lower() == "expected":
        items.append("Maintained expected progress in the latest NGRT assessment.")
    elif "better" in data["progress"].lower():
        items.append("Achieved better than expected progress in the latest NGRT assessment.")
    else:
        items.append("Progress category can help guide targeted reading intervention.")

    return items

# Interpretation of the student's development points based on their latest NGRT data and historical progress, 
# using rule-based logic to identify key areas where the student may need additional support in their reading
def development_points(data):
    return [
        "Build reading fluency through daily reading practice.",
        "Strengthen vocabulary understanding in fiction and non-fiction texts.",
        "Answer why, how, and evidence-based comprehension questions."
    ]

# Interpretation of practical next steps for the student based on their latest NGRT data and historical progress, 
# using rule-based logic to suggest actionable strategies for supporting the student's reading development at home and in
def next_steps(data):
    return [
        "Read for 15 minutes daily at home.",
        "Use guided reading questions before, during, and after reading.",
        "Monitor fluency and comprehension weekly in class."
    ]

# ================================================================
# OpenAI interpretation function for reader profiles with fallback
# ================================================================
def generate_ai_reader_profile_interpretation(data):
    """
    Uses OpenAI to generate a friendly reader profile interpretation.
    Falls back to the rule-based interpretation if the AI call fails.
    """

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        prompt = f"""
        Write a parent-friendly and teacher-useful interpretation of this NGRT reader profile.

        Student name: {data.get("name")}
        Gender: {data.get("gender")}
        Latest assessment: {data.get("latest_exam_label")}
        Reader profile: {data.get("reader_profile")}

        Requirements:
        - Write exactly 8 concise sentences.
        - Keep each sentence around 10 to 16 words.
        - Use a professional school report tone.
        - Avoid overly negative language.
        - Include what the reader profile suggests.
        - Include practical next-step reading support based on the indicated reader profile.
        - Do not use bullet points.
        - Include the actual reader profile text as the first sentence.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an educational data analyst writing parent-friendly reading assessment interpretations based on the student's reader profile."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=320
        )

        return response.choices[0].message.content.strip()

    except Exception:
        return data.get("reader_profile", "Reader profile is not available for this student.")
    
# =========================================================
# Main PDF builder
# =========================================================

# This function generates the individual NGRT PDF report by building the necessary data, 
# setting up the PDF document, defining styles, and assembling the content into a structured report format. 
# It includes error handling to return None if data is missing or if any issues arise during PDF generation.
def generate_ngrt_indv_extl_rpt(student_id):
    """
    Generates the individual NGRT PDF report.
    This is called by the route in routess.py.
    """
    data = build_individual_report_data(student_id)

    if not data:
        return None

    output_path = os.path.join(
        tempfile.gettempdir(),
        f"examinsight_individual_ngrt_external_{student_id}.pdf"
    )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=2.0 * cm,
        bottomMargin=1.6 * cm
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=EI_DARK,
        alignment=TA_LEFT,
        spaceAfter=4
    ))

    styles.add(ParagraphStyle(
        name="SubTitle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=EI_MUTED,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="SectionTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        textColor=EI_BLUE,
        spaceBefore=8,
        spaceAfter=5
    ))

    styles.add(ParagraphStyle(
        name="SmallText",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=EI_DARK,
        spaceAfter=3
    ))

    styles.add(ParagraphStyle(
        name="BoxTitle",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=EI_DARK,
        spaceAfter=5
    ))

    story = []

    # =====================================================
    # Page 1
    # =====================================================

    story.append(section_title("External Benchmark Test", styles))
    story.append(Paragraph(
        "This report provides an overview of the student's reading attainment and progress across the available NGRT assessments. "
        "It summarises key scores including SAS, stanine, reading age, progress category, reading thresholds, and reader profile. "
        "The information presented is intended to support parent communication, teacher planning, intervention tracking, and next-step reading support.",
        styles["SubTitle"]
    ))

    story.append(make_student_info_table(data))
    story.append(Spacer(1, 10))

    story.append(make_kpi_table(data))
    story.append(Spacer(1, 10))

    story.append(section_title("Score Interpretation", styles))
    story.append(Paragraph(score_interpretation(data), styles["SmallText"]))
    story.append(Spacer(1, 10))

    story.append(section_title("Attainment Band", styles))
    story.append(Spacer(1, 8))
    story.append(StanineScale(data["stanine"]))
    story.append(Spacer(1, 10))

    story.append(make_threshold_table(data))
    story.append(Spacer(1, 10))

    story.append(section_title("Reader Profile", styles))
    # story.append(Paragraph(data["reader_profile"], styles["SmallText"]))
    # generate AI interpretation with fallback to rule-based text if AI fails
    reader_profile_text = generate_ai_reader_profile_interpretation(data)
    story.append(Paragraph(reader_profile_text, styles["SmallText"]))

    story.append(PageBreak())

    # =====================================================
    # Page 2
    # =====================================================

    story.append(section_title("Progress across all External Benchmark Tests (NGRT)", styles))
    story.append(Paragraph(
        "This section tracks the student’s performance across all available NGRT external benchmark tests "
        "to support evidence-based intervention and progress monitoring.",
        styles["SubTitle"]
    ))

    story.append(make_history_table(data))
    story.append(Spacer(1, 10))

    story.append(SimpleSASLineChart(data["history"]))
    story.append(Spacer(1, 2))
    story.append(Paragraph(progress_interpretation(data), styles["SmallText"]))
    story.append(Spacer(1, 10))

    story.append(SimpleComparisonBarChart(
        student_sas=data["sas"],
        class_avg=data["averages"]["class_avg_sas"],
        cohort_avg=data["averages"]["cohort_avg_sas"]
    ))
    story.append(Spacer(1, 2))
    story.append(Paragraph(
        "The comparison chart shows the student's latest SAS against the class and cohort averages. "
        "This helps identify whether the student is performing broadly in line with peers or may need additional support. "
        "It should be interpreted alongside classroom reading evidence, teacher observations, and progress across previous NGRT assessments.",
        styles["SmallText"]
    ))

    story.append(Spacer(1, 4))

    # Three support columns
    support_table = Table(
        [[
            paragraph_list("Strengths", generate_ai_strengths_interpretation(data), styles),
            paragraph_list("Areas for Development", development_points(data), styles),
            paragraph_list("Recommended Next Steps", next_steps(data), styles),
        ]],
        colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm]
    )

    support_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(support_table)

    doc.build(
        story,
        onFirstPage=lambda canvas, doc: add_header_footer(
            canvas,
            doc,
            report_title="ExamInsight: NGRT Individual Student Report",
            logo_path=logo_path
        ),
        onLaterPages=lambda canvas, doc: add_header_footer(
            canvas,
            doc,
            report_title="ExamInsight: NGRT Individual Student Report",
            logo_path=logo_path
        ),
    )

    return output_path