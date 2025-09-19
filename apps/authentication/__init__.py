
from flask import Blueprint, app

blueprint = Blueprint(
    # blueprint for apps/authentication
    'auth_blueprint',
    __name__,
    url_prefix=''
)

from apps.home import blueprint as home_blueprint
app.register_blueprint(home_blueprint)