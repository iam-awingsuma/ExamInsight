
# Flask core utilities for routing, rendering, and requests
from flask import render_template, redirect, request, url_for, flash, abort, Flask
# Flask-Login utilities for user session management
from flask_login import (
    current_user,
    login_user,
    logout_user
)
from functools import wraps # Python standard library for function decorators
from apps import db, login_manager # Core database instance and login manager extensions
from apps.authentication import blueprint # Authentication module blueprint definition
from apps.authentication.forms import LoginForm # Form validation class for user login
from apps.authentication.models import Users # Database model representing registered users
from apps.config import Config # Application environment and setup configurations

from apps.authentication.util import verify_pass # Password verification utility function

# Role-based access control decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('auth_blueprint.login'))
        return f(*args, **kwargs)
    return decorated_function


# Login & Registration
@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(request.form)
    if 'login' in request.form:

        # read form data
        user_id  = request.form['username'] # we can have here username OR email
        password = request.form['password']

        # Locate user
        user = Users.find_by_username(user_id)

        # if user not found
        if not user:
            user = Users.find_by_email(user_id)
            if not user:
                return render_template( 'authentication/login.html',
                                       msg='Unknown User or Email', form=login_form)

        # Check the password
        if verify_pass(password, user.password):
            login_user(user)
            # return redirect(url_for('home_blueprint.index'))
        
            # Redirect based on user role
            if user.is_admin:
                # redirect to index.html with user management access
                return redirect(url_for('home_blueprint.index'))
            else:
                # redirect to index.html without user management acess
                return redirect(url_for('home_blueprint.index'))

        # Something (user or pass) is not ok
        return render_template('authentication/login.html',
                               msg='Wrong username or password', form=login_form)
    # If user is not authenticated, show login page
    if not current_user.is_authenticated:
        return render_template('authentication/login.html', form=login_form)
    
    # Redirect based on user role when already logged in
    if current_user.is_admin:
        return redirect(url_for('home_blueprint.index'))
    
    return redirect(url_for('home_blueprint.index'))

# Logout route to handle user logout and session termination
@blueprint.route('/logout')
def logout():
    logout_user()
    return redirect('/login')

# Redirect users to the login page when they attempt to access protected routes without authentication
@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect('/login')
