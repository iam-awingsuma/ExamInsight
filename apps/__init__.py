import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module

db = SQLAlchemy()
login_manager = LoginManager()

from flask_login import (
    current_user,
    login_user,
    logout_user
)

from apps import db, login_manager
from apps.authentication import blueprint
from apps.authentication.forms import LoginForm, CreateAccountForm
from apps.authentication.models import Users
from apps.config import Config

from apps.authentication.util import verify_pass


def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)

def register_blueprints(app):
    for module_name in ('authentication', 'home'):
        try:
            module = import_module(f'apps.{module_name}.routes')
            app.register_blueprint(module.blueprint)
            print(f"Registered blueprint: { module_name }")
        except Exception as e:
            print(f"Error registering blueprint: { module_name }: {e}")


def create_app(config):

    # Contextual
    static_prefix = '/static'
    templates_dir = os.path.dirname(config.BASE_DIR)

    TEMPLATES_FOLDER = os.path.join(templates_dir,'templates')
    STATIC_FOLDER = os.path.join(templates_dir,'static')

    app = Flask(__name__, static_url_path=static_prefix, template_folder=TEMPLATES_FOLDER, static_folder=STATIC_FOLDER)
    app.secret_key = "your_secret_key"  # Required for session management

    app.config.from_object(config)
    register_extensions(app)
    register_blueprints(app)

    return app
