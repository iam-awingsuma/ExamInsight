# apps/reports.py

from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

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

    Allowed values:
    - ngrta
    - ngrtb
    - ngrtc
    """

    exam = (exam or "").strip().lower()

    exam_map = {
        "ngrta": ("NGRT-A", NGRTA),
        "ngrtb": ("NGRT-B", NGRTB),
        "ngrtc": ("NGRT-C", NGRTC),
    }

    return exam_map.get(exam)


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
    # NGRT-A may not have progress_category.
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


# --------------------------------------------------
# PDF builder
# --------------------------------------------------

def build_ngrt_summary_pdf(exam):
    """
    Builds the downloadable ExamInsight NGRT PDF report
    for NGRT-A, NGRT-B, or NGRT-C.
    """

    report = build_ngrt_report_data(exam)

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
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

    # ------------------------------------------
    # Title
    # ------------------------------------------
    story.append(Paragraph(f"ExamInsight {report['latest_exam']} Summary Report", styles["Title"]))
    story.append(Spacer(1, 8))

    generated_date = datetime.now().strftime("%d %B %Y")
    story.append(Paragraph(f"<b>Date Generated:</b> {generated_date}", styles["Normal"]))
    story.append(Spacer(1, 14))

    story.append(
        Paragraph(
            f"This report summarizes the selected NGRT assessment dataset: <b>{report['latest_exam']}</b>.",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 18))

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
    story.append(Spacer(1, 20))

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
    story.append(Spacer(1, 12))

    story.append(Paragraph(report["statements"]["attainment"], styles["SmallText"]))
    story.append(Spacer(1, 18))

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
    story.append(Spacer(1, 12))

    story.append(Paragraph(report["statements"]["progress"], styles["SmallText"]))
    story.append(Spacer(1, 18))

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
    story.append(Spacer(1, 12))

    story.append(Paragraph(report["statements"]["threshold"], styles["SmallText"]))

    # Build PDF
    doc.build(story)

    buffer.seek(0)
    return buffer


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