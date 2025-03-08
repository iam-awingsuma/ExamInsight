
from flask import Blueprint

blueprint = Blueprint(
    # blueprint for apps/authentication
    'auth_blueprint',
    __name__,
    url_prefix=''
)