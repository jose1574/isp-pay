from flask import Blueprint

config_bp = Blueprint('config', __name__, template_folder='templates')

from . import routes