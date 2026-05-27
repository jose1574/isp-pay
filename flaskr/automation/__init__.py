from flask import Blueprint

automation_bp = Blueprint('automation', __name__, template_folder='templates')

from . import routes
