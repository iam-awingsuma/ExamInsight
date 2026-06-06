# apps/reports.py

import os
import re
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
from urllib.parse import urlencode
import requests

from flask import request

from sqlalchemy import func

from apps import db
from apps.authentication.models import NGRTA, NGRTB, NGRTC, Students, InternalExam

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

# returns blank white space if value is None
def clean_pdf_text(value, default=""):
    if value is None:
        return default
    return escape(str(value).strip())

# returns "-"" if the value is null
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
        "and External Benchmark Tests at Pristine Private School"
    )

    page_number = "| Page %d" % doc.page

    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#4B5563"))

    # Footer text on the left
    canvas.drawString(
        left_margin,
        footer_text_y,
        footnote
    )

    # Page number aligned to the right-most margin
    canvas.drawRightString(
        page_width - right_margin,
        footer_text_y,
        page_number
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
    generated_date = datetime.now().strftime("%a, %d-%b-%Y")
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
    generated_date = datetime.now().strftime("%a, %d-%b-%Y")

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

# Soft background colours
EI_BLUE_BG = colors.HexColor("#E0F2FE")
EI_GREEN_BG = colors.HexColor("#DCFCE7")
EI_YELLOW_BG = colors.HexColor("#FEF3C7")
EI_RED_BG = colors.HexColor("#FEE2E2")
EI_ORANGE_BG = colors.HexColor("#FFEDD5")

PAGE_WIDTH, PAGE_HEIGHT = A4


#***********************************************
#******* Extl Assmt - Individual Report *******#
#***********************************************

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
        "date_generated": datetime.now().strftime("%a, %d-%b-%Y"),
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

        # KPI title at the top
        self.canv.setFillColor(EI_DARK)
        self.canv.setFont("Helvetica-Bold", 8)
        self.canv.drawCentredString(self.width / 2, self.height - 16, self.title)

        # KPI value in the middle with wrapping
        value_style = ParagraphStyle(
            name="KPIValueWrapped",
            fontName="Helvetica-Bold",
            fontSize=15,
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
        y = (self.height / 2) - (wrapped_height / 2) + 2

        value_paragraph.drawOn(self.canv, x, y)

        # KPI subtitle at the bottom
        self.canv.setFillColor(EI_MUTED)
        self.canv.setFont("Helvetica", 7)
        self.canv.drawCentredString(self.width / 2, 8, self.subtitle)

# custom Flowable to draw the stanine scale with the student's stanine marked
class StanineScale(Flowable):
    """
    Draws stanine 1-9 scale and marks the student stanine.
    """
    def __init__(self, stanine, student_full_name="Student", width=17 * cm, height=2.2 * cm):
        Flowable.__init__(self)
        self.stanine = safe_int(stanine)
        self.width = width
        self.height = height
        self.student_full_name = student_full_name

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
            # self.canv.drawCentredString(marker_x, 68, "Student Stanine")
            self.canv.drawCentredString(marker_x, 68, f"{self.student_full_name}'s Stanine")

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
        self.canv.drawString(0, self.height - 12, "SAS Progress across NGRT Assessments")

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
        self.canv.drawString(x0 + chart_w - 65, y100 + 4, "Avg SAS: 100")

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
        self.canv.drawString(0, self.height - 12, "Reading Literacy: Student vs Class and Cohort Average SAS Comparison")

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

    # table.setStyle(TableStyle([
    #     ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    #     ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    #     ("LEFTPADDING", (0, 0), (-1, -1), 2),
    #     ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    # ]))

    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("BACKGROUND", (0, 0), (0, 0), EI_BLUE_BG),
        ("BACKGROUND", (1, 0), (1, 0), EI_GREEN_BG),
        ("BACKGROUND", (2, 0), (2, 0), EI_YELLOW_BG),
        ("BACKGROUND", (3, 0), (3, 0), EI_RED_BG),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    return table

# Reading literacy thresholds table displaying SAS thresholds, 
# their meaning, and whether the student achieved them or not
def make_threshold_table(data):
    rows = [["Reading Literacy Thresholds", "Meaning", "Status"]] + data["thresholds"]

    status_styles = []

    # Start at row 1 because row 0 is the header
    for row_index, row in enumerate(data["thresholds"], start=1):
        status = str(row[2]).strip().lower()

        if status == "achieved":
            # bg_color = colors.HexColor("#DCFCE7")    # light green
            # text_color = colors.HexColor("#166534")  # green text
            bg_color = EI_GREEN_BG    # light green
            text_color = EI_GREEN  # green text
        else:
            # bg_color = colors.HexColor("#FEF3C7")    # light yellow
            # text_color = colors.HexColor("#92400E")  # yellow/brown text
            bg_color = EI_YELLOW_BG    # light yellow
            text_color = EI_YELLOW  # yellow/brown text

        status_styles.extend([
            ("BACKGROUND", (2, row_index), (2, row_index), bg_color),
            ("TEXTCOLOR", (2, row_index), (2, row_index), text_color),
            ("FONTNAME", (2, row_index), (2, row_index), "Helvetica"),
        ])

    table = Table(rows, colWidths=[5.0 * cm, 8.2 * cm, 4.0 * cm])

    base_styles = [
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
    ]

    table.setStyle(TableStyle(base_styles + status_styles))

    return table

# Table to display the student's NGRT history with exam label, SAS, Stanine,
# Reading Age, and Progress Category for each assessment taken
# def make_history_table(data):
#     rows = [["External Benchmark Test", "SAS", "Stanine", "Reading Age", "Progress Category"]]

#     for item in data["history"]:
#         progress_value = str(item.get("progress", "-")).strip()

#         rows.append([
#             item["exam_label"],
#             f"{item['sas']:.0f}",
#             f"{item['stanine']:.0f}",
#             item["reading_age"],
#             "No Progress Available" if progress_value == "-" else progress_value
#         ])

#     table = Table(rows, colWidths=[4.8 * cm, 2.2 * cm, 2.2 * cm, 2.8 * cm, 4.8 * cm])

#     table.setStyle(TableStyle([
#         ("BACKGROUND", (0, 0), (-1, 0), EI_BLUE),
#         ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
#         ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
#         ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
#         ("FONTSIZE", (0, 0), (-1, -1), 8),
#         ("GRID", (0, 0), (-1, -1), 0.4, EI_BORDER),
#         ("ALIGN", (1, 1), (2, -1), "CENTER"),
#         ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
#         ("TOPPADDING", (0, 0), (-1, -1), 5),
#         ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
#     ]))

#     return table

def make_history_table(data):
    rows = [["External Benchmark Test", "SAS", "Stanine", "Reading Age", "Progress Category"]]

    progress_styles = []

    for row_index, item in enumerate(data["history"], start=1):
        progress_value = str(item.get("progress", "-")).strip()

        display_progress = "No Progress Available" if progress_value == "-" else progress_value

        rows.append([
            item["exam_label"],
            f"{item['sas']:.0f}",
            f"{item['stanine']:.0f}",
            item["reading_age"],
            display_progress
        ])

        progress_lower = display_progress.lower()

        if progress_lower == "no progress available":
            bg_color = EI_BLUE_BG
            text_color = EI_BLUE
            font_name = "Helvetica"

        elif progress_lower == "lower than expected":
            bg_color = EI_RED_BG    # light red
            text_color = EI_RED  # red text
            font_name = "Helvetica"

        elif progress_lower == "expected":
            bg_color = EI_YELLOW_BG    # light yellow
            text_color = EI_YELLOW  # yellow text
            font_name = "Helvetica"

        elif progress_lower == "better than expected":
            bg_color = EI_GREEN_BG    # light green
            text_color = EI_GREEN  # green text
            font_name = "Helvetica"

        else:
            bg_color = colors.white
            text_color = colors.black
            font_name = "Helvetica"

        progress_styles.extend([
            ("BACKGROUND", (4, row_index), (4, row_index), bg_color),
            ("TEXTCOLOR", (4, row_index), (4, row_index), text_color),
            ("FONTNAME", (4, row_index), (4, row_index), font_name),
            ("ALIGN", (4, row_index), (4, row_index), "CENTER"),
        ])

    table = Table(rows, colWidths=[4.8 * cm, 2.2 * cm, 2.2 * cm, 2.8 * cm, 4.8 * cm])

    base_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), EI_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("ALIGN", (1, 1), (2, -1), "CENTER"),
        ("ALIGN", (4, 1), (4, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]

    table.setStyle(TableStyle(base_styles + progress_styles))

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

# ==============================================
# OpenAI interpretation function for strengths,
# areas for development, and next steps
# with fallback functions
# ===============================================
def generate_ai_profile_support(data):
    """
    Uses OpenAI to generate:
    1. Strengths
    2. Areas for Development
    3. Recommended Next Steps

    Returns a dictionary with three separate lists.
    Falls back to rule-based functions if the AI call fails or parsing is incomplete.
    """

    try:
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing or not loaded.")

        client = OpenAI(api_key=api_key)

        # Prepare NGRT history for the AI prompt.
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
        Write reading profile support statements for a student's NGRT external benchmark report.

        Student name: {data.get("name")}
        Gender: {data.get("gender")}
        Latest assessment: {data.get("latest_exam_label")}
        SAS: {data.get("sas")}
        Stanine: {data.get("stanine")}
        Stanine band: {data.get("band")}
        Reading age: {data.get("reading_age")}
        Progress category: {data.get("progress")}
        Reader profile: {data.get("reader_profile")}

        NGRT history:
        {history_text}

        Requirements:
        Create three separate sections using these exact headings:
        Strengths:
        Areas for Development:
        Recommended Next Steps:

        Under each heading:
        - Write exactly 3 concise statements.
        - Each statement should be one sentence.
        - Start each statement with "-".
        - Use a professional school report tone.
        - Be positive, supportive, and evidence-based.
        - Avoid overly negative language.
        - Do not number the statements.

        Content guidance:
        - Strengths should focus on attainment, progress, reading confidence, or reading development.
        - Areas for Development should identify reading skills that need further practice.
        - Recommended Next Steps should include practical support for fluency, vocabulary, and comprehension.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an educational data analyst writing strengths, areas for development, "
                        "and recommended next steps for student NGRT reading assessment reports."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=500
        )

        ai_text = response.choices[0].message.content.strip()

        return parse_ai_support_sections(ai_text, data)

    except Exception as e:

        return {
            "strengths": strengths(data),
            "development_areas": development_points(data),
            "next_steps": next_steps(data)
        }


def parse_ai_support_sections(ai_text, data):
    """
    Parses AI response into three separate lists:
    strengths, development areas, and next steps.

    This version accepts:
    - bullets starting with -
    - bullets starting with •
    - bullets starting with *
    - numbered items like 1.
    - headings with markdown bold, e.g. **Strengths:**
    """

    sections = {
        "strengths": [],
        "development_areas": [],
        "next_steps": []
    }

    current_section = None

    for line in ai_text.splitlines():
        clean_line = line.strip()

        if not clean_line:
            continue

        # Remove markdown bold markers.
        heading_line = clean_line.replace("*", "").strip().lower()

        # Detect headings flexibly.
        if heading_line.startswith("strengths"):
            current_section = "strengths"
            continue

        if heading_line.startswith("areas for development"):
            current_section = "development_areas"
            continue

        if heading_line.startswith("recommended next steps"):
            current_section = "next_steps"
            continue

        if not current_section:
            continue

        # Remove bullet symbols or numbering.
        statement = re.sub(r"^[-•*]\s*", "", clean_line)
        statement = re.sub(r"^\d+[\).\s]+", "", statement)
        statement = statement.strip()

        # Avoid accidentally storing headings as statements.
        if statement.lower() in [
            "strengths:",
            "areas for development:",
            "recommended next steps:"
        ]:
            continue

        if statement:
            sections[current_section].append(statement)

    # Fallback only for the section that failed.
    if len(sections["strengths"]) < 3:
        sections["strengths"] = strengths(data)

    if len(sections["development_areas"]) < 3:
        sections["development_areas"] = development_points(data)

    if len(sections["next_steps"]) < 3:
        sections["next_steps"] = next_steps(data)

    # Keep only 3 statements per section.
    sections["strengths"] = sections["strengths"][:3]
    sections["development_areas"] = sections["development_areas"][:3]
    sections["next_steps"] = sections["next_steps"][:3]

    return sections
   
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

# =================================================
# OpenAI interpretation function for considerations
# for a class teacher and considerations for a
# reading specialist with fallback functions
# =================================================
def generate_ai_considerations_support(data):
    """
    Uses OpenAI to generate:
    1. Considerations for the Class Teacher
    2. Considerations for the Reading Specialist

    Returns a dictionary with two separate lists.
    Falls back to rule-based functions if the AI call fails or parsing is incomplete.
    """

    try:
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing or not loaded.")

        client = OpenAI(api_key=api_key)

        # Prepare NGRT history for the AI prompt.
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
        Write reading profile considerations for a student's NGRT external benchmark report.

        Student name: {data.get("name")}
        Gender: {data.get("gender")}
        Latest assessment: {data.get("latest_exam_label")}
        SAS: {data.get("sas")}
        Stanine: {data.get("stanine")}
        Stanine band: {data.get("band")}
        Reading age: {data.get("reading_age")}
        Progress category: {data.get("progress")}
        Reader profile: {data.get("reader_profile")}

        NGRT history:
        {history_text}

        Requirements:
        Create two separate sections using these exact headings:
        Considerations for a Class Teacher:
        Considerations for a Reading Specialist:

        Under each heading:
        - Write exactly 3 comprehensive statements.
        - Each statement should be one sentence.
        - Start each statement with "-".
        - Use a professional school report tone.
        - Be positive, supportive, and evidence-based.
        - Avoid overly negative language.
        - Do not number the statements.

        Content guidance:
        - Considerations for a Class Teacher should focus on classroom-based opportunities to strengthen reading development through guided reading, vocabulary practice, fluency routines, comprehension questioning, and regular reading exposure.
        - Considerations for a Reading Specialist should identify specific reading skills requiring targeted support, intervention, or extension, such as decoding, fluency, vocabulary, inference, comprehension, reading stamina, or confidence.
        - Both sections should be evidence-based, practical, supportive, and linked to the student’s NGRT data, reader profile, progress category, SAS, and stanine band.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an educational data analyst writing professional, evidence-based NGRT reading assessment guidance. "
                        "Write practical considerations for class teachers and reading specialists based on the student's SAS, stanine, "
                        "stanine band, reading age, progress category, reader profile, and NGRT history. "
                        "Use a supportive school-report tone, avoid overly negative language, and provide clear next-step guidance "
                        "for classroom reading development and targeted reading intervention."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=380
        )

        ai_text = response.choices[0].message.content.strip()

        return parse_ai_considerations_sections(ai_text, data)

    except Exception as e:

        return {
            "class_teacher": class_teacher_considerations(data),
            "reading_specialist": reading_specialist_considerations(data),
        }

# Helper function to parse the AI response into two separate lists for class teacher and reading specialist considerations
def parse_ai_considerations_sections(ai_text, data):
    """
    Parses AI response into two separate lists:
    considerations for the class teacher and considerations for the reading specialist.

    This version accepts:
    - bullets starting with -
    - bullets starting with •
    - bullets starting with *
    - numbered items like 1.
    - headings with markdown bold, e.g. **Strengths:**
    """

    sections = {
        "class_teacher": [],
        "reading_specialist": [],
    }

    current_section = None

    for line in ai_text.splitlines():
        clean_line = line.strip()

        if not clean_line:
            continue

        # Remove markdown bold markers.
        heading_line = clean_line.replace("*", "").strip().lower()

        # Detect headings flexibly.
        if heading_line.startswith("considerations for a class teacher"):
            current_section = "class_teacher"
            continue

        if heading_line.startswith("considerations for a reading specialist"):
            current_section = "reading_specialist"
            continue

        if not current_section:
            continue

        # Remove bullet symbols or numbering.
        statement = re.sub(r"^[-•*]\s*", "", clean_line)
        statement = re.sub(r"^\d+[\).\s]+", "", statement)
        statement = statement.strip()

        # Avoid accidentally storing headings as statements.
        if statement.lower() in [
            "considerations for a class teacher:",
            "considerations for a reading specialist:"
        ]:
            continue

        if statement:
            sections[current_section].append(statement)

    # Fallback only for the section that failed.
    if len(sections["class_teacher"]) < 3:
        sections["class_teacher"] = class_teacher_considerations(data)

    if len(sections["reading_specialist"]) < 3:
        sections["reading_specialist"] = reading_specialist_considerations(data)

    # Keep only 3 statements per section.
    sections["class_teacher"] = sections["class_teacher"][:3]
    sections["reading_specialist"] = sections["reading_specialist"][:3]

    return sections

# Rule-based considerations for the class teacher based on the student's NGRT data, reader profile, and progress category,
def class_teacher_considerations(data):
    return [
        "Provide regular guided reading sessions focusing on the student's reading level.",
        "Incorporate vocabulary instruction linked to the student's reader profile.",
        "Use comprehension questioning strategies to deepen understanding during reading."
    ]

# Rule-based considerations for the reading specialist based on the student's NGRT data, reader profile, and progress category,
def reading_specialist_considerations(data):
    return [
        "Target decoding and fluency skills through structured intervention sessions.",
        "Focus on vocabulary development using both fiction and non-fiction texts.",
        "Support inference and comprehension skills with evidence-based strategies."
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

# Helper function to set up the PDF document, styles, and story list.
# reuse across different report types while maintaining a consistent format and style throughout the reports.
def setup_individual_report_pdf(output_path):
    """
    Creates the shared PDF document setup, styles, and story list
    for individual assessment reports.

    Can be reused for:
    - External assessment individual reports, such as NGRT
    - Internal assessment individual reports, such as English, Mathematics, and Science
    """

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=2.0 * cm,
        bottomMargin=1.6 * cm
    )

    styles = getSampleStyleSheet()

    if "ReportTitle" not in styles:
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

    if "SubTitle" not in styles:
        styles.add(ParagraphStyle(
            name="SubTitle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=EI_MUTED,
            spaceAfter=8
        ))

    if "SectionTitle" not in styles:
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

    if "SmallText" not in styles:
        styles.add(ParagraphStyle(
            name="SmallText",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=EI_DARK,
            spaceAfter=3
        ))

    if "BoxTitle" not in styles:
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

    return doc, styles, story
    
# =============================================================================
# Main PDF builder - external assessments (Assessment Data + Report Generation)
# =============================================================================

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

    doc, styles, story = setup_individual_report_pdf(output_path)

    # =====================================================
    # Page 1
    # =====================================================

    story.append(section_title("External Benchmark Test", styles))
    story.append(Paragraph(
        "This report provides an overview of the student's reading attainment and progress across the available NGRT assessments. "
        "It summarises key scores including SAS, stanine, reading age, progress category, reading thresholds, and reader profile. "
        "The information presented is intended to support parent communication, teacher planning, intervention tracking, and next-step reading support.",
        styles["SmallText"]
    ))
    story.append(Spacer(1, 10))

    story.append(make_student_info_table(data))
    story.append(Spacer(1, 10))

    story.append(make_kpi_table(data))
    story.append(Spacer(1, 10))

    story.append(section_title("Score Interpretation", styles))
    story.append(Paragraph(score_interpretation(data), styles["SmallText"]))
    story.append(Spacer(1, 10))

    story.append(section_title("Attainment Band", styles))
    story.append(Spacer(1, 10))

    student_full_name = data.get("name", "Student")
    story.append(StanineScale(data["stanine"], student_full_name))
    story.append(Spacer(1, 10))

    story.append(make_threshold_table(data))
    story.append(Spacer(1, 10))

    story.append(section_title("Reader Profile", styles))
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
        styles["SmallText"]
    ))
    story.append(Spacer(1, 10))
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

    story.append(Spacer(1, 10))
    story.append(PageBreak())

    story.append(section_title("Reading Profile and Recommended Support", styles))
    story.append(Paragraph(
        "The student’s reading profile reflects current strengths, areas for development, and recommended support based on NGRT assessment evidence. "
        "Strengths highlight what the student is already demonstrating in reading attainment and progress. "
        "Areas for development identify the reading skills that may need further practice, such as fluency, vocabulary, comprehension, or confidence. "
        "Recommended support provides practical actions for teachers and parents to help the student make continued progress. "
        "Together, these points give a focused picture of how the student can be supported in the next stage of reading development.",
        styles["SmallText"]
    ))
    story.append(Spacer(1, 10))

    ai_support = generate_ai_profile_support(data)

    # Three support columns with AI-generated content and fallback to rule-based content if AI fails
    support_table = Table(
        [[
            paragraph_list("Strengths", ai_support["strengths"], styles),
            paragraph_list("Areas for Development", ai_support["development_areas"], styles),
            paragraph_list("Recommended Next Steps", ai_support["next_steps"], styles),
        ]],
        colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm]
    )

    support_table.setStyle(TableStyle([
        # Different background color per cell
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#CFECF3")),  # Strengths
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F6FFDC")),  # Areas for Development
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#DAF9DE")),  # Recommended Next Steps

        # Borders and layout
        ("BOX", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),

        # Padding
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(support_table)
    story.append(Spacer(1, 10))

    ai_considerations = generate_ai_considerations_support(data)

    story.extend(paragraph_list("Considerations for a Class Teacher", ai_considerations["class_teacher"], styles))
    story.append(Spacer(1, 10))

    story.extend(paragraph_list("Considerations for a Reading Specialist", ai_considerations["reading_specialist"], styles))

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


# =============================================================================
# Build Report Data - Internal Assessment (English, Mathematics, Science)
# =============================================================================

# Data builder function for the internal assessment report, which retrieves the necessary student and internal exam data,
def build_internal_individual_report_data(student_id):
    """
    Builds all required data for one student's internal assessment report.
    """

    student = Students.query.filter_by(student_id=student_id).first()

    if not student:
        return None

    internal = InternalExam.query.filter_by(student_id=student_id).first()

    if not internal:
        return None

    full_name = f"{student.forename or ''} {student.surname or ''}".strip()

    subjects = {
        "english": {
            "label": "English",
            "previous_pct": clean_number(getattr(internal, "eng_prevPct", None)),
            "previous_grade": clean_text(getattr(internal, "eng_prevGr", None)),
            "current_pct": clean_number(getattr(internal, "eng_currPct", None)),
            "current_grade": clean_text(getattr(internal, "eng_currGr", None)),
            "progress_category": clean_text(getattr(internal, "eng_progcat", None)),
        },
        "mathematics": {
            "label": "Mathematics",
            "previous_pct": clean_number(getattr(internal, "maths_prevPct", None)),
            "previous_grade": clean_text(getattr(internal, "maths_prevGr", None)),
            "current_pct": clean_number(getattr(internal, "maths_currPct", None)),
            "current_grade": clean_text(getattr(internal, "maths_currGr", None)),
            "progress_category": clean_text(getattr(internal, "maths_progcat", None)),
        },
        "science": {
            "label": "Science",
            "previous_pct": clean_number(getattr(internal, "sci_prevPct", None)),
            "previous_grade": clean_text(getattr(internal, "sci_prevGr", None)),
            "current_pct": clean_number(getattr(internal, "sci_currPct", None)),
            "current_grade": clean_text(getattr(internal, "sci_currGr", None)),
            "progress_category": clean_text(getattr(internal, "sci_progcat", None)),
        },
    }

    averages = calculate_internal_averages(student)

    current_values = [
        subject["current_pct"]
        for subject in subjects.values()
        if subject["current_pct"] is not None
    ]

    overall_average = round(sum(current_values) / len(current_values), 1) if current_values else None

    strongest_subject = get_strongest_subject(subjects)
    support_priority = get_support_priority(subjects)
    main_progress_category = get_main_progress_category(subjects)

    return {
        "student": student,
        "student_id": student.student_id,
        "student_name": full_name,
        "gender": clean_text(getattr(student, "gender", "")),
        "year_group": clean_text(getattr(student, "yrgrp", "")).upper(),
        "status": clean_text(getattr(student, "status", "")),
        "nationality": clean_text(getattr(student, "nationality", "")),
        "sped": clean_text(getattr(student, "sped", "")),
        "date_generated": datetime.now().strftime("%a, %d-%b-%Y"),

        "subjects": subjects,
        "overall_average": overall_average,
        "strongest_subject": strongest_subject,
        "support_priority": support_priority,
        "main_progress_category": main_progress_category,
        "averages": averages,
    }

# Helper function to calculate class and cohort averages for internal assessments in English, Mathematics, and Science.
def calculate_internal_averages(student):
    """
    Calculates class and cohort current percentage averages for English, Mathematics, and Science.
    """

    yrgrp = getattr(student, "yrgrp", None)

    def avg_for_subject(column_name, class_only=False):
        column = getattr(InternalExam, column_name)

        query = (
            db.session.query(func.avg(column))
            .join(Students, Students.student_id == InternalExam.student_id)
        )

        if class_only and yrgrp:
            query = query.filter(func.lower(Students.yrgrp) == yrgrp.lower())

        value = query.scalar()
        return round(float(value), 1) if value is not None else None

    return {
        "class": {
            "english": avg_for_subject("eng_currPct", class_only=True),
            "mathematics": avg_for_subject("maths_currPct", class_only=True),
            "science": avg_for_subject("sci_currPct", class_only=True),
        },
        "cohort": {
            "english": avg_for_subject("eng_currPct", class_only=False),
            "mathematics": avg_for_subject("maths_currPct", class_only=False),
            "science": avg_for_subject("sci_currPct", class_only=False),
        }
    }

# =============================================================================
# Report Tables
# =============================================================================

def section_title(title, styles):
    return Paragraph(title, styles["SectionTitle"])


def make_internal_student_info_table(data):
    table_data = [
        [
            Paragraph("<b>Student Name</b>", get_plain_style()),
            Paragraph(data["student_name"], get_plain_style()),
            Paragraph("<b>Student ID</b>", get_plain_style()),
            Paragraph(str(data["student_id"]), get_plain_style()),
        ],
        [
            Paragraph("<b>Year Group</b>", get_plain_style()),
            Paragraph(data["year_group"], get_plain_style()),
            Paragraph("<b>Gender</b>", get_plain_style()),
            Paragraph(data["gender"], get_plain_style()),
        ],
        [
            Paragraph("<b>Latest Assessment</b>", get_plain_style()),
            Paragraph("Internal Assessment", get_plain_style()),
            Paragraph("<b>Date Generated</b>", get_plain_style()),
            Paragraph(data["date_generated"], get_plain_style()),
        ],
    ]

    table = Table(table_data, colWidths=[3.5 * cm, 5 * cm, 3.5 * cm, 5 * cm])

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")), # light background for the first column
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F1F5F9")), # white background for the second column
        ("BOX", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    return table


def make_internal_kpi_table(data):
    """
    Creates four KPI cards:
    Overall Current Average, Strongest Subject, Main Progress Category, Support Priority.
    """

    overall = format_pct(data["overall_average"])
    strongest = data["strongest_subject"] or "-"
    progress = data["main_progress_category"] or "-"
    priority = data["support_priority"] or "-"

    table_data = [
        [
            make_kpi_cell(
                overall,
                "Overall Current Average",
                "Across English, Maths, Science",
                EI_BLUE
            ),
            make_kpi_cell(
                strongest,
                "Strongest Subject",
                "Highest current percentage",
                EI_GREEN
            ),
            make_kpi_cell(
                progress,
                "Main Progress Category",
                "Most common progress category",
                EI_YELLOW
            ),
            make_kpi_cell(
                priority,
                "Support Priority",
                "Lowest current percentage",
                EI_RED
            ),
        ]
    ]

    table = Table(table_data, colWidths=[4.2 * cm, 4.2 * cm, 4.2 * cm, 4.2 * cm])

    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("BACKGROUND", (0, 0), (0, 0), EI_BLUE_BG),
        ("BACKGROUND", (1, 0), (1, 0), EI_GREEN_BG),
        ("BACKGROUND", (2, 0), (2, 0), EI_YELLOW_BG),
        ("BACKGROUND", (3, 0), (3, 0), EI_RED_BG),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    return table


def make_kpi_cell(value, title, subtitle, value_color=EI_DARK):
    value_style = ParagraphStyle(
        name=f"KPIValueStyle_{str(value_color)}",
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=value_color,
        alignment=TA_CENTER,
    )

    return [
        Paragraph(str(value), value_style),
        Spacer(1, 2),
        Paragraph(title, get_kpi_title_style()),
        Spacer(1, 2),
        Paragraph(subtitle, get_kpi_subtitle_style()),
    ]


def make_subject_summary_table(data, styles):
    subjects = data["subjects"]

    table_data = [
        [
            "Subject",
            "Previous %",
            "Previous Grade",
            "Current %",
            "Current Grade",
            "Progress Category"
        ]
    ]

    progress_styles = []

    for row_index, subject in enumerate(subjects.values(), start=1):
        progress_category = subject["progress_category"]

        table_data.append([
            subject["label"],
            format_pct(subject["previous_pct"]),
            subject["previous_grade"],
            format_pct(subject["current_pct"]),
            subject["current_grade"],
            progress_category,
        ])

        progress_value = str(progress_category or "").strip().lower()

        if "below" in progress_value:
            bg_color = EI_RED_BG
            text_color = EI_RED
        elif "above" in progress_value:
            bg_color = EI_GREEN_BG
            text_color = EI_GREEN
        elif "expected" in progress_value:
            bg_color = EI_YELLOW_BG
            text_color = EI_YELLOW
        else:
            bg_color = colors.white
            text_color = EI_DARK

        progress_styles.extend([
            ("BACKGROUND", (5, row_index), (5, row_index), bg_color),
            ("TEXTCOLOR", (5, row_index), (5, row_index), text_color),
            ("FONTNAME", (5, row_index), (5, row_index), "Helvetica"),
        ])

    table = Table(
        table_data,
        colWidths=[3.2 * cm, 2.5 * cm, 2.7 * cm, 2.5 * cm, 2.7 * cm, 3.2 * cm]
    )

    base_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), EI_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, EI_LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]

    table.setStyle(TableStyle(base_styles + progress_styles))

    return table

def make_progress_table(data, styles):
    subjects = data["subjects"]

    table_data = [
        [
            "Subject",
            "Previous %",
            "Current %",
            "Change",
            "Previous Grade",
            "Current Grade",
            "Progress"
        ]
    ]

    # Store row-specific colour styles here
    progress_styles = []

    for row_index, subject in enumerate(subjects.values(), start=1):
        previous_pct = subject["previous_pct"]
        current_pct = subject["current_pct"]
        progress_category = subject["progress_category"]

        if previous_pct is not None and current_pct is not None:
            change = current_pct - previous_pct
            change_text = f"{change:+.1f}"
        else:
            change_text = "-"

        table_data.append([
            subject["label"],
            format_pct(previous_pct),
            format_pct(current_pct),
            change_text,
            subject["previous_grade"],
            subject["current_grade"],
            progress_category,
        ])

        # Apply colour based on progress category
        progress_value = str(progress_category or "").strip().lower()

        if "below" in progress_value:
            bg_color = EI_RED_BG
            text_color = EI_RED
        elif "above" in progress_value:
            bg_color = EI_GREEN_BG
            text_color = EI_GREEN
        elif "expected" in progress_value:
            bg_color = EI_YELLOW_BG
            text_color = EI_YELLOW
        else:
            bg_color = colors.white
            text_color = EI_DARK

        progress_styles.extend([
            ("BACKGROUND", (6, row_index), (6, row_index), bg_color),
            ("TEXTCOLOR", (6, row_index), (6, row_index), text_color),
            ("FONTNAME", (6, row_index), (6, row_index), "Helvetica"),
        ])

    table = Table(
        table_data,
        colWidths=[2.8 * cm, 2.3 * cm, 2.3 * cm, 2.0 * cm, 2.5 * cm, 2.5 * cm, 2.6 * cm]
    )

    base_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), EI_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, EI_LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]

    table.setStyle(TableStyle(base_styles + progress_styles))

    return table

def make_internal_threshold_table(data, styles):
    avg = data["overall_average"]

    thresholds = [
        {
            "threshold": "Current average >= 60%",
            "meaning": "Working within expected attainment range",
            "achieved": avg is not None and avg >= 60
        },
        {
            "threshold": "Current average >= 70%",
            "meaning": "Secure internal assessment attainment",
            "achieved": avg is not None and avg >= 70
        },
        {
            "threshold": "Current average >= 80%",
            "meaning": "High attainment / enrichment level",
            "achieved": avg is not None and avg >= 80
        },
    ]

    table_data = [["Threshold", "Meaning", "Status"]]

    status_styles = []

    for row_index, item in enumerate(thresholds, start=1):
        status_text = "Achieved" if item["achieved"] else "Target"

        table_data.append([
            item["threshold"],
            item["meaning"],
            status_text
        ])

        if item["achieved"]:
            bg_color = EI_GREEN_BG    # light green
            text_color = EI_GREEN  # green text
        else:
            bg_color = EI_YELLOW_BG    # light yellow
            text_color = EI_YELLOW  # yellow/brown text

        status_styles.extend([
            ("BACKGROUND", (2, row_index), (2, row_index), bg_color),
            ("TEXTCOLOR", (2, row_index), (2, row_index), text_color),
            ("FONTNAME", (2, row_index), (2, row_index), "Helvetica"),
        ])

    table = Table(table_data, colWidths=[4.5 * cm, 8.5 * cm, 3.5 * cm])

    base_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), EI_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),

        ("ALIGN", (2, 1), (2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("BOX", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, EI_BORDER),

        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, EI_LIGHT]),

        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]

    table.setStyle(TableStyle(base_styles + status_styles))

    return table

# =============================================================================
# Simple ReportLab Charts
# =============================================================================

class SubjectProgressBarChart(Flowable):
    """
    Bar chart showing Previous % and Current % for English, Mathematics, and Science.
    """

    def __init__(self, subjects, width=16.5 * cm, height=7 * cm):
        super().__init__()
        self.subjects = subjects
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv

        x0 = 1 * cm
        y0 = 1 * cm
        chart_width = self.width - 2 * cm
        chart_height = self.height - 2 * cm

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(EI_DARK)
        c.drawString(0, self.height - 0.4 * cm, "Previous vs Current Percentage by Subject")

        # Axis
        c.setStrokeColor(EI_BORDER)
        c.line(x0, y0, x0, y0 + chart_height)
        c.line(x0, y0, x0 + chart_width, y0)

        # Y-axis labels
        c.setFont("Helvetica", 6)
        c.setFillColor(EI_MUTED)

        for value in range(0, 101, 20):
            y = y0 + (value / 100) * chart_height
            c.drawRightString(x0 - 4, y - 2, str(value))
            c.setStrokeColor(colors.HexColor("#E5E7EB"))
            c.line(x0, y, x0 + chart_width, y)

        subject_values = list(self.subjects.values())
        group_width = chart_width / len(subject_values)
        bar_width = 0.85 * cm

        for index, subject in enumerate(subject_values):
            group_x = x0 + index * group_width + group_width / 2

            previous = subject["previous_pct"] or 0
            current = subject["current_pct"] or 0

            previous_height = (previous / 100) * chart_height
            current_height = (current / 100) * chart_height

            # Previous bar
            c.setFillColor(colors.HexColor("#93C5FD"))
            c.rect(group_x - bar_width - 2, y0, bar_width, previous_height, fill=1, stroke=0)

            # Current bar
            c.setFillColor(colors.HexColor("#2563EB"))
            c.rect(group_x + 2, y0, bar_width, current_height, fill=1, stroke=0)

            # Values
            c.setFont("Helvetica", 6)
            c.setFillColor(EI_DARK)
            c.drawCentredString(group_x - bar_width / 2 - 2, y0 + previous_height + 3, format_pct(previous))
            c.drawCentredString(group_x + bar_width / 2 + 2, y0 + current_height + 3, format_pct(current))

            # Subject label
            c.setFont("Helvetica", 7)
            c.setFillColor(EI_MUTED)
            c.drawCentredString(group_x, y0 - 12, subject["label"])

        # Legend
        legend_y = self.height - 0.8 * cm

        c.setFillColor(colors.HexColor("#93C5FD"))
        c.rect(self.width - 4.7 * cm, legend_y, 8, 8, fill=1, stroke=0)
        c.setFillColor(EI_MUTED)
        c.setFont("Helvetica", 6)
        c.drawString(self.width - 4.3 * cm, legend_y, "Previous AY")

        c.setFillColor(colors.HexColor("#2563EB"))
        c.rect(self.width - 2.5 * cm, legend_y, 8, 8, fill=1, stroke=0)
        c.setFillColor(EI_MUTED)
        c.drawString(self.width - 2.1 * cm, legend_y, "Current AY")


class SubjectComparisonBarChart(Flowable):
    """
    Bar chart comparing Student, Class Average, and Cohort Average per subject.
    """

    def __init__(self, subjects, averages, width=16.5 * cm, height=7 * cm):
        super().__init__()
        self.subjects = subjects
        self.averages = averages
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv

        x0 = 1 * cm
        y0 = 1 * cm
        chart_width = self.width - 2 * cm
        chart_height = self.height - 2 * cm

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(EI_DARK)
        c.drawString(0, self.height - 0.2 * cm, "Student vs Class and Cohort Average by Subject")

        # Axis
        c.setStrokeColor(EI_BORDER)
        c.line(x0, y0, x0, y0 + chart_height)
        c.line(x0, y0, x0 + chart_width, y0)

        c.setFont("Helvetica", 6)
        c.setFillColor(EI_MUTED)

        for value in range(0, 101, 20):
            y = y0 + (value / 100) * chart_height
            c.drawRightString(x0 - 4, y - 2, str(value))
            c.setStrokeColor(colors.HexColor("#E5E7EB"))
            c.line(x0, y, x0 + chart_width, y)

        subject_keys = ["english", "mathematics", "science"]
        group_width = chart_width / len(subject_keys)
        bar_width = 0.85 * cm
        bar_gap = 5

        for index, key in enumerate(subject_keys):
            subject = self.subjects[key]

            # Center of each subject group
            group_x = x0 + index * group_width + group_width / 2

            student_value = subject["current_pct"] or 0
            class_value = self.averages["class"].get(key) or 0
            cohort_value = self.averages["cohort"].get(key) or 0

            values = [
                ("Student", student_value, colors.HexColor("#2563EB"), -bar_width - bar_gap),
                ("Class", class_value, colors.HexColor("#10B981"), 0),
                ("Cohort", cohort_value, colors.HexColor("#F59E0B"), bar_width + bar_gap),
            ]

            for label, value, color, offset in values:
                bar_height = (value / 100) * chart_height
                c.setFillColor(color)
                c.rect(group_x + offset, y0, bar_width, bar_height, fill=1, stroke=0)

                c.setFont("Helvetica", 6)
                c.setFillColor(EI_DARK)
                c.drawCentredString(group_x + offset + bar_width / 2, y0 + bar_height + 4, format_pct(value))

            # Label centered under the full 3-bar group
            label_x = group_x + (bar_width / 2)

            c.setFont("Helvetica", 7)
            c.setFillColor(EI_MUTED)
            c.drawCentredString(label_x, y0 - 16, subject["label"])

        # Legend
        legend_y = self.height - 0.8 * cm

        legend_items = [
            ("Student", colors.HexColor("#2563EB")),
            ("Class Avg", colors.HexColor("#10B981")),
            ("Cohort Avg", colors.HexColor("#F59E0B")),
        ]

        legend_x = self.width - 5.7 * cm

        for label, color in legend_items:
            c.setFillColor(color)
            c.rect(legend_x, legend_y, 8, 8, fill=1, stroke=0)
            c.setFillColor(EI_MUTED)
            c.setFont("Helvetica", 6)
            c.drawString(legend_x + 12, legend_y, label)
            legend_x += 1.9 * cm

# =============================================================================
# Text Interpretation Helpers
# =============================================================================

def internal_assessment_interpretation(data):
    name = data["student_name"]
    subjects = data["subjects"]

    eng = subjects["english"]
    maths = subjects["mathematics"]
    sci = subjects["science"]

    overall = format_pct(data["overall_average"])
    strongest = data["strongest_subject"] or "the strongest subject"
    priority = data["support_priority"] or "the main support area"
    progress = data["main_progress_category"] or "not yet available"

    return (
        f"{name} has demonstrated an overall current average of {overall} across the available "
        f"internal assessment records. The student's current scores are {format_pct(eng['current_pct'])} "
        f"in English, {format_pct(maths['current_pct'])} in Mathematics, and {format_pct(sci['current_pct'])} "
        f"in Science. The strongest area is currently {strongest}, while {priority} should be monitored "
        f"as a priority for targeted support. The main progress category is {progress}, which should be "
        f"reviewed alongside classroom evidence, teacher observations, and ongoing formative assessment."
    )


def learning_profile_text(data):
    name = data["student_name"]
    strongest = data["strongest_subject"] or "one subject area"
    priority = data["support_priority"] or "one subject area"
    progress = data["main_progress_category"] or "available progress information"

    return (
        f"{name}'s learning profile shows the student's current attainment across English, Mathematics, "
        f"and Science. The available assessment evidence indicates that {strongest} is currently a relative "
        f"strength, while {priority} may require closer monitoring or additional support. The student's progress "
        f"profile is currently described as {progress}. This information should be used to guide planning, "
        f"intervention, feedback, and next-step classroom support."
    )


def progress_interpretation_internal(data):
    name = data["student_name"]
    subjects = data["subjects"]

    improved_subjects = []
    declined_subjects = []
    stable_subjects = []

    for subject in subjects.values():
        prev = subject["previous_pct"]
        curr = subject["current_pct"]

        if prev is None or curr is None:
            continue

        difference = curr - prev

        if difference > 2:
            improved_subjects.append(subject["label"])
        elif difference < -2:
            declined_subjects.append(subject["label"])
        else:
            stable_subjects.append(subject["label"])

    parts = []

    if improved_subjects:
        parts.append(f"improvement is evident in {', '.join(improved_subjects)}")

    if stable_subjects:
        parts.append(f"performance is broadly stable in {', '.join(stable_subjects)}")

    if declined_subjects:
        parts.append(f"closer monitoring may be needed in {', '.join(declined_subjects)}")

    if not parts:
        return (
            f"The progress data for {name} should be reviewed alongside classroom evidence and teacher observations. "
            f"Further assessment information may be needed to identify clear progress patterns."
        )

    return (
        f"The progress data shows that {', while '.join(parts)}. This pattern helps identify where "
        f"{name} is making gains and where additional support may be needed. Continued monitoring, targeted feedback, "
        f"and focused intervention will help sustain progress across the next assessment cycle."
    )

# fallback function to generate support points based on the available data if the AI call fails or returns incomplete output
def generate_internal_support_points(data):
    """
    Rule-based fallback for internal assessment support points.
    """

    name = data.get("student_name", "The student")
    strongest = data.get("strongest_subject") or "a subject area"
    priority = data.get("support_priority") or "a subject area"
    overall = format_pct(data.get("overall_average"))
    progress = data.get("main_progress_category") or "available progress information"

    return {
        "strengths": [
            f"{name} has an overall current average of {overall} across the available internal assessment records.",
            f"{strongest} is currently a relative strength based on the available current percentage scores.",
            f"The main progress category is {progress}, providing a useful indication of the student's current learning direction."
        ],
        "development_areas": [
            f"{priority} should be monitored as a priority area for additional support or targeted review.",
            "The student may benefit from further opportunities to revisit key concepts, address misconceptions, and strengthen core skills.",
            "Progress should continue to be reviewed using classroom evidence, formative assessment, and teacher feedback."
        ],
        "next_steps": [
            f"Provide focused intervention or guided practice in {priority} to address gaps and strengthen confidence.",
            "Use short review tasks, modelled examples, success criteria, and regular feedback to support steady improvement.",
            "Continue to monitor performance across English, Mathematics, and Science during the next assessment cycle."
        ]
    }

# parser to split the AI output into three sections based on the expected format
def parse_ai_support_sections(ai_text):
    """
    Parses AI output into three sections:
    - strengths
    - development_areas
    - next_steps
    """

    sections = {
        "strengths": [],
        "development_areas": [],
        "next_steps": []
    }

    current_section = None

    for line in ai_text.splitlines():
        clean_line = line.strip()

        if not clean_line:
            continue

        lower_line = clean_line.lower()

        if lower_line.startswith("strengths"):
            current_section = "strengths"
            continue

        if lower_line.startswith("areas for development"):
            current_section = "development_areas"
            continue

        if lower_line.startswith("recommended next steps"):
            current_section = "next_steps"
            continue

        if clean_line.startswith("-") and current_section:
            statement = clean_line.lstrip("-").strip()

            if statement:
                sections[current_section].append(statement)

    return sections

# validator to ensure the AI output contains exactly 3 statements for each section
def is_valid_support_output(parsed):
    """
    Checks that the AI returned exactly 3 statements
    for each required section.
    """

    required_keys = ["strengths", "development_areas", "next_steps"]

    for key in required_keys:
        if key not in parsed:
            return False

        if not isinstance(parsed[key], list):
            return False

        if len(parsed[key]) != 3:
            return False

    return True

# ==============================================
# Internal Assessment Report:
# Learning Profile and Recommended Support
# OpenAI interpretation with fallback function
# ===============================================
def generate_ai_internal_support_points(data):
    """
    Uses OpenAI to generate:
    1. Strengths
    2. Areas for Development
    3. Recommended Next Steps

    Returns a dictionary with three separate lists.
    Falls back to rule-based functions if the AI call fails or parsing is incomplete.
    """
    name = data.get("student_name", "The student")
    strongest = data.get("strongest_subject") or "a subject area"
    priority = data.get("support_priority") or "a subject area"
    overall = format_pct(data.get("overall_average"))
    progress = data.get("main_progress_category") or "available progress information"

    try:
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing or not loaded.")

        client = OpenAI(api_key=api_key)

        prompt = f"""
        You are writing professional comments for a student's internal assessment PDF report.

        Student information:
        Student name: {name}
        Gender: {data.get("gender")}
        Strongest subject/area: {strongest}
        Support priority: {priority}
        Overall average: {overall}
        Main progress category: {progress}

        Create the response in exactly this format:

        Strengths:
        - ...
        - ...
        - ...

        Areas for Development:
        - ...
        - ...
        - ...

        Recommended Next Steps:
        - ...
        - ...
        - ...

        Rules:
        - Write exactly 3 bullet statements under each heading.
        - Each bullet must be one sentence only.
        - Each bullet must begin with "-".
        - Use a professional, balanced, school-report tone.
        - Make the statements specific to the data provided.
        - Refer to the strongest subject/area in the Strengths section.
        - Refer to the support priority in the Areas for Development section.
        - Provide practical support actions in the Recommended Next Steps section.
        - Avoid deficit-based wording such as "weak", "poor", "failing", or "struggling badly".
        - Do not include markdown tables, numbering, emojis, introductions, or closing comments.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an educational data analyst writing professional, supportive, "
                        "and evidence-based comments for internal assessment student reports. "
                        "You write clearly for teachers and parents."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=500
        )

        ai_text = response.choices[0].message.content.strip()

        parsed = parse_ai_support_sections(ai_text)

        if not is_valid_support_output(parsed):
            return generate_internal_support_points(data)

        return parsed

    except Exception as e:
        print(f"AI internal support generation failed: {e}")
        return generate_internal_support_points(data)

# Fallback function for subject-specific considerations for classroom support based on internal assessment data
def generate_subject_considerations(data):
    """
    Rule-based fallback for subject-specific and class teacher considerations.
    Used when AI generation fails or returns incomplete output.
    """

    priority = data.get("support_priority") or "the identified support area"

    return {
        "english": [
            "Continue guided reading, vocabulary development, and sentence-level writing practice.",
            "Provide opportunities for extended responses using modelled examples and success criteria.",
            "Monitor spelling, punctuation, grammar, comprehension accuracy, and quality of written explanations."
        ],
        "mathematics": [
            "Provide regular arithmetic fluency practice and revisit key number facts.",
            "Use visual models, worked examples, and step-by-step modelling for problem-solving.",
            "Address misconceptions through short, targeted intervention tasks and daily review."
        ],
        "science": [
            "Strengthen scientific vocabulary through word banks, oral rehearsal, and labelled diagrams.",
            "Encourage the student to explain observations using because, so, and therefore.",
            "Use practical investigations and real-life examples to connect assessment content with understanding."
        ],
        "class_teacher": [
            f"Use {priority} as the main starting point for targeted classroom support.",
            "Review the student's assessment outcomes alongside books, questioning, quizzes, and classroom participation.",
            "Plan short, focused next steps and monitor whether the student responds positively to intervention."
        ]
    }

# parser to split the AI output into four sections based on the expected format
def parse_ai_subject_considerations(ai_text):
    """
    Parses AI output into four sections:
    - english
    - mathematics
    - science
    - class_teacher
    """

    sections = {
        "english": [],
        "mathematics": [],
        "science": [],
        "class_teacher": []
    }

    current_section = None

    for line in ai_text.splitlines():
        clean_line = line.strip()

        if not clean_line:
            continue

        lower_line = clean_line.lower()

        if lower_line.startswith("considerations for english"):
            current_section = "english"
            continue

        if lower_line.startswith("considerations for mathematics"):
            current_section = "mathematics"
            continue

        if lower_line.startswith("considerations for science"):
            current_section = "science"
            continue

        if lower_line.startswith("considerations for a class teacher"):
            current_section = "class_teacher"
            continue

        if clean_line.startswith("-") and current_section:
            statement = clean_line.lstrip("-").strip()

            if statement:
                sections[current_section].append(statement)

    return sections

# validator to ensure the AI output contains exactly 3 statements for each subject/support section
def is_valid_subject_considerations(parsed):
    """
    Checks that the AI returned exactly 3 statements
    for each required subject/support section.
    """

    required_keys = [
        "english",
        "mathematics",
        "science",
        "class_teacher"
    ]

    for key in required_keys:
        if key not in parsed:
            return False

        if not isinstance(parsed[key], list):
            return False

        if len(parsed[key]) != 3:
            return False

    return True

# ==============================================
# Internal Assessment Report:
# Subject Considerations for Classroom Support
# OpenAI interpretation with fallback function
# ===============================================
def generate_ai_subject_considerations(data):
    """
    Uses OpenAI to generate subject-specific support considerations for:
    1. English
    2. Mathematics
    3. Science
    4. Class Teacher

    Falls back to generate_subject_considerations(data) if AI fails
    or the parsed output is incomplete.
    """

    name = data.get("student_name", "The student")
    gender = data.get("gender", "-")
    strongest = data.get("strongest_subject") or "a subject area"
    priority = data.get("support_priority") or "the identified support area"
    overall = format_pct(data.get("overall_average"))
    progress = data.get("main_progress_category") or "available progress information"

    subjects = data.get("subjects", {})

    english = subjects.get("english", {})
    mathematics = subjects.get("mathematics", {})
    science = subjects.get("science", {})

    try:
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing or not loaded.")

        client = OpenAI(api_key=api_key)

        prompt = f"""
        You are writing professional subject-specific support considerations for a student's internal assessment PDF report.

        Student information:
        Student name: {name}
        Gender: {gender}
        Overall average: {overall}
        Strongest subject/area: {strongest}
        Support priority: {priority}
        Main progress category: {progress}

        Internal assessment data:
        English:
        - Previous percentage: {format_pct(english.get("previous_pct"))}
        - Previous grade: {english.get("previous_grade", "-")}
        - Current percentage: {format_pct(english.get("current_pct"))}
        - Current grade: {english.get("current_grade", "-")}
        - Progress category: {english.get("progress_category", "-")}

        Mathematics:
        - Previous percentage: {format_pct(mathematics.get("previous_pct"))}
        - Previous grade: {mathematics.get("previous_grade", "-")}
        - Current percentage: {format_pct(mathematics.get("current_pct"))}
        - Current grade: {mathematics.get("current_grade", "-")}
        - Progress category: {mathematics.get("progress_category", "-")}

        Science:
        - Previous percentage: {format_pct(science.get("previous_pct"))}
        - Previous grade: {science.get("previous_grade", "-")}
        - Current percentage: {format_pct(science.get("current_pct"))}
        - Current grade: {science.get("current_grade", "-")}
        - Progress category: {science.get("progress_category", "-")}

        Create the response in exactly this format:

        Considerations for English:
        - ...
        - ...
        - ...

        Considerations for Mathematics:
        - ...
        - ...
        - ...

        Considerations for Science:
        - ...
        - ...
        - ...

        Considerations for a Class Teacher:
        - ...
        - ...
        - ...

        Rules:
        - Write exactly 3 bullet statements under each heading.
        - Each bullet must be one complete sentence.
        - Each bullet must begin with "-".
        - Use a professional, balanced, school-report tone.
        - Make the statements specific to the assessment data provided.
        - Keep the language positive, supportive, and evidence-based.
        - Avoid deficit-based wording such as "weak", "poor", "failing", or "struggling badly".
        - Do not include markdown tables, numbering, emojis, introductions, or closing comments.
        - Keep each statement concise and suitable for inclusion in a PDF report.

        Content guidance:
        - English considerations should focus on reading, vocabulary, sentence construction, comprehension, writing accuracy, or extended responses.
        - Mathematics considerations should focus on arithmetic fluency, number facts, problem-solving, reasoning, modelling, or misconception review.
        - Science considerations should focus on scientific vocabulary, explanation, observation, practical investigation, and applying concepts.
        - Class teacher considerations should focus on classroom planning, targeted support, evidence review, feedback, and monitoring the student's response to intervention.
        - Link the class teacher section to the support priority where appropriate.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an educational data analyst writing professional, supportive, "
                        "and evidence-based subject considerations for internal assessment student reports."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=650
        )

        ai_text = response.choices[0].message.content.strip()

        parsed = parse_ai_subject_considerations(ai_text)

        if not is_valid_subject_considerations(parsed):
            return generate_subject_considerations(data)

        return parsed

    except Exception as e:
        print(f"AI subject consideration generation failed: {e}")
        return generate_subject_considerations(data)

# =============================================================================
# Utility and Formatting Helpers
# =============================================================================

def clean_text(value):
    if value is None:
        return "-"
    value = str(value).strip()
    return value if value else "-"


def clean_number(value):
    if value is None or value == "":
        return None

    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return None


def format_pct(value):
    if value is None:
        return "-"

    try:
        value = float(value)
        if value.is_integer():
            return f"{int(value)}%"
        return f"{value:.1f}%"
    except (TypeError, ValueError):
        return "-"


def get_strongest_subject(subjects):
    valid_subjects = [
        subject for subject in subjects.values()
        if subject["current_pct"] is not None
    ]

    if not valid_subjects:
        return "-"

    strongest = max(valid_subjects, key=lambda item: item["current_pct"])
    return strongest["label"]


def get_support_priority(subjects):
    valid_subjects = [
        subject for subject in subjects.values()
        if subject["current_pct"] is not None
    ]

    if not valid_subjects:
        return "-"

    weakest = min(valid_subjects, key=lambda item: item["current_pct"])
    return weakest["label"]


def get_main_progress_category(subjects):
    categories = [
        subject["progress_category"]
        for subject in subjects.values()
        if subject["progress_category"] and subject["progress_category"] != "-"
    ]

    if not categories:
        return "-"

    return max(set(categories), key=categories.count)


def paragraph_list(title, items, styles):
    elements = [
        Paragraph(f"<b>{title}</b>", styles["BoxTitle"]),
        Spacer(1, 4)
    ]

    for item in items:
        elements.append(Paragraph(f"- {item}", styles["SmallText"]))

    return elements

# =============================================================================
# Paragraph styles used by helper tables
# =============================================================================

def get_plain_style():
    return ParagraphStyle(
        name="InternalPlainStyle",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=EI_DARK,
        alignment=TA_LEFT,
    )


def get_kpi_title_style():
    return ParagraphStyle(
        name="InternalKpiTitleStyle",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=EI_DARK,
        alignment=TA_CENTER,
    )


def get_kpi_value_style():
    return ParagraphStyle(
        name="InternalKpiValueStyle",
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=EI_DARK,
        alignment=TA_CENTER,
    )


def get_kpi_subtitle_style():
    return ParagraphStyle(
        name="InternalKpiSubtitleStyle",
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=EI_MUTED,
        alignment=TA_CENTER,
    )

# =============================================================================
# Main PDF builder - internal assessments (Assessment Data + Report Generation)
# =============================================================================

def generate_intl_indv_rpt(student_id):
    """
    Generates the individual internal assessment PDF report.
    """

    data = build_internal_individual_report_data(student_id)

    if not data:
        return None

    output_path = os.path.join(
        tempfile.gettempdir(),
        f"examinsight_individual_internal_report_{student_id}.pdf"
    )

    doc, styles, story = setup_individual_report_pdf(output_path)

    # =====================================================
    # Page 1: Student Overview and Current Summary
    # =====================================================

    story.append(section_title("Internal Assessment Report", styles))
    story.append(Paragraph(
        "This report provides an overview of the student's attainment and progress across available "
        "internal assessments in English, Mathematics, and Science, summarising previous and current "
        "assessment outcomes, subject grades, progress categories, and key areas for support. The information "
        "presented is intended to support parent communication, teacher planning, intervention tracking, and "
        "next-step learning support.",
        styles["SmallText"]
    ))
    story.append(Spacer(1, 10))

    story.append(make_internal_student_info_table(data))
    story.append(Spacer(1, 10))

    story.append(make_internal_kpi_table(data))
    story.append(Spacer(1, 10))

    story.append(section_title("Internal Assessment Interpretation", styles))
    story.append(Paragraph(internal_assessment_interpretation(data), styles["SmallText"]))
    story.append(Spacer(1, 10))

    story.append(section_title("Subject Attainment and Progress Summary", styles))
    story.append(make_subject_summary_table(data, styles))
    story.append(Spacer(1, 10))

    story.append(section_title("Internal Assessment Thresholds", styles))
    story.append(make_internal_threshold_table(data, styles))
    story.append(Spacer(1, 10))

    story.append(section_title("Learning Profile", styles))
    story.append(Paragraph(learning_profile_text(data), styles["SmallText"]))

    story.append(PageBreak())

    # =====================================================
    # Page 2: Progress and Comparison
    # =====================================================

    story.append(section_title("Progress across Internal Assessments", styles))
    story.append(Paragraph(
        "This section tracks the student's performance across available internal assessment records "
        "in English, Mathematics, and Science to support evidence-based intervention and progress monitoring.",
        styles["SmallText"]
    ))
    story.append(Spacer(1, 10))

    story.append(make_progress_table(data, styles))
    story.append(Spacer(1, 10))

    story.append(SubjectProgressBarChart(data["subjects"]))
    story.append(Spacer(1, 6))

    story.append(Paragraph(progress_interpretation_internal(data), styles["SmallText"]))
    story.append(Spacer(1, 12))

    story.append(SubjectComparisonBarChart(data["subjects"], data["averages"]))
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "The comparison chart shows the student's current internal assessment performance against "
        "class and cohort averages. This helps identify whether the student is performing broadly in line "
        "with peers, exceeding expectations, or requiring additional support. It should be interpreted "
        "alongside classroom evidence, teacher observations, books, quizzes, and ongoing formative assessment.",
        styles["SmallText"]
    ))

    story.append(PageBreak())

    # =====================================================
    # Page 3: Recommended Support
    # =====================================================

    story.append(section_title("Learning Profile and Recommended Support", styles))
    story.append(Paragraph(
        "The student's internal assessment profile reflects current strengths, areas for development, "
        "and recommended support based on English, Mathematics, and Science assessment evidence. Strengths "
        "highlight what the student is already demonstrating across subject areas. Areas for development "
        "identify the skills or subjects that may need further practice. Recommended support provides practical "
        "actions for teachers and parents to help the student make continued progress.",
        styles["SmallText"]
    ))
    story.append(Spacer(1, 10))

    support = generate_ai_internal_support_points(data)

    support_table = Table(
        [[
            paragraph_list("Strengths", support["strengths"], styles),
            paragraph_list("Areas for Development", support["development_areas"], styles),
            paragraph_list("Recommended Next Steps", support["next_steps"], styles),
        ]],
        colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm]
    )

    support_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#CFECF3")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F6FFDC")),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#DAF9DE")),

        ("BOX", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),

        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(support_table)
    story.append(Spacer(1, 10))

    subject_considerations = generate_ai_subject_considerations(data)

    story.extend(paragraph_list("Considerations for English", subject_considerations["english"], styles))
    story.append(Spacer(1, 8))

    story.extend(paragraph_list("Considerations for Mathematics", subject_considerations["mathematics"], styles))
    story.append(Spacer(1, 8))

    story.extend(paragraph_list("Considerations for Science", subject_considerations["science"], styles))
    story.append(Spacer(1, 8))

    story.extend(paragraph_list("Considerations for a Class Teacher", subject_considerations["class_teacher"], styles))

    # global logo path variable
    # report generates even without the logo in case the image file is missing or the path is incorrect, 
    # but it will simply omit the logo from the header
    try:
        selected_logo_path = logo_path
    except NameError:
        selected_logo_path = None

    doc.build(
        story,
        onFirstPage=lambda canvas, doc: add_header_footer(
            canvas,
            doc,
            report_title="ExamInsight: Internal Assessment Individual Student Report",
            logo_path=selected_logo_path
        ),
        onLaterPages=lambda canvas, doc: add_header_footer(
            canvas,
            doc,
            report_title="ExamInsight: Internal Assessment Individual Student Report",
            logo_path=selected_logo_path
        ),
    )

    return output_path

# ===================================================
# Cohort listing-related report generation functions
# ===================================================

# Defines paragraph styles used in the cohort listing report
def get_listing_styles():
    return {
        "header": ParagraphStyle(
            name="ListingHeader",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#111827"),
            alignment=TA_CENTER,
        ),
        "student": ParagraphStyle(
            name="StudentInfo",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=EI_MUTED,
            alignment=TA_LEFT,
        ),
        "subject": ParagraphStyle(
            name="SubjectInfo",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=EI_MUTED,
            alignment=TA_LEFT,
        ),
        "progress": ParagraphStyle(
            name="ProgressText",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "SmallText": ParagraphStyle(
            name="SmallText",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=EI_DARK,
            alignment=TA_LEFT,
            spaceAfter=3,
        ),
    }

# formatting helpers
def pdf_safe(value, fallback="-"):
    if value is None or value == "":
        return fallback
    return str(value)


def pdf_pct(value):
    if value is None or value == "" or value == "-":
        return "-"

    try:
        value = float(value)
        if value.is_integer():
            return f"{int(value)}%"
        return f"{value:.1f}%"
    except (TypeError, ValueError):
        return str(value)


def get_progress_colors(progress):
    value = str(progress or "").strip().lower()

    if "below" in value:
        return colors.HexColor("#FEE2E2"), colors.HexColor("#991B1B")

    if "above" in value:
        return colors.HexColor("#DCFCE7"), colors.HexColor("#166534")

    if "expected" in value:
        return colors.HexColor("#FEF3C7"), colors.HexColor("#92400E")

    return colors.white, colors.HexColor("#111827")

# subject cell builder
def make_subject_listing_cell(subject_data, styles):
    if not subject_data:
        subject_data = {}

    prev_pct = pdf_pct(subject_data.get("previous_percentage"))
    prev_grade = pdf_safe(subject_data.get("previous_grade"))
    curr_pct = pdf_pct(subject_data.get("current_percentage"))
    curr_grade = pdf_safe(subject_data.get("current_grade"))
    progress = pdf_safe(subject_data.get("progress_category"), "No Progress Available")

    bg_color, text_color = get_progress_colors(progress)

    score_text = Paragraph(
        f"""
        Previous AY: <font color="#FF6600"><b>{prev_pct}</b></font>, <b>{prev_grade}</b><br/>
        Current AY: <font color="#0BA6DF"><b>{curr_pct}</b></font>, <b>{curr_grade}</b>
        """,
        styles["subject"]
    )

    progress_style = ParagraphStyle(
        name=f"Progress_{progress}",
        parent=styles["progress"],
        textColor=text_color,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
    )

    progress_bar = Table(
        [[Paragraph(progress.upper(), progress_style)]],
        colWidths=[5.8 * cm]
    )

    progress_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("BOX", (0, 0), (-1, -1), 0.2, bg_color),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    cell = Table(
        [
            [score_text],
            [progress_bar]
        ],
        colWidths=[5.8 * cm]
    )

    cell.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    return cell

# student information cell builder
def make_student_listing_cell(student, styles):
    student_id = pdf_safe(student.get("student_id"))
    name = pdf_safe(student.get("name"))
    gender = pdf_safe(student.get("gender"))
    nationality = pdf_safe(student.get("nationality"))
    status = pdf_safe(student.get("status"))
    yrgrp = pdf_safe(student.get("yrgrp"))

    sped = str(student.get("sped") or "").strip()

    sen_line = ""
    if sped and sped.lower() != "no":
        sen_line = f'<br/><font color="#DC2626"><b>SEN Details:</b> {sped}</font>'

    text = f"""
    <font color="#111827"><b>{student_id}</b></font>
    <font color="#FF6600"><b>{name}</b></font><br/>
    {gender}, {nationality}<br/>
    {status}, Year {yrgrp}
    {sen_line}
    """

    return Paragraph(text, styles["student"])

# function to determine the report scope label based on filters applied to the cohort listing
def get_internal_listing_scope_label(filters):
    """
    Returns report scope label for the Internal Assessment cohort listing.
    - Classwise if a specific year group is selected
    - Cohort if no specific year group is selected
    """

    yrgrp = (filters or {}).get("yrgrp", "").strip()

    if yrgrp and yrgrp != "All Year Groups":
        return f"YEAR {yrgrp.upper()} CLASSWISE REPORT", EI_BLUE

    return "COHORT REPORT", EI_ORANGE

# main PDF generator
def generate_internal_cohort_listing_pdf(filters=None):
    """
    Generates a downloadable PDF cohort listing for InternalExam.
    Uses /api/reports/internal/combined-data as the data source.
    """

    filters = filters or {}

    query_string = urlencode(filters)

    base_url = request.host_url.rstrip("/")
    api_url = f"{base_url}/api/reports/internal/combined-data"

    if query_string:
        api_url = f"{api_url}?{query_string}"

    response = requests.get(api_url, timeout=20)

    if response.status_code != 200:
        return None

    students = response.json()

    output_path = os.path.join(
        tempfile.gettempdir(),
        "examinsight_internal_cohort_listing.pdf"
    )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=2.0 * cm,
        bottomMargin=1.5 * cm
    )

    styles = get_listing_styles()

    story = []

    report_scope, report_scope_color = get_internal_listing_scope_label(filters)
    generated_date = datetime.now().strftime("%a, %d-%b-%Y")    
    story.append(
        Paragraph(
            f'<font color="{report_scope_color.hexval()}"><b>{report_scope}</b></font>'
            f' &emsp; | &emsp; '
            f'<b>Date Generated:</b> {generated_date}',
            styles["SmallText"]
        )
    )
    story.append(Spacer(1, 4))

    story.append(Paragraph(
        "Combined English, Mathematics, and Science internal assessment records showing previous attainment, current attainment, and progress category.",
        ParagraphStyle(
            name="ReportSubtitle",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=EI_MUTED,
            alignment=TA_LEFT,
            spaceAfter=8
        )
    ))

    story.append(Spacer(1, 6))

    table_rows = [
        [
            Paragraph("STUDENT INFORMATION", styles["header"]),
            Paragraph("ENGLISH", styles["header"]),
            Paragraph("MATHEMATICS", styles["header"]),
            Paragraph("SCIENCE", styles["header"]),
        ]
    ]

    for student in students:
        internal = student.get("internal_assessment", {})

        table_rows.append([
            make_student_listing_cell(student, styles),
            make_subject_listing_cell(internal.get("english"), styles),
            make_subject_listing_cell(internal.get("mathematics"), styles),
            make_subject_listing_cell(internal.get("science"), styles),
        ])

    if len(table_rows) == 1:
        table_rows.append([
            Paragraph("No matching internal assessment records found.", styles["student"]),
            "",
            "",
            ""
        ])

    table = Table(
        table_rows,
        colWidths=[
            10.5 * cm,
            6.0 * cm,
            6.0 * cm,
            6.0 * cm,
        ],
        repeatRows=1
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
        ("TEXTCOLOR", (0, 0), (-1, 0), EI_DARK),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, EI_BORDER),

        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),

        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F8FAFC")
        ]),

        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(table)

    try:
        selected_logo_path = logo_path
    except NameError:
        selected_logo_path = None

    doc.build(
        story,
        onFirstPage=lambda canvas, doc: add_header_footer(
            canvas,
            doc,
            report_title="ExamInsight: Internal Assessment Listing Report",
            logo_path=selected_logo_path
        ),
        onLaterPages=lambda canvas, doc: add_header_footer(
            canvas,
            doc,
            report_title="ExamInsight: Internal Assessment Listing Report",
            logo_path=selected_logo_path
        )
    )

    return output_path

# =========================================================
# Allowed Internal Assessment Year Groups
# Database stores yrgrp values in lowercase.
# =========================================================

ALLOWED_INTERNAL_YRGRPS = ["2-a", "2-b", "2-c", "2-d", "2-e", "2-f"]

# helper function to generate a cohort listing PDF for a specific year group
def generate_internal_cohort_listing_by_yrgrp_pdf(yrgrp):
    """
    Generates a downloadable Internal Assessment cohort listing PDF
    for one selected year group only.

    Database year groups are stored as lowercase:
    2-a, 2-b, 2-c, 2-d, 2-e, 2-f.
    """

    if not yrgrp:
        return None

    yrgrp_db = yrgrp.strip().lower()

    if yrgrp_db not in ALLOWED_INTERNAL_YRGRPS:
        return None

    filters = {
        # "q": "",
        # "gender": "All Genders",
        "yrgrp": yrgrp_db,
        # "status": "All Registration Status",
        # "sen": "All SEN/SPED",
    }

    return generate_internal_cohort_listing_pdf(filters)


# =========================================================
# Summary Report: Internal Assessment
# English, Mathematics, and Science.
# =========================================================

# -----------------------------
# Subject Configuration
# -----------------------------

INTERNAL_SUMMARY_SUBJECTS = {
    "english": {
        "api_key": "english",
        "label": "English",
        "header_label": "ENGLISH INTERNAL ASSESSMENT",
        "total_label": "Total Intake for English Assessment",
        "threshold_label": "English Attainment Thresholds",
        "current_label": "Current English %",
        "filename": "examinsight_english_internal_summary_report.pdf",
    },

    "mathematics": {
        "api_key": "mathematics",
        "label": "Mathematics",
        "header_label": "MATHEMATICS INTERNAL ASSESSMENT",
        "total_label": "Total Intake for Mathematics Assessment",
        "threshold_label": "Mathematics Attainment Thresholds",
        "current_label": "Current Mathematics %",
        "filename": "examinsight_mathematics_internal_summary_report.pdf",
    },

    "science": {
        "api_key": "science",
        "label": "Science",
        "header_label": "SCIENCE INTERNAL ASSESSMENT",
        "total_label": "Total Intake for Science Assessment",
        "threshold_label": "Science Attainment Thresholds",
        "current_label": "Current Science %",
        "filename": "examinsight_science_internal_summary_report.pdf",
    },
}


# ---------------------------------------------------------
# Helper: safely convert API values to float
# ---------------------------------------------------------

def safe_report_float(value, default=None):
    """
    Converts a value from the API into a float.
    Handles None, blank values, and '-' safely.
    """

    if value is None:
        return default

    value = str(value).strip()

    if value == "" or value == "-":
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------
# Helper: safely format percentage values
# ---------------------------------------------------------

def format_report_pct(value):
    """
    Formats numeric values as percentages for the PDF.
    """

    value = safe_report_float(value)

    if value is None:
        return "-"

    if value.is_integer():
        return f"{int(value)}%"

    return f"{value:.1f}%"


# ---------------------------------------------------------
# Helper: normalise progress category text
# ---------------------------------------------------------

def normalise_progress_category(value):
    """
    Normalises progress category values from the API.
    Expected values may include:
    - Below Expected
    - Expected
    - Above Expected
    """

    value = str(value or "").strip()

    if not value or value == "-":
        return "No Progress Available"

    lower_value = value.lower()

    if "below" in lower_value:
        return "Below Expected"

    if "above" in lower_value:
        return "Above Expected"

    if "expected" in lower_value:
        return "Expected"

    return value


# ---------------------------------------------------------
# Helper: percentage count
# ---------------------------------------------------------

def percentage(part, whole):
    """
    Returns percentage rounded to 1 decimal place.
    """

    return round((part / whole) * 100, 1) if whole else 0.0


# ---------------------------------------------------------
# Reusable table style
# ---------------------------------------------------------

def internal_summary_table_style(subject_label):
    """
    Standard table style for internal assessment summary PDFs.
    Used for English, Mathematics, and Science summary reports.
    """

    if subject_label == "English":
        header_color = EI_BLUE
    elif subject_label == "Mathematics":
        header_color = EI_YELLOW
    elif subject_label == "Science":
        header_color = EI_GREEN
    else:
        header_color = EI_BLUE

    return TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        # Body
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),

        # Alignment
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        # Borders and row colours
        ("GRID", (0, 0), (-1, -1), 0.4, EI_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, EI_LIGHT]),

        # Padding
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ])


# Optional: keep this if your old English code still calls it
# def english_summary_table_style():
#     """
#     Backward-compatible wrapper.
#     """

#     return internal_summary_table_style()


# ---------------------------------------------------------
# Progress table with background colours
# ---------------------------------------------------------

def make_internal_summary_progress_table(progress, subject_label):
    """
    Creates the progress distribution table with coloured row backgrounds.
    """

    if subject_label == "English":
        header_color = EI_BLUE
    elif subject_label == "Mathematics":
        header_color = EI_YELLOW
    elif subject_label == "Science":
        header_color = EI_GREEN
    else:
        header_color = EI_BLUE

    progress_data = [
        ["Progress Category", "Count", "Percentage"],
        ["Above Expected", progress.get("above_count", 0), f'{progress.get("above_pct", 0)}%'],
        ["Expected", progress.get("expected_count", 0), f'{progress.get("expected_pct", 0)}%'],
        ["Below Expected", progress.get("below_count", 0), f'{progress.get("below_pct", 0)}%'],
        ["No Progress Available", progress.get("no_progress_count", 0), f'{progress.get("no_progress_pct", 0)}%'],
    ]

    progress_table = Table(progress_data, colWidths=[250, 100, 110])

    progress_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        # Body text
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),

        # Row background colours
        ("BACKGROUND", (0, 1), (-1, 1), colors.white),   # Above Expected
        ("BACKGROUND", (0, 2), (-1, 2), colors.white),  # Expected
        ("BACKGROUND", (0, 3), (-1, 3), colors.white),     # Below Expected
        ("BACKGROUND", (0, 4), (-1, 4), colors.white),    # No Progress Available

        # Row text colours
        ("TEXTCOLOR", (0, 1), (-1, 1), EI_GREEN),
        ("TEXTCOLOR", (0, 2), (-1, 2), EI_YELLOW),
        ("TEXTCOLOR", (0, 3), (-1, 3), EI_RED),
        ("TEXTCOLOR", (0, 4), (-1, 4), EI_BLUE),

        # Layout
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, EI_BORDER),

        # Padding
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    return progress_table


# ---------------------------------------------------------
# Generic Subject Summary Data Builder
# ---------------------------------------------------------

def build_internal_subject_summary_data(subject_key, filters=None):
    """
    Builds whole-cohort internal assessment summary data for one subject.

    Supported subject_key values:
    - english
    - mathematics
    - science

    Data source:
    /api/reports/internal/combined-data
    """

    filters = filters or {}

    subject_config = INTERNAL_SUMMARY_SUBJECTS.get(subject_key)

    if not subject_config:
        return None

    api_subject_key = subject_config["api_key"]
    subject_label = subject_config["label"]

    # Build API URL using the current Flask host.
    base_url = request.host_url.rstrip("/")
    api_url = f"{base_url}/api/reports/internal/combined-data"

    # Add query parameters only if filters are supplied.
    query_params = {
        key: value
        for key, value in filters.items()
        if value is not None and str(value).strip() != ""
    }

    if query_params:
        api_url = f"{api_url}?{urlencode(query_params)}"

    # Request filtered or full cohort data from your API.
    response = requests.get(api_url, timeout=20)

    if response.status_code != 200:
        return None

    students = response.json()

    # Keep only students with at least some assessment data for this subject.
    subject_records = []

    for student in students:
        internal = student.get("internal_assessment", {})
        subject_data = internal.get(api_subject_key, {})

        previous_pct = safe_report_float(subject_data.get("previous_percentage"))
        current_pct = safe_report_float(subject_data.get("current_percentage"))

        # Skip completely blank subject records.
        if previous_pct is None and current_pct is None:
            continue

        yrgrp = str(student.get("yrgrp") or "Unknown").strip().upper()

        subject_records.append({
            "student_id": student.get("student_id"),
            "name": student.get("name"),
            "yrgrp": yrgrp,
            "previous_pct": previous_pct,
            "previous_grade": subject_data.get("previous_grade", "-"),
            "current_pct": current_pct,
            "current_grade": subject_data.get("current_grade", "-"),
            "progress_category": normalise_progress_category(
                subject_data.get("progress_category")
            ),
        })

    total_students = len(subject_records)

    # Safe empty structure if no data exists.
    if total_students == 0:
        return {
            "subject_label": subject_label,
            "total_students": 0,
            "avg_previous": 0,
            "avg_current": 0,
            "avg_change": 0,
            "attainment": {},
            "progress": {},
            "thresholds": {},
            "classes": [],
            "statements": {
                "overview": f"No {subject_label} internal assessment data is available.",
                "attainment": f"No {subject_label} attainment distribution can be calculated.",
                "progress": f"No {subject_label} progress data is available.",
                "comparison": "No class/year group comparison can be generated.",
            }
        }

    # Extract valid previous/current values.
    previous_values = [
        row["previous_pct"]
        for row in subject_records
        if row["previous_pct"] is not None
    ]

    current_values = [
        row["current_pct"]
        for row in subject_records
        if row["current_pct"] is not None
    ]

    avg_previous = round(sum(previous_values) / len(previous_values), 1) if previous_values else 0
    avg_current = round(sum(current_values) / len(current_values), 1) if current_values else 0
    avg_change = round(avg_current - avg_previous, 1)

    # -----------------------------------------------------
    # Attainment distribution based on current percentage
    # -----------------------------------------------------
    below_60 = sum(
        1 for row in subject_records
        if row["current_pct"] is not None and row["current_pct"] < 60
    )

    range_60_69 = sum(
        1 for row in subject_records
        if row["current_pct"] is not None and 60 <= row["current_pct"] < 70
    )

    range_70_79 = sum(
        1 for row in subject_records
        if row["current_pct"] is not None and 70 <= row["current_pct"] < 80
    )

    range_80_plus = sum(
        1 for row in subject_records
        if row["current_pct"] is not None and row["current_pct"] >= 80
    )

    attainment = {
        "below_60_count": below_60,
        "below_60_pct": percentage(below_60, total_students),

        "range_60_69_count": range_60_69,
        "range_60_69_pct": percentage(range_60_69, total_students),

        "range_70_79_count": range_70_79,
        "range_70_79_pct": percentage(range_70_79, total_students),

        "range_80_plus_count": range_80_plus,
        "range_80_plus_pct": percentage(range_80_plus, total_students),
    }

    # -----------------------------------------------------
    # Progress category distribution
    # -----------------------------------------------------
    below_expected = sum(
        1 for row in subject_records
        if row["progress_category"] == "Below Expected"
    )

    expected = sum(
        1 for row in subject_records
        if row["progress_category"] == "Expected"
    )

    above_expected = sum(
        1 for row in subject_records
        if row["progress_category"] == "Above Expected"
    )

    no_progress = sum(
        1 for row in subject_records
        if row["progress_category"] == "No Progress Available"
    )

    progress_total = below_expected + expected + above_expected + no_progress

    progress = {
        "below_count": below_expected,
        "below_pct": percentage(below_expected, progress_total),

        "expected_count": expected,
        "expected_pct": percentage(expected, progress_total),

        "above_count": above_expected,
        "above_pct": percentage(above_expected, progress_total),

        "no_progress_count": no_progress,
        "no_progress_pct": percentage(no_progress, progress_total),
    }

    # -----------------------------------------------------
    # Attainment thresholds
    # -----------------------------------------------------
    at_60 = sum(
        1 for row in subject_records
        if row["current_pct"] is not None and row["current_pct"] >= 60
    )

    at_70 = sum(
        1 for row in subject_records
        if row["current_pct"] is not None and row["current_pct"] >= 70
    )

    at_80 = sum(
        1 for row in subject_records
        if row["current_pct"] is not None and row["current_pct"] >= 80
    )

    thresholds = {
        "at_60_count": at_60,
        "at_60_pct": percentage(at_60, total_students),

        "at_70_count": at_70,
        "at_70_pct": percentage(at_70, total_students),

        "at_80_count": at_80,
        "at_80_pct": percentage(at_80, total_students),
    }

    # -----------------------------------------------------
    # Class/year group comparison
    # -----------------------------------------------------
    grouped = {}

    for row in subject_records:
        yrgrp = row["yrgrp"]

        if yrgrp not in grouped:
            grouped[yrgrp] = []

        grouped[yrgrp].append(row)

    class_rows = []

    for yrgrp, rows in sorted(grouped.items()):
        class_previous = [
            row["previous_pct"]
            for row in rows
            if row["previous_pct"] is not None
        ]

        class_current = [
            row["current_pct"]
            for row in rows
            if row["current_pct"] is not None
        ]

        class_avg_previous = round(sum(class_previous) / len(class_previous), 1) if class_previous else 0
        class_avg_current = round(sum(class_current) / len(class_current), 1) if class_current else 0
        class_change = round(class_avg_current - class_avg_previous, 1)

        class_at_60 = sum(
            1 for row in rows
            if row["current_pct"] is not None and row["current_pct"] >= 60
        )

        class_above_expected = sum(
            1 for row in rows
            if row["progress_category"] == "Above Expected"
        )

        class_expected = sum(
            1 for row in rows
            if row["progress_category"] == "Expected"
        )

        class_below_expected = sum(
            1 for row in rows
            if row["progress_category"] == "Below Expected"
        )

        class_rows.append({
            "yrgrp": yrgrp,
            "count": len(rows),
            "avg_previous": class_avg_previous,
            "avg_current": class_avg_current,
            "avg_change": class_change,
            "at_60_pct": percentage(class_at_60, len(rows)),
            "below_expected": class_below_expected,
            "expected": class_expected,
            "above_expected": class_above_expected,
        })

    # -----------------------------------------------------
    # Interpretation statements
    # -----------------------------------------------------
    dominant_attainment = max(
        [
            ("below 60%", below_60, attainment["below_60_pct"]),
            ("60%-69%", range_60_69, attainment["range_60_69_pct"]),
            ("70%-79%", range_70_79, attainment["range_70_79_pct"]),
            ("80% and above", range_80_plus, attainment["range_80_plus_pct"]),
        ],
        key=lambda item: item[1]
    )

    dominant_progress = max(
        [
            ("Below Expected", below_expected, progress["below_pct"]),
            ("Expected", expected, progress["expected_pct"]),
            ("Above Expected", above_expected, progress["above_pct"]),
            ("No Progress Available", no_progress, progress["no_progress_pct"]),
        ],
        key=lambda item: item[1]
    )

    if class_rows:
        highest_class = max(class_rows, key=lambda row: row["avg_current"])
        lowest_class = min(class_rows, key=lambda row: row["avg_current"])

        comparison_statement = (
            f"The highest {subject_label} current average is in {highest_class['yrgrp']} "
            f"at {highest_class['avg_current']}%, while the lowest current average is in "
            f"{lowest_class['yrgrp']} at {lowest_class['avg_current']}%."
        )
    else:
        comparison_statement = "Class/year group comparison is not available."

    return {
        "subject_label": subject_label,
        "total_students": total_students,
        "avg_previous": avg_previous,
        "avg_current": avg_current,
        "avg_change": avg_change,
        "attainment": attainment,
        "progress": progress,
        "thresholds": thresholds,
        "classes": class_rows,
        "statements": {
            "overview": (
                f"The {subject_label} cohort has an average current attainment of {avg_current}% "
                f"compared with a previous average of {avg_previous}%, showing an average change of {avg_change:+.1f} percentage points."
            ),
            "attainment": (
                f"The largest attainment group is {dominant_attainment[0]}, "
                f"with {dominant_attainment[1]} students ({dominant_attainment[2]}%)."
            ),
            "progress": (
                f"The most common {subject_label} progress category is {dominant_progress[0]}, "
                f"representing {dominant_progress[1]} students ({dominant_progress[2]}%)."
            ),
            "comparison": comparison_statement,
        }
    }


# ---------------------------------------------------------
# Generic Subject Summary PDF Builder
# ---------------------------------------------------------

def build_internal_subject_summary_pdf(subject_key, filters=None):
    """
    Builds a downloadable Internal Assessment Summary Report for a selected subject.

    Supported subject_key values:
    - english
    - mathematics
    - science
    """

    subject_config = INTERNAL_SUMMARY_SUBJECTS.get(subject_key)

    if not subject_config:
        return None

    report = build_internal_subject_summary_data(subject_key, filters)

    if not report:
        return None

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

    # Small paragraph style for interpretation statements.
    styles.add(
        ParagraphStyle(
            name="SmallText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=EI_DARK,
        )
    )

    if subject_key == "english":
        fontColor = EI_BLUE
    elif subject_key == "mathematics":
        fontColor = EI_ORANGE
    elif subject_key == "science":
        fontColor = EI_GREEN
    else:
        fontColor = EI_BLUE

    # Section title style similar to other ExamInsight reports.
    styles.add(
        ParagraphStyle(
            name="SummarySectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=fontColor,
            spaceBefore=8,
            spaceAfter=5,
        )
    )

    story = []

    subject_label = subject_config["label"]
    report_title = "ExamInsight: Summary Report"

    # -----------------------------------------------------
    # Report intro
    # -----------------------------------------------------
    generated_date = datetime.now().strftime("%a, %d-%b-%Y")

    if subject_label == "English":
        header_ = f'<font color="{EI_BLUE.hexval()}"><b>{subject_config["header_label"]}</b></font>'
    elif subject_label == "Mathematics":
        header_ = f'<font color="{EI_ORANGE.hexval()}"><b>{subject_config["header_label"]}</b></font>'
    elif subject_label == "Science":
        header_ = f'<font color="{EI_GREEN.hexval()}"><b>{subject_config["header_label"]}</b></font>'
    else:
        f'<font color="{EI_BLUE.hexval()}"><b>{report_title}</b></font>'

    story.append(
        Paragraph(
            header_ +
            f' &nbsp; | &nbsp; '
            f"<b>Date Generated:</b> {generated_date}",
            styles["SmallText"]
        )
    )
    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            f"This report summarises the {subject_label} internal assessment dataset for the selected cohort. "
            "It highlights overall performance, progress trends, attainment thresholds, and comparative "
            "outcomes across classes/year groups.",
            styles["SmallText"]
        )
    )
    story.append(Spacer(1, 12))

    # -----------------------------------------------------
    # KPI summary table
    # -----------------------------------------------------
    summary_data = [
        ["Metric", "Value"],
        ["Subject", subject_label],
        [subject_config["total_label"], report["total_students"]],
        ["Average Previous Attainment", f'{report["avg_previous"]}%'],
        ["Average Current Attainment", f'{report["avg_current"]}%'],
        ["Average Change", f'{report["avg_change"]:+.1f} percentage points'],
    ]

    summary_table = Table(summary_data, colWidths=[250, 210])
    summary_table.setStyle(internal_summary_table_style(subject_label))

    story.append(summary_table)
    story.append(Spacer(1, 8))
    story.append(Paragraph(report["statements"]["overview"], styles["SmallText"]))
    story.append(Spacer(1, 10))

    # -----------------------------------------------------
    # Attainment distribution
    # -----------------------------------------------------
    story.append(Paragraph("Attainment Distribution", styles["SummarySectionTitle"]))
    story.append(Spacer(1, 6))

    att = report["attainment"]

    attainment_data = [
        ["Band", "Current % Range", "Count", "Percentage"],
        ["Below Expected Attainment", "Below 60%", att.get("below_60_count", 0), f'{att.get("below_60_pct", 0)}%'],
        ["Expected Range", "60%-69%", att.get("range_60_69_count", 0), f'{att.get("range_60_69_pct", 0)}%'],
        ["Secure Attainment", "70%-79%", att.get("range_70_79_count", 0), f'{att.get("range_70_79_pct", 0)}%'],
        ["High Attainment", "80% and above", att.get("range_80_plus_count", 0), f'{att.get("range_80_plus_pct", 0)}%'],
    ]

    attainment_table = Table(attainment_data, colWidths=[170, 120, 80, 90])
    attainment_table.setStyle(internal_summary_table_style(subject_label))

    story.append(attainment_table)
    story.append(Spacer(1, 6))
    story.append(Paragraph(report["statements"]["attainment"], styles["SmallText"]))
    story.append(Spacer(1, 10))

    # -----------------------------------------------------
    # Progress distribution
    # -----------------------------------------------------
    story.append(Paragraph("Progress Distribution", styles["SummarySectionTitle"]))
    story.append(Spacer(1, 6))

    progress_table = make_internal_summary_progress_table(report["progress"], subject_label)

    story.append(progress_table)
    story.append(Spacer(1, 6))
    story.append(Paragraph(report["statements"]["progress"], styles["SmallText"]))
    story.append(Spacer(1, 10))

    # -----------------------------------------------------
    # Attainment thresholds
    # -----------------------------------------------------
    story.append(Paragraph(subject_config["threshold_label"], styles["SummarySectionTitle"]))
    story.append(Spacer(1, 6))

    thr = report["thresholds"]

    threshold_data = [
        ["Threshold", "Count", "Percentage"],
        [f'{subject_config["current_label"]} >= 60', thr.get("at_60_count", 0), f'{thr.get("at_60_pct", 0)}%'],
        [f'{subject_config["current_label"]} >= 70', thr.get("at_70_count", 0), f'{thr.get("at_70_pct", 0)}%'],
        [f'{subject_config["current_label"]} >= 80', thr.get("at_80_count", 0), f'{thr.get("at_80_pct", 0)}%'],
    ]

    threshold_table = Table(threshold_data, colWidths=[250, 100, 110])
    threshold_table.setStyle(internal_summary_table_style(subject_label))

    story.append(threshold_table)
    story.append(Spacer(1, 10))

    # -----------------------------------------------------
    # Move comparison table to page 2
    # -----------------------------------------------------
    story.append(PageBreak())

    # -----------------------------------------------------
    # Class/year group comparison
    # -----------------------------------------------------
    story.append(Paragraph("Class / Year Group Comparison", styles["SummarySectionTitle"]))
    story.append(Spacer(1, 6))

    class_data = [
        [
            "Class",
            "Students",
            "Avg Previous",
            "Avg Current",
            "Change",
            "% >= 60",
            "Below",
            "Expected",
            "Above",
        ]
    ]

    for row in report["classes"]:
        class_data.append([
            row["yrgrp"],
            row["count"],
            f'{row["avg_previous"]}%',
            f'{row["avg_current"]}%',
            f'{row["avg_change"]:+.1f}',
            f'{row["at_60_pct"]}%',
            row["below_expected"],
            row["expected"],
            row["above_expected"],
        ])

    class_table = Table(
        class_data,
        colWidths=[50, 55, 65, 65, 55, 55, 45, 55, 45]
    )

    class_table.setStyle(internal_summary_table_style(subject_label))

    story.append(class_table)
    story.append(Spacer(1, 6))
    story.append(Paragraph(report["statements"]["comparison"], styles["SmallText"]))

    # -----------------------------------------------------
    # Build PDF with your existing header/footer function
    # -----------------------------------------------------
    try:
        selected_logo_path = logo_path
    except NameError:
        selected_logo_path = None

    doc.build(
        story,
        onFirstPage=lambda canvas, doc: add_header_footer(
            canvas,
            doc,
            report_title=report_title,
            logo_path=selected_logo_path,
        ),
        onLaterPages=lambda canvas, doc: add_header_footer(
            canvas,
            doc,
            report_title=report_title,
            logo_path=selected_logo_path,
        ),
    )

    buffer.seek(0)

    return buffer


# ---------------------------------------------------------
# Subject Wrapper Functions
# ---------------------------------------------------------

def build_internal_english_summary_pdf(filters=None):
    """
    Builds the downloadable English Internal Assessment Summary Report.
    """

    return build_internal_subject_summary_pdf("english", filters)


def build_internal_mathematics_summary_pdf(filters=None):
    """
    Builds the downloadable Mathematics Internal Assessment Summary Report.
    """

    return build_internal_subject_summary_pdf("mathematics", filters)


def build_internal_science_summary_pdf(filters=None):
    """
    Builds the downloadable Science Internal Assessment Summary Report.
    """

    return build_internal_subject_summary_pdf("science", filters)
