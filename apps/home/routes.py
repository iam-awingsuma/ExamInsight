import os
from apps.home import blueprint
from flask import render_template, request, redirect, url_for, request, flash, get_flashed_messages
from werkzeug.utils import secure_filename
from jinja2 import TemplateNotFound
from flask_login import login_required, current_user
from apps import db

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


# Role-based access control decorator
# def admin_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if not current_user.is_authenticated or not current_user.is_admin:
#             flash('Admin access required.', 'error')
#             return redirect(url_for('authentication_blueprint.login'))
#         return f(*args, **kwargs)
#     return decorated_function


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
    users = Users.query.all()  # Fetch all users from the database
    return render_template('pages/users-all.html', users=users, segment='all users', parent='users')

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
        
        # Create user data dictionary from form
        # user_data = {
        #     'username': request.form['username'],
        #     'email': request.form['email'],
        #     'password': request.form['password'],
        #     'is_admin': False  # Default to regular user
        # }

        # Check if this is the first user (make them admin)
        if Users.query.count() == 0:
            user['is_admin'] = True

        # else we can create the user
        user = Users(**request.form)
        db.session.add(user)
        db.session.commit()

        return render_template('pages/users-add.html',
                               segment='add users',
                               parent='users',
                               msg='User created successfully.',
                               success=True,
                               form=create_account_form)

    else:
        return render_template('pages/users-add.html', segment='add users', parent='users', form=create_account_form)


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
