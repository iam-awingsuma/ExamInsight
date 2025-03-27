import os
import pandas as pd
from apps.home import blueprint
from flask import render_template, request, redirect, url_for, request, flash, get_flashed_messages, session, Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from jinja2 import TemplateNotFound
from flask_login import login_required, current_user
from apps import db
from sqlalchemy.exc import IntegrityError

from apps.authentication.models import NGRTB
from apps.authentication.models import Students

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
@blueprint.route('/display_ngrtb')
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


# define a new route for templates/pages/internalexam_m.html
@blueprint.route('/intlexam_m')
def intlexam_m():
    return render_template('pages/intlexam_m.html', segment='internal assessment (midterm)', parent='intAssmnt')

# define a new route for templates/pages/internalexam_f.html
@blueprint.route('/intlexam_f')
def intlexam_f():
    return render_template('pages/intlexam_f.html', segment='internal assessment (final)', parent='intAssmnt')

# define a new route for templates/pages/display_ngrta.html
@blueprint.route('/display_ngrta')
def display_ngrta():
    return render_template('pages/display_ngrta.html', segment='external data - NGRT (Form-A)', parent='extBTest')

# define a new route for templates/pages/display_ngrtc.html
@blueprint.route('/display_ngrtc')
def display_ngrtc():
    return render_template('pages/display_ngrtc.html', segment='external data - NGRT (Form-C)', parent='extBTest')

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