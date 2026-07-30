import os # System files and OS utilities
import re # Regular expressions for pattern matching and validation
import uuid # For generating unique identifiers
from colorama import Fore, Style # Colorama for terminal text styling
from apps import db # Database instance from the apps package
from apps.authentication.models import Users, NGRTA, NGRTB, NGRTC, InternalExam, Students # Importing models from the authentication module
from apps.config import Config # Importing configuration settings from the config module
from apps.messages import Messages # Importing message templates from the messages module
from marshmallow import ValidationError # Marshmallow for data validation and error handling
from functools import wraps # Wraps for preserving function metadata in decorators
from urllib.parse import urlencode # URL encoding for query parameters
from flask import request, url_for # Flask request and URL generation utilities
from sqlalchemy import or_, String, literal # SQLAlchemy utilities for query construction and type handling
from uuid import uuid4 # For generating unique identifiers
import datetime, time # Date and time utilities for timestamp generation and manipulation

message = Messages.message

# Global configuration variables retrieved from the Config class
Currency = Config.CURRENCY
PAYMENT_TYPE = Config.PAYMENT_TYPE
STATE = Config.STATE

# Regular expression pattern for validating email addresses
regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')

# FTP image URL retrieved from environment variables
def get_ts():
    return int(time.time())

# Password validation function
def password_validate(password):
    """ password validate """
    msg = ''
    while True:
        if len(password) < 6:
           msg = "Make sure your password is at lest 6 letters"
           return msg
        elif re.search('[0-9]',password) is None:
            msg = "Make sure your password has a number in it"
            return msg
        elif re.search('[A-Z]',password) is None: 
            msg = "Make sure your password has a capital letter in it"
            return msg
        else:
            msg = True
            break
        
    return True

# Email validation function
def emailValidate(email):
    """ validate email  """
    if re.fullmatch(regex, email):
        return True
    else:
        return False

# santise file name
def sanitise_fille_name(value):
    """ remove special char  """
    return value.strip().lower().replace(' ', '_').replace('(', '').replace(')', '').replace(',', '').replace('=','_').replace('-', '_').replace('#', '')

# create folder for save csv
def createFolder(folder_name):
    """ create folder for save csv """
    if not os.path.exists(f'{folder_name}'):
        os.makedirs(f'{folder_name}')

    return folder_name

# generate unique file name
def uniqueFileName(file_name):
    """ for Unique file name"""
    file_uuid = uuid.uuid4()
    IMAGE_NAME = f'{file_uuid}-{file_name}'
    return IMAGE_NAME

# generate server image url
def serverImageUrl(file_name):
    """ for Unique file name"""
    url = f'{FTP_IMAGE_URL}{file_name}' # type: ignore
    return url

# generate server image url
def errorColor(error):
    """ for terminal input error color """
    print(Fore.RED + f'{error}')
    print(Style.RESET_ALL)
    return True

# generate server image url
def splitUrlGetFilename(url):
    """ image url split and get file name  """
    return url.split('/')[-1]

# validate state
def validateState(state):
    """ check valid state methods  """
    # if check state  validate or not
    if state not in list(STATE.keys()):
        raise ValidationError(
            f"{message['invalid_state']}, expected {expectedValue(STATE)}", 422)
    else:
        value = 0
        if state == "completed":
            value =  1
        elif state == "pending":
            value = 2
        else:
            value = 3

    return value 

# validate payment type
def expectedValue(data):
    """ key get values """
    values = []
    for k,v in data.items():
        values.append(f'{v}.({k})')

    return ",".join(values)

# create access token
def createAccessToken():
    """ create access token w"""
    rand_token = uuid4()

    return f"{str(rand_token)}"

# token validate
def token_required(f):
    """ check token """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"]
        if not token:
            return {
                "message": "Authentication Token is missing!",
                "error": "Unauthorized"
            }, 401
        try:
            current_user = Users.find_by_api_token(token)
            if current_user is None:
                return {
                "message": "Invalid Authentication token!",
                "error": "Unauthorized"
            }, 401
            # if not current_user["active"]:
            #     abort(403)
        except Exception as e:
            return {
                "message": "Something went wrong",
                "error": str(e)
            }, 500

        return f(current_user, **kwargs)

    return decorated

# Helper functions for applying search and filters to SQLAlchemy queries, 
# generating dropdown values, building URLs, and managing active filters in web applications.
def _apply_search(query, search_cfg, qval):
    if not qval or not search_cfg:
        return query
    like = f"%{qval}%"
    ors = []
    for col in search_cfg["columns"]:
        ors.append(col.ilike(like) if not hasattr(col, "type") else col.ilike(like))
    return query.filter(or_(*ors))

# Helper function to apply filters to a SQLAlchemy query 
# based on provided filter configurations and request arguments.
def _apply_filters(query, filters_cfg, args):
    for f in filters_cfg:
        val = (args.get(f["param"], "") or "").strip()
        if not val:
            continue
        if "custom" in f and callable(f["custom"]):
            query = f["custom"](query, val)
        else:
            # default equality filter
            query = query.filter(f["column"] == val)
    return query

# Helper function to generate dropdown values for a web application 
# based on provided configurations and database session.
def _dropdown_values(dropdowns_cfg, db_session):
    out = {}
    for key, maker in dropdowns_cfg.items():
        out[key] = maker(db_session)
    return out

# Helper function to build a URL for removing a specific filter 
# from the current request's query parameters.
def _build_remove_url(endpoint, base_args, key):
    args = base_args.copy()
    args.pop(key, None)
    return url_for(endpoint) + "?" + urlencode(args)

# Helper function to generate a list of active filters 
# based on the current request's query parameters,
# provided labels, and the endpoint for removing filters.
def _active_filters(args, labels, endpoint):
    items = []
    base_args = args.to_dict()
    for key, label in labels.items():
        val = (args.get(key, "") or "").strip()
        if val:
            items.append((label, val, _build_remove_url(endpoint, base_args, key)))
    return items

# Helper functions for generating SQLAlchemy expressions for subject metrics,
# calculating cohort and class progress, and fetching NGRT assessment data.
from apps.authentication.models import InternalExam, Students
from sqlalchemy.sql import func, case

# Helper function to build labeled SQLAlchemy expressions for one subject's metrics.
def _subject_cols(col, prefix: str, thr60: int, thr70: int):
    """
    Build labeled SQLAlchemy expressions for one subject:
      avg, n, >=60 pass, >=70 pass, >=60 pct, >=70 pct.
    Labels match the current schema (e.g., eng_avg, eng_n, eng60_pass, eng70_pass, eng60_pct, eng70_pct).
    """
    n     = func.count(col).label(f"{prefix}_n")
    ge60  = func.sum(case((col >= thr60, 1), else_=0)).label(f"{prefix}60_pass")
    ge70  = func.sum(case((col >= thr70, 1), else_=0)).label(f"{prefix}70_pass")
    avg   = func.avg(col).label(f"{prefix}_avg")
    pct60 = ((ge60 * 100.0) / func.nullif(n, 0)).label(f"{prefix}60_pct")
    pct70 = ((ge70 * 100.0) / func.nullif(n, 0)).label(f"{prefix}70_pct")
    return [avg, n, ge60, ge70, pct60, pct70]

# Helper function to generate a full list of labeled columns for ENG, MATHS, and SCI subjects,
# using the exact labels currently in use (e.g., eng_*, maths_*, sci_*).
def per_class_metrics(thr60: int = 60, thr70: int = 70):
    """
    Return the full list of labeled columns for ENG / MATHS / SCI
    with the exact labels being used:
      eng_* , maths_* , sci_*
    """
    eng   = _subject_cols(InternalExam.eng_currPct,   "eng",   thr60, thr70)
    maths = _subject_cols(InternalExam.maths_currPct, "maths", thr60, thr70)
    sci   = _subject_cols(InternalExam.sci_currPct,   "sci",   thr60, thr70)
    return [*eng, *maths, *sci]

# Extract cohort progress for E/M/S
def cohort_progress(col):
        """
        Return 2 percentages for a progcat column:
        - p_sum = %('expected') + %('above expected')
        - p_above = %('above expected')
        """
        norm = func.lower(func.trim(col))  # normalise for safe matching

        # total non-null rows for this subject's progcat
        total = db.session.query(func.count(col)).scalar() or 0

        # count of 'expected'
        exp_cnt = db.session.query(
            func.sum(case((norm == "expected", 1), else_=0))
        ).scalar() or 0

        # count of 'above expected'
        above_cnt = db.session.query(
            func.sum(case((norm == "above expected", 1), else_=0))
        ).scalar() or 0

        # count of expected and above (sum), and above only
        cnt_exp_above = exp_cnt + above_cnt
        cnt_above_only = above_cnt

        # percentages (protect from divide-by-zero)
        p_expected = round((exp_cnt / total * 100.0), 1) if total else 0.0
        p_above    = round((above_cnt / total * 100.0), 1) if total else 0.0

        # requested variables
        pct_exp_above = round(p_expected + p_above, 1)  # Expected + Above Expected
        pct_above_only = p_above # Above Expected only (explicit name)

        return total, cnt_exp_above, cnt_above_only, pct_exp_above, pct_above_only

# Extract class-wise progress for E/M/S
def class_progress(col, class_col):
    """
    Returns a dict mapping each class -> the same 5-tuple as cohort_progress:
      { "2-A": (total, cnt_exp_above, cnt_above_only, pct_exp_above, pct_above_only), ... }
    """
    # If strings are provided, resolve them to actual SQLAlchemy columns
    if isinstance(col, str):
        col = getattr(InternalExam, col)
    if isinstance(class_col, str):
        class_col = getattr(Students, class_col)

    # Normalize values: handle NULL, spaces, commas, casing
    norm = func.lower(func.trim(func.replace(func.coalesce(col, ""), ",", "")))

    # Build a grouped query to calculate counts for each class
    q = (
        db.session.query(
            class_col.label("klass"),

            # IMPORTANT: don't use count(col); count rows instead
            func.count(InternalExam.student_id).label("total"),

            func.sum(case((norm == "expected", 1), else_=0)).label("exp_cnt"),
            func.sum(case((norm == "above expected", 1), else_=0)).label("above_cnt"),
        )
        .select_from(InternalExam)
        .join(Students, InternalExam.student_id == Students.student_id)
        .group_by(class_col)
    )

    result = {}
    # Iterate over the query results and calculate percentages for each class
    for klass, total, exp_cnt, above_cnt in q.all():
        total = int(total or 0)
        exp_cnt = int(exp_cnt or 0)
        above_cnt = int(above_cnt or 0)

        cnt_exp_above  = exp_cnt + above_cnt
        cnt_above_only = above_cnt

        pct_exp_above  = round((cnt_exp_above / total * 100.0), 1) if total else 0.0
        pct_above_only = round((cnt_above_only / total * 100.0), 1) if total else 0.0

        result[str(klass).strip().lower()] = (total, cnt_exp_above, cnt_above_only, pct_exp_above, pct_above_only)

    return result

# Modular function to fetch NGRT assessment data for a given model (A/B/C) and combine with student info, ready for JSON output
def fetch_ngrt_asst_json(db, Students, asst_model):
    """
    Returns a list[dict] combining Students + an NGRT assessment model row,
    ordered by yrgrp then forename, JSON-ready.
    """
    rows = (
        db.session.query(Students, asst_model)
        .join(asst_model, asst_model.student_id == Students.student_id)
        .order_by(Students.yrgrp, Students.forename)
        .all()
    )

    # Return a list of dictionaries, each containing student info and the corresponding NGRT assessment data
    return [
        {
            **asst.to_dict(),
            "forename": student.forename,
            "surname": student.surname,
            "gender": student.gender,
            "yrgrp": student.yrgrp,
        }
        for student, asst in rows # Unpack each tuple of (Students, asst_model) into a combined dictionary
    ]

# Modular function to fetch all 3 NGRT assessments and 
# combine into a single payload dict for the external analytics endpoint
def fetch_extl_asst_payload(db, Students, NGRTA, NGRTB, NGRTC):
    """
    Returns the full payload dict for external analytics endpoint.
    """
    return {
        "ngrta": fetch_ngrt_asst_json(db, Students, NGRTA),
        "ngrtb": fetch_ngrt_asst_json(db, Students, NGRTB),
        "ngrtc": fetch_ngrt_asst_json(db, Students, NGRTC),
    }

# Convert exam key into the corresponding NGRT model class
def get_ngrt_model_by_exam(exam):
    exam = (exam or "").strip().lower().replace("-", "")

    exam_map = { "ngrta": NGRTA, "ngrtb": NGRTB, "ngrtc": NGRTC, }

    return exam_map.get(exam)

# Reusable query helper for NGRT-A, NGRT-B, and NGRT-C, with dynamic model selection based on the exam parameter
def get_filtered_ngrt_combined_data(exam, args=None):
    args = args or request.args

    Model = get_ngrt_model_by_exam(exam)

    # If the exam parameter is invalid, return an empty list
    if Model is None:
        return []

    # Extract search and filter parameters from the request arguments
    q = (args.get("q", "") or "").strip()
    gender = (args.get("gender", "") or "").strip()
    yrgrp = (args.get("yrgrp", "") or "").strip()
    status = (args.get("status", "") or "").strip()
    sped = (args.get("sped", "") or "").strip()

    # Build the base query joining Students with the selected NGRT model
    query = (
        db.session.query(Students, Model)
        .join(Model, Model.student_id == Students.student_id)
    )

    # Search by forename, surname, or student_id
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Students.forename.ilike(like),
                Students.surname.ilike(like),
                Students.student_id.cast(String).ilike(like),
            )
        )

    # Filter by gender
    if gender:
        query = query.filter(Students.gender == gender)

    # Filter by year group/class
    if yrgrp:
        query = query.filter(Students.yrgrp == yrgrp)

    # Filter by status
    if status:
        query = query.filter(Students.status == status)

    # Filter by SEN/SPED
    if sped:
        if sped == "Any SEN Support":
            query = query.filter(Students.sped != "No")
        elif sped == "No SEN/SPED Support":
            query = query.filter(Students.sped == "No")

    # Filter by progress category (if provided)
    if progress_category := (args.get("progress_category", "") or "").strip():
        query = query.filter(getattr(Model, "progress_category").ilike(progress_category))

    combined_data = (
        query
        .order_by(Students.yrgrp, Students.forename)
        .all()
    )

    # Return the combined data as a list of tuples (Students, Model)
    return combined_data