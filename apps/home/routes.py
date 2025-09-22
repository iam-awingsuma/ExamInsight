import os
import pandas as pd
from apps.home import blueprint
from flask import Flask, render_template, request, redirect, url_for, request, flash, get_flashed_messages, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from jinja2 import TemplateNotFound
from flask_login import login_required, current_user
from apps import db
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func

from apps.authentication.models import NGRTA
from apps.authentication.models import NGRTB
from apps.authentication.models import NGRTC
from apps.authentication.models import InternalExam
from apps.authentication.models import Students

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


# Define the upload folder & allowed extensions
UPLOAD_FOLDER = 'static/assets/images/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Helper function to check file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    ngrta_data = NGRTA.query.all()  # Fetch all entries from NGRTA table
    # student_data = Students.query.all()  # Fetch all entries from Students table  
    student_data = Students.query.order_by(Students.yrgrp, Students.forename).all()
    
    # Check if either table is empty
    ngrta_empty = not ngrta_data  # True if NGRTA is empty
    students_empty = not student_data  # True if Students is empty
    
    # If both tables are empty
    if ngrta_empty and students_empty:
        return render_template(
            'pages/display_ngrta.html',
            segment='external data - NGRT (Form-A)',
            parent='extBTest',
            no_data=True,
            ngrta_data=None,
            student_data=None,
            msg_ngrta='No NGRT-A data available.',
            msg_students='No student data available.'
        )
    # If only NGRTA is empty
    elif ngrta_empty:
        return render_template(
            'pages/display_ngrta.html',
            segment='external data - NGRT (Form-A)',
            parent='extBTest',
            no_data=True,
            msg_ngrta='No NGRT-A data available.',
            student_data=student_data,
            ngrta_data=None
        )
    # If only Students is empty
    elif students_empty:
        return render_template(
            'pages/display_ngrta.html',
            segment='external data - NGRT (Form-A)',
            parent='extBTest',
            no_data=True,
            msg_students='No student data available.',
            ngrta_data=ngrta_data,
            student_data=None
        )
    # If both tables have data
    else:
        combined_data = db.session.query(Students, NGRTA).join(Students, NGRTA.student_id == Students.student_id).order_by(Students.yrgrp, Students.forename).all()
        return render_template(
            'pages/display_ngrta.html',
            segment='external data - NGRT (Form-A)',
            parent='extBTest',
            no_data=False,
            combined_data=combined_data
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
    ngrtb_data = NGRTB.query.all()  # Fetch all entries from NGRTB table
    # student_data = Students.query.all()  # Fetch all entries from Students table  
    student_data = Students.query.order_by(Students.yrgrp, Students.forename).all()
    
    # Check if either table is empty
    ngrtb_empty = not ngrtb_data  # True if NGRTB is empty
    students_empty = not student_data  # True if Students is empty
    
    # If both tables are empty
    if ngrtb_empty and students_empty:
        return render_template(
            'pages/display_ngrtb.html',
            segment='external data - NGRT (Form-B)',
            parent='extBTest',
            no_data=True,
            ngrtb_data=None,
            student_data=None,
            msg_ngrtb='No NGRT-B data available.',
            msg_students='No student data available.'
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
            ngrtb_data=None
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
            student_data=None
        )
    # If both tables have data
    else:
        combined_data = db.session.query(Students, NGRTB).join(Students, NGRTB.student_id == Students.student_id).order_by(Students.yrgrp, Students.forename).all()
        return render_template(
            'pages/display_ngrtb.html',
            segment='external data - NGRT (Form-B)',
            parent='extBTest',
            no_data=False,
            combined_data=combined_data
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
    ngrtc_data = NGRTC.query.all()  # Fetch all entries from NGRTC table
    # student_data = Students.query.all()  # Fetch all entries from Students table  
    student_data = Students.query.order_by(Students.yrgrp, Students.forename).all()
    
    # Check if either table is empty
    ngrtc_empty = not ngrtc_data  # True if NGRTC is empty
    students_empty = not student_data  # True if Students is empty
    
    # If both tables are empty
    if ngrtc_empty and students_empty:
        return render_template(
            'pages/display_ngrtc.html',
            segment='external data - NGRT (Form-C)',
            parent='extBTest',
            no_data=True,
            ngrtc_data=None,
            student_data=None,
            msg_ngrtc='No NGRT-C data available.',
            msg_students='No student data available.'
        )
    # If only NGRTC is empty
    elif ngrtc_empty:
        return render_template(
            'pages/display_ngrtc.html',
            segment='external data - NGRT (Form-C)',
            parent='extBTest',
            no_data=True,
            msg_ngrtc='No NGRT-C data available.',
            student_data=student_data,
            ngrtc_data=None
        )
    # If only Students is empty
    elif students_empty:
        return render_template(
            'pages/display_ngrtc.html',
            segment='external data - NGRT (Form-C)',
            parent='extBTest',
            no_data=True,
            msg_students='No student data available.',
            ngrtc_data=ngrtc_data,
            student_data=None
        )
    # If both tables have data
    else:
        combined_data = db.session.query(Students, NGRTC).join(Students, NGRTC.student_id == Students.student_id).order_by(Students.yrgrp, Students.forename).all()
        return render_template(
            'pages/display_ngrtc.html',
            segment='external data - NGRT (Form-C)',
            parent='extBTest',
            no_data=False,
            combined_data=combined_data
        )

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
    intlexam_data = InternalExam.query.all()  # Fetch all entries from internal_exam table
    # Fetch all entries from Students table  
    student_data = Students.query.order_by(Students.yrgrp, Students.forename).all()
    
    # Check if either table is empty
    intlexam_empty = not intlexam_data  # True if internalexam is empty
    students_empty = not student_data  # True if Students is empty
    
    # If both tables are empty
    if intlexam_empty and students_empty:
        return render_template(
            'pages/intlexam.html',
            segment='internal assessment (final term)',
            parent='intAssmnt',
            no_data=True,
            intlexam_data=None,
            student_data=None,
            msg_intlexam='No Internal Exam data available.',
            msg_students='No student data available.'
        )
    # If only internalexam is empty
    elif intlexam_empty:
        return render_template(
            'pages/intlexam.html',
            segment='internal assessment (final term)',
            parent='intAssmnt',
            no_data=True,
            msg_intlexam='No Internal Exam data available.',
            student_data=student_data,
            intlexam_data=None
        )
    # If only Students is empty
    elif students_empty:
        return render_template(
            'pages/intlexam.html',
            segment='internal assessment (final term)',
            parent='intAssmnt',
            no_data=True,
            msg_students='No student data available.',
            intlexam_data=intlexam_data,
            student_data=None
        )
    # If both tables have data
    else:
        combined_data = db.session.query(Students, InternalExam).join(Students, InternalExam.student_id == Students.student_id).order_by(Students.yrgrp, Students.forename).all()
        return render_template(
            'pages/intlexam.html',
            segment='internal assessment (final term)',
            parent='intAssmnt',
            no_data=False,
            combined_data=combined_data
        )


# # Student Management Routes
# @blueprint.route('/student_management', methods=['GET'])
# def student_management():
#     # Fetch all entries from Students table  
#     students = Students.query.order_by(Students.yrgrp, Students.forename).all()
    
#     # Check if students table is empty
#     students_empty = not students  # True if Students is empty

#     # For filter dropdowns
#     genders = [g[0] for g in db.session.query(Students.gender).distinct().order_by(Students.gender).all()]
#     yrgrps   = [y[0] for y in db.session.query(Students.yrgrp).distinct().order_by(Students.yrgrp).all()]
#     regstat  = [r[0] for r in db.session.query(Students.status).distinct().order_by(Students.status).all()]



#     # If students table is empty
#     if students_empty:
#         return render_template(
#             'pages/students-all.html',
#             segment='student management',
#             parent='studentMgt',
#             no_data=True,
#             students=None,
#             msg_students='No student data available.'
#         )
#     else:
#         return render_template(
#             'pages/students-all.html',
#             segment='student management',
#             parent='studentMgt',
#             no_data=False,
#             students=students,
#             genders=genders,
#             yrgrps=yrgrps,
#             regstat=regstat
#         )

# Student Management Routes
@blueprint.route("/student_management", methods=["GET"])
def student_management():
    # ---- Read query params (empty string = no filter) ----
    q        = request.args.get("q", "", type=str).strip()
    gender   = request.args.get("gender", "", type=str).strip()
    yrgrp    = request.args.get("yrgrp", "", type=str).strip()
    # nat      = request.args.get("nat", "", type=str).strip()      # nationality
    status   = request.args.get("status", "", type=str).strip()     # optional (regstat)

    # ---- Build the query incrementally ----
    query = Students.query

    if q:
        like = f"%{q}%"
        # adjust fields you want searchable
        query = query.filter(
            db.or_(
                Students.forename.ilike(like),
                Students.surname.ilike(like),
                Students.student_id.cast(db.String).ilike(like),
            )
        )
    if gender:
        query = query.filter(Students.gender == gender)

    if yrgrp:
        query = query.filter(Students.yrgrp == yrgrp)

    if status:
        query = query.filter(Students.status == status)

    # ---- Order & fetch ----
    students = query.order_by(Students.yrgrp, Students.forename).all()

    # ---- For dropdown options (distinct values) ----
    genders = [g[0] for g in db.session.query(Students.gender).distinct().order_by(Students.gender)]
    yrgrps  = [y[0] for y in db.session.query(Students.yrgrp).distinct().order_by(Students.yrgrp)]
    regstat = [r[0] for r in db.session.query(Students.status).distinct().order_by(Students.status)]

    # ---- Flags / active chips ----
    table_is_empty   = Students.query.count() == 0           # database has no students at all
    filtered_is_empty = (len(students) == 0 and not table_is_empty)

    active_filters = []
    base_args = request.args.to_dict()

    def build_remove_url(key):
        args = base_args.copy()
        args.pop(key, None)
        return url_for("home_blueprint.student_management") + "?" + urlencode(args)

    if q:        active_filters.append(("Search", q, build_remove_url("q")))
    if gender:   active_filters.append(("Gender", gender, build_remove_url("gender")))
    if yrgrp:    active_filters.append(("Year", yrgrp, build_remove_url("yrgrp")))
    if status:   active_filters.append(("Status", status, build_remove_url("status")))

    return render_template(
        "pages/students-all.html",
        segment="student management",
        parent="studentMgt",
        no_data=table_is_empty,
        students=students,
        # dropdown data
        genders=genders,
        yrgrps=yrgrps,
        regstat=regstat,
        # current selections (so selects stay selected)
        q=q, gender=gender, yrgrp=yrgrp, status=status,
        # ui helpers
        filtered_is_empty=filtered_is_empty,
        active_filters=active_filters,
    )


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