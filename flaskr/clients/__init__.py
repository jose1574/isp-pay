from flask import Blueprint

clients_bp = Blueprint('clients', __name__, template_folder='templates')

from . import routes