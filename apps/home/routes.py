import os
from apps.home import blueprint
from flask import render_template, request, redirect, url_for, request, flash
from werkzeug.utils import secure_filename
from jinja2 import TemplateNotFound
from flask_login import login_required, current_user
from apps import db

from flask_login import (
    current_user,
    login_user,
    logout_user
)

from apps.authentication.forms import CreateAccountForm
from apps.authentication.models import Users

@blueprint.route('/')
@blueprint.route('/index')
@login_required
def index():
    # return render_template('pages/index.html', segment='dashboard', parent="dashboard")
    return render_template('pages/index.html', segment='dashboard')

# define a new route for templates/pages/tables.html
@blueprint.route('/tables')
def tables():
    return render_template('pages/tables.html', segment='tables')

@blueprint.route('/all-users')
def allusers():
    return render_template('pages/users-all.html', segment='all users', parent='users')

@blueprint.route('/add-users', methods=['GET', 'POST'])
def addusers():
    # return render_template('pages/users-add.html', segment='add users', parent='users')
    create_account_form = CreateAccountForm(request.form)
    if 'addusers' in request.form:

        username = request.form['username']
        email = request.form['email']
        # designation = request.form['designation']

        # Check if username already exists
        user = Users.query.filter_by(username=username).first()
        if user:
            # return render_template('authentication/register.html',
            return render_template('pages/users-add.html',
                                   segment='add users',
                                   parent='users',
                                   msg='Username already registered.',
                                   success=False,
                                   form=create_account_form)

        # Check email exists
        user = Users.query.filter_by(email=email).first()
        if user:
            return render_template('pages/users-add.html',
                                   segment='add users',
                                   parent='users',
                                   msg='E-mail already registered.',
                                   success=False,
                                   form=create_account_form)

        # else we can create the user
        user = Users(**request.form)
        db.session.add(user)
        db.session.commit()

        # Delete user from session
        # logout_user()

        return render_template('pages/users-add.html',
                               segment='add users',
                               parent='users',
                               msg='User created successfully.',
                               success=True,
                               form=create_account_form)

    else:
        return render_template('pages/users-add.html', segment='add users', parent='users', form=create_account_form)

@blueprint.route('/rp-users')
def rpusers():
    return render_template('pages/users-rp.html', segment='roles and permissions', parent='users')

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

# @blueprint.route('/profile', methods=['GET', 'POST'])
# def profile():
#     if request.method == 'POST':
#         first_name = request.form.get('first_name')
#         last_name = request.form.get('last_name')
#         designation = request.form.get('designation')
#         address = request.form.get('address')

#         current_user.first_name = first_name
#         current_user.last_name = last_name
#         current_user.designation = designation
#         current_user.address = address

#         try:
#             db.session.commit()
#         except Exception as e:
#             db.session.rollback()

#         return redirect(url_for('home_blueprint.profile'))

#     return render_template('pages/profile.html', segment='profile')


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
