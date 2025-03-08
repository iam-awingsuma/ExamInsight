from flask import Blueprint

blueprint = Blueprint(
    # blueprint for apps/home
    'home_blueprint',
    __name__,
    url_prefix=''
)