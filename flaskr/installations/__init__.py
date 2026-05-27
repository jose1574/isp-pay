from flask import Blueprint

installations_bp = Blueprint('installations', __name__, template_folder='templates')

from . import routes