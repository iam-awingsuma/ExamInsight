# imports Flask's routing modularizer
from flask import Blueprint

blueprint = Blueprint(
    # blueprint for apps/authentication
    'auth_blueprint',
    # points to current module for locating assets and templates
    __name__,
    # base URL path prefix (empty string keeps routes at the root level)
    url_prefix=''
)