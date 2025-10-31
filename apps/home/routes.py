import os
import pandas as pd
import requests
from apps.home import blueprint
from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from jinja2 import TemplateNotFound
from flask_login import login_required, current_user
from apps import db
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, case, func, String, and_, or_

from apps.authentication.models import NGRTA, NGRTB, NGRTC, InternalExam, Students

from apps.home import make_list_context, _build_predicates

from apps.helpers import per_class_metrics, cohort_progress

from urllib.parse import urlencode

from flask_login import (
    current_user,
    login_user,
    logout_user,
    login_required
)

from functools import wraps

from apps.authentication.forms import CreateAccountForm
from apps.authentication.models import Users
from apps.authentication.routes import admin_required


@blueprint.route('/')
@blueprint.route('/index')
@login_required
def index():
    # return render_template('pages/index.html', segment='dashboard', parent="dashboard")
    # logged_in = session.get('logged_in', False) # check if user is logged in for session management
    return render_template('pages/index.html', segment='dashboard')


#************************
#*** Data Management ***#
#************************
# Define the upload folder & allowed extensions
UPLOAD_FOLDER = 'static/assets/images/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Helper function to check file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#*******************************
#*** User Management Routes ***#
#*******************************
@blueprint.route('/all-users')
def allusers():
    users = Users.query.all()  # Fetch all users from the database
    return render_template('pages/users-all.html', users=users, segment='all users', parent='userMgt')

@blueprint.route('/add-users', methods=['GET', 'POST'])
def addusers():
    create_account_form = CreateAccountForm(request.form)
    if 'addusers' in request.form:

        username = request.form['username']
        email = request.form['email']

        # Check if username already exists
        user = Users.query.filter_by(username=username).first()
        if user:
            return render_template('pages/users-add.html',
                                   segment='add users',
                                   parent='userMgt',
                                   msg='Username already registered.',
                                   success=False,
                                   form=create_account_form)

        # Check email exists
        user = Users.query.filter_by(email=email).first()
        if user:
            return render_template('pages/users-add.html',
                                   segment='add users',
                                   parent='userMgt',
                                   msg='E-mail already registered.',
                                   success=False,
                                   form=create_account_form)

        # Check if this is the first user (make them admin)
        if Users.query.count() == 0:
            user['is_admin'] = True

        # else we can create the user
        user = Users(**request.form)
        db.session.add(user)
        db.session.commit()

        return render_template('pages/users-add.html',
                               segment='add users',
                               parent='userMgt',
                               msg='User created successfully.',
                               success=True,
                               form=create_account_form)

    else:
        return render_template('pages/users-add.html', segment='add users', parent='userMgt', form=create_account_form)


#*******************************
#*** Profile Mgt/Page Route ***#
#*******************************
@blueprint.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        designation = request.form.get('designation')
        address = request.form.get('address')

        # Update user details
        current_user.first_name = first_name
        current_user.last_name = last_name
        current_user.designation = designation
        current_user.address = address

        # Check if a file was uploaded
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                
                # Save the file
                file.save(file_path)

                # Update user profile picture in the database
                current_user.profile_image = filename  # Assuming 'profile_image' is a column in Users table

        try:
            db.session.commit()
            flash("Profile updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash("Error updating profile!", "danger")

        return redirect(url_for('home_blueprint.profile'))

    return render_template('pages/profile.html', segment='profile')


# define the CSV upload folder for temporary storage
CSV_UPLOAD = 'static/assets/csv'

# Ensure the CSV upload folder exists
if not os.path.exists(CSV_UPLOAD):
    os.makedirs(CSV_UPLOAD)


#************************************
#*** External Assessments Routes ***#
#************************************
@blueprint.route('/display_ngrta', methods=['POST'])
def upload_ngrta():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(request.url)
    
    if file and file.filename.endswith('.csv'):
        # Save the file temporarily
        filepath = os.path.join(CSV_UPLOAD, file.filename)
        file.save(filepath)
        
        # Read CSV and store in database
        df = pd.read_csv(filepath)
        
        for index, row in df.iterrows():
            # Insert data into table - students
            student_id=int(row['student_id'])

            # Handle students table
            student = Students.query.filter_by(student_id=student_id).first()
            if student:
                # Update existing student record
                student.forename = str(row['forename'])
                student.surname = str(row['surname'])
                student.gender = str(row['gender'])
                student.date_of_birth = str(row['date_of_birth'])
                student.yrgrp = str(row['yrgrp'])
                student.sped = str(row['sped'])
                student.nationality = str(row['nationality'])
                student.status = str(row['status'])
            else:
                # New student record
                student = Students(
                    student_id=student_id,
                    forename=str(row['forename']),
                    surname=str(row['surname']),
                    gender=str(row['gender']),
                    date_of_birth=str(row['date_of_birth']),
                    yrgrp=str(row['yrgrp']),
                    sped=str(row['sped']),
                    nationality=str(row['nationality']),
                    status=str(row['status'])
                )
                db.session.add(student)
            
            # Handle NGRTA table
            ngrta = NGRTA.query.filter_by(student_id=student_id).first()
            if ngrta:
                # Update existing NGRTB record
                ngrta.ngrt_level = str(row['ngrt_level'])
                ngrta.sas = int(row['sas'])
                ngrta.stanine = int(row['stanine'])
                ngrta.reading_age = str(row['reading_age'])
                ngrta.profile_desc = str(row['profile_desc'])
            else:
                # New NGRTA record
                ngrta = NGRTA(
                    student_id=student_id,
                    ngrt_level=str(row['ngrt_level']),
                    sas=int(row['sas']),
                    stanine=int(row['stanine']),
                    reading_age=str(row['reading_age']),
                    profile_desc=str(row['profile_desc'])
                )
                db.session.add(ngrta)
        
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Some records were skipped due to duplicates.", "warning")  # Duplicate message

        # Clean up temporary file
        os.remove(filepath)
        return redirect(url_for('home_blueprint.display_ngrta'))
    
    return redirect(request.url)

# define a new route for templates/pages/display_ngrta.html
@blueprint.route('/display_ngrta', methods=['GET'])
def display_ngrta():
    # student_data = Students.query.all()  # Fetch all entries from Students table  
    student_data = Students.query.order_by(Students.yrgrp, Students.forename).all()
    ngrta_data = NGRTA.query.all()  # Fetch all entries from NGRTA table
    
    # Check if either table is empty
    ngrta_empty = not ngrta_data  # True if NGRTA is empty
    students_empty = not student_data  # True if Students is empty
    
    # modularized search filters for NGRT-A students view
    config = {
        "search": {
            "param": "q",
            "columns": [Students.forename, Students.surname, Students.student_id.cast(String)],
        },
        "filters": [
            {"param": "gender", "column": Students.gender},
            {"param": "yrgrp", "column": Students.yrgrp},
            {"param": "status", "column": Students.status},
            {"param": "sped", "custom_pred": lambda v: (Students.sped != "No") if v == "Any SEN Support" else (Students.sped == "No")},
        ],
        "order_by": [Students.yrgrp, Students.forename],
        "dropdowns": {
            "genders": lambda s: [g[0] for g in s.query(Students.gender).distinct().order_by(Students.gender)],
            "yrgrps":  lambda s: [y[0] for y in s.query(Students.yrgrp).distinct().order_by(Students.yrgrp)],
            "statuses":  lambda s: [t[0] for t in s.query(Students.status).distinct().order_by(Students.status)],
            "speds":  lambda s: ["Any SEN Support", "No SEN/SPED Support"],
        },
        # labels for the filter chips
        "labels": {"q": "Search", "gender": "Gender", "yrgrp": "Year", "status": "Status", "sped": "SEN/SPED",},
    }

    ctx = make_list_context(model=Students, db=db, config=config, endpoint="home_blueprint.display_ngrta")
    
    # If both tables are empty
    if ngrta_empty and students_empty:
        return render_template(
            'pages/display_ngrta.html',
            segment='external data - NGRT (Form-A)',
            parent='extBTest',
            no_data=True, ngrta_data=None, student_data=None,
            msg_ngrta='No NGRT-A data available.',
            msg_students='No student data available.',
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"], yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"], speds=ctx["dropdowns"]["speds"],
            **ctx["current"],
            filtered_is_empty=ctx["filtered_is_empty"], active_filters=ctx["active_filters"],
        )
    # If only NGRTA is empty
    elif ngrta_empty:
        return render_template(
            'pages/display_ngrta.html',
            segment='external data - NGRT (Form-A)',
            parent='extBTest',
            no_data=True, ngrta_data=None,
            msg_ngrta='No NGRT-A data available.',
            student_data=student_data,
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"], yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"], speds=ctx["dropdowns"]["speds"],
            **ctx["current"],
            filtered_is_empty=ctx["filtered_is_empty"], active_filters=ctx["active_filters"],
        )
    # If only Students is empty
    elif students_empty:
        return render_template(
            'pages/display_ngrta.html',
            segment='external data - NGRT (Form-A)',
            parent='extBTest',
            no_data=True, student_data=None,
            msg_students='No student data available.',
            ngrta_data=ngrta_data,
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"], yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"], speds=ctx["dropdowns"]["speds"],
            **ctx["current"],
            filtered_is_empty=ctx["filtered_is_empty"], active_filters=ctx["active_filters"],
        )
    # If both tables have data
    else:
        preds = ctx["predicates"]
        combined_data = (
            db.session.query(Students, NGRTA)
            .join(Students, NGRTA.student_id == Students.student_id)
            .filter(*preds) # same filters/search applied
            .order_by(Students.yrgrp, Students.forename)
            .all()
        )
        return render_template(
            'pages/display_ngrta.html',
            segment='external data - NGRT (Form-A)',
            parent='extBTest',
            no_data=False,
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"], yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"], speds=ctx["dropdowns"]["speds"],
            **ctx["current"],
            filtered_is_empty=ctx["filtered_is_empty"], active_filters=ctx["active_filters"],
            combined_data=combined_data,
        )

@blueprint.route('/display_ngrtb', methods=['POST'])
def upload_ngrtb():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(request.url)
    
    if file and file.filename.endswith('.csv'):
        # Save the file temporarily
        filepath = os.path.join(CSV_UPLOAD, file.filename)
        file.save(filepath)
        
        # Read CSV and store in database
        df = pd.read_csv(filepath)
        
        # Clear existing data (optional)
        # db.session.query(NGRTB).delete()
        
        for index, row in df.iterrows():
            # Insert data into table - students
            student_id=int(row['student_id'])

            # Handle students table
            student = Students.query.filter_by(student_id=student_id).first()
            if student:
                # Update existing student record
                student.forename = str(row['forename'])
                student.surname = str(row['surname'])
                student.gender = str(row['gender'])
                student.date_of_birth = str(row['date_of_birth'])
                student.yrgrp = str(row['yrgrp'])
                student.sped = str(row['sped'])
                student.nationality = str(row['nationality'])
                student.status = str(row['status'])
            else:
                # New student record
                student = Students(
                    student_id=student_id,
                    forename=str(row['forename']),
                    surname=str(row['surname']),
                    gender=str(row['gender']),
                    date_of_birth=str(row['date_of_birth']),
                    yrgrp=str(row['yrgrp']),
                    sped=str(row['sped']),
                    nationality=str(row['nationality']),
                    status=str(row['status'])
                )
                db.session.add(student)
            
            # Handle NGRTB table
            ngrtb = NGRTB.query.filter_by(student_id=student_id).first()
            if ngrtb:
                # Update existing NGRTB record
                ngrtb.ngrt_level = str(row['ngrt_level'])
                ngrtb.sas = int(row['sas'])
                ngrtb.stanine = int(row['stanine'])
                ngrtb.reading_age = str(row['reading_age'])
                ngrtb.prev_test_name = str(row['prev_test_name'])
                ngrtb.prev_sas = int(row['prev_sas'])
                ngrtb.prev_stanine = int(row['prev_stanine'])
                ngrtb.progress_category = str(row['progress_category'])
                ngrtb.reader_profile = str(row['reader_profile'])
                ngrtb.profile_desc = str(row['profile_desc'])
            else:
                # New NGRTB record
                ngrtb = NGRTB(
                    student_id=student_id,
                    ngrt_level=str(row['ngrt_level']),
                    sas=int(row['sas']),
                    stanine=int(row['stanine']),
                    reading_age=str(row['reading_age']),
                    prev_test_name=str(row['prev_test_name']),
                    prev_sas=int(row['prev_sas']),
                    prev_stanine=int(row['prev_stanine']),
                    progress_category=str(row['progress_category']),
                    reader_profile=str(row['reader_profile']),
                    profile_desc=str(row['profile_desc'])
                )
                db.session.add(ngrtb)
        
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Some records were skipped due to duplicates.", "warning")  # Duplicate message

        # Clean up temporary file
        os.remove(filepath)
        return redirect(url_for('home_blueprint.display_ngrtb'))
    
    return redirect(request.url)

# define a new route for templates/pages/display_ngrtb.html
@blueprint.route('/display_ngrtb', methods=['GET'])
def display_ngrtb():
    # student_data = Students.query.all()  # Fetch all entries from Students table  
    student_data = Students.query.order_by(Students.yrgrp, Students.forename).all()
    ngrtb_data = NGRTB.query.all()  # Fetch all entries from NGRTB table

    # Check if either table is empty
    ngrtb_empty = not ngrtb_data  # True if NGRTB is empty
    students_empty = not student_data  # True if Students is empty

    # modularized search filters for NGRT-B students view
    config = {
        "search": {
            "param": "q",
            "columns": [Students.forename, Students.surname, Students.student_id.cast(String)],
        },
        "filters": [
            {"param": "gender", "column": Students.gender},
            {"param": "yrgrp", "column": Students.yrgrp},
            {"param": "status", "column": Students.status},
            {"param": "sped", "custom_pred": lambda v: (Students.sped != "No") if v == "Any SEN Support" else (Students.sped == "No")},
            {"param": "progress_category", "column": NGRTB.progress_category},
        ],
        "order_by": [Students.yrgrp, Students.forename],
        "dropdowns": {
            "genders": lambda s: [g[0] for g in s.query(Students.gender).distinct().order_by(Students.gender)],
            "yrgrps":  lambda s: [y[0] for y in s.query(Students.yrgrp).distinct().order_by(Students.yrgrp)],
            "statuses":  lambda s: [t[0] for t in s.query(Students.status).distinct().order_by(Students.status)],
            "speds":  lambda s: ["Any SEN Support", "No SEN/SPED Support"],
            "progress_categories": lambda s: [p[0] for p in s.query(NGRTB.progress_category).distinct().order_by(NGRTB.progress_category)],
        },
        # labels for the filter chips
        "labels": {"q": "Search", "gender": "Gender", "yrgrp": "Year", "status": "Status", "sped": "SEN/SPED","progress_category": "Progress",},
    }

    ctx = make_list_context(model=Students, db=db, config=config, endpoint="home_blueprint.display_ngrtb")
    
    # If both tables are empty
    if ngrtb_empty and students_empty:
        return render_template(
            'pages/display_ngrtb.html',
            segment='external data - NGRT (Form-B)', parent='extBTest',
            no_data=True, ngrtb_data=None, student_data=None,
            msg_ngrtb='No NGRT-B data available.',
            msg_students='No student data available.',
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"],
            yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"],
            speds=ctx["dropdowns"]["speds"],
            progress_categories=ctx["dropdowns"]["progress_categories"],
            **ctx["current"],
            # no_data=ctx["no_data"],
            filtered_is_empty=ctx["filtered_is_empty"],
            active_filters=ctx["active_filters"],
        )
    # If only NGRTB is empty
    elif ngrtb_empty:
        return render_template(
            'pages/display_ngrtb.html',
            segment='external data - NGRT (Form-B)',
            parent='extBTest',
            no_data=True,
            msg_ngrtb='No NGRT-B data available.',
            student_data=student_data,
            ngrtb_data=None,
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"],
            yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"],
            speds=ctx["dropdowns"]["speds"],
            progress_categories=ctx["dropdowns"]["progress_categories"],
            **ctx["current"],
            # no_data=ctx["no_data"],
            filtered_is_empty=ctx["filtered_is_empty"],
            active_filters=ctx["active_filters"],
        )
    # If only Students is empty
    elif students_empty:
        return render_template(
            'pages/display_ngrtb.html',
            segment='external data - NGRT (Form-B)',
            parent='extBTest',
            no_data=True,
            msg_students='No student data available.',
            ngrtb_data=ngrtb_data,
            student_data=None,
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"],
            yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"],
            speds=ctx["dropdowns"]["speds"],
            progress_categories=ctx["dropdowns"]["progress_categories"],
            **ctx["current"],
            # no_data=ctx["no_data"],
            filtered_is_empty=ctx["filtered_is_empty"],
            active_filters=ctx["active_filters"],
        )
    # If both tables have data
    else:
        preds = ctx["predicates"]
        combined_data = (
            db.session.query(Students, NGRTB)
            .join(Students, NGRTB.student_id == Students.student_id)
            .filter(*preds) # same filters/search applied
            .order_by(Students.yrgrp, Students.forename)
            .all()
        )
        return render_template(
            'pages/display_ngrtb.html',
            segment='external data - NGRT (Form-B)',
            parent='extBTest',
            no_data=False,
            genders=ctx["dropdowns"]["genders"],
            yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"],
            speds=ctx["dropdowns"]["speds"],
            progress_categories=ctx["dropdowns"]["progress_categories"],
            **ctx["current"],
            students=ctx["rows"],
            # no_data=ctx["no_data"],
            filtered_is_empty=ctx["filtered_is_empty"],
            active_filters=ctx["active_filters"],
            combined_data=combined_data,
        )

@blueprint.route('/display_ngrtc', methods=['POST'])
def upload_ngrtc():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(request.url)
    
    if file and file.filename.endswith('.csv'):
        # Save the file temporarily
        filepath = os.path.join(CSV_UPLOAD, file.filename)
        file.save(filepath)
        
        # Read CSV and store in database
        df = pd.read_csv(filepath)
        
        for index, row in df.iterrows():
            # Insert data into table - students
            student_id=int(row['student_id'])

            # Handle students table
            student = Students.query.filter_by(student_id=student_id).first()
            if student:
                # Update existing student record
                student.forename = str(row['forename'])
                student.surname = str(row['surname'])
                student.gender = str(row['gender'])
                student.date_of_birth = str(row['date_of_birth'])
                student.yrgrp = str(row['yrgrp'])
                student.sped = str(row['sped'])
                student.nationality = str(row['nationality'])
                student.status = str(row['status'])
            else:
                # New student record
                student = Students(
                    student_id=student_id,
                    forename=str(row['forename']),
                    surname=str(row['surname']),
                    gender=str(row['gender']),
                    date_of_birth=str(row['date_of_birth']),
                    yrgrp=str(row['yrgrp']),
                    sped=str(row['sped']),
                    nationality=str(row['nationality']),
                    status=str(row['status'])
                )
                db.session.add(student)
            
            # Handle NGRTC table
            ngrtc = NGRTC.query.filter_by(student_id=student_id).first()
            if ngrtc:
                # Update existing NGRTC record
                ngrtc.ngrt_level = str(row['ngrt_level'])
                ngrtc.sas = int(row['sas'])
                ngrtc.stanine = int(row['stanine'])
                ngrtc.reading_age = str(row['reading_age'])
                ngrtc.prev_test_name = str(row['prev_test_name'])
                ngrtc.prev_sas = int(row['prev_sas'])
                ngrtc.prev_stanine = int(row['prev_stanine'])
                ngrtc.progress_category = str(row['progress_category'])
                ngrtc.reader_profile = str(row['reader_profile'])
                ngrtc.profile_desc = str(row['profile_desc'])
            else:
                # New NGRTC record
                ngrtc = NGRTC(
                    student_id=student_id,
                    ngrt_level=str(row['ngrt_level']),
                    sas=int(row['sas']),
                    stanine=int(row['stanine']),
                    reading_age=str(row['reading_age']),
                    prev_test_name=str(row['prev_test_name']),
                    prev_sas=int(row['prev_sas']),
                    prev_stanine=int(row['prev_stanine']),
                    progress_category=str(row['progress_category']),
                    reader_profile=str(row['reader_profile']),
                    profile_desc=str(row['profile_desc'])
                )
                db.session.add(ngrtc)
        
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Some records were skipped due to duplicates.", "warning")  # Duplicate message

        # Clean up temporary file
        os.remove(filepath)
        return redirect(url_for('home_blueprint.display_ngrtc'))
    
    return redirect(request.url)

# define a new route for templates/pages/display_ngrtc.html
@blueprint.route('/display_ngrtc', methods=['GET'])
def display_ngrtc():
    # student_data = Students.query.all()  # Fetch all entries from Students table  
    student_data = Students.query.order_by(Students.yrgrp, Students.forename).all()
    ngrtc_data = NGRTC.query.all()  # Fetch all entries from NGRTC table
    
    # Check if either table is empty
    ngrtc_empty = not ngrtc_data  # True if NGRTC is empty
    students_empty = not student_data  # True if Students is empty
    
    # modularized search filters for NGRT-C students view
    config = {
        "search": {
            "param": "q",
            "columns": [Students.forename, Students.surname, Students.student_id.cast(String)],
        },
        "filters": [
            {"param": "gender", "column": Students.gender},
            {"param": "yrgrp", "column": Students.yrgrp},
            {"param": "status", "column": Students.status},
            {"param": "sped", "custom_pred": lambda v: (Students.sped != "No") if v == "Any SEN Support" else (Students.sped == "No")},
            {"param": "progress_category", "column": NGRTC.progress_category},
        ],
        "order_by": [Students.yrgrp, Students.forename],
        "dropdowns": {
            "genders": lambda s: [g[0] for g in s.query(Students.gender).distinct().order_by(Students.gender)],
            "yrgrps":  lambda s: [y[0] for y in s.query(Students.yrgrp).distinct().order_by(Students.yrgrp)],
            "statuses":  lambda s: [t[0] for t in s.query(Students.status).distinct().order_by(Students.status)],
            "speds":  lambda s: ["Any SEN Support", "No SEN/SPED Support"],
            "progress_categories": lambda s: [p[0] for p in s.query(NGRTC.progress_category).distinct().order_by(NGRTC.progress_category)],
        },
        # labels for the filter chips
        "labels": {"q": "Search", "gender": "Gender", "yrgrp": "Year", "status": "Status", "sped": "SEN/SPED","progress_category": "Progress",},
    }

    # Build rows + chips + reusable predicates
    ctx = make_list_context(model=Students, db=db, config=config, endpoint="home_blueprint.display_ngrtc")

    # If both tables are empty
    if ngrtc_empty and students_empty:
        return render_template(
            'pages/display_ngrtc.html',
            segment='external data - NGRT (Form-C)', parent='extBTest',
            no_data=True, ngrtc_data=None, student_data=None,
            msg_ngrtc='No NGRT-C data available.',
            msg_students='No student data available.',
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"], yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"], speds=ctx["dropdowns"]["speds"],
            progress_categories=ctx["dropdowns"]["progress_categories"],
            **ctx["current"],
            filtered_is_empty=ctx["filtered_is_empty"], active_filters=ctx["active_filters"],
        )
    # If only NGRTC is empty
    elif ngrtc_empty:
        return render_template(
            'pages/display_ngrtc.html',
            segment='external data - NGRT (Form-C)', parent='extBTest',
            no_data=True, ngrtc_data=None,
            msg_ngrtc='No NGRT-C data available.',
            student_data=student_data,
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"], yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"], speds=ctx["dropdowns"]["speds"],
            progress_categories=ctx["dropdowns"]["progress_categories"],
            **ctx["current"],
            filtered_is_empty=ctx["filtered_is_empty"], active_filters=ctx["active_filters"],
        )
    # If only Students is empty
    elif students_empty:
        return render_template(
            'pages/display_ngrtc.html',
            segment='external data - NGRT (Form-C)', parent='extBTest',
            no_data=True, student_data=None,
            msg_students='No student data available.',
            ngrtc_data=ngrtc_data,
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"], yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"], speds=ctx["dropdowns"]["speds"],
            progress_categories=ctx["dropdowns"]["progress_categories"],
            **ctx["current"],
            filtered_is_empty=ctx["filtered_is_empty"], active_filters=ctx["active_filters"],
        )
    # If both tables have data
    else:
        preds = ctx["predicates"]
        combined_data = (
            db.session.query(Students, NGRTC)
            .join(Students, NGRTC.student_id == Students.student_id)
            .filter(*preds) # same filters/search applied
            .order_by(Students.yrgrp, Students.forename)
            .all()
        )
        return render_template(
            'pages/display_ngrtc.html',
            segment='external data - NGRT (Form-C)', parent='extBTest',
            no_data=False,
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"], yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"], speds=ctx["dropdowns"]["speds"],
            progress_categories=ctx["dropdowns"]["progress_categories"],
            **ctx["current"],
            filtered_is_empty=ctx["filtered_is_empty"], active_filters=ctx["active_filters"],
            combined_data=combined_data
        )


#***********************************
#*** Internal Assessment Routes ***#
#***********************************
@blueprint.route('/display_intlexam', methods=['POST'])
def upload_intlexam():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(request.url)
    
    if file and file.filename.endswith('.csv'):
        # Save the file temporarily
        filepath = os.path.join(CSV_UPLOAD, file.filename)
        file.save(filepath)
        
        # Read CSV and store in database
        df = pd.read_csv(filepath)
        
        for index, row in df.iterrows():
            # Insert data into table - students
            student_id=int(row['student_id'])

            # Handle students table
            student = Students.query.filter_by(student_id=student_id).first()
            if student:
                # Update existing student record
                student.forename = str(row['forename'])
                student.surname = str(row['surname'])
                student.gender = str(row['gender'])
                student.date_of_birth = str(row['date_of_birth'])
                student.yrgrp = str(row['yrgrp'])
                student.sped = str(row['sped'])
                student.nationality = str(row['nationality'])
                student.status = str(row['status'])
            else:
                # New student record
                student = Students(
                    student_id=student_id,
                    forename=str(row['forename']),
                    surname=str(row['surname']),
                    gender=str(row['gender']),
                    date_of_birth=str(row['date_of_birth']),
                    yrgrp=str(row['yrgrp']),
                    sped=str(row['sped']),
                    nationality=str(row['nationality']),
                    status=str(row['status'])
                )
                db.session.add(student)

            # Handle internal_exam table
            internalexam = InternalExam.query.filter_by(student_id=student_id).first()
            if internalexam:
                # Update existing Internal Exam records
                internalexam.eng_prevPct = int(row['eng_prevPct'])
                internalexam.eng_prevGr = str(row['eng_prevGr'])
                internalexam.eng_currPct = int(row['eng_currPct'])
                internalexam.eng_currGr = str(row['eng_currGr'])
                internalexam.eng_progcat = str(row['eng_progcat'])
                internalexam.maths_prevPct = int(row['maths_prevPct'])
                internalexam.maths_prevGr = str(row['maths_prevGr'])
                internalexam.maths_currPct = int(row['maths_currPct'])
                internalexam.maths_currGr = str(row['maths_currGr'])
                internalexam.maths_progcat = str(row['maths_progcat'])
                internalexam.sci_prevPct = int(row['sci_prevPct'])
                internalexam.sci_prevGr = str(row['sci_prevGr'])
                internalexam.sci_currPct = int(row['sci_currPct'])
                internalexam.sci_currGr = str(row['sci_currGr'])
                internalexam.sci_progcat = str(row['sci_progcat'])
            else:
                # New Internal Exam records
                internalexam = InternalExam(
                    student_id=student_id,
                    eng_prevPct = int(row['eng_prevPct']),
                    eng_prevGr = str(row['eng_prevGr']),
                    eng_currPct = int(row['eng_currPct']),
                    eng_currGr = str(row['eng_currGr']),
                    eng_progcat = str(row['eng_progcat']),
                    maths_prevPct = int(row['maths_prevPct']),
                    maths_prevGr = str(row['maths_prevGr']),
                    maths_currPct = int(row['maths_currPct']),
                    maths_currGr = str(row['maths_currGr']),
                    maths_progcat = str(row['maths_progcat']),
                    sci_prevPct = int(row['sci_prevPct']),
                    sci_prevGr = str(row['sci_prevGr']),
                    sci_currPct = int(row['sci_currPct']),
                    sci_currGr = str(row['sci_currGr']),
                    sci_progcat = str(row['sci_progcat'])
                )
                db.session.add(internalexam)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Some records were skipped due to duplicates.", "warning")  # Duplicate message

        # Clean up temporary file
        os.remove(filepath)
        return redirect(url_for('home_blueprint.display_intlexam'))
    
    return redirect(request.url)

# define a new route for templates/pages/intlexam.html
@blueprint.route('/display_intlexam', methods=['GET'])
def display_intlexam():
    # Fetch all entries from Students table  
    student_data = Students.query.order_by(Students.yrgrp, Students.forename).all()
    intlexam_data = InternalExam.query.all()  # Fetch all entries from internal_exam table
    
    # Check if either table is empty
    intlexam_empty = not intlexam_data  # True if internalexam is empty
    students_empty = not student_data  # True if Students is empty
    
    # modularized search filters for internal exam students view
    config = {
        "search": {
            "param": "q",
            "columns": [Students.forename, Students.surname, Students.student_id.cast(String)],
        },
        "filters": [
            {"param": "gender", "column": Students.gender},
            {"param": "yrgrp", "column": Students.yrgrp},
            {"param": "status", "column": Students.status},
            {"param": "sped", "custom_pred": lambda v: (Students.sped != "No") if v == "Any SEN Support" else (Students.sped == "No")},
        ],
        "order_by": [Students.yrgrp, Students.forename],
        "dropdowns": {
            "genders": lambda s: [g[0] for g in s.query(Students.gender).distinct().order_by(Students.gender)],
            "yrgrps":  lambda s: [y[0] for y in s.query(Students.yrgrp).distinct().order_by(Students.yrgrp)],
            "statuses":  lambda s: [t[0] for t in s.query(Students.status).distinct().order_by(Students.status)],
            "speds":  lambda s: ["Any SEN Support", "No SEN/SPED Support"],
        },
        # labels for the filter chips
        "labels": {"q": "Search", "gender": "Gender", "yrgrp": "Year", "status": "Status", "sped": "SEN/SPED"},
    }

    # Build rows + chips + reusable predicates
    ctx = make_list_context(model=Students, db=db, config=config, endpoint="home_blueprint.display_intlexam")

    # If both tables are empty
    if intlexam_empty and students_empty:
        return render_template(
            'pages/intlexam.html',
            segment='internal assessment (final term)',
            parent='intAssmnt',
            no_data=True, intlexam_data=None, student_data=None,
            msg_intlexam='No Internal Exam data available.',
            msg_students='No student data available.',
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"], yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"], speds=ctx["dropdowns"]["speds"],
            **ctx["current"],
            filtered_is_empty=ctx["filtered_is_empty"], active_filters=ctx["active_filters"],
        )
    # If only internalexam is empty
    elif intlexam_empty:
        return render_template(
            'pages/intlexam.html',
            segment='internal assessment (final term)',
            parent='intAssmnt',
            no_data=True, intlexam_data=None,
            student_data=student_data,
            msg_intlexam='No Internal Exam data available.',
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"], yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"], speds=ctx["dropdowns"]["speds"],
            **ctx["current"],
            filtered_is_empty=ctx["filtered_is_empty"], active_filters=ctx["active_filters"],
        )
    # If only Students is empty
    elif students_empty:
        return render_template(
            'pages/intlexam.html',
            segment='internal assessment (final term)',
            parent='intAssmnt',
            no_data=True, student_data=None,
            intlexam_data=intlexam_data,
            msg_students='No student data available.',
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"], yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"], speds=ctx["dropdowns"]["speds"],
            **ctx["current"],
            filtered_is_empty=ctx["filtered_is_empty"], active_filters=ctx["active_filters"],
        )
    # If both tables have data
    else:
        preds = ctx["predicates"]
        combined_data = (
            db.session.query(Students, InternalExam)
            .join(Students, InternalExam.student_id == Students.student_id)
            .filter(*preds) # same filters/search applied
            .order_by(Students.yrgrp, Students.forename)
            .all()
        )
        return render_template(
            'pages/intlexam.html',
            segment='internal assessment (final term)',
            parent='intAssmnt',
            no_data=False,
            students=ctx["rows"],
            genders=ctx["dropdowns"]["genders"], yrgrps=ctx["dropdowns"]["yrgrps"],
            statuses=ctx["dropdowns"]["statuses"], speds=ctx["dropdowns"]["speds"],
            **ctx["current"],
            filtered_is_empty=ctx["filtered_is_empty"], active_filters=ctx["active_filters"],
            combined_data=combined_data,
        )


#**********************************
#*** Student Management Routes ***#
#**********************************
@blueprint.route("/student_management", methods=["GET"])
def student_management():
    # Fetch all entries from Students table
    student_data = Students.query.order_by(Students.yrgrp, Students.forename).all()

    students_empty = not student_data  # database has no students at all

    # modularized search filters for students table
    config = {
        "search": {
            "param": "q",
            "columns": [Students.forename, Students.surname, Students.student_id.cast(String)],
        },
        "filters": [
            {"param": "gender", "column": Students.gender},
            {"param": "yrgrp", "column": Students.yrgrp},
            {"param": "status", "column": Students.status},
            {"param": "sped", "custom_pred": lambda v: (Students.sped != "No") if v == "Any SEN Support" else (Students.sped == "No")},
        ],
        "order_by": [Students.yrgrp, Students.forename],
        "dropdowns": {
            "genders": lambda s: [g[0] for g in s.query(Students.gender).distinct().order_by(Students.gender)],
            "yrgrps":  lambda s: [y[0] for y in s.query(Students.yrgrp).distinct().order_by(Students.yrgrp)],
            "statuses":  lambda s: [t[0] for t in s.query(Students.status).distinct().order_by(Students.status)],
            "speds":  lambda s: ["Any SEN Support", "No SEN/SPED Support"],
        },
        # labels for the filter chips
        "labels": {"q": "Search", "gender": "Gender", "yrgrp": "Year", "status": "Status", "sped": "SEN/SPED",},
    }

    # Build rows + chips + reusable predicates
    ctx = make_list_context(model=Students, db=db, config=config, endpoint="home_blueprint.student_management")

    preds = ctx["predicates"]
    combined_data = (
        db.session.query(Students)
        .filter(*preds) # same filters/search applied
        .order_by(Students.yrgrp, Students.forename)
        .all()
    )

    return render_template(
        "pages/students-all.html",
        segment="student management",
        parent="studentMgt",
        no_data=students_empty,
        # dropdown data
        students=ctx["rows"],
        genders=ctx["dropdowns"]["genders"], yrgrps=ctx["dropdowns"]["yrgrps"],
        statuses=ctx["dropdowns"]["statuses"], speds=ctx["dropdowns"]["speds"],
        **ctx["current"],
        filtered_is_empty=ctx["filtered_is_empty"], active_filters=ctx["active_filters"],
        combined_data=combined_data,
    )

#*******************************
#*** User Management Routes ***#
#*******************************
# Grant admin rights route for users
@blueprint.route('/make_admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def make_admin(user_id):
    user = Users.query.get_or_404(user_id)
    user.is_admin = True
    db.session.commit()
    flash(f'User {user.username} is granted admin rights.', 'success')
    return redirect(url_for('home_blueprint.allusers'))

# Remove admin rights route for users
@blueprint.route('/remove_admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def remove_admin(user_id):
    user = Users.query.get_or_404(user_id)

    # Prevent removing the last admin
    admin_count = Users.query.filter_by(is_admin=True).count()
    if admin_count <= 1 and user.is_admin:
        flash('Sorry, last admin account cannot be removed.', 'error')
    else:
        if user.id == current_user.id:
            flash('Sorry, cannot revoke admin rights for own account while logged in.', 'error')
        else:
            user.is_admin = False
            db.session.commit()
            flash(f'Admin rights removed from {user.username}.', 'success')
    return redirect(url_for('home_blueprint.allusers'))


# Delete User Route for Admins
@blueprint.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = Users.query.get_or_404(user_id)
    
    # Don't allow deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account while logged in.', 'error')
        return redirect(url_for('home_blueprint.allusers'))
    
    # Don't allow deleting the last admin
    if user.is_admin:
        admin_count = Users.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            flash('Cannot delete the last admin account.', 'error')
            return redirect(url_for('home_blueprint.allusers'))
    
    # Store username before deletion for the flash message
    deleted_user = user.username
    
    # Delete the user
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {deleted_user} has been deleted successfully.', 'success')
    messages = get_flashed_messages()
    print(messages)  # Check if messages exist in the backend
    return redirect(url_for('home_blueprint.allusers'))


# Helper - Extract current page name from request
@blueprint.app_template_filter('replace_value')
def replace_value(value, args):
  return value.replace(args, " ").title()

def get_segment(request):
    try:
        segment = request.path.split('/')[-1]
        if segment == '':
            segment = 'index'
        return segment
    except:
        return None

#*******************************************************
#*** Performance Analytics Routes - Cohort Insights ***#
#*******************************************************
@blueprint.route("/analytics", methods=["GET"])
def analytics_internal():
    # Year groups from Students (since InternalExam doesn’t store yrgrp)
    year_groups = [yg for (yg,) in db.session.query(Students.yrgrp) # selects distinct year groups from Students
                   .filter(Students.yrgrp.isnot(None)) # does not include Null values
                   .distinct() # only distinct values
                   .order_by(Students.yrgrp).all()] # order by year group ascending and fetch all rows
    
    # count students per year group (excluding NULLs), ordered ascending
    rc_yrgrp = (
        db.session.query(Students.yrgrp, func.count(Students.id))
        .filter(Students.yrgrp.isnot(None))
        .group_by(Students.yrgrp)
        .order_by(Students.yrgrp)
        .all()
    )

    # if you want a dict {yrgrp: count}
    counts_by_yrgrp = dict(rc_yrgrp)
    
    #* KPIs: Y2 Cohort, Average Attainment for E/M/S
    # Total count of InternalExam intakes
    count_intake = db.session.query(InternalExam).count()

    # Render Cohort averages of current year for English, Maths, Science (chart 1)
    curr_avg_eng = round(db.session.query(func.avg(InternalExam.eng_currPct)).scalar() or 0, 1) # round to ensure it doesn’t return None
    curr_avg_maths = round(db.session.query(func.avg(InternalExam.maths_currPct)).scalar() or 0, 1) # round to ensure it doesn’t return None
    curr_avg_sci = round(db.session.query(func.avg(InternalExam.sci_currPct)).scalar() or 0, 1) # round to ensure it doesn’t return None

    # averages for English, Maths, Science but for previous-year results
    prev_avg_eng = round(db.session.query(func.avg(InternalExam.eng_prevPct)).scalar() or 0, 1)
    prev_avg_maths = round(db.session.query(func.avg(InternalExam.maths_prevPct)).scalar() or 0, 1)
    prev_avg_sci = round(db.session.query(func.avg(InternalExam.sci_prevPct)).scalar() or 0, 1)
    
    # Round for display, but keep as float and 1 decimal place for English, Maths, Science
    data = {
        "eng_prev": round(float(prev_avg_eng), 1), 
        "maths_prev": round(float(prev_avg_maths), 1),
        "sci_prev": round(float(prev_avg_sci), 1),
        "eng_curr": round(float(curr_avg_eng), 1),
        "maths_curr": round(float(curr_avg_maths), 1),
        "sci_curr": round(float(curr_avg_sci), 1),
    }

    #*** Cohort ATTAINMENT Chart
    # ≥60 for at/above curr std and ≥ 70 for above curr std
    def ge60_ge70_for(col): 
        # count non-null values in this column + how many meet each cut
        n, ge60, ge70 = db.session.query(
            func.count(col),  # counts non-null values only
            func.sum(case((col >= 60, 1), else_=0)), # counts how many are >= 60
            func.sum(case((col >= 70, 1), else_=0)) # counts how many are >= 70
        ).one()

        n = int(n or 0) # ensure n is int and not None
        ge60 = int(ge60 or 0) # ensure ge60 is int and not None
        ge70 = int(ge70 or 0) # ensure ge70 is int and not None
        pct60 = round((ge60 / n * 100.0), 1) if n else 0.0 # avoid division by zero; percentage for 60+
        pct70 = round((ge70 / n * 100.0), 1) if n else 0.0 # avoid division by zero; percentage for 70+
        # return pct60, pct70
        return n, ge60, ge70, pct60, pct70

    eng_n, eng60, eng70, eng_pct60, eng_pct70 = ge60_ge70_for(InternalExam.eng_currPct) # compute English for current-year 60/70+
    math_n, math60, math70, math_pct60, math_pct70 = ge60_ge70_for(InternalExam.maths_currPct) # compute Maths for current-year 60/70+
    sci_n, sci60, sci70, sci_pct60, sci_pct70 = ge60_ge70_for(InternalExam.sci_currPct) # compute Science for current-year 60/70+

    # table rows for attainment table
    attainment_table = [
        {
            "subject": "English",
            "n": eng_n,
            "ge60_count": eng60, "ge60_pct": eng_pct60,
            "ge70_count": eng70, "ge70_pct": eng_pct70,
        },
        {
            "subject": "Maths",
            "n": math_n,
            "ge60_count": math60, "ge60_pct": math_pct60,
            "ge70_count": math70, "ge70_pct": math_pct70,
        },
        {
            "subject": "Science",
            "n": sci_n,
            "ge60_count": sci60, "ge60_pct": sci_pct60,
            "ge70_count": sci70, "ge70_pct": sci_pct70,
        },
    ]

     # payload for the thresholds chart (60+ and 70+) - cohort attainment
    threshold_data = [
        {"subject": "English", "ge60_count": eng60, "ge70_count": eng70, "ge60": eng_pct60, "ge70": eng_pct70}, # 60+ and 70+ for English
        {"subject": "Maths", "ge60_count": math60, "ge70_count": math70, "ge60": math_pct60, "ge70": math_pct70}, # 60+ and 70+ for Maths
        {"subject": "Science", "ge60_count": sci60, "ge70_count": sci70, "ge60": sci_pct60,  "ge70": sci_pct70}, # 60+ and 70+ for Science
    ]

    #*** Cohort PROGRESS Chart
    # For each subject, compute:
    # - %('expected') + %('above expected')
    # - %('above expected')
    def simple_progress(col):
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
        p_sum        = round(p_expected + p_above, 1)  # Expected + Above Expected
        p_above_only = p_above # Above Expected only (explicit name)

        return total, cnt_exp_above, cnt_above_only, p_sum, p_above_only

    # Compute per subject
    eng_total, cnt_eng_exp_above, cnt_eng_above_only, eng_sum, eng_above_only = simple_progress(InternalExam.eng_progcat)
    maths_total, cnt_maths_exp_above, cnt_maths_above_only, maths_sum, maths_above_only = simple_progress(InternalExam.maths_progcat)
    sci_total, cnt_sci_exp_above, cnt_sci_above_only, sci_sum, sci_above_only = simple_progress(InternalExam.sci_progcat)

    # Payload for the simple progress chart
    progress_simple_data = [
        {"subject": "English", "n": eng_total, "count_exp_above": cnt_eng_exp_above, "count_above_only": cnt_eng_above_only, "sum_expected_above": eng_sum,   "above_only": eng_above_only},
        {"subject": "Maths", "n": maths_total, "count_exp_above": cnt_maths_exp_above, "count_above_only": cnt_maths_above_only, "sum_expected_above": maths_sum, "above_only": maths_above_only},
        {"subject": "Science", "n": sci_total, "count_exp_above": cnt_sci_exp_above, "count_above_only": cnt_sci_above_only, "sum_expected_above": sci_sum,   "above_only": sci_above_only},
    ]

    #*** Student ATTAINMENT Chart: Gender-specific 
    def _pct(n, d):
        return round((n / d) * 100.0, 1) if d else 0.0
    
    # Normalise gender to lowercase for M/Male or F/Female
    male_pred = or_(
        func.lower(func.trim(Students.gender)) == "m",
        func.lower(func.trim(Students.gender)) == "male",
    )
    female_pred = or_(
        func.lower(func.trim(Students.gender)) == "f",
        func.lower(func.trim(Students.gender)) == "female",
    )

    def _gender_threshold_for(col, threshold, gender_pred):
        """
        % of distinct students of a given gender with non-null 'col'
        who are >= threshold for that subject.
        """
        # denominator: distinct students of gender with a non-null current mark for this subject
        denom = db.session.query(
            func.count(func.distinct(InternalExam.student_id))
        ).join(Students, InternalExam.student_id == Students.student_id)\
        .filter(gender_pred, col.isnot(None)).scalar() or 0

        # numerator: distinct students of gender with mark >= threshold
        numer = db.session.query(
            func.count(func.distinct(case((col >= threshold, InternalExam.student_id))))
        ).join(Students, InternalExam.student_id == Students.student_id)\
        .filter(gender_pred).scalar() or 0

        return int(numer), _pct(int(numer), int(denom)), int(denom)

    def _build_gender_payload(threshold):
        """[{subject, male_n, male_pct, male_total, female_n, female_pct, female_total}]"""
        m_n, m_p, m_t = _gender_threshold_for(InternalExam.eng_currPct,   threshold, male_pred)
        f_n, f_p, f_t = _gender_threshold_for(InternalExam.eng_currPct,   threshold, female_pred)
        eng_row = {"subject":"English","male_n":m_n,"male_pct":m_p,"male_total": m_t,"female_n":f_n,"female_pct":f_p,"female_total": f_t}

        m_n, m_p, m_t = _gender_threshold_for(InternalExam.maths_currPct, threshold, male_pred)
        f_n, f_p, f_t = _gender_threshold_for(InternalExam.maths_currPct, threshold, female_pred)
        maths_row = {"subject":"Maths","male_n":m_n,"male_pct":m_p,"male_total": m_t,"female_n":f_n,"female_pct":f_p,"female_total": f_t}

        m_n, m_p, m_t = _gender_threshold_for(InternalExam.sci_currPct,   threshold, male_pred)
        f_n, f_p, f_t = _gender_threshold_for(InternalExam.sci_currPct,   threshold, female_pred)
        sci_row = {"subject":"Science","male_n":m_n,"male_pct":m_p,"male_total": m_t,"female_n":f_n,"female_pct":f_p,"female_total": f_t}

        return [eng_row, maths_row, sci_row]
    
    gender_ge60_data = _build_gender_payload(60)
    gender_ge70_data = _build_gender_payload(70)

    #*** Student PROGRESS Chart: Gender-specific
    def _gender_progress_for(prog_col, gender_pred):
        """
        Returns two percentages for a subject's progress column for a given gender:
        - p_sum:   % Expected OR Above Expected
        - p_above: % Above Expected only
        Denominator = distinct students of that gender with a NON-NULL value in this prog_col.
        """
        norm = func.lower(func.trim(prog_col))

        # Denominator: distinct students of that gender with a recorded progress value
        denom = db.session.query(
            func.count(func.distinct(InternalExam.student_id))
        ).join(Students, InternalExam.student_id == Students.student_id)\
        .filter(gender_pred, prog_col.isnot(None)).scalar() or 0

        # Numerators (distinct students per category)
        exp_cnt = db.session.query(
            func.count(func.distinct(case((norm == "expected", InternalExam.student_id))))
        ).join(Students, InternalExam.student_id == Students.student_id)\
        .filter(gender_pred).scalar() or 0

        above_cnt = db.session.query(
            func.count(func.distinct(case((norm == "above expected", InternalExam.student_id))))
        ).join(Students, InternalExam.student_id == Students.student_id)\
        .filter(gender_pred).scalar() or 0

        p_expected = _pct(int(exp_cnt), int(denom))
        p_above    = _pct(int(above_cnt), int(denom))
        p_sum      = round(p_expected + p_above, 2)

        # count of expected + above
        c_sum = int(exp_cnt + above_cnt)
        c_above = int(above_cnt)

        # return int(numer), _pct(int(numer), int(denom)), int(denom)
        # return p_sum, p_above
        return c_sum, p_sum, c_above, p_above, int(denom)

    def _build_gender_progress_payload():
        """
        Returns two lists (for two charts):
        - sum_data   : [{subject, male, female}] using Expected OR Above Expected
        - above_data : [{subject, male, female}] using Above Expected only
        """
        # English
        mc_sum_e, m_sum_e, mc_abv_e, m_abv_e, m_total_e = _gender_progress_for(InternalExam.eng_progcat,   male_pred)
        fc_sum_e, f_sum_e, fc_abv_e, f_abv_e, f_total_e = _gender_progress_for(InternalExam.eng_progcat,   female_pred)
        # Maths
        mc_sum_m, m_sum_m, mc_abv_m, m_abv_m, m_total_m = _gender_progress_for(InternalExam.maths_progcat, male_pred)
        fc_sum_m, f_sum_m, fc_abv_m, f_abv_m, f_total_m = _gender_progress_for(InternalExam.maths_progcat, female_pred)
        # Science
        mc_sum_s, m_sum_s, mc_abv_s, m_abv_s, m_total_s = _gender_progress_for(InternalExam.sci_progcat,   male_pred)
        fc_sum_s, f_sum_s, fc_abv_s, f_abv_s, f_total_s = _gender_progress_for(InternalExam.sci_progcat,   female_pred)

        sum_data = [
            {"subject": "English", "male_n": mc_sum_e, "male_pct": m_sum_e, "male_total": m_total_e, "female_n": fc_sum_e, "female_pct": f_sum_e, "female_total": f_total_e},
            {"subject": "Maths", "male_n": mc_sum_m, "male_pct": m_sum_m, "male_total": m_total_m, "female_n": fc_sum_m, "female_pct": f_sum_m, "female_total": f_total_m},
            {"subject": "Science", "male_n": mc_sum_s, "male_pct": m_sum_s, "male_total": m_total_s, "female_n": fc_sum_s, "female_pct": f_sum_s, "female_total": f_total_s},
        ]
        above_data = [
            {"subject": "English", "male_n": mc_abv_e, "male_pct": m_abv_e, "male_total": m_total_e, "female_n": fc_abv_e, "female_pct": f_abv_e, "female_total": f_total_e},
            {"subject": "Maths", "male_n": mc_abv_m, "male_pct": m_abv_m, "male_total": m_total_e, "female_n": fc_abv_m, "female_pct": f_abv_m, "female_total": f_total_e},
            {"subject": "Science", "male_n": mc_abv_s, "male_pct": m_abv_s, "male_total": m_total_e, "female_n": fc_abv_s, "female_pct": f_abv_s, "female_total": f_total_e},
        ]
        
        return sum_data, above_data
    
    gender_prog_exp_above, gender_prog_above_data = _build_gender_progress_payload()

    # Year Group Analytics payload from API endpoint - /api/yrgrp_analytics
    resp = requests.get(request.url_root.rstrip("/") + "/api/yrgrp_analytics")
    yrgrp_payload = resp.json()

    return render_template(
        "pages/analytics_internal.html",
        segment="analytics",
        parent="analytics",
        year_groups=year_groups, count_intake=count_intake,
        avg_eng=curr_avg_eng, avg_maths=curr_avg_maths, avg_sci=curr_avg_sci,
        data=data, threshold_data=threshold_data,
        progress_simple_data=progress_simple_data,
        gender_ge60_data=gender_ge60_data,
        gender_ge70_data=gender_ge70_data,
        gender_prog_exp_above=gender_prog_exp_above,
        gender_prog_above_data=gender_prog_above_data,
        attainment_table=attainment_table,
        counts_by_yrgrp=counts_by_yrgrp,
        yrgrp_payload=yrgrp_payload,
    )

#*********************************************************************
#*** Performance Analytics Routes - Student & Year Group Insights ***#
#*********************************************************************
# --- Student dropdown for analytics page :: Student Insights page ---
@blueprint.route("/api/students_by_year", methods=["GET"])
def api_students_by_year():
    yrgrp = request.args.get("yrgrp", "").strip()
    if not yrgrp:
        return jsonify({"students": []})

    # Only students who have InternalExam rows (so analytics won’t be empty)
    q = (
        db.session.query(Students.student_id, Students.forename, Students.surname)
        .join(InternalExam, InternalExam.student_id == Students.student_id)
        .filter(Students.yrgrp == yrgrp)
        .distinct()
        .order_by(Students.forename, Students.surname)
    )
    data = [{"id": sid, "name": f"{fn} {sn}"} for (sid, fn, sn) in q.all()]
    return jsonify({"students": data})
    
# --- Main analytics payload (cards + charts + tables) :: Year Group & Student Insights (Internal Assessment Analytics) ---
@blueprint.route("/api/analytics", methods=["GET"])
def api_analytics():
    # Get 'yrgrp' and 'student_id' from the request's query parameters
    # (default to empty string) and remove extra spaces
    yrgrp = request.args.get("yrgrp", "").strip()
    sid   = request.args.get("student_id", "").strip()

    # Filter InternalExam via Students for yrgrp when provided
    base_q = db.session.query(InternalExam).join(Students, Students.student_id == InternalExam.student_id)
    if yrgrp:
        base_q = base_q.filter(Students.yrgrp == yrgrp)
    if sid:
        base_q = base_q.filter(InternalExam.student_id == int(sid))

    rows = base_q.all()

    # ---- If no data, return empty but valid payload ----
    if not rows:
        prog_order = ["Below Expected", "Expected", "Above Expected"]
        empty = {
            "line": {  # prev vs current by subject with line chart
                "labels": ["Previous", "Current"],
                "english": [0, 0],
                "maths": [0, 0],
                "science": [0, 0],
            },
            "bands": {
                "labels": [
                    "E/D",  # <60
                    "C",    # 60-69
                    "B",    # 70-79
                    "A",    # 80-89
                    "A*"    # ≥90
                ],
                "counts": [0, 0, 0, 0, 0]
            }, 
            "progcats": {
                "labels": prog_order,
                "counts": [0, 0, 0],
                "english": [0, 0, 0],
                "maths":   [0, 0, 0],
                "science": [0, 0, 0],
            },
            "kpi_total": {
                "title": "All Year Groups (Total Cohort)",
                "count": 0
            }
        }
        return jsonify(empty)

    # aggregate current % across 3 subjects (skip Nones)
    curr_values, prev_values = [], []

    # ---------- progress categories per subject ----------
    # Normalize to 3 buckets and keep a locked order for the x-axis
    prog_order = ["Below Expected", "Expected", "Above Expected"]

    def norm_progcat(s: str) -> str:
        """Map any spelling to one of the 3 buckets."""
        if not s:
            return ""
        t = s.strip().lower()
        # common variants
        if t.startswith("below"):
            return "Below Expected"
        if t.startswith("expected") or t == "at expected":
            return "Expected"
        if t.startswith("above") or "better" in t:
            return "Above Expected"
        # fallback: title-case, but only keep if in our order
        u = s.strip().title()
        return u if u in prog_order else ""

    # Totals (all subjects pooled) and per-subject dicts
    prog_counts_total = {k: 0 for k in prog_order}
    prog_counts_by_subj = {
        "english": {k: 0 for k in prog_order},
        "maths":   {k: 0 for k in prog_order},
        "science": {k: 0 for k in prog_order},
    }

    # Attainment Bands:
    # distribution bands use current % from all subjects
    #* Boundary Behaviour for Distribution Bands:
    #* <60 Beginning/Developing
    #* 60-69 Secure
    #* 70-79 Secure+
    #* 80-89 Exceeding
    #* ≥90 Advanced

    # --- Distribution Bands ---
    def band_of(p):
        if p is None: return None
        if p < 60:   return "E/D"
        if p <= 69:  return "C"
        if p <= 79:  return "B"
        if p <= 89:  return "A"
        return "A*" # ≥90

    # band_order = ["<60", "60-69", "70-79", "80-89", "≥90"]
    band_order = ["E/D", "C", "B", "A", "A*"]
    band_counts = {b: 0 for b in band_order}
    band_counts_by_subj = {
        "eng": {b: 0 for b in band_order},
        "maths": {b: 0 for b in band_order},
        "sci": {b: 0 for b in band_order},
    }

    # For the line chart: average per subject (prev/curr)
    eng_prev, eng_curr, n_eng = 0.0, 0.0, 0
    m_prev, m_curr, n_m = 0.0, 0.0, 0
    s_prev, s_curr, n_s = 0.0, 0.0, 0

    for r in rows:
        # Collect per subject safely (might be None)
         for prev, curr, progcat, subj_key, subj_out in [
            (r.eng_prevPct,   r.eng_currPct,   r.eng_progcat,   "eng",   "english"),
            (r.maths_prevPct, r.maths_currPct, r.maths_progcat, "maths", "maths"),
            (r.sci_prevPct,   r.sci_currPct,   r.sci_progcat,   "sci",   "science"),
        ]:
            # KPIs: curr/prev values
            if curr is not None:
                curr_values.append(curr)
                b = band_of(curr)
                if b: 
                    band_counts[b] += 1
                    band_counts_by_subj[subj_key][b] += 1
            if prev is not None:
                prev_values.append(prev)

            # ---------- Progress category tally ----------
            bucket = norm_progcat(progcat)
            if bucket:
                prog_counts_total[bucket] += 1
                prog_counts_by_subj[subj_out][bucket] += 1

            # Line chart subject averages
            if subj_key == "eng":
                if prev is not None: eng_prev += prev; n_eng += 1
                if curr is not None: eng_curr += curr
            # elif subj == "maths":
            elif subj_key == "maths":
                if prev is not None: m_prev += prev; n_m += 1
                if curr is not None: m_curr += curr
            else:
                if prev is not None: s_prev += prev; n_s += 1
                if curr is not None: s_curr += curr

    # Subject means for line chart (based on counts where prev existed)
    eng_prev_mean = round(eng_prev / n_eng, 1) if n_eng else 0.0
    eng_curr_mean = round(eng_curr / n_eng, 1) if n_eng else 0.0
    m_prev_mean   = round(m_prev / n_m, 1)     if n_m   else 0.0
    m_curr_mean   = round(m_curr / n_m, 1)     if n_m   else 0.0
    s_prev_mean   = round(s_prev / n_s, 1)     if n_s   else 0.0
    s_curr_mean   = round(s_curr / n_s, 1)     if n_s   else 0.0

    # --- Per-subject CURRENT% lists for KPIs (ignore None) ---
    eng_curr_list = [r.eng_currPct for r in rows if r.eng_currPct is not None]
    m_curr_list   = [r.maths_currPct for r in rows if r.maths_currPct is not None]
    s_curr_list   = [r.sci_currPct for r in rows if r.sci_currPct is not None]

    def avg_num(lst):
        return round(sum(lst) / len(lst), 1) if lst else 0.0

    eng_avg = round(avg_num(eng_curr_list), 1)
    m_avg   = round(avg_num(m_curr_list), 1)
    s_avg   = round(avg_num(s_curr_list), 1)

    # --- Adaptive total-students KPI ---
    if sid:
        student = db.session.query(Students.forename, Students.surname).filter(Students.student_id == sid).first()
        if student:
            full_name = f"{student.forename} {student.surname}"
            full_name = (full_name[:20] + "…") if len(full_name) > 20 else full_name
        else:
            full_name = "Unknown Student"

        total_label = full_name
        total_value = 1
    elif yrgrp:
        total_label = f"Year {yrgrp}"
        total_value = len({r.student_id for r in rows})
    else:
        total_label = "Year 2 Cohort"
        total_value = len({r.student_id for r in rows})

    payload = {
        "line": {
            "labels": ["Previous", "Current"],
            "english": [eng_prev_mean, eng_curr_mean],
            "maths":   [m_prev_mean,  m_curr_mean],
            "science": [s_prev_mean,  s_curr_mean],
        },
        "bands": {
            "labels": band_order,
            "counts": [band_counts[b] for b in band_order],
            "english": [band_counts_by_subj["eng"][b] for b in band_order],
            "maths":   [band_counts_by_subj["maths"][b]   for b in band_order],
            "science": [band_counts_by_subj["sci"][b] for b in band_order],
        },
        # ---------- subject arrays for progress categories ----------
        "progcats": {
            "labels":  prog_order,
            "counts":  [prog_counts_total[k] for k in prog_order],  # pooled
            "english": [prog_counts_by_subj["english"][k] for k in prog_order],
            "maths":   [prog_counts_by_subj["maths"][k] for k in prog_order],
            "science": [prog_counts_by_subj["science"][k] for k in prog_order],
        },
        "kpi_subjects": {
            "english": eng_avg,
            "maths":   m_avg,
            "science": s_avg,
        },
        "kpi_total": {
            "title": total_label,
            "count": int(total_value),
        },     
    }

    return jsonify(payload)


@blueprint.route("/api/yrgrp_analytics", methods=["GET"])
def api_yeargroup_attainment_by_class():
    # --- Year Group Attainment by Class :: Year Group Insights page ---
    target_year = 2
    class_labels = sorted([c[0] for c in db.session.query(Students.yrgrp).distinct().filter(Students.yrgrp.ilike(f"{target_year}-%")).all()])

    CLASS_COL = Students.yrgrp

    def _r(v, dp=1):  # safe round
        try:
            return round(float(v), dp)
        except (TypeError, ValueError):
            return 0.0

    # Per-class or year group average attainment for English, Maths, Science
    rows = (
        db.session.query(
            CLASS_COL.label("class"),
            func.avg(InternalExam.eng_currPct).label("eng"),
            func.avg(InternalExam.maths_currPct).label("maths"),
            func.avg(InternalExam.sci_currPct).label("sci"),
        )
        .join(InternalExam, InternalExam.student_id == Students.student_id)
        .filter(func.lower(func.trim(CLASS_COL)).in_([c.lower() for c in class_labels]))
        .filter(func.trim(CLASS_COL).in_(class_labels))
        .group_by(CLASS_COL)
        .all()
    )

    # put into dict keyed by class for easy lookup
    by_class = {c: {"eng": 0.0, "maths": 0.0, "sci": 0.0} for c in class_labels}

    for r in rows:
        cls = r._mapping["class"]
        if cls in by_class:
            by_class[cls] = {
                "eng":   _r(r._mapping["eng"]),
                "maths": _r(r._mapping["maths"]),
                "sci":   _r(r._mapping["sci"]),
            }

    # Cohort averages of current year for English, Maths, Science
    c_eng = round(db.session.query(func.avg(InternalExam.eng_currPct)).scalar() or 0, 1) # round to ensure it doesn’t return None
    c_maths = round(db.session.query(func.avg(InternalExam.maths_currPct)).scalar() or 0, 1) # round to ensure it doesn’t return None
    c_sci = round(db.session.query(func.avg(InternalExam.sci_currPct)).scalar() or 0, 1) # round to ensure it doesn’t return None

    cohort = {"eng": _r(c_eng), "maths": _r(c_maths), "sci": _r(c_sci)}

    #**********************************************
    #* Year Group vs. Cohort | Attainment ≥60 & ≥70
    #**********************************************
    # # Per-class or year group average attainment (E/M/S) ≥60
    thr60, thr70 = 60, 70
    classes = class_labels  # use all classes found for target year group
    yrgrp_norm = func.lower(func.trim(Students.yrgrp))

    per_class = (
        db.session.query(
            Students.yrgrp.label("class"),
            *per_class_metrics(thr60, thr70)
        )
        .join(Students, Students.student_id == InternalExam.student_id)
        .filter(func.lower(func.trim(Students.yrgrp)).in_([c.lower() for c in classes]))
        .group_by(Students.yrgrp)
        .order_by(Students.yrgrp)
        .all()
    )

    # Turn into a tidy list of dicts
    subjects = ("eng", "maths", "sci")

    def _rfloat(m, k, dp=1):
        v = m.get(k)
        return round(float(v), dp) if v is not None else 0.0

    def _rint(m, k):
        v = m.get(k)
        return int(v) if v is not None else 0

    def _row_to_dict(m):
        out = {"class": (m.get("class") or "").upper()}
        n_values = []
        for s in subjects:
            out[f"{s}_avg"] = _rfloat(m, f"{s}_avg")
            # out[f"{s}_n"]   = _rint(m, f"{s}_n")
            n = _rint(m, f"{s}_n")
            out[f"{s}_n"] = n
            out[f"{s}60_pass"] = _rint(m, f"{s}60_pass")
            out[f"{s}70_pass"] = _rint(m, f"{s}70_pass")
            out[f"{s}60_pct"]  = _rfloat(m, f"{s}60_pct")
            out[f"{s}70_pct"]  = _rfloat(m, f"{s}70_pct")
            n_values.append(n)

        # Derive a single class_n
        # Prefer the first non-zero (common when all subjects share same cohort size);
        # otherwise fall back to max; otherwise 0.
        class_n = next((n for n in n_values if n), (max(n_values) if n_values else 0))
        out["class_n"] = class_n

        return out

    class_stats = [_row_to_dict(rec._mapping) for rec in per_class]

    # Cohort average attainment (E/M/S) ≥60 & ≥70
    def _cohort_exprs(thr60=60, thr70=70):
        """Return labeled expressions for all subjects (avg, n, ≥60/≥70 counts, %)."""
        def cols(col, pfx):
            n     = func.count(col).label(f"{pfx}_n")
            ge60  = func.sum(case((col >= thr60, 1), else_=0)).label(f"{pfx}60_pass")
            ge70  = func.sum(case((col >= thr70, 1), else_=0)).label(f"{pfx}70_pass")
            avg   = func.avg(col).label(f"{pfx}_avg")
            pct60 = ((ge60 * 100.0) / func.nullif(n, 0)).label(f"{pfx}60_pct")
            pct70 = ((ge70 * 100.0) / func.nullif(n, 0)).label(f"{pfx}70_pct")
            return [avg, n, ge60, ge70, pct60, pct70]

        return [
            *cols(InternalExam.eng_currPct,   "eng"),
            *cols(InternalExam.maths_currPct, "maths"),
            *cols(InternalExam.sci_currPct,   "sci"),
        ]

    def build_cohort_stats(classes, thr60=60, thr70=70):
        row = (
            db.session.query(*_cohort_exprs(thr60, thr70))
            .join(Students, Students.student_id == InternalExam.student_id)
            .filter(yrgrp_norm.in_([c.lower() for c in classes]))
            .one()
        )
        m = row._mapping

        def rfloat(k, dp=1): 
            v = m.get(k)
            return round(float(v), dp) if v is not None else 0.0

        def rint(k): 
            v = m.get(k)
            return int(v) if v is not None else 0

        # Fill using a single loop; keys match your existing schema exactly
        cohort_stats = {"class": "Cohort"}

        for s in subjects:
            n = rint(f"{s}_n")  # read once
            cohort_stats[f"{s}Co_avg"]   = rfloat(f"{s}_avg")
            cohort_stats[f"{s}Co_n"]     = n
            cohort_stats[f"{s}C60_pass"] = rint(f"{s}60_pass")
            cohort_stats[f"{s}C70_pass"] = rint(f"{s}70_pass")
            cohort_stats[f"{s}C60_pct"]  = rfloat(f"{s}60_pct")
            cohort_stats[f"{s}C70_pct"]  = rfloat(f"{s}70_pct")

        cohort_stats["cohort_n"] = n # all subjects have the same n
        return cohort_stats
 
    cohort_stats = build_cohort_stats(classes, thr60, thr70)

    cohort_progress_list = [
        cohort_progress(getattr(InternalExam, f"{subj}_progcat"))
        for subj in subjects
    ]

    engCo, mathsCo, sciCo = cohort_progress_list

    (eng_total, eng_cnt_exp_above, eng_cnt_above_only,
    eng_pct_exp_above, eng_pct_above_only) = engCo

    (maths_total, maths_cnt_exp_above, maths_cnt_above_only,
    maths_pct_exp_above, maths_pct_above_only) = mathsCo

    (sci_total, sci_cnt_exp_above, sci_cnt_above_only,
    sci_pct_exp_above, sci_pct_above_only) = sciCo

    # --- Single-chart payload ---
    yrgrp_payload = {
        "cohort_progress": [
            {"subject": "English", 
             "cohort_n": eng_total,
             "engCnt_exp_above": eng_cnt_exp_above,
             "engCnt_above_only": eng_cnt_above_only,
             "engPct_exp_above": eng_pct_exp_above,  
             "engPct_above_only": eng_pct_above_only},
            {"subject": "Maths",   
             "cohort_n": maths_total, 
             "mathsCnt_exp_above": maths_cnt_exp_above, 
             "mathsCnt_above_only": maths_cnt_above_only, 
             "mathsPct_exp_above": maths_pct_exp_above, 
             "mathsPct_above_only": maths_pct_above_only},
            {"subject": "Science", 
             "cohort_n": sci_total, 
             "sciCnt_exp_above": sci_cnt_exp_above, 
             "sciCnt_above_only": sci_cnt_above_only, 
             "sciPct_exp_above": sci_pct_exp_above,   
             "sciPct_above_only": sci_pct_above_only},
        ],
        "thr60": thr60, "thr70": thr70,
        "subjects": ["English", "Maths", "Science"],
        "by_class": class_stats + [cohort_stats],
        # traces: one per class + cohort
        "traces": [
            {"name": cls.upper(),
             "y": [by_class[cls]["eng"], by_class[cls]["maths"], by_class[cls]["sci"]],
             "type": "bar"
            } for cls in class_labels
        ] + [{
            "name": "Cohort",
            "y": [cohort["eng"], cohort["maths"], cohort["sci"]],
            "type": "bar",
            "isCohort": True  # hint for styling on the frontend
        }],
        "meta": {
            "year": target_year,
            "notes": "Averages (0–100), rounded to 1 dp."
        }
    }

    return jsonify(yrgrp_payload)