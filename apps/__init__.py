import os # System files and OS utilities
import pandas as pd # Data processing and tabular data analysis

from flask import Flask  # Core Web framework for route handling and application context
from flask_login import LoginManager  # Manages user authentication and session states
from flask_sqlalchemy import SQLAlchemy  # Object-Relational Mapper (ORM) for database interactions
from importlib import import_module  # Dynamic module importer used for loading routes/blueprints

# added to configure the Docker container / images
from pathlib import Path

db = SQLAlchemy() # Initialize the SQLAlchemy database instance for ORM functionality
login_manager = LoginManager() # Initialize the Flask-Login manager for handling user sessions and authentication

# Flask-Login configuration
from flask_login import (
    current_user,
    login_user,
    logout_user
)

from apps import db, login_manager # Importing the database and login manager instances for user session management
from apps.authentication import blueprint # Importing the authentication blueprint for user-related routes and views
from apps.authentication.forms import LoginForm, CreateAccountForm # Importing form classes for user login and account creation
from apps.authentication.models import Users # Importing the Users model for database interactions related to user accounts
from apps.config import Config # Importing the configuration class for application settings and environment variables

# Flask-Login user loader callback
from apps.authentication.util import verify_pass

# Flask-Login user loader callback function 
# to retrieve a user by their ID from the database
def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)

# Function to register blueprints for modular route handling
def register_blueprints(app):
    for module_name in ('authentication', 'home'):
        try:
            module = import_module(f'apps.{module_name}.routes')
            app.register_blueprint(module.blueprint)
            print(f"Registered blueprint: { module_name }")
        except Exception as e:
            print(f"Error registering blueprint: { module_name }: {e}")

# Function to create and configure the Flask application instance
def create_app(config):
    static_prefix = '/static'

    # Get the project root directory (/ExamInsight inside the container)
    # Using Path(__file__).resolve().parent.parent reliably points to the project root
    project_root = Path(__file__).resolve().parent.parent

    # Define paths for templates and static files relative to the project root
    TEMPLATES_FOLDER = project_root / "templates"
    STATIC_FOLDER = project_root / "static"

    # Create the Flask application instance with specified static and template folders
    app = Flask(
        __name__,
        static_url_path=static_prefix,
        template_folder=str(TEMPLATES_FOLDER),
        static_folder=str(STATIC_FOLDER)
    )
    app.secret_key = "your_secret_key" # Set a secret key for session management and security features

    # Load configuration settings from the provided config object
    app.config.from_object(config)
    register_extensions(app)
    register_blueprints(app)

    # Set the login view for Flask-Login to redirect unauthenticated users
    return app